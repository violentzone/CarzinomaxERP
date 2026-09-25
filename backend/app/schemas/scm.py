from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal

# Product Category
class ProductCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProductCategoryCreate(ProductCategoryBase):
    pass

class ProductCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

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

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    unit_price: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    category_id: Optional[int] = None

class ProductResponse(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
