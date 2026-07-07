from datetime import date
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal

# Product Category
class ProductCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProductCategoryCreate(ProductCategoryBase):
    pass

class ProductCategoryResponse(ProductCategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Product
class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    unit_price: Decimal = Field(default=Decimal("0.0"))
    cost: Decimal = Field(default=Decimal("0.0"))
    category_id: int

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Warehouse
class WarehouseBase(BaseModel):
    code: str
    name: str
    location: Optional[str] = None

class WarehouseCreate(WarehouseBase):
    pass

class WarehouseResponse(WarehouseBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Inventory Stock
class InventoryStockBase(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: Decimal = Field(default=Decimal("0.0"))

class InventoryStockCreate(InventoryStockBase):
    pass

class InventoryStockResponse(InventoryStockBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Stock Movement
class StockMovementBase(BaseModel):
    product_id: int
    warehouse_id: int
    movement_type: str  # in, out, transfer
    quantity: Decimal
    reference: Optional[str] = None

class StockMovementCreate(StockMovementBase):
    pass

class StockMovementResponse(StockMovementBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Vendor
class VendorBase(BaseModel):
    code: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class VendorCreate(VendorBase):
    pass

class VendorResponse(VendorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Purchase Order Line
class PurchaseOrderLineBase(BaseModel):
    product_id: int
    quantity: Decimal = Field(default=Decimal("1.0"))
    unit_price: Decimal = Field(default=Decimal("0.0"))

class PurchaseOrderLineCreate(PurchaseOrderLineBase):
    pass

class PurchaseOrderLineResponse(PurchaseOrderLineBase):
    id: int
    purchase_order_id: int
    amount: Decimal
    model_config = ConfigDict(from_attributes=True)

# Purchase Order
class PurchaseOrderBase(BaseModel):
    vendor_id: int
    po_number: str
    order_date: date
    delivery_date: Optional[date] = None
    status: str = "draft"

class PurchaseOrderCreate(PurchaseOrderBase):
    lines: List[PurchaseOrderLineCreate]

class PurchaseOrderResponse(PurchaseOrderBase):
    id: int
    total_amount: Decimal
    lines: List[PurchaseOrderLineResponse]
    model_config = ConfigDict(from_attributes=True)

# Shipment Item
class ShipmentItemBase(BaseModel):
    product_id: int
    quantity: Decimal

class ShipmentItemCreate(ShipmentItemBase):
    pass

class ShipmentItemResponse(ShipmentItemBase):
    id: int
    shipment_id: int
    model_config = ConfigDict(from_attributes=True)

# Shipment
class ShipmentBase(BaseModel):
    shipment_number: str
    order_reference: str
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    status: str = "pending"
    shipped_date: Optional[date] = None
    estimated_delivery_date: Optional[date] = None

class ShipmentCreate(ShipmentBase):
    items: List[ShipmentItemCreate]

class ShipmentResponse(ShipmentBase):
    id: int
    items: List[ShipmentItemResponse]
    model_config = ConfigDict(from_attributes=True)
