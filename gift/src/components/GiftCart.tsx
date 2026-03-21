"use client";

import { motion, AnimatePresence } from "framer-motion";
import { amazonUrl, secondMerchant } from "@/lib/affiliate-client";
import { trackClick } from "@/lib/tracking";
import type { CartItem } from "@/lib/use-cart";

const AMAZON_TAG = process.env.NEXT_PUBLIC_AMAZON_AFFILIATE_TAG;

interface Props {
  items: CartItem[];
  onRemove: (title: string) => void;
  onClear: () => void;
  onClose: () => void;
  showToast?: (msg: string) => void;
}

export default function GiftCart({ items, onRemove, onClear, onClose, showToast }: Props) {
  const copyCart = () => {
    const text = [
      `🛒 Ma liste de cadeaux (${items.length})`,
      "",
      ...items.map(
        (item, i) =>
          `${i + 1}. ${item.gift.title} — ${item.gift.priceRange}\n   ${item.gift.reason}`
      ),
    ].join("\n");
    navigator.clipboard.writeText(text).then(() => {
      showToast?.("📋 Liste du panier copiée !");
    });
  };

  const shareCart = () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      showToast?.("🔗 Lien copié !");
    });
  };

  return (
    <>
      {/* Overlay */}
      <motion.div
        className="fixed inset-0 z-[90] bg-black/40 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <motion.aside
        role="dialog"
        aria-modal="true"
        aria-label="Mon panier de cadeaux"
        className="fixed right-0 top-0 bottom-0 z-[100] w-full max-w-sm bg-white dark:bg-gray-900 shadow-2xl flex flex-col"
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", stiffness: 340, damping: 38 }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <span className="text-2xl" aria-hidden="true">🛒</span>
            <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
              Mon panier
            </h2>
            {items.length > 0 && (
              <span className="bg-brand-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                {items.length}
              </span>
            )}
          </div>
          <motion.button
            onClick={onClose}
            aria-label="Fermer le panier"
            className="w-8 h-8 rounded-full flex items-center justify-center text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            ✕
          </motion.button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          <AnimatePresence mode="popLayout">
            {items.length === 0 ? (
              <motion.div
                key="empty"
                className="flex flex-col items-center justify-center h-full gap-4 py-20 text-center px-6"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
              >
                <motion.div
                  className="text-6xl"
                  animate={{ y: [0, -8, 0] }}
                  transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
                  aria-hidden="true"
                >
                  🛒
                </motion.div>
                <p className="text-gray-500 dark:text-gray-400 font-semibold">
                  Votre panier est vide
                </p>
                <p className="text-gray-400 dark:text-gray-500 text-sm">
                  Swipe à droite ou cliquez sur &ldquo;+ Panier&rdquo; sur une idée pour l&apos;ajouter ici.
                </p>
              </motion.div>
            ) : (
              <ul className="divide-y divide-gray-100 dark:divide-gray-800">
                {items.map((item) => {
                  const merchant = secondMerchant(item.gift.category);
                  return (
                    <motion.li
                      key={item.gift.title}
                      layout
                      initial={{ opacity: 0, x: 40 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 40, height: 0 }}
                      transition={{ type: "spring", stiffness: 350, damping: 30 }}
                      className="px-5 py-4 flex flex-col gap-2"
                    >
                      {/* Title + price + remove */}
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="font-semibold text-sm text-gray-900 dark:text-gray-100 leading-snug">
                            {item.gift.title}
                          </p>
                          <p className="text-xs text-brand-600 dark:text-brand-400 font-semibold mt-0.5">
                            {item.gift.priceRange}
                          </p>
                        </div>
                        <motion.button
                          onClick={() => onRemove(item.gift.title)}
                          aria-label={`Retirer "${item.gift.title}" du panier`}
                          className="shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-gray-400 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/30 transition-colors text-sm"
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                        >
                          ✕
                        </motion.button>
                      </div>

                      {/* Reason */}
                      <p className="text-xs text-gray-500 dark:text-gray-400 italic leading-snug">
                        {item.gift.reason}
                      </p>

                      {/* Affiliate links */}
                      <div className="flex gap-2">
                        <motion.a
                          href={amazonUrl(item.gift.searchQuery, AMAZON_TAG)}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`Acheter "${item.gift.title}" sur Amazon.fr`}
                          className="flex-1 text-center py-1.5 rounded-lg text-xs font-semibold bg-amber-400 text-amber-900 shadow-sm"
                          whileHover={{ scale: 1.03 }}
                          whileTap={{ scale: 0.97 }}
                          onClick={() => trackClick(item.gift.title, "Amazon")}
                        >
                          🛒 Amazon.fr
                        </motion.a>
                        <motion.a
                          href={merchant.url(item.gift.searchQuery)}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`Acheter "${item.gift.title}" sur ${merchant.label}`}
                          className={`flex-1 text-center py-1.5 rounded-lg text-xs font-semibold ${merchant.className}`}
                          whileHover={{ scale: 1.03 }}
                          whileTap={{ scale: 0.97 }}
                          onClick={() => trackClick(item.gift.title, merchant.label)}
                        >
                          {merchant.icon} {merchant.label}
                        </motion.a>
                      </div>
                    </motion.li>
                  );
                })}
              </ul>
            )}
          </AnimatePresence>
        </div>

        {/* Footer actions */}
        {items.length > 0 && (
          <div className="border-t border-gray-100 dark:border-gray-800 px-5 py-4 space-y-2">
            <div className="flex gap-2">
              <motion.button
                onClick={copyCart}
                aria-label="Copier la liste du panier"
                className="flex-1 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 text-sm font-semibold bg-gray-50 dark:bg-gray-800"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                📋 Copier
              </motion.button>
              <motion.button
                onClick={shareCart}
                aria-label="Partager le panier"
                className="flex-1 py-2.5 rounded-xl border border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-300 text-sm font-semibold bg-brand-50/50 dark:bg-brand-900/20"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                🔗 Partager
              </motion.button>
            </div>
            <motion.button
              onClick={() => { onClear(); showToast?.("Panier vidé"); }}
              aria-label="Vider le panier"
              className="w-full py-2 rounded-xl text-xs text-red-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors font-medium"
              whileTap={{ scale: 0.98 }}
            >
              🗑 Vider le panier
            </motion.button>
          </div>
        )}
      </motion.aside>
    </>
  );
}
