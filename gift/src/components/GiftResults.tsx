"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence, useMotionValue, useTransform, animate } from "framer-motion";
import type { AnalysisResult, GiftIdea } from "@/types";
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

function getPlatformName(trendSource: string): string {
  return trendSource
    .replace(" Viral", "")
    .replace(" Trending", "")
    .replace(" Popular", "");
}

function PlatformIcon({ platform }: { platform: string }) {
  if (platform === "TikTok") {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5 shrink-0" aria-hidden="true">
        <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.67a8.26 8.26 0 0 0 4.83 1.54V6.76a4.85 4.85 0 0 1-1.06-.07z" />
      </svg>
    );
  }
  if (platform === "Instagram") {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5 shrink-0" aria-hidden="true">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
      </svg>
    );
  }
  if (platform === "Pinterest") {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5 shrink-0" aria-hidden="true">
        <path d="M12 0C5.373 0 0 5.373 0 12c0 5.084 3.163 9.426 7.627 11.174-.105-.949-.2-2.405.042-3.441.218-.937 1.407-5.965 1.407-5.965s-.359-.719-.359-1.782c0-1.668.967-2.914 2.171-2.914 1.023 0 1.518.769 1.518 1.69 0 1.029-.655 2.568-.994 3.995-.283 1.194.599 2.169 1.777 2.169 2.133 0 3.772-2.249 3.772-5.495 0-2.873-2.064-4.882-5.012-4.882-3.414 0-5.418 2.561-5.418 5.207 0 1.031.397 2.138.893 2.738a.36.36 0 0 1 .083.345l-.333 1.36c-.053.22-.174.267-.402.161-1.499-.698-2.436-2.889-2.436-4.649 0-3.785 2.75-7.262 7.929-7.262 4.163 0 7.398 2.967 7.398 6.931 0 4.136-2.607 7.464-6.227 7.464-1.216 0-2.359-.632-2.75-1.378l-.748 2.853c-.271 1.043-1.002 2.35-1.492 3.146C9.57 23.812 10.763 24 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0z" />
      </svg>
    );
  }
  if (platform === "YouTube") {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5 shrink-0" aria-hidden="true">
        <path d="M23.495 6.205a3.007 3.007 0 0 0-2.088-2.088c-1.87-.501-9.396-.501-9.396-.501s-7.507-.01-9.396.501A3.007 3.007 0 0 0 .527 6.205a31.247 31.247 0 0 0-.522 5.805 31.247 31.247 0 0 0 .522 5.783 3.007 3.007 0 0 0 2.088 2.088c1.868.502 9.396.502 9.396.502s7.506 0 9.396-.502a3.007 3.007 0 0 0 2.088-2.088 31.247 31.247 0 0 0 .5-5.783 31.247 31.247 0 0 0-.5-5.805zM9.609 15.601V8.408l6.264 3.602z" />
      </svg>
    );
  }
  return <span className="text-sm" aria-hidden="true">🔥</span>;
}

const BUDGET_FILTERS = [
  { label: "Tout", max: Infinity },
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

function trackClick(title: string, merchant: string) {
  try {
    const raw = localStorage.getItem("gift_clicks") || "[]";
    const clicks: { title: string; merchant: string; ts: number }[] = JSON.parse(raw);
    clicks.push({ title, merchant, ts: Date.now() });
    localStorage.setItem("gift_clicks", JSON.stringify(clicks.slice(-200)));
  } catch {}
}

/** Animated number counter via framer-motion */
function AnimatedCount({ to }: { to: number }) {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (v) => Math.round(v));

  useEffect(() => {
    const controls = animate(count, to, { duration: 0.7, ease: "easeOut" });
    return controls.stop;
  }, [count, to]);

  return <motion.span>{rounded}</motion.span>;
}

interface GiftCardProps {
  gift: GiftIdea;
  index: number;
  feedback: Record<string, "up" | "down">;
  onFeedback: (title: string, type: "up" | "down") => void;
}

function GiftCard({ gift, index, feedback, onFeedback }: GiftCardProps) {
  const trendColor = gift.trendSource
    ? (TREND_SOURCE_COLORS[gift.trendSource] ?? "bg-orange-500 text-white")
    : null;
  const myFeedback = feedback[gift.title];

  return (
    <motion.article
      variants={cardVariants}
      aria-label={`Cadeau : ${gift.title}`}
      className={`bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm rounded-2xl p-5 border flex flex-col gap-3 group ${
        gift.trending
          ? "border-orange-300 ring-1 ring-orange-200 shadow-md shadow-orange-100/60"
          : "border-white/70 dark:border-gray-700 shadow-sm shadow-brand-100/40"
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

      {/* Affiliate CTAs */}
      <div className="mt-auto flex gap-2 pt-1">
        <motion.a
          href={amazonUrl(gift.searchQuery, AMAZON_TAG)}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Trouver "${gift.title}" sur Amazon.fr`}
          className="flex-1 text-center py-2 rounded-xl text-sm font-semibold bg-amber-400 text-amber-900 shadow-sm"
          whileHover={{ scale: 1.03, backgroundColor: "#f59e0b" }}
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
              whileHover={{ scale: 1.03, backgroundColor: merchant.hoverColor }}
              whileTap={{ scale: 0.97 }}
              onClick={() => trackClick(gift.title, merchant.label)}
            >
              {merchant.icon} {merchant.label}
            </motion.a>
          );
        })()}
      </div>

      {/* Feedback */}
      <div className="flex items-center gap-2 pt-1 border-t border-gray-100 dark:border-gray-700">
        <span className="text-xs text-gray-400 dark:text-gray-500 flex-1">Cette idée vous plaît ?</span>
        <motion.button
          onClick={() => onFeedback(gift.title, "up")}
          aria-label="J'aime cette idée"
          aria-pressed={myFeedback === "up"}
          className={`w-8 h-8 rounded-full flex items-center justify-center text-base transition-colors ${
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
          className={`w-8 h-8 rounded-full flex items-center justify-center text-base transition-colors ${
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
    </motion.article>
  );
}

interface Props {
  result: AnalysisResult;
  recipientName: string;
  onReset: () => void;
  showToast?: (message: string) => void;
}

export default function GiftResults({ result, recipientName, onReset, showToast }: Props) {
  const [maxBudget, setMaxBudget] = useState(Infinity);
  const [trendingOnly, setTrendingOnly] = useState(false);
  const [activeCategory, setActiveCategory] = useState(ALL_CATEGORIES);
  const [feedback, setFeedback] = useState<Record<string, "up" | "down">>({});

  useEffect(() => {
    try {
      const saved = localStorage.getItem("gift_feedback");
      if (saved) setFeedback(JSON.parse(saved));
    } catch {}
  }, []);

  const handleFeedback = useCallback((title: string, type: "up" | "down") => {
    const updated = { ...feedback, [title]: type };
    setFeedback(updated);
    try {
      localStorage.setItem("gift_feedback", JSON.stringify(updated));
    } catch {}
    showToast?.(type === "up" ? "Idée enregistrée 👍" : "Feedback noté 👎");
  }, [feedback, showToast]);

  const hasTrending = result.giftIdeas.some((g) => g.trending);
  const categories = Array.from(new Set(result.giftIdeas.map((g) => g.category.toLowerCase())));

  const filtered = result.giftIdeas.filter((g) => {
    if (trendingOnly && !g.trending) return false;
    if (activeCategory !== ALL_CATEGORIES && g.category.toLowerCase() !== activeCategory) return false;
    return parseLowerPrice(g.priceRange) < maxBudget;
  });

  const copyList = () => {
    const text = [
      `🎁 Idées cadeaux pour ${recipientName}`,
      "",
      ...result.giftIdeas.map(
        (g, i) => `${i + 1}. ${g.title} — ${g.priceRange}\n   ${g.reason}`
      ),
    ].join("\n");
    navigator.clipboard.writeText(text).then(() => {
      showToast?.("📋 Liste copiée dans le presse-papier !");
    });
  };

  const shareLink = () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      showToast?.("🔗 Lien copié ! Partagez-le à vos proches.");
    });
  };

  const exportPDF = () => {
    window.print();
  };

  return (
    <div className="space-y-5">
      {/* Profile summary */}
      <motion.section
        aria-label={`Profil de ${recipientName}`}
        className="bg-gradient-to-r from-brand-500 to-purple-600 rounded-2xl p-5 text-white shadow-lg shadow-brand-300/30"
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
        <h2 className="text-lg font-bold mb-1">Profil de {recipientName}</h2>
        <p className="text-brand-100 text-sm leading-relaxed">{result.profileSummary}</p>

        {result.interests.length > 0 && (
          <motion.div
            className="mt-3 flex flex-wrap gap-2"
            aria-label="Centres d'intérêt détectés"
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
      </motion.section>

      {/* ── Sticky filter bar ── */}
      <div
        role="toolbar"
        aria-label="Filtres des cadeaux"
        className="sticky top-2 z-20 -mx-6 sm:-mx-8 px-6 sm:px-8 py-3 bg-white/90 dark:bg-gray-900/90 backdrop-blur-md border-b border-white/60 dark:border-gray-700/60 space-y-2 no-print"
      >
        {/* Budget */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 mr-1">Budget :</span>
          {BUDGET_FILTERS.map((f) => (
            <motion.button
              key={f.label}
              onClick={() => setMaxBudget(f.max)}
              aria-pressed={maxBudget === f.max}
              className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
                maxBudget === f.max
                  ? "bg-brand-500 text-white border-brand-500 shadow"
                  : "bg-white/70 text-gray-600 border-gray-200 hover:border-brand-300 dark:bg-gray-800/70 dark:text-gray-300 dark:border-gray-600"
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
              aria-pressed={trendingOnly}
              className={`ml-1 px-3 py-1 rounded-full text-xs font-semibold border flex items-center gap-1 transition-colors ${
                trendingOnly
                  ? "bg-orange-500 text-white border-orange-500 shadow"
                  : "bg-white/70 text-orange-500 border-orange-300 hover:border-orange-400 dark:bg-gray-800/70 dark:border-orange-700"
              }`}
              whileHover={{ scale: 1.06 }}
              whileTap={{ scale: 0.93 }}
            >
              🔥 Tendances
            </motion.button>
          )}
          <span className="ml-auto text-xs font-semibold text-brand-600 dark:text-brand-400 tabular-nums">
            <AnimatedCount to={filtered.length} /> idée{filtered.length > 1 ? "s" : ""}
          </span>
        </div>

        {/* Category filters */}
        {categories.length > 1 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 mr-1">Catégorie :</span>
            <motion.button
              onClick={() => setActiveCategory(ALL_CATEGORIES)}
              aria-pressed={activeCategory === ALL_CATEGORIES}
              className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
                activeCategory === ALL_CATEGORIES
                  ? "bg-brand-500 text-white border-brand-500 shadow"
                  : "bg-white/70 text-gray-600 border-gray-200 hover:border-brand-300 dark:bg-gray-800/70 dark:text-gray-300 dark:border-gray-600"
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
                aria-pressed={activeCategory === cat}
                className={`px-3 py-1 rounded-full text-xs font-semibold border capitalize transition-colors ${
                  activeCategory === cat
                    ? "bg-brand-500 text-white border-brand-500 shadow"
                    : "bg-white/70 text-gray-600 border-gray-200 hover:border-brand-300 dark:bg-gray-800/70 dark:text-gray-300 dark:border-gray-600"
                }`}
                whileHover={{ scale: 1.06 }}
                whileTap={{ scale: 0.93 }}
              >
                {cat}
              </motion.button>
            ))}
          </div>
        )}
      </div>

      {/* Gift grid */}
      <section aria-label="Liste des idées cadeaux">
        <motion.h2
          className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          🎁{" "}
          <AnimatedCount to={filtered.length} />{" "}
          idée{filtered.length > 1 ? "s" : ""} cadeau parfaite{filtered.length > 1 ? "s" : ""}
        </motion.h2>

        <AnimatePresence mode="wait">
          {filtered.length === 0 ? (
            <motion.div
              key="empty"
              className="flex flex-col items-center justify-center py-14 gap-4 text-center"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <motion.div
                className="text-6xl"
                animate={{ rotate: [-5, 5, -5], y: [0, -8, 0] }}
                transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
                aria-hidden="true"
              >
                🎁
              </motion.div>
              <p className="text-gray-500 dark:text-gray-400 font-semibold">Aucun cadeau dans cette sélection</p>
              <p className="text-gray-400 dark:text-gray-500 text-sm">
                Essaie un budget plus élevé ou retire un filtre.
              </p>
              <motion.button
                onClick={() => { setMaxBudget(Infinity); setActiveCategory(ALL_CATEGORIES); setTrendingOnly(false); }}
                className="px-5 py-2 rounded-full bg-brand-500 text-white text-sm font-semibold shadow"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Réinitialiser les filtres
              </motion.button>
            </motion.div>
          ) : (
            <motion.div
              key="grid"
              role="list"
              className="grid grid-cols-1 sm:grid-cols-2 gap-4"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
            >
              {filtered.map((gift, i) => (
                <GiftCard
                  key={`${gift.title}-${i}`}
                  gift={gift}
                  index={i}
                  feedback={feedback}
                  onFeedback={handleFeedback}
                />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* Action buttons */}
      <div className="flex gap-2 flex-wrap no-print" role="group" aria-label="Actions">
        <motion.button
          onClick={copyList}
          aria-label="Copier la liste de cadeaux"
          className="flex-1 py-3 rounded-2xl border-2 border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 font-semibold bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm flex items-center justify-center gap-2 text-sm min-w-[130px]"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
        >
          📋 Copier la liste
        </motion.button>

        <motion.button
          onClick={shareLink}
          aria-label="Copier le lien de partage"
          className="flex-1 py-3 rounded-2xl border-2 border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-300 font-semibold bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm flex items-center justify-center gap-2 text-sm min-w-[130px]"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
        >
          🔗 Partager
        </motion.button>

        <motion.button
          onClick={exportPDF}
          aria-label="Exporter en PDF"
          className="py-3 px-4 rounded-2xl border-2 border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 font-semibold bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm flex items-center justify-center gap-2 text-sm"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
          title="Imprimer / Enregistrer en PDF"
        >
          🖨️ PDF
        </motion.button>
      </div>

      {/* Affiliate disclaimer */}
      <p className="text-xs text-gray-400 dark:text-gray-500 text-center no-print">
        Les liens Amazon peuvent inclure un tag affilié — nous percevons une petite commission sans coût supplémentaire pour vous.
      </p>

      {/* Reset */}
      <motion.button
        onClick={onReset}
        aria-label="Lancer une nouvelle recherche"
        className="w-full py-3 rounded-2xl border-2 border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-300 font-semibold bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm no-print"
        whileHover={{ scale: 1.01, backgroundColor: "rgba(253,244,255,0.7)" }}
        whileTap={{ scale: 0.98 }}
        transition={{ type: "spring", stiffness: 400, damping: 20 }}
      >
        ↩ Nouvelle recherche
      </motion.button>
    </div>
  );
}
