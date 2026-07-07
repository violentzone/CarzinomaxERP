from datetime import date
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal

# GL Account
class GLAccountBase(BaseModel):
    code: str
    name: str
    type: str  # asset, liability, equity, revenue, expense
    description: Optional[str] = None

class GLAccountCreate(GLAccountBase):
    pass

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

class FixedAssetResponse(FixedAssetBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Payment
class PaymentBase(BaseModel):
    invoice_id: int
    payment_date: date
    amount: Decimal
    payment_method: str
    reference: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class PaymentResponse(PaymentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
