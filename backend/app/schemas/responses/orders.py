"""Orders response DTOs."""

from typing import Optional
from pydantic import BaseModel, Field


class CartItemResponse(BaseModel):
    """A single item in the cart response."""

    cart_item_id: str = Field(..., description="Cart item ID")
    product_id: str = Field(..., description="Product SKU (F### or S###)")
    product_name: str = Field(..., description="Human-readable product name")
    category: str = Field(..., description="food | supplement")
    price_inr: float = Field(..., description="Price in INR")
    quantity: int = Field(..., description="Quantity in cart")
    subtotal_inr: float = Field(..., description="price_inr Ã— quantity")
    expires_at: Optional[str] = Field(None, description="ISO datetime when cart item expires")

    class Config:
        json_schema_extra = {
            "example": {
                "cart_item_id": "456f7890-a1b2-34d5-b678-901234567890",
                "product_id": "F001",
                "product_name": "Royal Canin Labrador 30kg",
                "category": "food",
                "price_inr": 500.00,
                "quantity": 1,
                "subtotal_inr": 500.00,
                "expires_at": None,
            }
        }


class CartResponse(BaseModel):
    """Response containing cart summary."""

    items: list[CartItemResponse] = Field(..., description="Cart items")
    item_count: int = Field(..., description="Total items in cart")
    subtotal_inr: float = Field(..., description="Subtotal before delivery")
    delivery_fee_inr: float = Field(..., description="Delivery fee")
    total_inr: float = Field(..., description="Total after delivery")
    free_delivery: bool = Field(..., description="Whether free delivery applies")
    resume_prompt: Optional[str] = Field(None, description="Prompt to resume checkout")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "cart_item_id": "456f7890-a1b2-34d5-b678-901234567890",
                        "product_id": "F001",
                        "product_name": "Royal Canin Labrador 30kg",
                        "category": "food",
                        "price_inr": 500.00,
                        "quantity": 1,
                        "subtotal_inr": 500.00,
                        "expires_at": None,
                    }
                ],
                "item_count": 1,
                "subtotal_inr": 500.00,
                "delivery_fee_inr": 0.00,
                "total_inr": 500.00,
                "free_delivery": True,
                "resume_prompt": "You have 1 item waiting in your cart. Ready to checkout?",
            }
        }


class OrderResponse(BaseModel):
    """Response after creating an order."""

    order_id: str = Field(..., description="Order ID")
    user_id: str = Field(..., description="User ID")
    pet_id: str = Field(..., description="Pet ID")
    status: str = Field(..., description="Order status (pending, confirmed, shipped, delivered)")
    items_count: int = Field(..., description="Number of items")
    subtotal_inr: float = Field(..., description="Subtotal before delivery")
    delivery_fee_inr: float = Field(..., description="Delivery fee")
    total_inr: float = Field(..., description="Total amount")
    created_at: str = Field(..., description="ISO datetime when created")
    estimated_delivery: Optional[str] = Field(None, description="Estimated delivery date")

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "789a1234-b5cd-67e8-f901-234567890123",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "pet_id": "456f7890-a1b2-34d5-b678-901234567890",
                "status": "pending",
                "items_count": 2,
                "subtotal_inr": 700.00,
                "delivery_fee_inr": 49.00,
                "total_inr": 749.00,
                "created_at": "2026-04-25T10:30:00Z",
                "estimated_delivery": "2026-04-27",
            }
        }

