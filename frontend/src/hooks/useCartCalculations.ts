import { useMemo } from "react";
import type { CartItem } from "@/components/CartView";
import { DELIVERY_FEE, FREE_THRESHOLD } from "@/utils/cart-utils";

export interface CartCalculations {
  inCart: CartItem[];
  subtotal: number;
  deliveryFee: number;
  total: number;
  amountForFreeDelivery: number;
}

export function useCartCalculations(items: CartItem[]): CartCalculations {
  const inCart = useMemo(() => items.filter((item) => item.quantity > 0), [items]);

  const subtotal = useMemo(() => {
    return inCart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  }, [inCart]);

  const deliveryFee = subtotal >= FREE_THRESHOLD ? 0 : DELIVERY_FEE;
  const total = subtotal + deliveryFee;
  const amountForFreeDelivery = Math.max(0, FREE_THRESHOLD - subtotal);

  return { inCart, subtotal, deliveryFee, total, amountForFreeDelivery };
}
