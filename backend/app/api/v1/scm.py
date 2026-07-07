from typing import Annotated, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from decimal import Decimal

from app.api.deps import get_db, RoleChecker
from app.models.scm import (
    ProductCategory, Product, Warehouse, InventoryStock,
    StockMovement, Vendor, PurchaseOrder, PurchaseOrderLine, Shipment, ShipmentItem
)
from app.schemas.scm import (
    ProductCategoryCreate, ProductCategoryResponse,
    ProductCreate, ProductResponse,
    WarehouseCreate, WarehouseResponse,
    InventoryStockCreate, InventoryStockResponse,
    StockMovementCreate, StockMovementResponse,
    VendorCreate, VendorResponse,
    PurchaseOrderCreate, PurchaseOrderResponse,
    ShipmentCreate, ShipmentResponse,
)

router = APIRouter(dependencies=[Depends(RoleChecker(["scm", "admin"]))])

# --- Product Categories ---
@router.post("/categories", response_model=ProductCategoryResponse)
async def create_category(
    db: Annotated[AsyncSession, Depends(get_db)],
    category_in: ProductCategoryCreate
) -> Any:
    """Create a new product category.

    Args:
        db: The database session dependency.
        category_in: The product category creation payload.

    Returns:
        Any: The created ProductCategory database instance.

    Raises:
        HTTPException: If a category with the same name already exists.
    """
    result = await db.execute(select(ProductCategory).filter(ProductCategory.name == category_in.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category already exists."
        )
    db_cat = ProductCategory(**category_in.model_dump())
    db.add(db_cat)
    await db.commit()
    await db.refresh(db_cat)
    return db_cat

@router.get("/categories", response_model=List[ProductCategoryResponse])
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """List all product categories.

    Args:
        db: The database session dependency.

    Returns:
        Any: A list of ProductCategory database instances.
    """
    result = await db.execute(select(ProductCategory))
    return result.scalars().all()

# --- Products ---
@router.post("/products", response_model=ProductResponse)
async def create_product(
    db: Annotated[AsyncSession, Depends(get_db)],
    product_in: ProductCreate
) -> Any:
    """Create a new product inventory master item.

    Args:
        db: The database session dependency.
        product_in: The product creation payload.

    Returns:
        Any: The created Product database instance.

    Raises:
        HTTPException: If the SKU already exists, or the specified category does not exist.
    """
    result = await db.execute(select(Product).filter(Product.sku == product_in.sku))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product SKU already exists."
        )
    
    # Check category exists
    cat_res = await db.execute(select(ProductCategory).filter(ProductCategory.id == product_in.category_id))
    if not cat_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found."
        )
        
    db_prod = Product(**product_in.model_dump())
    db.add(db_prod)
    await db.commit()
    await db.refresh(db_prod)
    return db_prod

@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100
) -> Any:
    """List products.

    Args:
        db: The database session dependency.
        skip: The number of records to skip (for pagination).
        limit: The maximum number of records to return.

    Returns:
        Any: A list of Product database instances.
    """
    result = await db.execute(select(Product).offset(skip).limit(limit))
    return result.scalars().all()

# --- Warehouses ---
@router.post("/warehouses", response_model=WarehouseResponse)
async def create_warehouse(
    db: Annotated[AsyncSession, Depends(get_db)],
    wh_in: WarehouseCreate
) -> Any:
    """Register a new storage warehouse location.

    Args:
        db: The database session dependency.
        wh_in: The warehouse creation payload.

    Returns:
        Any: The created Warehouse database instance.

    Raises:
        HTTPException: If a warehouse with the same code already exists.
    """
    result = await db.execute(select(Warehouse).filter(Warehouse.code == wh_in.code))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warehouse code already exists."
        )
    db_wh = Warehouse(**wh_in.model_dump())
    db.add(db_wh)
    await db.commit()
    await db.refresh(db_wh)
    return db_wh

@router.get("/warehouses", response_model=List[WarehouseResponse])
async def list_warehouses(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """List all registered warehouses.

    Args:
        db: The database session dependency.

    Returns:
        Any: A list of Warehouse database instances.
    """
    result = await db.execute(select(Warehouse))
    return result.scalars().all()

# --- Inventory Stocks ---
@router.get("/stocks", response_model=List[InventoryStockResponse])
async def list_stocks(
    db: Annotated[AsyncSession, Depends(get_db)],
    warehouse_id: Optional[int] = None,
    product_id: Optional[int] = None,
) -> Any:
    """Query current inventory stock levels, optionally filtered by warehouse or product.

    Args:
        db: The database session dependency.
        warehouse_id: Optional filter for a specific warehouse.
        product_id: Optional filter for a specific product.

    Returns:
        Any: A list of InventoryStock database instances.
    """
    query = select(InventoryStock)
    if warehouse_id:
        query = query.filter(InventoryStock.warehouse_id == warehouse_id)
    if product_id:
        query = query.filter(InventoryStock.product_id == product_id)
    result = await db.execute(query)
    return result.scalars().all()

# --- Vendors ---
@router.post("/vendors", response_model=VendorResponse)
async def create_vendor(
    db: Annotated[AsyncSession, Depends(get_db)],
    vendor_in: VendorCreate
) -> Any:
    """Register a new supply vendor.

    Args:
        db: The database session dependency.
        vendor_in: The vendor creation payload.

    Returns:
        Any: The created Vendor database instance.

    Raises:
        HTTPException: If a vendor with the same code already exists.
    """
    result = await db.execute(select(Vendor).filter(Vendor.code == vendor_in.code))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor code already exists."
        )
    db_vendor = Vendor(**vendor_in.model_dump())
    db.add(db_vendor)
    await db.commit()
    await db.refresh(db_vendor)
    return db_vendor

@router.get("/vendors", response_model=List[VendorResponse])
async def list_vendors(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """List all registered vendors.

    Args:
        db: The database session dependency.

    Returns:
        Any: A list of Vendor database instances.
    """
    result = await db.execute(select(Vendor))
    return result.scalars().all()

# --- Purchase Orders ---
@router.post("/purchase-orders", response_model=PurchaseOrderResponse)
async def create_purchase_order(
    db: Annotated[AsyncSession, Depends(get_db)],
    po_in: PurchaseOrderCreate
) -> Any:
    """Create a new procurement purchase order (PO) to buy products from a vendor.

    Calculates total purchase amount based on PO lines.

    Args:
        db: The database session dependency.
        po_in: The purchase order creation payload with lines.

    Returns:
        Any: The created PurchaseOrder database instance loaded with lines.

    Raises:
        HTTPException: If the PO number already exists, or if a line item specifies a non-existent product.
    """
    result = await db.execute(select(PurchaseOrder).filter(PurchaseOrder.po_number == po_in.po_number))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PO number already exists."
        )
        
    db_po = PurchaseOrder(
        vendor_id=po_in.vendor_id,
        po_number=po_in.po_number,
        order_date=po_in.order_date,
        delivery_date=po_in.delivery_date,
        status=po_in.status,
    )
    db.add(db_po)
    await db.flush()
    
    total_amount = Decimal("0.0")
    for line in po_in.lines:
        prod_res = await db.execute(select(Product).filter(Product.id == line.product_id))
        if not prod_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {line.product_id} not found."
            )
            
        qty = Decimal(str(line.quantity))
        price = Decimal(str(line.unit_price))
        line_amount = qty * price
        total_amount += line_amount
        
        db_line = PurchaseOrderLine(
            purchase_order_id=db_po.id,
            product_id=line.product_id,
            quantity=line.quantity,
            unit_price=line.unit_price,
            amount=float(line_amount),
        )
        db.add(db_line)
        
    db_po.total_amount = float(total_amount)
    await db.commit()
    
    # Reload with lines
    res = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .filter(PurchaseOrder.id == db_po.id)
    )
    return res.scalar_one()

@router.post("/purchase-orders/{po_id}/receive", response_model=PurchaseOrderResponse)
async def receive_purchase_order(
    po_id: int,
    warehouse_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Mark a purchase order as received and deposit/increment stocks in the specified warehouse.

    Records the stock movements.

    Args:
        po_id: The ID of the Purchase Order to receive.
        warehouse_id: The ID of the Warehouse where the goods are received.
        db: The database session dependency.

    Returns:
        Any: The updated PurchaseOrder database instance.

    Raises:
        HTTPException: If the PO or warehouse is not found, or if the PO is already received.
    """
    # Fetch PO with lines
    po_res = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .filter(PurchaseOrder.id == po_id)
    )
    po = po_res.scalar_one_or_none()
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase Order not found."
        )
        
    if po.status == "received":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Purchase Order has already been received."
        )
         
    # Check warehouse
    wh_res = await db.execute(select(Warehouse).filter(Warehouse.id == warehouse_id))
    if not wh_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found."
        )
        
    # Update inventory for each line
    for line in po.lines:
        # Find or create InventoryStock
        stock_res = await db.execute(
            select(InventoryStock)
            .filter(
                InventoryStock.product_id == line.product_id,
                InventoryStock.warehouse_id == warehouse_id
            )
        )
        stock = stock_res.scalar_one_or_none()
        
        if stock:
            stock.quantity = float(Decimal(str(stock.quantity)) + Decimal(str(line.quantity)))
        else:
            stock = InventoryStock(
                product_id=line.product_id,
                warehouse_id=warehouse_id,
                quantity=line.quantity,
            )
            db.add(stock)
            
        # Log stock movement
        movement = StockMovement(
            product_id=line.product_id,
            warehouse_id=warehouse_id,
            movement_type="in",
            quantity=line.quantity,
            reference=f"PO Received: {po.po_number}"
        )
        db.add(movement)
        
    po.status = "received"
    await db.commit()
    
    # Reload PO
    po_res = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .filter(PurchaseOrder.id == po_id)
    )
    return po_res.scalar_one()

# --- Shipments ---
@router.post("/shipments", response_model=ShipmentResponse)
async def create_shipment(
    db: Annotated[AsyncSession, Depends(get_db)],
    shipment_in: ShipmentCreate
) -> Any:
    """Record a shipment log to track products being dispatched or transported.

    Args:
        db: The database session dependency.
        shipment_in: The shipment details and line items.

    Returns:
        Any: The created Shipment database instance loaded with items.
    """
    # Start transaction to log shipments
    db_shipment = Shipment(
        shipment_number=shipment_in.shipment_number,
        order_reference=shipment_in.order_reference,
        carrier=shipment_in.carrier,
        tracking_number=shipment_in.tracking_number,
        status=shipment_in.status,
        shipped_date=shipment_in.shipped_date,
        estimated_delivery_date=shipment_in.estimated_delivery_date,
    )
    db.add(db_shipment)
    await db.flush()
    
    for item in shipment_in.items:
        db_item = ShipmentItem(
            shipment_id=db_shipment.id,
            product_id=item.product_id,
            quantity=item.quantity,
        )
        db.add(db_item)
        
    await db.commit()
    
    res = await db.execute(
        select(Shipment)
        .options(selectinload(Shipment.items))
        .filter(Shipment.id == db_shipment.id)
    )
    return res.scalar_one()
