from typing import Annotated, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from decimal import Decimal

from app.api.deps import get_db, RoleChecker
from app.models.finance import GLAccount, JournalEntry, JournalLine, Invoice, InvoiceLine, FixedAsset, Payment
from app.models.hr import Employee
from app.schemas.finance import (
    GLAccountCreate, GLAccountUpdate, GLAccountResponse,
    JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse,
    InvoiceCreate, InvoiceUpdate, InvoiceResponse,
    FixedAssetCreate, FixedAssetUpdate, FixedAssetResponse,
    PaymentCreate, PaymentUpdate, PaymentResponse,
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

@router.put("/accounts/{account_id}", response_model=GLAccountResponse)
async def update_gl_account(
    account_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    account_in: GLAccountUpdate
) -> Any:
    """Update a general ledger account. Only the provided fields are changed.

    Args:
        account_id: The ID of the GL account to update.
        db: The database session dependency.
        account_in: The fields to update.

    Returns:
        Any: The updated GLAccount database instance.

    Raises:
        HTTPException: If the account is not found, or the new code is taken.
    """
    result = await db.execute(select(GLAccount).filter(GLAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GL Account not found.")

    data = account_in.model_dump(exclude_unset=True)

    if "code" in data and data["code"] != account.code:
        dup_res = await db.execute(select(GLAccount).filter(GLAccount.code == data["code"]))
        if dup_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GL Account with this code already exists."
            )

    for key, value in data.items():
        setattr(account, key, value)
    await db.commit()
    await db.refresh(account)
    return account

@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gl_account(
    account_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a general ledger account.

    Args:
        account_id: The ID of the GL account to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the account is not found, or journal lines reference it.
    """
    result = await db.execute(select(GLAccount).filter(GLAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GL Account not found.")

    line_res = await db.execute(
        select(JournalLine.id).filter(JournalLine.gl_account_id == account_id).limit(1)
    )
    if line_res.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GL Account is used by journal entries and cannot be deleted."
        )

    await db.delete(account)
    await db.commit()

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

@router.put("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    invoice_in: InvoiceUpdate
) -> Any:
    """Update an invoice. When lines are provided they replace the existing
    lines and tax/total amounts are recalculated.

    Args:
        invoice_id: The ID of the invoice to update.
        db: The database session dependency.
        invoice_in: The header fields and optional replacement lines.

    Returns:
        Any: The updated Invoice database instance loaded with its lines.

    Raises:
        HTTPException: If the invoice is not found, or the new invoice number is taken.
    """
    result = await db.execute(
        select(Invoice).options(selectinload(Invoice.lines)).filter(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")

    data = invoice_in.model_dump(exclude_unset=True)
    lines = data.pop("lines", None)

    if "invoice_number" in data and data["invoice_number"] != invoice.invoice_number:
        dup_res = await db.execute(
            select(Invoice).filter(Invoice.invoice_number == data["invoice_number"])
        )
        if dup_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice with this invoice number already exists."
            )

    for key, value in data.items():
        setattr(invoice, key, value)

    if lines is not None:
        await db.execute(sa_delete(InvoiceLine).where(InvoiceLine.invoice_id == invoice_id))
        invoice.lines = []

        total_amount = Decimal("0.0")
        tax_amount = Decimal("0.0")
        for line in lines:
            line_qty = Decimal(str(line["quantity"]))
            line_price = Decimal(str(line["unit_price"]))
            line_tax_rate = Decimal(str(line["tax_rate"]))

            line_subtotal = line_qty * line_price
            line_tax = line_subtotal * (line_tax_rate / Decimal("100.0"))
            line_total = line_subtotal + line_tax

            total_amount += line_total
            tax_amount += line_tax

            db.add(InvoiceLine(
                invoice_id=invoice_id,
                description=line["description"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                tax_rate=line["tax_rate"],
                amount=float(line_total),
            ))

        invoice.total_amount = float(total_amount)
        invoice.tax_amount = float(tax_amount)

    await db.commit()

    res = await db.execute(
        select(Invoice).options(selectinload(Invoice.lines)).filter(Invoice.id == invoice_id)
    )
    return res.scalar_one()

@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete an invoice along with its lines. Recorded payments are kept
    as expense records and detached (their invoice link is cleared).

    Args:
        invoice_id: The ID of the invoice to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the invoice is not found.
    """
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.lines), selectinload(Invoice.payments))
        .filter(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")

    await db.delete(invoice)
    await db.commit()

# --- Payments ---
async def _recompute_invoice_status(db: AsyncSession, invoice: Invoice) -> None:
    """Re-derive an invoice's paid status from the sum of its payments.

    Args:
        db: The database session (payments must be flushed/committed-visible).
        invoice: The invoice whose status should be recomputed.
    """
    payments_res = await db.execute(select(Payment).filter(Payment.invoice_id == invoice.id))
    total_paid = sum(p.amount for p in payments_res.scalars().all())

    if total_paid >= invoice.total_amount and total_paid > 0:
        invoice.status = "paid"
    elif total_paid > 0:
        invoice.status = "partially_paid"
    else:
        invoice.status = "unpaid"

@router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    db: Annotated[AsyncSession, Depends(get_db)],
    payment_in: PaymentCreate
) -> Any:
    """Record a categorized company payment.

    Procurement payments may link an invoice, whose paid status is then
    recalculated. Salary payments must reference an employee; rent payments a
    contract number. Category/field consistency is enforced by the schema.

    Args:
        db: The database session dependency.
        payment_in: The payment recording payload.

    Returns:
        Any: The created Payment database instance.

    Raises:
        HTTPException: If a linked invoice or employee is not found.
    """
    invoice = None
    if payment_in.invoice_id is not None:
        invoice_res = await db.execute(select(Invoice).filter(Invoice.id == payment_in.invoice_id))
        invoice = invoice_res.scalar_one_or_none()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found."
            )

    if payment_in.employee_id is not None:
        emp_res = await db.execute(select(Employee).filter(Employee.id == payment_in.employee_id))
        if not emp_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found."
            )

    db_payment = Payment(**payment_in.model_dump())
    db.add(db_payment)
    await db.flush()

    if invoice is not None:
        await _recompute_invoice_status(db, invoice)

    await db.commit()
    await db.refresh(db_payment)
    return db_payment

@router.get("/payments", response_model=List[PaymentResponse])
async def list_payments(
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """List recorded payments, optionally filtered by category.

    Args:
        db: The database session dependency.
        category: Optional category filter (e.g. 'salary', 'rent').
        skip: The number of records to skip (for pagination).
        limit: The maximum number of records to return.

    Returns:
        Any: A list of Payment database instances, newest first.
    """
    query = select(Payment)
    if category:
        query = query.filter(Payment.category == category)
    query = query.order_by(Payment.payment_date.desc(), Payment.id.desc())
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

@router.put("/payments/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    payment_in: PaymentUpdate
) -> Any:
    """Update a payment and recompute the linked invoice's paid status.

    Category and linked invoice cannot be changed — delete and re-record
    instead. employee_id is only accepted on salary payments and
    contract_number only on rent payments.

    Args:
        payment_id: The ID of the payment to update.
        db: The database session dependency.
        payment_in: The fields to update.

    Returns:
        Any: The updated Payment database instance.

    Raises:
        HTTPException: If the payment or a new employee is not found, or a
            category-specific field is sent for the wrong category.
    """
    result = await db.execute(select(Payment).filter(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")

    data = payment_in.model_dump(exclude_unset=True)

    if "employee_id" in data:
        if payment.category != "salary":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="employee_id is only allowed on salary payments."
            )
        if data["employee_id"] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Salary payments require employee_id."
            )
        emp_res = await db.execute(select(Employee).filter(Employee.id == data["employee_id"]))
        if not emp_res.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")

    if "contract_number" in data:
        if payment.category == "rent":
            if not (data["contract_number"] and data["contract_number"].strip()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Rent payments require contract_number."
                )
        elif data["contract_number"] is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="contract_number is only allowed on rent payments."
            )

    for key, value in data.items():
        setattr(payment, key, value)
    await db.flush()

    if payment.invoice_id is not None:
        invoice_res = await db.execute(select(Invoice).filter(Invoice.id == payment.invoice_id))
        invoice = invoice_res.scalar_one_or_none()
        if invoice:
            await _recompute_invoice_status(db, invoice)

    await db.commit()
    await db.refresh(payment)
    return payment

@router.delete("/payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a payment and recompute the linked invoice's paid status.

    Args:
        payment_id: The ID of the payment to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the payment is not found.
    """
    result = await db.execute(select(Payment).filter(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")

    invoice_id = payment.invoice_id
    await db.delete(payment)
    await db.flush()

    if invoice_id is not None:
        invoice_res = await db.execute(select(Invoice).filter(Invoice.id == invoice_id))
        invoice = invoice_res.scalar_one_or_none()
        if invoice:
            await _recompute_invoice_status(db, invoice)

    await db.commit()

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

@router.put("/fixed-assets/{asset_id}", response_model=FixedAssetResponse)
async def update_fixed_asset(
    asset_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    asset_in: FixedAssetUpdate
) -> Any:
    """Update a fixed asset. Only the provided fields are changed.

    Args:
        asset_id: The ID of the fixed asset to update.
        db: The database session dependency.
        asset_in: The fields to update.

    Returns:
        Any: The updated FixedAsset database instance.

    Raises:
        HTTPException: If the asset is not found, or the new asset code is taken.
    """
    result = await db.execute(select(FixedAsset).filter(FixedAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fixed asset not found.")

    data = asset_in.model_dump(exclude_unset=True)

    if "asset_code" in data and data["asset_code"] != asset.asset_code:
        dup_res = await db.execute(select(FixedAsset).filter(FixedAsset.asset_code == data["asset_code"]))
        if dup_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Asset with this asset code already exists."
            )

    for key, value in data.items():
        setattr(asset, key, value)
    await db.commit()
    await db.refresh(asset)
    return asset

@router.delete("/fixed-assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fixed_asset(
    asset_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a fixed asset.

    Args:
        asset_id: The ID of the fixed asset to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the asset is not found.
    """
    result = await db.execute(select(FixedAsset).filter(FixedAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fixed asset not found.")

    await db.delete(asset)
    await db.commit()

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

@router.put("/journal-entries/{entry_id}", response_model=JournalEntryResponse)
async def update_journal_entry(
    entry_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    entry_in: JournalEntryUpdate
) -> Any:
    """Update a journal entry. When lines are provided they replace the
    existing lines and the debit/credit balance is re-verified.

    Args:
        entry_id: The ID of the journal entry to update.
        db: The database session dependency.
        entry_in: The header fields and optional replacement lines.

    Returns:
        Any: The updated JournalEntry database instance loaded with its lines.

    Raises:
        HTTPException: If the entry is not found, the new lines don't balance,
            or a GL account is not found.
    """
    result = await db.execute(
        select(JournalEntry).options(selectinload(JournalEntry.lines)).filter(JournalEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found.")

    data = entry_in.model_dump(exclude_unset=True)
    lines = data.pop("lines", None)

    if lines is not None:
        total_debit = sum(Decimal(str(l["debit"])) for l in lines)
        total_credit = sum(Decimal(str(l["credit"])) for l in lines)
        if total_debit != total_credit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Double entry violation: Total debits ({total_debit}) must equal total credits ({total_credit})."
            )

        for line in lines:
            gl_check = await db.execute(select(GLAccount).filter(GLAccount.id == line["gl_account_id"]))
            if not gl_check.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"GL Account with ID {line['gl_account_id']} not found."
                )

        await db.execute(sa_delete(JournalLine).where(JournalLine.journal_entry_id == entry_id))
        entry.lines = []
        for line in lines:
            db.add(JournalLine(
                journal_entry_id=entry_id,
                gl_account_id=line["gl_account_id"],
                debit=line["debit"],
                credit=line["credit"],
            ))

    for key, value in data.items():
        setattr(entry, key, value)

    await db.commit()

    res = await db.execute(
        select(JournalEntry).options(selectinload(JournalEntry.lines)).filter(JournalEntry.id == entry_id)
    )
    return res.scalar_one()

@router.delete("/journal-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry(
    entry_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a journal entry along with its lines.

    Args:
        entry_id: The ID of the journal entry to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the entry is not found.
    """
    result = await db.execute(
        select(JournalEntry).options(selectinload(JournalEntry.lines)).filter(JournalEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found.")

    await db.delete(entry)
    await db.commit()
