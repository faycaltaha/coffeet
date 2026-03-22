"use client";

import { useState, useEffect, useCallback } from "react";
import type { GiftIdea, WatchedItem } from "@/types";

const KEY = "gift_watchlist";

export function useWatchlist() {
  const [items, setItems] = useState<WatchedItem[]>([]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved) setItems(JSON.parse(saved));
    } catch {}
  }, []);

  const addItem = useCallback((gift: GiftIdea) => {
    setItems((prev) => {
      if (prev.some((i) => i.gift.title === gift.title)) return prev;
      const next = [...prev, { gift, savedAt: Date.now() }];
      try { localStorage.setItem(KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  const removeItem = useCallback((title: string) => {
    setItems((prev) => {
      const next = prev.filter((i) => i.gift.title !== title);
      try { localStorage.setItem(KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  const isWatched = useCallback(
    (title: string) => items.some((i) => i.gift.title === title),
    [items]
  );

  return { items, addItem, removeItem, isWatched };
}
