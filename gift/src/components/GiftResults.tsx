"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence, useMotionValue, useTransform, animate } from "framer-motion";
import type { AnalysisResult } from "@/types";
import GiftCard from "@/components/GiftCard";
import type { CartItem } from "@/lib/use-cart";

const BUDGET_FILTERS = [
  { label: "Tout", max: Infinity },
  { label: "< €50", max: 50 },
  { label: "< €100", max: 100 },
  { label: "< €200", max: 200 },
];

const ALL_CATEGORIES = "all";
const INITIAL_VISIBLE = 8;

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 28, scale: 0.96 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring" as const, stiffness: 280, damping: 24 },
  },
};

function parseLowerPrice(range: string): number {
  const match = range.match(/\d+/);
  return match ? parseInt(match[0], 10) : 0;
}

/** Animated number counter via framer-motion */
function AnimatedCount({ to }: { to: number }) {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (v) => Math.round(v));
  useEffect(() => {
    const ctrl = animate(count, to, { duration: 0.7, ease: "easeOut" });
    return ctrl.stop;
  }, [count, to]);
  return <motion.span>{rounded}</motion.span>;
}

interface Props {
  result: AnalysisResult;
  recipientName: string;
  onReset: () => void;
  showToast?: (msg: string) => void;
  cartItems: CartItem[];
  onAddToCart: (gift: import("@/types").GiftIdea) => void;
  onRemoveFromCart: (title: string) => void;
  isInCart: (title: string) => boolean;
}

export default function GiftResults({
  result,
  recipientName,
  onReset,
  showToast,
  onAddToCart,
  onRemoveFromCart,
  isInCart,
}: Props) {
  const [maxBudget, setMaxBudget] = useState(Infinity);
  const [trendingOnly, setTrendingOnly] = useState(false);
  const [activeCategory, setActiveCategory] = useState(ALL_CATEGORIES);
  const [feedback, setFeedback] = useState<Record<string, "up" | "down">>({});

  // Pool management: displayed vs hidden pool
  const [displayedGifts, setDisplayedGifts] = useState(result.giftIdeas.slice(0, INITIAL_VISIBLE));
  const poolRef = useRef(result.giftIdeas.slice(INITIAL_VISIBLE));

  // Reset when result changes
  useEffect(() => {
    setDisplayedGifts(result.giftIdeas.slice(0, INITIAL_VISIBLE));
    poolRef.current = result.giftIdeas.slice(INITIAL_VISIBLE);
  }, [result]);

  // Load persisted feedback
  useEffect(() => {
    try {
      const saved = localStorage.getItem("gift_feedback");
      if (saved) setFeedback(JSON.parse(saved));
    } catch {}
  }, []);

  const handleFeedback = useCallback(
    (title: string, type: "up" | "down") => {
      const updated = { ...feedback, [title]: type };
      setFeedback(updated);
      try { localStorage.setItem("gift_feedback", JSON.stringify(updated)); } catch {}
      showToast?.(type === "up" ? "Idée enregistrée 👍" : "Feedback noté 👎");
    },
    [feedback, showToast]
  );

  const handleAddToCart = useCallback(
    (gift: import("@/types").GiftIdea) => {
      onAddToCart(gift);
      showToast?.(`🛒 "${gift.title}" ajouté au panier !`);
    },
    [onAddToCart, showToast]
  );

  const handleRemoveFromCart = useCallback(
    (title: string) => {
      onRemoveFromCart(title);
      showToast?.("Retiré du panier");
    },
    [onRemoveFromCart, showToast]
  );

  /** Replace a gift (by title) with the next from the pool, cycling dismissed back in */
  const refreshGift = useCallback(
    (title: string) => {
      const pool = poolRef.current;
      if (pool.length === 0) {
        showToast?.("Plus d'alternatives disponibles 😔");
        return;
      }
      const [next, ...rest] = pool;
      const removed = displayedGifts.find((g) => g.title === title);
      setDisplayedGifts((prev) => prev.map((g) => (g.title === title ? next : g)));
      // Put dismissed card at end of pool so it can cycle back
      poolRef.current = removed ? [...rest, removed] : rest;
    },
    [displayedGifts, showToast]
  );

  const hasTrending = displayedGifts.some((g) => g.trending);
  const categories = Array.from(new Set(displayedGifts.map((g) => g.category.toLowerCase())));

  const filtered = displayedGifts.filter((g) => {
    if (trendingOnly && !g.trending) return false;
    if (activeCategory !== ALL_CATEGORIES && g.category.toLowerCase() !== activeCategory) return false;
    return parseLowerPrice(g.priceRange) < maxBudget;
  });

  const canRefresh = poolRef.current.length > 0;

  const copyList = () => {
    const text = [
      `🎁 Idées cadeaux pour ${recipientName}`,
      "",
      ...displayedGifts.map((g, i) => `${i + 1}. ${g.title} — ${g.priceRange}\n   ${g.reason}`),
    ].join("\n");
    navigator.clipboard.writeText(text).then(() => showToast?.("📋 Liste copiée !"));
  };

  const shareLink = () => {
    navigator.clipboard.writeText(window.location.href).then(() =>
      showToast?.("🔗 Lien copié ! Partagez-le à vos proches.")
    );
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

      {/* Sticky filter bar */}
      <div
        role="toolbar"
        aria-label="Filtres des cadeaux"
        className="sticky top-2 z-20 -mx-6 sm:-mx-8 px-6 sm:px-8 py-3 bg-white/90 dark:bg-gray-900/90 backdrop-blur-md border-b border-white/60 dark:border-gray-700/60 space-y-2 no-print"
      >
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

        {categories.length > 1 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 mr-1">Catégorie :</span>
            {[ALL_CATEGORIES, ...categories].map((cat) => (
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
                {cat === ALL_CATEGORIES ? "Tout" : cat}
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
          🎁 <AnimatedCount to={filtered.length} /> idée{filtered.length > 1 ? "s" : ""} cadeau parfaite{filtered.length > 1 ? "s" : ""}
        </motion.h2>

        <AnimatePresence mode="wait">
          {filtered.length === 0 ? (
            <motion.div
              key="empty"
              className="flex flex-col items-center justify-center py-14 gap-4 text-center"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
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
                <motion.div key={`${gift.title}-${i}`} variants={cardVariants} role="listitem">
                  <GiftCard
                    gift={gift}
                    index={i}
                    feedback={feedback}
                    onFeedback={handleFeedback}
                    onRefresh={canRefresh ? () => refreshGift(gift.title) : undefined}
                    canRefresh={canRefresh}
                    inCart={isInCart(gift.title)}
                    onAddToCart={handleAddToCart}
                    onRemoveFromCart={handleRemoveFromCart}
                  />
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Pool indicator */}
        {poolRef.current.length > 0 && (
          <motion.p
            className="text-xs text-gray-400 dark:text-gray-500 text-center mt-3"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            🔄 {poolRef.current.length} alternative{poolRef.current.length > 1 ? "s" : ""} disponible{poolRef.current.length > 1 ? "s" : ""} — cliquez &ldquo;Autre idée&rdquo; pour les découvrir
          </motion.p>
        )}
      </section>

      {/* Action buttons */}
      <div className="flex gap-2 flex-wrap no-print" role="group" aria-label="Actions">
        <motion.button
          onClick={copyList}
          aria-label="Copier la liste de cadeaux"
          className="flex-1 py-3 rounded-2xl border-2 border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 font-semibold bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm flex items-center justify-center gap-2 text-sm min-w-[120px]"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
        >
          📋 Copier
        </motion.button>
        <motion.button
          onClick={shareLink}
          aria-label="Copier le lien de partage"
          className="flex-1 py-3 rounded-2xl border-2 border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-300 font-semibold bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm flex items-center justify-center gap-2 text-sm min-w-[120px]"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
        >
          🔗 Partager
        </motion.button>
        <motion.button
          onClick={() => window.print()}
          aria-label="Exporter en PDF"
          className="py-3 px-4 rounded-2xl border-2 border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 font-semibold bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm text-sm"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
          title="Imprimer / PDF"
        >
          🖨️
        </motion.button>
      </div>

      <p className="text-xs text-gray-400 dark:text-gray-500 text-center no-print">
        Les liens Amazon peuvent inclure un tag affilié — nous percevons une petite commission sans coût supplémentaire pour vous.
      </p>

      <motion.button
        onClick={onReset}
        aria-label="Lancer une nouvelle recherche"
        className="w-full py-3 rounded-2xl border-2 border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-300 font-semibold bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm no-print"
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.98 }}
      >
        ↩ Nouvelle recherche
      </motion.button>
    </div>
  );
}
