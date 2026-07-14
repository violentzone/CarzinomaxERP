from typing import Annotated, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete as sa_delete
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
    ProductCategoryCreate, ProductCategoryUpdate, ProductCategoryResponse,
    ProductCreate, ProductUpdate, ProductResponse,
    WarehouseCreate, WarehouseUpdate, WarehouseResponse,
    InventoryStockUpdate, InventoryStockResponse,
    VendorCreate, VendorUpdate, VendorResponse,
    PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse,
    ShipmentCreate, ShipmentUpdate, ShipmentResponse,
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

@router.put("/categories/{category_id}", response_model=ProductCategoryResponse)
async def update_category(
    category_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    category_in: ProductCategoryUpdate
) -> Any:
    """Update a product category. Only the provided fields are changed.

    Args:
        category_id: The ID of the category to update.
        db: The database session dependency.
        category_in: The fields to update.

    Returns:
        Any: The updated ProductCategory database instance.

    Raises:
        HTTPException: If the category is not found, or the new name is taken.
    """
    result = await db.execute(select(ProductCategory).filter(ProductCategory.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

    data = category_in.model_dump(exclude_unset=True)

    if "name" in data and data["name"] != category.name:
        dup_res = await db.execute(select(ProductCategory).filter(ProductCategory.name == data["name"]))
        if dup_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category already exists."
            )

    for key, value in data.items():
        setattr(category, key, value)
    await db.commit()
    await db.refresh(category)
    return category

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a product category.

    Args:
        category_id: The ID of the category to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the category is not found, or products still use it.
    """
    result = await db.execute(select(ProductCategory).filter(ProductCategory.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

    prod_res = await db.execute(select(Product.id).filter(Product.category_id == category_id).limit(1))
    if prod_res.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category has products and cannot be deleted."
        )

    await db.delete(category)
    await db.commit()

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

@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    product_in: ProductUpdate
) -> Any:
    """Update a product. Only the provided fields are changed.

    Args:
        product_id: The ID of the product to update.
        db: The database session dependency.
        product_in: The fields to update.

    Returns:
        Any: The updated Product database instance.

    Raises:
        HTTPException: If the product is not found, the new SKU is taken,
            or the new category doesn't exist.
    """
    result = await db.execute(select(Product).filter(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    data = product_in.model_dump(exclude_unset=True)

    if "sku" in data and data["sku"] != product.sku:
        dup_res = await db.execute(select(Product).filter(Product.sku == data["sku"]))
        if dup_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product SKU already exists."
            )

    if data.get("category_id"):
        cat_res = await db.execute(select(ProductCategory).filter(ProductCategory.id == data["category_id"]))
        if not cat_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found."
            )

    for key, value in data.items():
        setattr(product, key, value)
    await db.commit()
    await db.refresh(product)
    return product

@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a product along with its stock records and movements.

    Args:
        product_id: The ID of the product to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the product is not found, or purchase orders /
            shipments still reference it.
    """
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.stocks), selectinload(Product.movements))
        .filter(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    po_res = await db.execute(
        select(PurchaseOrderLine.id).filter(PurchaseOrderLine.product_id == product_id).limit(1)
    )
    if po_res.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is used on purchase orders and cannot be deleted."
        )

    ship_res = await db.execute(
        select(ShipmentItem.id).filter(ShipmentItem.product_id == product_id).limit(1)
    )
    if ship_res.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is used on shipments and cannot be deleted."
        )

    await db.delete(product)
    await db.commit()

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

@router.put("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    wh_in: WarehouseUpdate
) -> Any:
    """Update a warehouse. Only the provided fields are changed.

    Args:
        warehouse_id: The ID of the warehouse to update.
        db: The database session dependency.
        wh_in: The fields to update.

    Returns:
        Any: The updated Warehouse database instance.

    Raises:
        HTTPException: If the warehouse is not found, or the new code is taken.
    """
    result = await db.execute(select(Warehouse).filter(Warehouse.id == warehouse_id))
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found.")

    data = wh_in.model_dump(exclude_unset=True)

    if "code" in data and data["code"] != warehouse.code:
        dup_res = await db.execute(select(Warehouse).filter(Warehouse.code == data["code"]))
        if dup_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warehouse code already exists."
            )

    for key, value in data.items():
        setattr(warehouse, key, value)
    await db.commit()
    await db.refresh(warehouse)
    return warehouse

@router.delete("/warehouses/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warehouse(
    warehouse_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a warehouse along with its stock records and movements.

    Args:
        warehouse_id: The ID of the warehouse to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the warehouse is not found.
    """
    result = await db.execute(
        select(Warehouse)
        .options(selectinload(Warehouse.stocks))
        .filter(Warehouse.id == warehouse_id)
    )
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found.")

    # Stock movements have no ORM relationship from Warehouse — remove explicitly
    await db.execute(sa_delete(StockMovement).where(StockMovement.warehouse_id == warehouse_id))
    await db.delete(warehouse)
    await db.commit()

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

@router.put("/stocks/{stock_id}", response_model=InventoryStockResponse)
async def update_stock(
    stock_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    stock_in: InventoryStockUpdate
) -> Any:
    """Manually adjust a stock record's quantity. The delta is logged as a
    stock movement with a "Manual adjustment" reference.

    Args:
        stock_id: The ID of the stock record to adjust.
        db: The database session dependency.
        stock_in: The new quantity.

    Returns:
        Any: The updated InventoryStock database instance.

    Raises:
        HTTPException: If the stock record is not found.
    """
    result = await db.execute(select(InventoryStock).filter(InventoryStock.id == stock_id))
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock record not found.")

    new_qty = Decimal(str(stock_in.quantity))
    delta = new_qty - Decimal(str(stock.quantity))
    if delta != 0:
        db.add(StockMovement(
            product_id=stock.product_id,
            warehouse_id=stock.warehouse_id,
            movement_type="in" if delta > 0 else "out",
            quantity=float(abs(delta)),
            reference="Manual adjustment"
        ))
    stock.quantity = float(new_qty)

    await db.commit()
    await db.refresh(stock)
    return stock

@router.delete("/stocks/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock(
    stock_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a stock record.

    Args:
        stock_id: The ID of the stock record to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the stock record is not found.
    """
    result = await db.execute(select(InventoryStock).filter(InventoryStock.id == stock_id))
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock record not found.")

    await db.delete(stock)
    await db.commit()

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

@router.put("/vendors/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    vendor_in: VendorUpdate
) -> Any:
    """Update a vendor. Only the provided fields are changed.

    Args:
        vendor_id: The ID of the vendor to update.
        db: The database session dependency.
        vendor_in: The fields to update.

    Returns:
        Any: The updated Vendor database instance.

    Raises:
        HTTPException: If the vendor is not found, or the new code is taken.
    """
    result = await db.execute(select(Vendor).filter(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found.")

    data = vendor_in.model_dump(exclude_unset=True)

    if "code" in data and data["code"] != vendor.code:
        dup_res = await db.execute(select(Vendor).filter(Vendor.code == data["code"]))
        if dup_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor code already exists."
            )

    for key, value in data.items():
        setattr(vendor, key, value)
    await db.commit()
    await db.refresh(vendor)
    return vendor

@router.delete("/vendors/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a vendor.

    Args:
        vendor_id: The ID of the vendor to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the vendor is not found, or purchase orders reference it.
    """
    result = await db.execute(select(Vendor).filter(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found.")

    po_res = await db.execute(
        select(PurchaseOrder.id).filter(PurchaseOrder.vendor_id == vendor_id).limit(1)
    )
    if po_res.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor has purchase orders and cannot be deleted."
        )

    await db.delete(vendor)
    await db.commit()

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

@router.put("/purchase-orders/{po_id}", response_model=PurchaseOrderResponse)
async def update_purchase_order(
    po_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    po_in: PurchaseOrderUpdate
) -> Any:
    """Update a purchase order. When lines are provided they replace the
    existing lines and the total is recalculated.

    Received POs cannot be edited (their stock has already been posted), and
    the status cannot be set to "received" here — use the receive endpoint.

    Args:
        po_id: The ID of the purchase order to update.
        db: The database session dependency.
        po_in: The header fields and optional replacement lines.

    Returns:
        Any: The updated PurchaseOrder database instance loaded with lines.

    Raises:
        HTTPException: If the PO is not found, is already received, the new PO
            number is taken, the new vendor doesn't exist, or a line product is missing.
    """
    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.lines)).filter(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Order not found.")

    if po.status == "received":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Received purchase orders cannot be edited."
        )

    data = po_in.model_dump(exclude_unset=True)
    lines = data.pop("lines", None)

    if data.get("status") == "received":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the receive endpoint to mark a purchase order as received."
        )

    if "po_number" in data and data["po_number"] != po.po_number:
        dup_res = await db.execute(select(PurchaseOrder).filter(PurchaseOrder.po_number == data["po_number"]))
        if dup_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PO number already exists."
            )

    if data.get("vendor_id"):
        vendor_res = await db.execute(select(Vendor).filter(Vendor.id == data["vendor_id"]))
        if not vendor_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found."
            )

    for key, value in data.items():
        setattr(po, key, value)

    if lines is not None:
        for line in lines:
            prod_res = await db.execute(select(Product).filter(Product.id == line["product_id"]))
            if not prod_res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {line['product_id']} not found."
                )

        await db.execute(sa_delete(PurchaseOrderLine).where(PurchaseOrderLine.purchase_order_id == po_id))
        po.lines = []

        total_amount = Decimal("0.0")
        for line in lines:
            qty = Decimal(str(line["quantity"]))
            price = Decimal(str(line["unit_price"]))
            line_amount = qty * price
            total_amount += line_amount

            db.add(PurchaseOrderLine(
                purchase_order_id=po_id,
                product_id=line["product_id"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                amount=float(line_amount),
            ))

        po.total_amount = float(total_amount)

    await db.commit()

    res = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.lines)).filter(PurchaseOrder.id == po_id)
    )
    return res.scalar_one()

@router.delete("/purchase-orders/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_order(
    po_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a purchase order along with its lines.

    Received POs cannot be deleted because their stock has already been posted.

    Args:
        po_id: The ID of the purchase order to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the PO is not found or is already received.
    """
    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.lines)).filter(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Order not found.")

    if po.status == "received":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Received purchase orders cannot be deleted."
        )

    await db.delete(po)
    await db.commit()

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

@router.put("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def update_shipment(
    shipment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    shipment_in: ShipmentUpdate
) -> Any:
    """Update a shipment. When items are provided they replace the existing items.

    Args:
        shipment_id: The ID of the shipment to update.
        db: The database session dependency.
        shipment_in: The header fields and optional replacement items.

    Returns:
        Any: The updated Shipment database instance loaded with items.

    Raises:
        HTTPException: If the shipment is not found, or an item product is missing.
    """
    result = await db.execute(
        select(Shipment).options(selectinload(Shipment.items)).filter(Shipment.id == shipment_id)
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found.")

    data = shipment_in.model_dump(exclude_unset=True)
    items = data.pop("items", None)

    for key, value in data.items():
        setattr(shipment, key, value)

    if items is not None:
        for item in items:
            prod_res = await db.execute(select(Product).filter(Product.id == item["product_id"]))
            if not prod_res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {item['product_id']} not found."
                )

        await db.execute(sa_delete(ShipmentItem).where(ShipmentItem.shipment_id == shipment_id))
        shipment.items = []
        for item in items:
            db.add(ShipmentItem(
                shipment_id=shipment_id,
                product_id=item["product_id"],
                quantity=item["quantity"],
            ))

    await db.commit()

    res = await db.execute(
        select(Shipment).options(selectinload(Shipment.items)).filter(Shipment.id == shipment_id)
    )
    return res.scalar_one()

@router.delete("/shipments/{shipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shipment(
    shipment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a shipment along with its items.

    Args:
        shipment_id: The ID of the shipment to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the shipment is not found.
    """
    result = await db.execute(
        select(Shipment).options(selectinload(Shipment.items)).filter(Shipment.id == shipment_id)
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found.")

    await db.delete(shipment)
    await db.commit()
