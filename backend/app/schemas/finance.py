from datetime import date
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from decimal import Decimal

# GL Account
class GLAccountBase(BaseModel):
    code: str
    name: str
    type: str  # asset, liability, equity, revenue, expense
    description: Optional[str] = None

class GLAccountCreate(GLAccountBase):
    pass

class GLAccountUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None

class GLAccountResponse(GLAccountBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Journal Line
class JournalLineBase(BaseModel):
    gl_account_id: int
    debit: Decimal = Field(default=Decimal("0.0"))
    credit: Decimal = Field(default=Decimal("0.0"))

class JournalLineCreate(JournalLineBase):
    pass

class JournalLineResponse(JournalLineBase):
    id: int
    journal_entry_id: int
    model_config = ConfigDict(from_attributes=True)

# Journal Entry
class JournalEntryBase(BaseModel):
    entry_date: date
    description: str
    status: str = "draft"

class JournalEntryCreate(JournalEntryBase):
    lines: List[JournalLineCreate]

class JournalEntryUpdate(BaseModel):
    entry_date: Optional[date] = None
    description: Optional[str] = None
    status: Optional[str] = None
    lines: Optional[List[JournalLineCreate]] = None  # replaces all lines when provided

class JournalEntryResponse(JournalEntryBase):
    id: int
    lines: List[JournalLineResponse]
    model_config = ConfigDict(from_attributes=True)

# Invoice Line
class InvoiceLineBase(BaseModel):
    description: str
    quantity: Decimal = Field(default=Decimal("1.0"))
    unit_price: Decimal = Field(default=Decimal("0.0"))
    tax_rate: Decimal = Field(default=Decimal("0.0"))

class InvoiceLineCreate(InvoiceLineBase):
    pass

class InvoiceLineResponse(InvoiceLineBase):
    id: int
    invoice_id: int
    amount: Decimal
    model_config = ConfigDict(from_attributes=True)

# Invoice
class InvoiceBase(BaseModel):
    invoice_number: str
    partner_name: str
    invoice_type: str  # customer, vendor
    issue_date: date
    due_date: date
    status: str = "draft"

class InvoiceCreate(InvoiceBase):
    lines: List[InvoiceLineCreate]

class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    partner_name: Optional[str] = None
    invoice_type: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    lines: Optional[List[InvoiceLineCreate]] = None  # replaces all lines when provided

class InvoiceResponse(InvoiceBase):
    id: int
    total_amount: Decimal
    tax_amount: Decimal
    lines: List[InvoiceLineResponse]
    model_config = ConfigDict(from_attributes=True)

# Fixed Asset
class FixedAssetBase(BaseModel):
    name: str
    asset_code: str
    category: str
    acquisition_date: date
    cost: Decimal
    depreciation_method: str = "straight_line"
    current_value: Decimal
    status: str = "active"

class FixedAssetCreate(FixedAssetBase):
    pass

class FixedAssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_code: Optional[str] = None
    category: Optional[str] = None
    acquisition_date: Optional[date] = None
    cost: Optional[Decimal] = None
    depreciation_method: Optional[str] = None
    current_value: Optional[Decimal] = None
    status: Optional[str] = None

class FixedAssetResponse(FixedAssetBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Payment
PaymentCategory = Literal[
    "procurement", "salary", "rent", "utilities", "tax",
    "subscription", "travel", "loan_repayment", "other",
]

class PaymentBase(BaseModel):
    category: PaymentCategory = "procurement"  # default keeps legacy invoice-only payloads working
    invoice_id: Optional[int] = None       # procurement only (optional)
    employee_id: Optional[int] = None      # salary only (required)
    contract_number: Optional[str] = Field(default=None, max_length=100)  # rent only (required)
    payment_date: date
    amount: Decimal
    payment_method: str
    reference: Optional[str] = None  # TXN/cheque no., utility account, tax ref, ...

class PaymentCreate(PaymentBase):
    @model_validator(mode="after")
    def _check_category_refs(self):
        """Each category carries only its own reference field; mismatches are
        rejected rather than silently cleared."""
        if self.category == "salary":
            if self.employee_id is None:
                raise ValueError("salary payments require employee_id")
        elif self.employee_id is not None:
            raise ValueError("employee_id is only allowed on salary payments")
        if self.category == "rent":
            if not (self.contract_number and self.contract_number.strip()):
                raise ValueError("rent payments require contract_number")
        elif self.contract_number is not None:
            raise ValueError("contract_number is only allowed on rent payments")
        if self.category != "procurement" and self.invoice_id is not None:
            raise ValueError("invoice_id is only allowed on procurement payments")
        return self

class PaymentUpdate(BaseModel):
    # category and invoice_id intentionally not updatable — delete and re-record instead
    model_config = ConfigDict(extra="forbid")
    payment_date: Optional[date] = None
    amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    reference: Optional[str] = None
    employee_id: Optional[int] = None      # salary payments only — validated in endpoint
    contract_number: Optional[str] = None  # rent payments only — validated in endpoint

class PaymentResponse(PaymentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
