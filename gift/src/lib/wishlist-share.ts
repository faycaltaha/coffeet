import type { GiftIdea } from "@/types";

// Strip server-generated affiliate links before encoding (they can be rebuilt client-side)
type SlimGift = Omit<GiftIdea, "affiliateLinks">;

interface WishlistPayload {
  name: string;
  gifts: SlimGift[];
}

export function encodeWishlist(name: string, gifts: GiftIdea[]): string {
  try {
    const payload: WishlistPayload = {
      name,
      gifts: gifts.map(({ affiliateLinks: _a, ...g }) => g),
    };
    return btoa(encodeURIComponent(JSON.stringify(payload)));
  } catch { return ""; }
}

export function decodeWishlist(encoded: string): WishlistPayload | null {
  try {
    return JSON.parse(decodeURIComponent(atob(encoded)));
  } catch { return null; }
}

export type { WishlistPayload, SlimGift };
