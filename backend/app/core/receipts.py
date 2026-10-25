"""
Read a receipt or invoice with the shared LLM and turn it into an expense draft
The draft is never saved here: the Finance page shows it to the user, who books it through `POST /finance/expense`.
"""
import base64
from datetime import date
from typing import Literal, get_args

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError, ValidationInfo, field_validator

from app.ai_service import llm
from app.core.uploads import IMAGE_TYPES, LoadedAttachment, extract_pdf_text
from app.core.util_store import load_prompt
from app.models.finance import ExpenseCategory, ExpenseType

EXPENSE_TYPES = ', '.join(member.value for member in ExpenseType)
EXPENSE_CATEGORIES = ', '.join(get_args(ExpenseCategory))
CONFIDENCE_LEVELS = ('high', 'medium', 'low')
RECEIPT_PROMPT = load_prompt('receipt_extract_prompt.md')


class ReceiptDraft(BaseModel):
    vendor: str | None = None
    reference: str | None = None  # invoice / receipt number as printed
    amount: float | None = None  # grand total charged
    currency: str | None = None  # ISO code, display only, never stored
    expense_date: str | None = None  # YYYY-MM-DD
    due_date: str | None = None  # YYYY-MM-DD
    paid: bool | None = None  # True when the document shows the payment was made (till receipt, card line, PAID stamp), False for an invoice awaiting payment
    expense_type: ExpenseType | None = None
    category: ExpenseCategory | None = None
    description: str | None = None
    project_name: str | None = None  # one of the names handed to the model, or None
    confidence: Literal['high', 'medium', 'low'] = 'low'
    notes: str | None = None  # what was unreadable or assumed

    @field_validator('amount', mode='before')
    @classmethod
    def plain_number(cls, value: object) -> object:
        """
        Accept an amount the model wrote with a currency symbol or thousands separators, such as "$1,340.00"
        Args:
            value: Raw value from the model

        Returns:
            The value with symbols and separators stripped when it is a string, otherwise unchanged
        """
        if isinstance(value, str):
            return value.strip().lstrip('$€£¥').replace(',', '').strip() or None
        return value

    @field_validator('expense_type', 'category', mode='before')
    @classmethod
    def known_value_or_none(cls, value: object, info: ValidationInfo) -> str | None:
        """
        Lower-case a type or category and drop it when it is not an allowed value, so a small model writing "Cloud" does not fail the whole draft
        Args:
            value: Raw value from the model
            info: Pydantic field info, names the field being validated

        Returns:
            The allowed value, or None
        """
        if not isinstance(value, str):
            return None
        allowed = [member.value for member in ExpenseType] if info.field_name == 'expense_type' else get_args(ExpenseCategory)
        cleaned = value.strip().lower().replace(' ', '_')
        return cleaned if cleaned in allowed else None

    @field_validator('confidence', mode='before')
    @classmethod
    def known_confidence(cls, value: object) -> str:
        """
        Lower-case the confidence and fall back to `low` for anything unexpected
        Args:
            value: Raw value from the model

        Returns:
            One of `CONFIDENCE_LEVELS`
        """
        cleaned = value.strip().lower() if isinstance(value, str) else ''
        return cleaned if cleaned in CONFIDENCE_LEVELS else 'low'

    @field_validator('expense_date', 'due_date', mode='before')
    @classmethod
    def iso_date_or_none(cls, value: object) -> str | None:
        """
        Keep a date only when it parses as ISO; a date the model wrote in another format is dropped rather than failing the whole draft
        Args:
            value: Raw value from the model

        Returns:
            The ISO date string, or None
        """
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return date.fromisoformat(value.strip()[:10]).isoformat()
        except ValueError:
            return None


async def extract_receipt(attachment: LoadedAttachment, project_names: list[str]) -> ReceiptDraft:
    """
    Ask the shared LLM to read one receipt into a `ReceiptDraft`
    Args:
        attachment: Stored upload, an image or a PDF (`load_attachment`)
        project_names: Names of the dev projects the draft may link to

    Returns:
        The draft, unreadable fields left None

    Raises:
        ValueError: A PDF without a text layer (a scan), or the model did not return a usable draft
    """
    context = f'<context>\ntoday: {date.today().isoformat()}\nexpense_types: {EXPENSE_TYPES}\ncategories: {EXPENSE_CATEGORIES}\nprojects: {", ".join(project_names) or "(none)"}\n</context>'
    if attachment.content_type in IMAGE_TYPES:
        content = [{'type': 'text', 'text': 'Read this receipt.'}, {'type': 'image', 'base64': base64.b64encode(attachment.data).decode(), 'mime_type': attachment.content_type}]
    else:
        text = extract_pdf_text(attachment.data)
        if not text:
            raise ValueError('This PDF has no text layer, upload an image of it instead')
        content = [{'type': 'text', 'text': f'Read this receipt.\n<attachment type="{attachment.content_type}">\n{text}\n</attachment>'}]
    messages = [SystemMessage(content=RECEIPT_PROMPT + '\n\n' + context), HumanMessage(content=content)]
    # JSON-schema mode instead of tool calling: local vision models rarely support tools, and litellm maps it to the server's JSON/grammar mode. Not strict, because strict schemas refuse optional fields
    structured_llm = llm.with_structured_output(ReceiptDraft, method='json_schema', strict=False)
    try:
        draft = await structured_llm.ainvoke(messages)
    except (OutputParserException, ValidationError):
        # Provider errors (connection, auth, timeout) propagate to the caller as they are
        raise ValueError('The model did not return a usable draft')
    return draft
