from datetime import date
from typing import List, Optional
from sqlalchemy import String, Numeric, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

class ProductCategory(Base, TimestampMixin):
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    products: Mapped[List["Product"]] = relationship(back_populates="category")

class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    cost: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    category_id: Mapped[int] = mapped_column(ForeignKey("product_categories.id"), nullable=False)

    category: Mapped["ProductCategory"] = relationship(back_populates="products")
    stocks: Mapped[List["InventoryStock"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    movements: Mapped[List["StockMovement"]] = relationship(back_populates="product", cascade="all, delete-orphan")

class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    stocks: Mapped[List["InventoryStock"]] = relationship(back_populates="warehouse", cascade="all, delete-orphan")

class InventoryStock(Base, TimestampMixin):
    __tablename__ = "inventory_stocks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=0.0)

    product: Mapped["Product"] = relationship(back_populates="stocks")
    warehouse: Mapped["Warehouse"] = relationship(back_populates="stocks")

class StockMovement(Base, TimestampMixin):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False)  # in, out, transfer
    quantity: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # e.g., PO #, Invoice #, adjustment reason

    product: Mapped["Product"] = relationship(back_populates="movements")

class Vendor(Base, TimestampMixin):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship(back_populates="vendor")

class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False)
    po_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    delivery_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    total_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # draft, ordered, received, cancelled

    vendor: Mapped["Vendor"] = relationship(back_populates="purchase_orders")
    lines: Mapped[List["PurchaseOrderLine"]] = relationship(back_populates="purchase_order", cascade="all, delete-orphan")

class PurchaseOrderLine(Base, TimestampMixin):
    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=1.0)
    unit_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="lines")

class Shipment(Base, TimestampMixin):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    shipment_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    order_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    carrier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, shipped, delivered, cancelled
    shipped_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    estimated_delivery_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    items: Mapped[List["ShipmentItem"]] = relationship(back_populates="shipment", cascade="all, delete-orphan")

class ShipmentItem(Base, TimestampMixin):
    __tablename__ = "shipment_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)

    shipment: Mapped["Shipment"] = relationship(back_populates="items")
