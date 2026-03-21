"use client";

import { useState, useEffect, useCallback } from "react";
import type { GiftIdea } from "@/types";

export interface CartItem {
  gift: GiftIdea;
  addedAt: number;
}

export function useCart() {
  const [items, setItems] = useState<CartItem[]>([]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("gift_cart");
      if (saved) setItems(JSON.parse(saved));
    } catch {}
  }, []);

  const persist = (next: CartItem[]) => {
    setItems(next);
    try { localStorage.setItem("gift_cart", JSON.stringify(next)); } catch {}
  };

  const addItem = useCallback((gift: GiftIdea) => {
    setItems((prev) => {
      if (prev.some((i) => i.gift.title === gift.title)) return prev;
      const next = [...prev, { gift, addedAt: Date.now() }];
      try { localStorage.setItem("gift_cart", JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  const removeItem = useCallback((title: string) => {
    setItems((prev) => {
      const next = prev.filter((i) => i.gift.title !== title);
      try { localStorage.setItem("gift_cart", JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  const clearCart = useCallback(() => {
    setItems([]);
    try { localStorage.removeItem("gift_cart"); } catch {}
  }, []);

  const isInCart = useCallback(
    (title: string) => items.some((i) => i.gift.title === title),
    [items]
  );

  return { items, addItem, removeItem, clearCart, isInCart };
}
