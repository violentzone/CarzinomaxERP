from typing import Annotated, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from decimal import Decimal

from app.api.deps import get_db, RoleChecker
from app.models.finance import GLAccount, JournalEntry, JournalLine, Invoice, InvoiceLine, FixedAsset, Payment
from app.schemas.finance import (
    GLAccountCreate, GLAccountResponse,
    JournalEntryCreate, JournalEntryResponse,
    InvoiceCreate, InvoiceResponse,
    FixedAssetCreate, FixedAssetResponse,
    PaymentCreate, PaymentResponse,
)

# Protect all routes under finance with finance or admin role
router = APIRouter(dependencies=[Depends(RoleChecker(["finance", "admin"]))])

# --- GL Accounts ---
@router.post("/accounts", response_model=GLAccountResponse)
async def create_gl_account(
    db: Annotated[AsyncSession, Depends(get_db)],
    account_in: GLAccountCreate
) -> Any:
    """Create a new general ledger account.

    Args:
        db: The database session dependency.
        account_in: The GL account creation payload.

    Returns:
        Any: The created GLAccount database instance.

    Raises:
        HTTPException: If an account with the same code already exists.
    """
    result = await db.execute(select(GLAccount).filter(GLAccount.code == account_in.code))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GL Account with this code already exists."
        )
    
    db_account = GLAccount(**account_in.model_dump())
    db.add(db_account)
    await db.commit()
    await db.refresh(db_account)
    return db_account

@router.get("/accounts", response_model=List[GLAccountResponse])
async def list_gl_accounts(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100
) -> Any:
    """List general ledger accounts.

    Args:
        db: The database session dependency.
        skip: The number of records to skip (for pagination).
        limit: The maximum number of records to return.

    Returns:
        Any: A list of GLAccount database instances.
    """
    result = await db.execute(select(GLAccount).offset(skip).limit(limit))
    return result.scalars().all()

# --- Invoices ---
@router.post("/invoices", response_model=InvoiceResponse)
async def create_invoice(
    db: Annotated[AsyncSession, Depends(get_db)],
    invoice_in: InvoiceCreate
) -> Any:
    """Create a new customer/vendor invoice.

    Calculates tax and total amount based on the invoice lines.

    Args:
        db: The database session dependency.
        invoice_in: The invoice creation payload with lines.

    Returns:
        Any: The created Invoice database instance loaded with its lines.

    Raises:
        HTTPException: If an invoice with the same invoice number already exists.
    """
    result = await db.execute(select(Invoice).filter(Invoice.invoice_number == invoice_in.invoice_number))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice with this invoice number already exists."
        )
    
    # Calculate amounts
    total_amount = Decimal("0.0")
    tax_amount = Decimal("0.0")
    
    db_invoice = Invoice(
        invoice_number=invoice_in.invoice_number,
        partner_name=invoice_in.partner_name,
        invoice_type=invoice_in.invoice_type,
        issue_date=invoice_in.issue_date,
        due_date=invoice_in.due_date,
        status=invoice_in.status,
    )
    db.add(db_invoice)
    await db.flush()  # get invoice id
    
    for line in invoice_in.lines:
        line_qty = Decimal(str(line.quantity))
        line_price = Decimal(str(line.unit_price))
        line_tax_rate = Decimal(str(line.tax_rate))
        
        line_subtotal = line_qty * line_price
        line_tax = line_subtotal * (line_tax_rate / Decimal("100.0"))
        line_total = line_subtotal + line_tax
        
        total_amount += line_total
        tax_amount += line_tax
        
        db_line = InvoiceLine(
            invoice_id=db_invoice.id,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            tax_rate=line.tax_rate,
            amount=float(line_total),
        )
        db.add(db_line)
        
    db_invoice.total_amount = float(total_amount)
    db_invoice.tax_amount = float(tax_amount)
    
    await db.commit()
    
    # Reload with lines
    res = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.lines))
        .filter(Invoice.id == db_invoice.id)
    )
    return res.scalar_one()

@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    db: Annotated[AsyncSession, Depends(get_db)],
    invoice_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """List invoices, optionally filtered by invoice type.

    Args:
        db: The database session dependency.
        invoice_type: Optional filter for type ('customer' or 'vendor').
        skip: The number of records to skip (for pagination).
        limit: The maximum number of records to return.

    Returns:
        Any: A list of Invoice database instances.
    """
    query = select(Invoice).options(selectinload(Invoice.lines))
    if invoice_type:
        query = query.filter(Invoice.invoice_type == invoice_type)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

# --- Payments ---
@router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    db: Annotated[AsyncSession, Depends(get_db)],
    payment_in: PaymentCreate
) -> Any:
    """Record a payment against an invoice.

    Automatically updates the invoice status depending on the payment amount.

    Args:
        db: The database session dependency.
        payment_in: The payment recording payload.

    Returns:
        Any: The created Payment database instance.

    Raises:
        HTTPException: If the linked invoice is not found.
    """
    invoice_res = await db.execute(select(Invoice).filter(Invoice.id == payment_in.invoice_id))
    invoice = invoice_res.scalar_one_or_none()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found."
        )
        
    db_payment = Payment(**payment_in.model_dump())
    db.add(db_payment)
    
    # Auto update invoice status if fully paid (simple demo logic)
    # Check total payments
    payments_res = await db.execute(select(Payment).filter(Payment.invoice_id == payment_in.invoice_id))
    existing_payments = payments_res.scalars().all()
    total_paid = sum(p.amount for p in existing_payments) + float(payment_in.amount)
    
    if total_paid >= invoice.total_amount:
        invoice.status = "paid"
    else:
        invoice.status = "partially_paid"
        
    await db.commit()
    await db.refresh(db_payment)
    return db_payment

# --- Fixed Assets ---
@router.post("/fixed-assets", response_model=FixedAssetResponse)
async def create_fixed_asset(
    db: Annotated[AsyncSession, Depends(get_db)],
    asset_in: FixedAssetCreate
) -> Any:
    """Register a new fixed asset.

    Args:
        db: The database session dependency.
        asset_in: The fixed asset creation payload.

    Returns:
        Any: The created FixedAsset database instance.

    Raises:
        HTTPException: If an asset with the same asset code already exists.
    """
    result = await db.execute(select(FixedAsset).filter(FixedAsset.asset_code == asset_in.asset_code))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset with this asset code already exists."
        )
        
    db_asset = FixedAsset(**asset_in.model_dump())
    db.add(db_asset)
    await db.commit()
    await db.refresh(db_asset)
    return db_asset

@router.get("/fixed-assets", response_model=List[FixedAssetResponse])
async def list_fixed_assets(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100
) -> Any:
    """List registered fixed assets.

    Args:
        db: The database session dependency.
        skip: The number of records to skip (for pagination).
        limit: The maximum number of records to return.

    Returns:
        Any: A list of FixedAsset database instances.
    """
    result = await db.execute(select(FixedAsset).offset(skip).limit(limit))
    return result.scalars().all()

# --- Journal Entries ---
@router.post("/journal-entries", response_model=JournalEntryResponse)
async def create_journal_entry(
    db: Annotated[AsyncSession, Depends(get_db)],
    entry_in: JournalEntryCreate
) -> Any:
    """Create a new double-entry journal ledger transaction.

    Verifies that debits equal credits before saving.

    Args:
        db: The database session dependency.
        entry_in: The journal entry and transaction lines payload.

    Returns:
        Any: The created JournalEntry database instance loaded with its lines.

    Raises:
        HTTPException: If debits and credits do not balance, or if a GL account is not found.
    """
    # Validate debit equals credit (double entry accounting check)
    total_debit = sum(Decimal(str(l.debit)) for l in entry_in.lines)
    total_credit = sum(Decimal(str(l.credit)) for l in entry_in.lines)
    
    if total_debit != total_credit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Double entry violation: Total debits ({total_debit}) must equal total credits ({total_credit})."
        )
        
    db_entry = JournalEntry(
        entry_date=entry_in.entry_date,
        description=entry_in.description,
        status=entry_in.status
    )
    db.add(db_entry)
    await db.flush()
    
    for line in entry_in.lines:
        # Check GL Account exists
        gl_check = await db.execute(select(GLAccount).filter(GLAccount.id == line.gl_account_id))
        if not gl_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GL Account with ID {line.gl_account_id} not found."
            )
            
        db_line = JournalLine(
            journal_entry_id=db_entry.id,
            gl_account_id=line.gl_account_id,
            debit=line.debit,
            credit=line.credit,
        )
        db.add(db_line)
        
    await db.commit()
    
    # Reload with lines
    res = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .filter(JournalEntry.id == db_entry.id)
    )
    return res.scalar_one()
