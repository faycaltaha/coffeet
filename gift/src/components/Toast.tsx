"use client";

import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

export type ToastType = "success" | "error" | "info";

interface ToastProps {
  message: string;
  type?: ToastType;
  visible: boolean;
  onDismiss: () => void;
}

const STYLES: Record<ToastType, { bg: string; icon: string }> = {
  success: { bg: "bg-gray-900 dark:bg-gray-800", icon: "✅" },
  error:   { bg: "bg-red-600",                   icon: "❌" },
  info:    { bg: "bg-brand-600",                 icon: "ℹ️" },
};

export default function Toast({ message, type = "success", visible, onDismiss }: ToastProps) {
  useEffect(() => {
    if (!visible) return;
    const t = setTimeout(onDismiss, 2500);
    return () => clearTimeout(t);
  }, [visible, onDismiss]);

  const style = STYLES[type];

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="toast"
          role="status"
          aria-live="polite"
          initial={{ opacity: 0, y: 64, scale: 0.92 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 40, scale: 0.95 }}
          transition={{ type: "spring", stiffness: 380, damping: 28 }}
          className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-[200] flex items-center gap-2.5 px-5 py-3 rounded-2xl shadow-2xl text-white text-sm font-semibold backdrop-blur-sm select-none ${style.bg}`}
          onClick={onDismiss}
          style={{ maxWidth: "90vw", cursor: "pointer" }}
        >
          <span>{style.icon}</span>
          <span>{message}</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
