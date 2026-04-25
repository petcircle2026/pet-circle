"""Orders request DTOs."""

from typing import Optional
from pydantic import BaseModel, Field


class AddToCartRequest(BaseModel):
    """Request to add item to cart."""

    pet_id: str = Field(..., description="Pet ID")
    product_id: str = Field(..., min_length=4, max_length=10, description="Product SKU (F### or S###)")
    quantity: int = Field(..., ge=1, le=10, description="Quantity to add")

    class Config:
        json_schema_extra = {
            "example": {
                "pet_id": "123e4567-e89b-12d3-a456-426614174000",
                "product_id": "F001",
                "quantity": 2,
            }
        }


class RemoveFromCartRequest(BaseModel):
    """Request to remove item from cart."""

    pet_id: str = Field(..., description="Pet ID")
    cart_item_id: str = Field(..., description="Cart item ID")

    class Config:
        json_schema_extra = {
            "example": {
                "pet_id": "123e4567-e89b-12d3-a456-426614174000",
                "cart_item_id": "456f7890-a1b2-34d5-b678-901234567890",
            }
        }


class OrderItemRequest(BaseModel):
    """A single item in an order."""

    product_id: str = Field(..., description="Product SKU")
    quantity: int = Field(..., ge=1, le=10)
    price_paise: int = Field(..., gt=0, description="Price in paise (1 INR = 100 paise)")


class CheckoutRequest(BaseModel):
    """Request to checkout (create order)."""

    user_id: str = Field(..., description="User ID")
    pet_id: str = Field(..., description="Pet ID")
    items: list[OrderItemRequest] = Field(..., min_length=1, description="Items to order")
    notes: Optional[str] = Field(None, max_length=500, description="Optional order notes")
    delivery_address: Optional[str] = Field(None, max_length=500, description="Delivery address")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "pet_id": "456f7890-a1b2-34d5-b678-901234567890",
                "items": [
                    {"product_id": "F001", "quantity": 1, "price_paise": 50000},
                    {"product_id": "S002", "quantity": 2, "price_paise": 10000},
                ],
                "notes": "Please deliver in the morning",
            }
        }

