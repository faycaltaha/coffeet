"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

interface Props {
  ariaLabel: string;
  onClose: () => void;
  header: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
}

export default function DrawerBase({ ariaLabel, onClose, header, footer, children }: Props) {
  return (
    <>
      <motion.div
        className="fixed inset-0 z-[90] bg-black/40 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        aria-hidden="true"
      />
      <motion.aside
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
        className="fixed right-0 top-0 bottom-0 z-[100] w-full max-w-sm bg-white dark:bg-stone-900 shadow-2xl flex flex-col"
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", stiffness: 340, damping: 38 }}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-stone-100 dark:border-stone-800">
          {header}
          <motion.button
            onClick={onClose}
            aria-label="Fermer"
            className="w-8 h-8 rounded-full flex items-center justify-center text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            ✕
          </motion.button>
        </div>

        <div className="flex-1 overflow-y-auto">{children}</div>

        {footer && (
          <div className="border-t border-stone-100 dark:border-stone-800 px-5 py-4">
            {footer}
          </div>
        )}
      </motion.aside>
    </>
  );
}
