"""
SCM module, Query, add, remove and update Product and Purchase
"""
from decimal import Decimal, ROUND_HALF_UP
from traceback import format_exc

from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from starlette import status

from app.api.common import get_current_user, permission_check
from app.core.database import get_db
from app.core.log_module import user_log
from app.models import Product, Purchase, User

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
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('[PRODUCT] Query all products')
    products = (await db.scalars(select(Product))).all()
    data = []
    for p in products:
        data.append(p.to_dict())
    log.info(f"[PRODUCT] {str(len(data))} products found")

    return JSONResponse({
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
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[PRODUCT] Query product ID: {product_id}')

    product = await db.get(Product, product_id)
    if not product:
        log.warning(f'[PRODUCT] Product ID: {product_id} not found')
        return JSONResponse({"status": "fail", "error": f"Product with id {product_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    product_data = product.to_dict()
    log.info(f'[PRODUCT] Query product: {product_data}')

    return JSONResponse({"status": "success", "data": product_data}, status_code=status.HTTP_200_OK, media_type='application/json')


class CreateProduct(BaseModel):
    sku: str
    name: str
    description: str | None = None
    application_price: Decimal | None = Decimal("0.0")
    margin: Decimal | None = Decimal("0.0")
    copy_sold: int | None = 0


class UpdateProduct(BaseModel):
    sku: str | None = None
    name: str | None = None
    description: str | None = None
    application_price: Decimal | None = None
    margin: Decimal | None = None
    copy_sold: int | None = None


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
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[PRODUCT] Create product with sku: {new_product.sku}')

    try:
        existing_product = await db.scalar(select(Product).where(Product.sku == new_product.sku))
        if existing_product:
            log.warning(f'[PRODUCT] Product with sku {new_product.sku} already exists')
            return JSONResponse({"status": "fail", "error": f"Product with sku '{new_product.sku}' already exists"}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')

        product = Product(
            sku=new_product.sku,
            name=new_product.name,
            description=new_product.description,
            application_price=new_product.application_price if new_product.application_price is not None else Decimal("0.0"),
            margin=new_product.margin if new_product.margin is not None else Decimal("0.0"),
            copy_sold=new_product.copy_sold if new_product.copy_sold is not None else 0,
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
        product_data = product.to_dict()
        log.info(f'[PRODUCT] Product created: {product_data}')
        return JSONResponse({"status": "success", "data": product_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'[PRODUCT] Failed to create product: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


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
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[PRODUCT] Update product ID: {product_id}')

    old_product = await db.get(Product, product_id)
    if not old_product:
        log.warning(f'[PRODUCT] Product ID: {product_id} not found')
        return JSONResponse({"status": "fail", "error": f"Product with id {product_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_product:
            if field_value is not None:
                setattr(old_product, field_name, field_value)
        await db.commit()
        await db.refresh(old_product)
        log.info(f'[PRODUCT] Product updated: {old_product.to_dict()}')
        return JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'[PRODUCT] Failed to update product: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


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
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[PRODUCT] Delete product ID: {product_id}')

    product = await db.get(Product, product_id)
    if not product:
        log.warning(f'[PRODUCT] Product ID: {product_id} not found')
        return JSONResponse({"status": "fail", "error": f"Product with id {product_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(product)
        await db.commit()
        log.info(f'[PRODUCT] Product deleted ID: {product_id}')
        return JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'[PRODUCT] Failed to delete product: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@scm_router.get("/purchase_list")
async def get_purchase_list(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get all purchases in the database.
    Args:
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of Purchase objects
    """
    log = user_log(current_user.id)
    if not await permission_check('scm', current_user.id, db):
        response = JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
        return response
    log.info('[PURCHASE] Query all purchases')
    purchases = (await db.scalars(select(Purchase))).all()
    data = []
    for p in purchases:
        data.append(p.to_dict())
    log.info(f'[PURCHASE] {str(len(data))} purchases found')

    response = JSONResponse({"status": "success", "data": data}, status_code=status.HTTP_200_OK, media_type='application/json')
    return response


@scm_router.get("/purchase/{purchase_id}")
async def get_purchase(purchase_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get purchase by id
    Args:
        purchase_id: The purchase to query
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified Purchase object
    """
    log = user_log(current_user.id)
    if not await permission_check('scm', current_user.id, db):
        response = JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
        return response
    log.info(f'[PURCHASE] Query purchase ID: {purchase_id}')

    purchase = await db.get(Purchase, purchase_id)
    if not purchase:
        log.warning(f'[PURCHASE] Purchase ID: {purchase_id} not found')
        response = JSONResponse({"status": "fail", "error": f"Purchase with id {purchase_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
        return response

    purchase_data = purchase.to_dict()
    log.info(f'[PURCHASE] Query purchase: {purchase_data}')

    response = JSONResponse({"status": "success", "data": purchase_data}, status_code=status.HTTP_200_OK, media_type='application/json')
    return response


class CreatePurchase(BaseModel):
    item_name: str | None = None
    category: str | None = None
    unit_price: Decimal
    amount: Decimal


class UpdatePurchase(BaseModel):
    item_name: str | None = None
    category: str | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


@scm_router.post("/purchase")
async def create_purchase(new_purchase: CreatePurchase, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Create a new purchase, `total` is calculated as `unit_price` * `amount`
    Args:
        new_purchase: New purchase information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': purchase}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('scm', current_user.id, db):
        response = JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
        return response
    log.info(f'[PURCHASE] Create purchase with item name: {new_purchase.item_name}')

    try:
        if new_purchase.unit_price < 0 or new_purchase.amount < 0:
            log.warning('[PURCHASE] Negative unit_price or amount')
            response = JSONResponse({"status": "fail", "error": "unit_price and amount must not be negative"}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
            return response

        # Round the way the Numeric(15, 2) columns will, so the stored total equals the stored unit_price * amount
        unit_price = new_purchase.unit_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        amount = new_purchase.amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        purchase = Purchase(
            item_name=new_purchase.item_name,
            category=new_purchase.category,
            unit_price=unit_price,
            amount=amount,
            total=unit_price * amount,
        )
        db.add(purchase)
        await db.commit()
        await db.refresh(purchase)
        purchase_data = purchase.to_dict()
        log.info(f'[PURCHASE] Purchase created: {purchase_data}')
        response = JSONResponse({"status": "success", "data": purchase_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
        return response
    except Exception as err:
        log.error(f'[PURCHASE] Failed to create purchase: {format_exc()}')
        response = JSONResponse({"status": "fail", "error": str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
        return response


@scm_router.put("/purchase/{purchase_id}")
async def update_purchase(purchase_id: int, new_purchase: UpdatePurchase, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Update purchase by id, `total` is recalculated as `unit_price` * `amount`
    Args:
        purchase_id: Purchase ID to update
        new_purchase: New purchase information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('scm', current_user.id, db):
        response = JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
        return response
    log.info(f'[PURCHASE] Update purchase ID: {purchase_id}')

    old_purchase = await db.get(Purchase, purchase_id)
    if not old_purchase:
        log.warning(f'[PURCHASE] Purchase ID: {purchase_id} not found')
        response = JSONResponse({"status": "fail", "error": f"Purchase with id {purchase_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
        return response

    try:
        if (new_purchase.unit_price is not None and new_purchase.unit_price < 0) or (new_purchase.amount is not None and new_purchase.amount < 0):
            log.warning('[PURCHASE] Negative unit_price or amount')
            response = JSONResponse({"status": "fail", "error": "unit_price and amount must not be negative"}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
            return response

        for field_name, field_value in new_purchase:
            if field_value is not None:
                setattr(old_purchase, field_name, field_value)
        # Round the way the Numeric(15, 2) columns will, so the stored total equals the stored unit_price * amount
        old_purchase.unit_price = old_purchase.unit_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        old_purchase.amount = old_purchase.amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        old_purchase.total = old_purchase.unit_price * old_purchase.amount
        await db.commit()
        await db.refresh(old_purchase)
        log.info(f'[PURCHASE] Purchase updated: {old_purchase.to_dict()}')
        response = JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
        return response
    except Exception as err:
        log.error(f'[PURCHASE] Failed to update purchase: {format_exc()}')
        response = JSONResponse({"status": "fail", "error": str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
        return response


@scm_router.delete("/purchase/{purchase_id}")
async def delete_purchase(purchase_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Delete purchase by id
    Args:
        purchase_id: Purchase ID to delete
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('scm', current_user.id, db):
        response = JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
        return response
    log.info(f'[PURCHASE] Delete purchase ID: {purchase_id}')

    purchase = await db.get(Purchase, purchase_id)
    if not purchase:
        log.warning(f'[PURCHASE] Purchase ID: {purchase_id} not found')
        response = JSONResponse({"status": "fail", "error": f"Purchase with id {purchase_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
        return response

    try:
        await db.delete(purchase)
        await db.commit()
        log.info(f'[PURCHASE] Purchase deleted ID: {purchase_id}')
        response = JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
        return response
    except Exception as err:
        log.error(f'[PURCHASE] Failed to delete purchase: {format_exc()}')
        response = JSONResponse({"status": "fail", "error": str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
        return response
