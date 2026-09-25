"""
SCM module, Query, add, remove and update Product
"""
from decimal import Decimal
from traceback import format_exc

from fastapi import Depends, APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse as Response
from pydantic import BaseModel
from sqlalchemy import select
from starlette import status

from app.api.common import get_current_user, permission_check
from app.core.database import get_db
from app.core.log_module import user_log
from app.models import Product, User

scm_router = APIRouter(prefix="/scm", tags=["SCM"])


@scm_router.get("/product_list")
async def get_product_list(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get all products in the database.
    Args:
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of Product objects
    """
    log = user_log(current_user.id)
    if not await permission_check('scm', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('Query all products')
    products = (await db.scalars(select(Product))).all()
    data = []
    for p in products:
        data.append(jsonable_encoder(p.to_dict()))
    log.info(f"{str(len(data))} products found")

    return Response({
        "status": "success",
        "data": data,
    }, status_code=status.HTTP_200_OK, media_type='application/json')


@scm_router.get("/product/{product_id}")
async def get_product(product_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get product by id
    Args:
        product_id: The product to query
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified Product object
    """
    log = user_log(current_user.id)
    if not await permission_check('scm', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Query product ID: {product_id}')

    product = await db.get(Product, product_id)
    if not product:
        log.warning(f'Product ID: {product_id} not found')
        return Response({"status": "fail", "error": f"Product with id {product_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    product_data = jsonable_encoder(product.to_dict())
    log.info(f'Query product: {product_data}')

    return Response({"status": "success", "data": product_data}, status_code=status.HTTP_200_OK, media_type='application/json')


class CreateProduct(BaseModel):
    sku: str
    name: str
    description: str | None = None
    unit_price: Decimal | None = Decimal("0.0")
    cost: Decimal | None = Decimal("0.0")


class UpdateProduct(BaseModel):
    sku: str | None = None
    name: str | None = None
    description: str | None = None
    unit_price: Decimal | None = None
    cost: Decimal | None = None


@scm_router.post("/product")
async def create_product(new_product: CreateProduct, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Create a new product
    Args:
        new_product: New product information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': product}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('scm', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Create product with sku: {new_product.sku}')

    try:
        existing_product = await db.scalar(select(Product).where(Product.sku == new_product.sku))
        if existing_product:
            log.warning(f'Product with sku {new_product.sku} already exists')
            return Response({"status": "fail", "error": f"Product with sku '{new_product.sku}' already exists"}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')

        product = Product(
            sku=new_product.sku,
            name=new_product.name,
            description=new_product.description,
            unit_price=new_product.unit_price if new_product.unit_price is not None else Decimal("0.0"),
            cost=new_product.cost if new_product.cost is not None else Decimal("0.0"),
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
        product_data = jsonable_encoder(product.to_dict())
        log.info(f'Product created: {product_data}')
        return Response({"status": "success", "data": product_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to create product: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@scm_router.put("/product/{product_id}")
async def update_product(product_id: int, new_product: UpdateProduct, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Update product by id
    Args:
        product_id: Product ID to update
        new_product: New product information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('scm', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Update product ID: {product_id}')

    old_product = await db.get(Product, product_id)
    if not old_product:
        log.warning(f'Product ID: {product_id} not found')
        return Response({"status": "fail", "error": f"Product with id {product_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_product:
            if field_value is not None:
                setattr(old_product, field_name, field_value)
        await db.commit()
        await db.refresh(old_product)
        log.info(f'Product updated: {jsonable_encoder(old_product.to_dict())}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to update product: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@scm_router.delete("/product/{product_id}")
async def delete_product(product_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Delete product by id
    Args:
        product_id: Product ID to delete
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('scm', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Delete product ID: {product_id}')

    product = await db.get(Product, product_id)
    if not product:
        log.warning(f'Product ID: {product_id} not found')
        return Response({"status": "fail", "error": f"Product with id {product_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(product)
        await db.commit()
        log.info(f'Product deleted ID: {product_id}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to delete product: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
