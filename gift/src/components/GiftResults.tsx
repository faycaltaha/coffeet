"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { AnalysisResult, GiftIdea } from "@/types";
import { amazonUrl, secondMerchant } from "@/lib/affiliate";

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
};

const BUDGET_FILTERS = [
  { label: "All", max: Infinity },
  { label: "< €50", max: 50 },
  { label: "< €100", max: 100 },
  { label: "< €200", max: 200 },
];

const ALL_CATEGORIES = "all";

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.07 } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 28, scale: 0.96 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring" as const, stiffness: 280, damping: 24 },
  },
  exit: { opacity: 0, scale: 0.94, transition: { duration: 0.2 } },
};

function categoryColor(cat: string) {
  return CATEGORY_COLORS[cat.toLowerCase()] ?? CATEGORY_COLORS.default;
}

function parseLowerPrice(range: string): number {
  const match = range.match(/\d+/);
  return match ? parseInt(match[0], 10) : 0;
}

function GiftCard({ gift, index }: { gift: GiftIdea; index: number }) {
  const trendColor = gift.trendSource
    ? (TREND_SOURCE_COLORS[gift.trendSource] ?? "bg-orange-500 text-white")
    : null;

  return (
    <motion.div
      variants={cardVariants}
      className={`bg-white/80 backdrop-blur-sm rounded-2xl p-5 border flex flex-col gap-3 group ${
        gift.trending
          ? "border-orange-300 ring-1 ring-orange-200 shadow-md shadow-orange-100/60"
          : "border-white/70 shadow-sm shadow-brand-100/40"
      }`}
      whileHover={{
        y: -5,
        boxShadow: gift.trending
          ? "0 16px 40px -8px rgba(251,146,60,0.25)"
          : "0 16px 40px -8px rgba(192,38,211,0.18)",
        transition: { type: "spring", stiffness: 400, damping: 22 },
      }}
    >
      {/* Trending banner */}
      {gift.trending && gift.trendSource && (
        <div className={`-mx-5 -mt-5 px-4 py-1.5 rounded-t-2xl flex items-center gap-2 text-xs font-semibold ${trendColor}`}>
          <span>🔥</span>
          <span>
            Trending on{" "}
            {gift.trendSource
              .replace(" Viral", "")
              .replace(" Trending", "")
              .replace(" Popular", "")}
          </span>
        </div>
      )}

      {/* Title row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <motion.span
            className="text-2xl"
            animate={{ rotate: [0, -8, 8, 0] }}
            transition={{ duration: 2.5, repeat: Infinity, delay: index * 0.3, ease: "easeInOut" }}
          >
            {CARD_EMOJIS[index % CARD_EMOJIS.length]}
          </motion.span>
          <h3 className="font-bold text-gray-900 leading-snug">{gift.title}</h3>
        </div>
        <span className="shrink-0 text-sm font-semibold text-brand-600 bg-brand-50/80 px-3 py-1 rounded-full border border-brand-100">
          {gift.priceRange}
        </span>
      </div>

      {/* Description */}
      <p className="text-gray-600 text-sm leading-relaxed">{gift.description}</p>

      {/* Tags */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full capitalize ${categoryColor(gift.category)}`}>
          {gift.category}
        </span>
        <span className="text-xs text-gray-400 italic">{gift.reason}</span>
      </div>

      {/* Affiliate CTAs */}
      <div className="mt-auto flex gap-2 pt-1">
        <motion.a
          href={amazonUrl(gift.searchQuery, AMAZON_TAG)}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 text-center py-2 rounded-xl text-sm font-semibold bg-amber-400 text-amber-900 shadow-sm"
          whileHover={{ scale: 1.03, backgroundColor: "#f59e0b" }}
          whileTap={{ scale: 0.97 }}
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
              className={`flex-1 text-center py-2 rounded-xl text-sm font-semibold ${merchant.className}`}
              whileHover={{ scale: 1.03, backgroundColor: merchant.hoverColor }}
              whileTap={{ scale: 0.97 }}
            >
              {merchant.icon} {merchant.label}
            </motion.a>
          );
        })()}
      </div>
    </motion.div>
  );
}

interface Props {
  result: AnalysisResult;
  recipientName: string;
  onReset: () => void;
}

export default function GiftResults({ result, recipientName, onReset }: Props) {
  const [maxBudget, setMaxBudget] = useState(Infinity);
  const [trendingOnly, setTrendingOnly] = useState(false);
  const [activeCategory, setActiveCategory] = useState(ALL_CATEGORIES);
  const [copied, setCopied] = useState(false);

  const hasTrending = result.giftIdeas.some((g) => g.trending);
  const categories = Array.from(new Set(result.giftIdeas.map((g) => g.category.toLowerCase())));

  const filtered = result.giftIdeas.filter((g) => {
    if (trendingOnly && !g.trending) return false;
    if (activeCategory !== ALL_CATEGORIES && g.category.toLowerCase() !== activeCategory) return false;
    return parseLowerPrice(g.priceRange) < maxBudget;
  });

  const copyList = () => {
    const text = [
      `🎁 Gift ideas for ${recipientName}`,
      "",
      ...result.giftIdeas.map(
        (g, i) => `${i + 1}. ${g.title} — ${g.priceRange}\n   ${g.reason}`
      ),
    ].join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  };

  return (
    <div className="space-y-6">
      {/* Profile summary */}
      <motion.div
        className="bg-gradient-to-r from-brand-500 to-purple-600 rounded-2xl p-5 text-white shadow-lg shadow-brand-300/30"
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
        <h2 className="text-lg font-bold mb-1">Profile Summary for {recipientName}</h2>
        <p className="text-brand-100 text-sm leading-relaxed">{result.profileSummary}</p>

        {result.interests.length > 0 && (
          <motion.div
            className="mt-3 flex flex-wrap gap-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            {result.interests.map((interest, i) => (
              <motion.span
                key={interest}
                className="bg-white/20 text-white text-xs px-2.5 py-0.5 rounded-full border border-white/20"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.25 + i * 0.05, type: "spring", stiffness: 400, damping: 20 }}
              >
                {interest}
              </motion.span>
            ))}
          </motion.div>
        )}
      </motion.div>

      {/* Filters */}
      <motion.div
        className="flex items-center gap-2 flex-wrap"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.35 }}
      >
        <span className="text-xs font-semibold text-gray-500 mr-1">Budget:</span>
        {BUDGET_FILTERS.map((f) => (
          <motion.button
            key={f.label}
            onClick={() => setMaxBudget(f.max)}
            className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
              maxBudget === f.max
                ? "bg-brand-500 text-white border-brand-500 shadow"
                : "bg-white/70 text-gray-600 border-gray-200 hover:border-brand-300"
            }`}
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.93 }}
          >
            {f.label}
          </motion.button>
        ))}
        {hasTrending && (
          <motion.button
            onClick={() => setTrendingOnly((v) => !v)}
            className={`ml-2 px-3 py-1 rounded-full text-xs font-semibold border flex items-center gap-1 transition-colors ${
              trendingOnly
                ? "bg-orange-500 text-white border-orange-500 shadow"
                : "bg-white/70 text-orange-500 border-orange-300 hover:border-orange-400"
            }`}
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.93 }}
          >
            🔥 Trending only
          </motion.button>
        )}
        <span className="ml-auto text-xs text-gray-400">{filtered.length} ideas</span>
      </motion.div>

      {/* Category filters */}
      {categories.length > 1 && (
        <motion.div
          className="flex items-center gap-2 flex-wrap"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.35 }}
        >
          <span className="text-xs font-semibold text-gray-500 mr-1">Catégorie:</span>
          <motion.button
            onClick={() => setActiveCategory(ALL_CATEGORIES)}
            className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
              activeCategory === ALL_CATEGORIES
                ? "bg-brand-500 text-white border-brand-500 shadow"
                : "bg-white/70 text-gray-600 border-gray-200 hover:border-brand-300"
            }`}
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.93 }}
          >
            Tout
          </motion.button>
          {categories.map((cat) => (
            <motion.button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-3 py-1 rounded-full text-xs font-semibold border capitalize transition-colors ${
                activeCategory === cat
                  ? "bg-brand-500 text-white border-brand-500 shadow"
                  : "bg-white/70 text-gray-600 border-gray-200 hover:border-brand-300"
              }`}
              whileHover={{ scale: 1.06 }}
              whileTap={{ scale: 0.93 }}
            >
              {cat}
            </motion.button>
          ))}
        </motion.div>
      )}

      {/* Gift grid */}
      <div>
        <motion.h2
          className="text-lg font-bold text-gray-900 mb-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          🎁 {filtered.length} Perfect Gift Ideas
        </motion.h2>

        <AnimatePresence mode="wait">
          {filtered.length === 0 ? (
            <motion.p
              key="empty"
              className="text-center text-gray-400 text-sm py-8"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              No gifts in this range. Try a higher budget filter.
            </motion.p>
          ) : (
            <motion.div
              key="grid"
              className="grid grid-cols-1 sm:grid-cols-2 gap-4"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
            >
              {filtered.map((gift, i) => (
                <GiftCard key={`${gift.title}-${i}`} gift={gift} index={i} />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Share / copy list */}
      <motion.button
        onClick={copyList}
        className="w-full py-3 rounded-2xl border-2 border-gray-200 text-gray-600 font-semibold bg-white/50 backdrop-blur-sm flex items-center justify-center gap-2 text-sm"
        whileHover={{ scale: 1.01, backgroundColor: "rgba(249,250,251,0.9)" }}
        whileTap={{ scale: 0.98 }}
        transition={{ type: "spring", stiffness: 400, damping: 20 }}
      >
        {copied ? "✅ Liste copiée !" : "📋 Copier la liste pour partager"}
      </motion.button>

      {/* Affiliate disclaimer */}
      <p className="text-xs text-gray-400 text-center">
        Amazon links may include an affiliate tag — we earn a small commission at no extra cost to you.
      </p>

      {/* Reset */}
      <motion.button
        onClick={onReset}
        className="w-full py-3 rounded-2xl border-2 border-brand-200 text-brand-600 font-semibold bg-white/50 backdrop-blur-sm"
        whileHover={{ scale: 1.01, backgroundColor: "rgba(253,244,255,0.7)" }}
        whileTap={{ scale: 0.98 }}
        transition={{ type: "spring", stiffness: 400, damping: 20 }}
      >
        Search Again
      </motion.button>
    </div>
  );
}
