"use client";

import { motion, AnimatePresence } from "framer-motion";
import DrawerBase from "@/components/DrawerBase";
import { amazonUrl, secondMerchant } from "@/lib/affiliate-client";
import { trackClick } from "@/lib/tracking";
import type { WatchedItem } from "@/types";

const AMAZON_TAG = process.env.NEXT_PUBLIC_AMAZON_AFFILIATE_TAG;

function daysSince(ts: number) {
  return Math.floor((Date.now() - ts) / 86_400_000);
}

interface Props {
  items: WatchedItem[];
  onRemove: (title: string) => void;
  onClose: () => void;
  showToast?: (msg: string) => void;
}

export default function PriceWatchDrawer({ items, onRemove, onClose, showToast }: Props) {
  const header = (
    <div className="flex items-center gap-2">
      <span className="text-2xl" aria-hidden="true">🔔</span>
      <h2 className="text-lg font-bold text-stone-900 dark:text-stone-100">Alertes prix</h2>
      {items.length > 0 && (
        <span className="bg-brand-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
          {items.length}
        </span>
      )}
    </div>
  );

  return (
    <DrawerBase ariaLabel="Alertes prix" onClose={onClose} header={header}>
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
              🔔
            </motion.div>
            <p className="text-stone-500 dark:text-stone-400 font-semibold">Aucune alerte active</p>
            <p className="text-stone-400 dark:text-stone-500 text-sm">
              Cliquez sur 🔔 sur une idée cadeau pour surveiller son prix.
            </p>
          </motion.div>
        ) : (
          <ul className="divide-y divide-stone-100 dark:divide-stone-800">
            {items.map((item) => {
              const days = daysSince(item.savedAt);
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
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-semibold text-sm text-stone-900 dark:text-stone-100 leading-snug">
                        {item.gift.title}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                        <span className="text-xs text-brand-600 dark:text-brand-400 font-semibold">
                          {item.gift.priceRange}
                        </span>
                        <span className="text-xs text-stone-400 dark:text-stone-500">
                          {days === 0 ? "Sauvegardé aujourd'hui" : `Il y a ${days} j`}
                        </span>
                      </div>
                    </div>
                    <motion.button
                      onClick={() => { onRemove(item.gift.title); showToast?.("Alerte supprimée"); }}
                      aria-label={`Supprimer l'alerte pour "${item.gift.title}"`}
                      className="shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-stone-400 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/30 transition-colors text-sm"
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                    >
                      ✕
                    </motion.button>
                  </div>

                  <div className="flex gap-2">
                    <motion.a
                      href={amazonUrl(item.gift.searchQuery, AMAZON_TAG)}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Vérifier le prix de "${item.gift.title}" sur Amazon.fr`}
                      className="flex-1 text-center py-1.5 rounded-lg text-xs font-semibold bg-amber-400 text-amber-900 shadow-sm"
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => trackClick(item.gift.title, "Amazon")}
                    >
                      🛒 Vérifier Amazon
                    </motion.a>
                    <motion.a
                      href={merchant.url(item.gift.searchQuery)}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Vérifier le prix de "${item.gift.title}" sur ${merchant.label}`}
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
    </DrawerBase>
  );
}
