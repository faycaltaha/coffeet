"use client";

import { useRef } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import type { GiftIdea } from "@/types";
import { amazonUrl, secondMerchant } from "@/lib/affiliate-client";

const AMAZON_TAG = process.env.NEXT_PUBLIC_AMAZON_AFFILIATE_TAG;

const CATEGORY_COLORS: Record<string, string> = {
  experience: "bg-amber-100 text-amber-700",
  fashion: "bg-pink-100 text-pink-700",
  tech: "bg-blue-100 text-blue-700",
  beauty: "bg-rose-100 text-rose-700",
  food: "bg-green-100 text-green-700",
  books: "bg-indigo-100 text-indigo-700",
  home: "bg-orange-100 text-orange-700",
  sport: "bg-teal-100 text-teal-700",
  travel: "bg-cyan-100 text-cyan-700",
  art: "bg-purple-100 text-purple-700",
  default: "bg-gray-100 text-gray-700",
};

const CARD_EMOJIS = ["🎁", "🎀", "💝", "✨", "🌟", "💫", "🎊", "🛍️"];

const TREND_SOURCE_COLORS: Record<string, string> = {
  "TikTok Viral": "bg-[#010101] text-white",
  "Instagram Trending": "bg-gradient-to-r from-purple-500 to-pink-500 text-white",
  "Pinterest Popular": "bg-red-600 text-white",
  "YouTube Trending": "bg-red-500 text-white",
};

function getPlatformName(ts: string) {
  return ts.replace(" Viral", "").replace(" Trending", "").replace(" Popular", "");
}

function PlatformIcon({ platform }: { platform: string }) {
  if (platform === "TikTok")
    return <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5 shrink-0" aria-hidden="true"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.67a8.26 8.26 0 0 0 4.83 1.54V6.76a4.85 4.85 0 0 1-1.06-.07z"/></svg>;
  if (platform === "Instagram")
    return <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5 shrink-0" aria-hidden="true"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>;
  if (platform === "Pinterest")
    return <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5 shrink-0" aria-hidden="true"><path d="M12 0C5.373 0 0 5.373 0 12c0 5.084 3.163 9.426 7.627 11.174-.105-.949-.2-2.405.042-3.441.218-.937 1.407-5.965 1.407-5.965s-.359-.719-.359-1.782c0-1.668.967-2.914 2.171-2.914 1.023 0 1.518.769 1.518 1.69 0 1.029-.655 2.568-.994 3.995-.283 1.194.599 2.169 1.777 2.169 2.133 0 3.772-2.249 3.772-5.495 0-2.873-2.064-4.882-5.012-4.882-3.414 0-5.418 2.561-5.418 5.207 0 1.031.397 2.138.893 2.738a.36.36 0 0 1 .083.345l-.333 1.36c-.053.22-.174.267-.402.161-1.499-.698-2.436-2.889-2.436-4.649 0-3.785 2.75-7.262 7.929-7.262 4.163 0 7.398 2.967 7.398 6.931 0 4.136-2.607 7.464-6.227 7.464-1.216 0-2.359-.632-2.75-1.378l-.748 2.853c-.271 1.043-1.002 2.35-1.492 3.146C9.57 23.812 10.763 24 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0z"/></svg>;
  return <span className="text-sm" aria-hidden="true">🔥</span>;
}

function categoryColor(cat: string) {
  return CATEGORY_COLORS[cat.toLowerCase()] ?? CATEGORY_COLORS.default;
}

function trackClick(title: string, merchant: string) {
  try {
    const raw = localStorage.getItem("gift_clicks") || "[]";
    const clicks: { title: string; merchant: string; ts: number }[] = JSON.parse(raw);
    clicks.push({ title, merchant, ts: Date.now() });
    localStorage.setItem("gift_clicks", JSON.stringify(clicks.slice(-200)));
  } catch {}
}

export interface GiftCardProps {
  gift: GiftIdea;
  index: number;
  feedback: Record<string, "up" | "down">;
  onFeedback: (title: string, type: "up" | "down") => void;
  onRefresh?: () => void;
  canRefresh?: boolean;
  inCart: boolean;
  onAddToCart: (gift: GiftIdea) => void;
  onRemoveFromCart: (title: string) => void;
}

const SWIPE_THRESHOLD = 80;

export default function GiftCard({
  gift,
  index,
  feedback,
  onFeedback,
  onRefresh,
  canRefresh = false,
  inCart,
  onAddToCart,
  onRemoveFromCart,
}: GiftCardProps) {
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-180, 0, 180], [-8, 0, 8]);

  // Left swipe → refresh hint opacity
  const refreshHintOpacity = useTransform(x, [-SWIPE_THRESHOLD, -20, 0], [1, 0.5, 0]);
  // Right swipe → cart hint opacity
  const cartHintOpacity = useTransform(x, [0, 20, SWIPE_THRESHOLD], [0, 0.5, 1]);

  const isDismissed = useRef(false);

  const handleDragEnd = (_: unknown, info: { offset: { x: number }; velocity: { x: number } }) => {
    const offset = info.offset.x;
    const velocity = info.velocity.x;

    if ((offset < -SWIPE_THRESHOLD || velocity < -400) && canRefresh && !isDismissed.current) {
      // Swipe left → refresh
      isDismissed.current = true;
      animate(x, -500, { duration: 0.3, ease: "easeIn" }).then(() => {
        onRefresh?.();
        x.set(0);
        isDismissed.current = false;
      });
    } else if (offset > SWIPE_THRESHOLD || velocity > 400) {
      // Swipe right → add to cart
      animate(x, 500, { duration: 0.3, ease: "easeIn" }).then(() => {
        if (!inCart) onAddToCart(gift);
        x.set(0);
      });
    } else {
      // Snap back
      animate(x, 0, { type: "spring", stiffness: 400, damping: 30 });
    }
  };

  const trendColor = gift.trendSource
    ? (TREND_SOURCE_COLORS[gift.trendSource] ?? "bg-orange-500 text-white")
    : null;
  const myFeedback = feedback[gift.title];

  return (
    <div className="relative select-none">
      {/* Swipe-left hint: refresh */}
      {canRefresh && (
        <motion.div
          style={{ opacity: refreshHintOpacity }}
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 rounded-2xl bg-orange-100 dark:bg-orange-900/40 flex items-center justify-end pr-6 z-0"
        >
          <div className="flex flex-col items-center gap-1 text-orange-600 dark:text-orange-300">
            <span className="text-2xl">🔄</span>
            <span className="text-xs font-bold">Autre idée</span>
          </div>
        </motion.div>
      )}

      {/* Swipe-right hint: cart */}
      <motion.div
        style={{ opacity: cartHintOpacity }}
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 rounded-2xl bg-green-100 dark:bg-green-900/40 flex items-center pl-6 z-0"
      >
        <div className="flex flex-col items-center gap-1 text-green-600 dark:text-green-300">
          <span className="text-2xl">🛒</span>
          <span className="text-xs font-bold">Au panier</span>
        </div>
      </motion.div>

      {/* Card */}
      <motion.article
        style={{ x, rotate, zIndex: 1, position: "relative" }}
        drag="x"
        dragConstraints={{ left: 0, right: 0 }}
        dragElastic={0.25}
        onDragEnd={handleDragEnd}
        aria-label={`Cadeau : ${gift.title}`}
        className={`bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm rounded-2xl p-5 border flex flex-col gap-3 cursor-grab active:cursor-grabbing ${
          gift.trending
            ? "border-orange-300 ring-1 ring-orange-200 shadow-md shadow-orange-100/60"
            : "border-white/70 dark:border-gray-700 shadow-sm shadow-brand-100/40"
        }`}
        whileHover={{
          y: -4,
          boxShadow: gift.trending
            ? "0 16px 40px -8px rgba(251,146,60,0.25)"
            : "0 16px 40px -8px rgba(192,38,211,0.18)",
          transition: { type: "spring", stiffness: 400, damping: 22 },
        }}
      >
        {/* Swipe hint text (first card only) */}
        {index === 0 && canRefresh && (
          <p className="text-[10px] text-gray-300 dark:text-gray-600 text-center -mt-1 -mb-1 select-none">
            ← glisse pour changer · glisse pour ajouter →
          </p>
        )}

        {/* Trending banner */}
        {gift.trending && gift.trendSource && (
          <div
            aria-label={`Tendance sur ${getPlatformName(gift.trendSource)}`}
            className={`-mx-5 -mt-5 px-4 py-1.5 rounded-t-2xl flex items-center gap-2 text-xs font-semibold ${trendColor}`}
          >
            <PlatformIcon platform={getPlatformName(gift.trendSource)} />
            <span>Tendance sur {getPlatformName(gift.trendSource)}</span>
          </div>
        )}

        {/* Title row */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <motion.span
              aria-hidden="true"
              className="text-2xl"
              animate={{ rotate: [0, -8, 8, 0] }}
              transition={{ duration: 2.5, repeat: Infinity, delay: index * 0.3, ease: "easeInOut" }}
            >
              {CARD_EMOJIS[index % CARD_EMOJIS.length]}
            </motion.span>
            <h3 className="font-bold text-gray-900 dark:text-gray-100 leading-snug">{gift.title}</h3>
          </div>
          <span
            aria-label={`Prix : ${gift.priceRange}`}
            className="shrink-0 text-sm font-semibold text-brand-600 bg-brand-50/80 dark:bg-brand-900/30 dark:text-brand-300 px-3 py-1 rounded-full border border-brand-100 dark:border-brand-800"
          >
            {gift.priceRange}
          </span>
        </div>

        {/* Description */}
        <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed">{gift.description}</p>

        {/* Tags */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full capitalize ${categoryColor(gift.category)}`}>
            {gift.category}
          </span>
          <span className="text-xs text-gray-400 dark:text-gray-500 italic">{gift.reason}</span>
        </div>

        {/* Affiliate links */}
        <div className="flex gap-2">
          <motion.a
            href={amazonUrl(gift.searchQuery, AMAZON_TAG)}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Trouver "${gift.title}" sur Amazon.fr`}
            className="flex-1 text-center py-2 rounded-xl text-sm font-semibold bg-amber-400 text-amber-900 shadow-sm"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => trackClick(gift.title, "Amazon")}
          >
            🛒 Amazon.fr
          </motion.a>
          {(() => {
            const merchant = secondMerchant(gift.category);
            return (
              <motion.a
                href={merchant.url(gift.searchQuery)}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`Trouver "${gift.title}" sur ${merchant.label}`}
                className={`flex-1 text-center py-2 rounded-xl text-sm font-semibold ${merchant.className}`}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => trackClick(gift.title, merchant.label)}
              >
                {merchant.icon} {merchant.label}
              </motion.a>
            );
          })()}
        </div>

        {/* Action row: cart + refresh + feedback */}
        <div className="flex items-center gap-1.5 pt-1 border-t border-gray-100 dark:border-gray-700">
          {/* Add / remove from cart */}
          <motion.button
            onClick={() => inCart ? onRemoveFromCart(gift.title) : onAddToCart(gift)}
            aria-label={inCart ? `Retirer "${gift.title}" du panier` : `Ajouter "${gift.title}" au panier`}
            aria-pressed={inCart}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
              inCart
                ? "bg-green-500 text-white border-green-500 shadow-sm"
                : "bg-white/70 dark:bg-gray-800/70 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-gray-600 hover:border-green-400"
            }`}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.92 }}
          >
            {inCart ? "✅ Dans le panier" : "🛒 + Panier"}
          </motion.button>

          {/* Refresh */}
          {canRefresh && (
            <motion.button
              onClick={onRefresh}
              aria-label="Voir une autre idée cadeau"
              className="flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-semibold border bg-white/70 dark:bg-gray-800/70 text-orange-500 border-orange-200 dark:border-orange-700 hover:border-orange-400"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.92, rotate: 180 }}
              transition={{ type: "spring", stiffness: 400, damping: 20 }}
            >
              🔄 Autre idée
            </motion.button>
          )}

          {/* Spacer + feedback */}
          <div className="ml-auto flex items-center gap-1">
            <motion.button
              onClick={() => onFeedback(gift.title, "up")}
              aria-label="J'aime cette idée"
              aria-pressed={myFeedback === "up"}
              className={`w-7 h-7 rounded-full flex items-center justify-center text-sm transition-colors ${
                myFeedback === "up"
                  ? "bg-green-100 dark:bg-green-900/40 text-green-600"
                  : "hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400"
              }`}
              whileHover={{ scale: 1.15 }}
              whileTap={{ scale: 0.85 }}
            >
              👍
            </motion.button>
            <motion.button
              onClick={() => onFeedback(gift.title, "down")}
              aria-label="Cette idée ne me convient pas"
              aria-pressed={myFeedback === "down"}
              className={`w-7 h-7 rounded-full flex items-center justify-center text-sm transition-colors ${
                myFeedback === "down"
                  ? "bg-red-100 dark:bg-red-900/40 text-red-500"
                  : "hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400"
              }`}
              whileHover={{ scale: 1.15 }}
              whileTap={{ scale: 0.85 }}
            >
              👎
            </motion.button>
          </div>
        </div>
      </motion.article>
    </div>
  );
}
