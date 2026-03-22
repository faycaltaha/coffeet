"use client";

import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import { decodeWishlist } from "@/lib/wishlist-share";
import { amazonUrl, secondMerchant } from "@/lib/affiliate-client";
import { trackClick } from "@/lib/tracking";
import type { SlimGift } from "@/lib/wishlist-share";

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
  default: "bg-stone-100 text-stone-700",
};

function catColor(cat: string) {
  return CATEGORY_COLORS[cat.toLowerCase()] ?? CATEGORY_COLORS.default;
}

function GiftRow({ gift, index }: { gift: SlimGift; index: number }) {
  const merchant = secondMerchant(gift.category);
  return (
    <motion.article
      className="bg-white/85 dark:bg-stone-800/80 rounded-2xl p-5 border border-stone-100 dark:border-stone-700 shadow-sm flex flex-col gap-3"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07, type: "spring", stiffness: 280, damping: 24 }}
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-bold text-stone-900 dark:text-stone-100 leading-snug">{gift.title}</h3>
        <span className="shrink-0 text-sm font-semibold text-brand-700 bg-brand-100/80 px-3 py-1 rounded-full border border-brand-200">
          {gift.priceRange}
        </span>
      </div>
      <p className="text-stone-600 dark:text-stone-300 text-sm leading-relaxed">{gift.description}</p>
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full capitalize ${catColor(gift.category)}`}>
          {gift.category}
        </span>
        <span className="text-xs text-stone-400 italic">{gift.reason}</span>
      </div>
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
      </div>
    </motion.article>
  );
}

export default function WishlistContent() {
  const searchParams = useSearchParams();
  const payload = (() => {
    const d = searchParams.get("d");
    return d ? decodeWishlist(d) : null;
  })();

  if (!payload) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-6 px-4 text-center">
        <div className="text-6xl">🎁</div>
        <h1 className="text-2xl font-bold text-stone-800 dark:text-stone-100">Wishlist introuvable</h1>
        <p className="text-stone-500 text-sm max-w-xs">Ce lien est invalide ou a expiré.</p>
        <Link
          href="/"
          className="px-6 py-3 rounded-2xl bg-brand-500 text-white font-semibold shadow-md hover:bg-brand-600 transition-colors"
        >
          Créer ma wishlist →
        </Link>
      </div>
    );
  }

  return (
    <main className="min-h-screen py-12 px-4 flex flex-col items-center relative overflow-hidden">
      {/* Background orbs */}
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
        <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-[#F0D4BB]/30 blur-[80px]" />
        <div className="absolute -bottom-40 -right-40 w-[550px] h-[550px] rounded-full bg-[#FAF0E6]/40 blur-[80px]" />
      </div>

      {/* Header */}
      <motion.header
        className="text-center mb-8 max-w-xl w-full"
        initial={{ opacity: 0, y: -24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="text-5xl mb-3">🎁</div>
        <h1 className="text-3xl font-extrabold text-stone-800 dark:text-stone-100 tracking-tight mb-2">
          Liste de cadeaux pour{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-brand-400">
            {payload.name}
          </span>
        </h1>
        <p className="text-stone-500 dark:text-stone-400 text-sm">
          {payload.gifts.length} idée{payload.gifts.length > 1 ? "s" : ""} sélectionnée{payload.gifts.length > 1 ? "s" : ""} par GiftSense
        </p>
      </motion.header>

      {/* Gifts */}
      <div className="w-full max-w-xl grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        {payload.gifts.map((gift, i) => (
          <GiftRow key={gift.title} gift={gift} index={i} />
        ))}
      </div>

      {/* CTA */}
      <motion.div
        className="text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <p className="text-stone-400 text-xs mb-3">Envie de créer ta propre liste ?</p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-gradient-to-r from-brand-600 to-brand-400 text-white font-semibold shadow-lg hover:shadow-brand-300/40 transition-shadow"
        >
          ✨ Essayer GiftSense gratuitement
        </Link>
      </motion.div>
    </main>
  );
}
