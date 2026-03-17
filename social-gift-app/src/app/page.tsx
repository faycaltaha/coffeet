"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ProfileForm from "@/components/ProfileForm";
import GiftResults from "@/components/GiftResults";
import LoadingSpinner from "@/components/LoadingSpinner";
import type { AnalyzeRequest, AnalysisResult } from "@/types";
import { DEMO_RESULT } from "@/lib/demo-data";

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "result"; data: AnalysisResult; recipientName: string }
  | { status: "error"; message: string };

const LOADING_MESSAGES = [
  "Browsing social profiles…",
  "Discovering hidden interests…",
  "Curating personalised ideas…",
  "Wrapping up the perfect gifts…",
];

const PLATFORMS = [
  { icon: "📸", label: "Instagram" },
  { icon: "🎵", label: "TikTok" },
  { icon: "📌", label: "Pinterest" },
];

export default function HomePage() {
  const [state, setState] = useState<State>({ status: "idle" });
  const [loadingMsg, setLoadingMsg] = useState(LOADING_MESSAGES[0]);

  const runDemo = () => {
    setState({ status: "loading" });
    setTimeout(() => {
      setState({ status: "result", data: DEMO_RESULT, recipientName: "Alex" });
    }, 2200);
  };

  const handleSubmit = async (data: AnalyzeRequest) => {
    setState({ status: "loading" });
    let msgIdx = 0;
    const interval = setInterval(() => {
      msgIdx = (msgIdx + 1) % LOADING_MESSAGES.length;
      setLoadingMsg(LOADING_MESSAGES[msgIdx]);
    }, 3000);

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const json = await res.json();
      if (!json.success || !json.data) {
        setState({ status: "error", message: json.error ?? "Something went wrong." });
      } else {
        setState({ status: "result", data: json.data, recipientName: data.recipientName });
      }
    } catch {
      setState({ status: "error", message: "Network error. Please try again." });
    } finally {
      clearInterval(interval);
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center py-12 px-4 relative overflow-hidden">
      {/* Animated background orbs */}
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <motion.div
          className="absolute -top-32 -left-32 w-[600px] h-[600px] rounded-full bg-brand-300/25 blur-3xl"
          animate={{ x: [0, 50, 0], y: [0, 40, 0] }}
          transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute -bottom-32 -right-32 w-[550px] h-[550px] rounded-full bg-purple-300/25 blur-3xl"
          animate={{ x: [0, -50, 0], y: [0, -40, 0] }}
          transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute top-1/3 left-1/2 w-[350px] h-[350px] rounded-full bg-pink-200/20 blur-3xl"
          animate={{ x: [0, 30, -30, 0], y: [0, -30, 30, 0] }}
          transition={{ duration: 24, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>

      {/* Header */}
      <motion.div
        className="text-center mb-10"
        initial={{ opacity: 0, y: -32 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      >
        <motion.h1
          className="text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-brand-600 via-purple-600 to-pink-500 mb-3 tracking-tight"
          initial={{ scale: 0.85, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.6, ease: [0.34, 1.56, 0.64, 1] }}
        >
          🎁 GiftSense
        </motion.h1>
        <motion.p
          className="text-gray-500 max-w-sm mx-auto text-sm leading-relaxed"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.25, duration: 0.5 }}
        >
          Paste a social media handle and our AI scans their public profile to
          surface personalised gift ideas they&apos;ll actually love.
        </motion.p>

        <motion.div
          className="flex justify-center gap-5 mt-5"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.5 }}
        >
          {PLATFORMS.map(({ icon, label }, i) => (
            <motion.span
              key={label}
              className="flex items-center gap-1.5 text-xs text-gray-500 font-medium bg-white/70 backdrop-blur-sm px-3 py-1.5 rounded-full border border-white/80 shadow-sm"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5 + i * 0.08, type: "spring", stiffness: 400, damping: 20 }}
            >
              {icon} {label}
            </motion.span>
          ))}
        </motion.div>

        <motion.button
          onClick={runDemo}
          className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-gradient-to-r from-brand-500 to-purple-500 text-white text-sm font-semibold shadow-lg shadow-brand-400/30"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.7, type: "spring", stiffness: 300, damping: 20 }}
          whileHover={{ scale: 1.06, boxShadow: "0 8px 24px -4px rgba(192,38,211,0.45)" }}
          whileTap={{ scale: 0.95 }}
        >
          ▶ See a demo
        </motion.button>
      </motion.div>

      {/* Glass card */}
      <motion.div
        className="w-full max-w-xl glass rounded-3xl shadow-2xl shadow-brand-200/30 p-6 sm:p-8"
        initial={{ opacity: 0, y: 48, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.65, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
      >
        <AnimatePresence mode="wait">
          {state.status === "idle" && (
            <motion.div
              key="idle"
              initial={{ opacity: 0, x: -24 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 24 }}
              transition={{ duration: 0.35, ease: "easeInOut" }}
            >
              <ProfileForm onSubmit={handleSubmit} loading={false} />
            </motion.div>
          )}

          {state.status === "loading" && (
            <motion.div
              key="loading"
              initial={{ opacity: 0, scale: 0.93 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.93 }}
              transition={{ duration: 0.3 }}
            >
              <LoadingSpinner message={loadingMsg} />
            </motion.div>
          )}

          {state.status === "error" && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              <motion.div
                className="bg-red-50/80 border border-red-200 rounded-2xl p-4 text-sm text-red-700"
                initial={{ x: -8 }}
                animate={{ x: 0 }}
                transition={{ type: "spring", stiffness: 400, damping: 20 }}
              >
                <strong className="font-semibold">Oops!</strong> {state.message}
              </motion.div>
              <motion.button
                onClick={() => setState({ status: "idle" })}
                className="w-full py-3 rounded-2xl border-2 border-brand-200 text-brand-600 font-semibold bg-white/50"
                whileHover={{ scale: 1.01, backgroundColor: "rgba(253,244,255,0.8)" }}
                whileTap={{ scale: 0.98 }}
              >
                Try Again
              </motion.button>
            </motion.div>
          )}

          {state.status === "result" && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -24 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            >
              <GiftResults
                result={state.data}
                recipientName={state.recipientName}
                onReset={() => setState({ status: "idle" })}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Footer */}
      <motion.p
        className="mt-8 text-xs text-gray-400 text-center max-w-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
      >
        GiftSense only analyses publicly available social media data.
        No passwords or private access required.
      </motion.p>
    </main>
  );
}
