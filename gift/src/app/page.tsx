"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ProfileForm, { type RecentSearch } from "@/components/ProfileForm";
import GiftResults from "@/components/GiftResults";
import LoadingSpinner from "@/components/LoadingSpinner";
import Toast, { type ToastType } from "@/components/Toast";
import type { AnalyzeRequest, AnalysisResult } from "@/types";
import { DEMO_RESULT } from "@/lib/demo-data";

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "result"; data: AnalysisResult; recipientName: string }
  | { status: "error"; message: string };

const LOADING_MESSAGES = [
  "Analyse des profils…",
  "Découverte des centres d'intérêt…",
  "Sélection des meilleures idées…",
  "Préparation des cadeaux parfaits…",
];

const PLATFORMS = [
  { icon: "📸", label: "Instagram" },
  { icon: "🎵", label: "TikTok" },
  { icon: "📌", label: "Pinterest" },
  { icon: "▶️", label: "YouTube" },
];

// --- Cache helpers ---
function cacheKey(data: AnalyzeRequest): string {
  try {
    return btoa(unescape(encodeURIComponent(JSON.stringify(data)))).slice(0, 80);
  } catch { return ""; }
}

function loadFromCache(data: AnalyzeRequest): AnalysisResult | null {
  try {
    const key = cacheKey(data);
    if (!key) return null;
    const raw = localStorage.getItem(`gift_cache_${key}`);
    if (!raw) return null;
    const { result, ts } = JSON.parse(raw);
    if (Date.now() - ts > 86_400_000) return null;
    return result;
  } catch { return null; }
}

function saveToCache(data: AnalyzeRequest, result: AnalysisResult) {
  try {
    const key = cacheKey(data);
    if (!key) return;
    localStorage.setItem(`gift_cache_${key}`, JSON.stringify({ result, ts: Date.now() }));
  } catch {}
}

// --- Recent searches ---
function loadRecentSearches(): RecentSearch[] {
  try { return JSON.parse(localStorage.getItem("gift_recent") || "[]"); }
  catch { return []; }
}

function saveRecentSearch(data: AnalyzeRequest) {
  try {
    const recent = loadRecentSearches().filter(
      (r) => r.data.recipientName !== data.recipientName
    );
    const label = `${data.recipientName} · ${data.occasion} · ${data.budget}`;
    recent.unshift({ label, data, ts: Date.now() });
    localStorage.setItem("gift_recent", JSON.stringify(recent.slice(0, 3)));
  } catch {}
}

// --- URL params ---
function encodeFormToUrl(data: AnalyzeRequest): string {
  const params = new URLSearchParams();
  params.set("name", data.recipientName);
  params.set("occasion", data.occasion);
  params.set("budget", data.budget);
  params.set("relationship", data.relationship);
  if (data.interests?.length) params.set("interests", data.interests.join(","));
  for (const p of data.profiles) params.set(p.platform, p.handle);
  return params.toString();
}

function decodeUrlToForm(): AnalyzeRequest | null {
  try {
    if (typeof window === "undefined") return null;
    const params = new URLSearchParams(window.location.search);
    const name = params.get("name");
    if (!name) return null;
    const profiles = (["instagram", "tiktok", "pinterest", "youtube"] as const)
      .filter((p) => params.get(p))
      .map((p) => ({ platform: p, handle: params.get(p)! }));
    return {
      recipientName: name,
      occasion: params.get("occasion") ?? "Birthday",
      budget: params.get("budget") ?? "€30–€75",
      relationship: params.get("relationship") ?? "Best Friend",
      interests: params.get("interests")?.split(",").filter(Boolean) ?? [],
      profiles,
    };
  } catch { return null; }
}

// --- Confetti ---
async function triggerConfetti() {
  try {
    const { default: confetti } = await import("canvas-confetti");
    confetti({
      particleCount: 130,
      spread: 80,
      origin: { y: 0.55 },
      colors: ["#d946ef", "#a855f7", "#ec4899", "#f59e0b", "#10b981"],
    });
  } catch {}
}

export default function HomePage() {
  const [state, setState] = useState<State>({ status: "idle" });
  const [loadingMsg, setLoadingMsg] = useState(LOADING_MESSAGES[0]);
  const [progress, setProgress] = useState(0);
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([]);
  const [darkMode, setDarkMode] = useState(false);
  const [prefill, setPrefill] = useState<AnalyzeRequest | null>(null);

  // Toast state
  const [toast, setToast] = useState<{ message: string; type: ToastType; visible: boolean }>({
    message: "",
    type: "success",
    visible: false,
  });

  // Ref for scroll-to-card on submit
  const cardRef = useRef<HTMLDivElement>(null);

  const showToast = useCallback((message: string, type: ToastType = "success") => {
    setToast({ message, type, visible: true });
  }, []);

  const dismissToast = useCallback(() => {
    setToast((t) => ({ ...t, visible: false }));
  }, []);

  useEffect(() => {
    // Dark mode
    const saved = localStorage.getItem("gift_dark");
    if (saved === "1") {
      setDarkMode(true);
      document.documentElement.classList.add("dark");
    }
    // Recent searches
    setRecentSearches(loadRecentSearches());
    // URL prefill
    const urlData = decodeUrlToForm();
    if (urlData) setPrefill(urlData);
  }, []);

  const toggleDark = () => {
    setDarkMode((prev) => {
      const next = !prev;
      document.documentElement.classList.toggle("dark", next);
      localStorage.setItem("gift_dark", next ? "1" : "0");
      return next;
    });
  };

  const scrollToCard = () => {
    cardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const runDemo = () => {
    setState({ status: "loading" });
    setProgress(0);
    const timer = setInterval(() => setProgress((p) => Math.min(p + 8, 92)), 200);
    scrollToCard();
    setTimeout(() => {
      clearInterval(timer);
      setProgress(100);
      setTimeout(() => {
        setState({ status: "result", data: DEMO_RESULT, recipientName: "Alex" });
        triggerConfetti();
      }, 300);
    }, 2200);
  };

  const handleSubmit = useCallback(async (data: AnalyzeRequest) => {
    window.history.replaceState(null, "", `?${encodeFormToUrl(data)}`);

    const cached = loadFromCache(data);
    if (cached) {
      setState({ status: "result", data: cached, recipientName: data.recipientName });
      triggerConfetti();
      showToast("Résultats chargés depuis le cache ⚡");
      scrollToCard();
      return;
    }

    setState({ status: "loading" });
    setProgress(0);
    scrollToCard();

    const ticker = setInterval(() => {
      setProgress((p) => {
        if (p < 30) return p + 5;
        if (p < 70) return p + 1.5;
        if (p < 90) return p + 0.5;
        return p;
      });
    }, 500);

    let msgIdx = 0;
    const msgInterval = setInterval(() => {
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

      clearInterval(ticker);
      setProgress(100);

      if (!json.success || !json.data) {
        setState({ status: "error", message: json.error ?? "Une erreur est survenue." });
      } else {
        saveToCache(data, json.data);
        saveRecentSearch(data);
        setRecentSearches(loadRecentSearches());
        setTimeout(() => {
          setState({ status: "result", data: json.data, recipientName: data.recipientName });
          triggerConfetti();
        }, 300);
      }
    } catch {
      clearInterval(ticker);
      setState({ status: "error", message: "Erreur réseau. Merci de réessayer." });
    } finally {
      clearInterval(msgInterval);
    }
  }, [showToast]);

  return (
    <>
      {/* Skip to content – accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[300] focus:px-4 focus:py-2 focus:bg-brand-600 focus:text-white focus:rounded-xl focus:font-semibold"
      >
        Aller au contenu principal
      </a>

      <main id="main-content" className="min-h-screen flex flex-col items-center py-12 px-4 relative overflow-hidden">
        {/* Dark mode toggle */}
        <motion.button
          onClick={toggleDark}
          aria-label={darkMode ? "Passer en mode clair" : "Passer en mode sombre"}
          aria-pressed={darkMode}
          className="fixed top-4 right-4 z-50 w-10 h-10 rounded-full bg-white/80 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-600 shadow-md flex items-center justify-center text-lg backdrop-blur-sm"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
        >
          {darkMode ? "☀️" : "🌙"}
        </motion.button>

        {/* Animated background orbs */}
        <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
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
        <motion.header
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
            className="text-gray-500 dark:text-gray-400 max-w-sm mx-auto text-sm leading-relaxed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.25, duration: 0.5 }}
          >
            Colle un pseudo de réseau social et notre IA analyse le profil public
            pour trouver des idées cadeaux personnalisées qu&apos;ils vont adorer.
          </motion.p>

          <motion.div
            className="flex justify-center gap-3 mt-5 flex-wrap"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.5 }}
            aria-label="Réseaux sociaux supportés"
          >
            {PLATFORMS.map(({ icon, label }, i) => (
              <motion.span
                key={label}
                className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 font-medium bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm px-3 py-1.5 rounded-full border border-white/80 dark:border-gray-600 shadow-sm"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.5 + i * 0.08, type: "spring", stiffness: 400, damping: 20 }}
              >
                <span aria-hidden="true">{icon}</span> {label}
              </motion.span>
            ))}
          </motion.div>

          <motion.button
            onClick={runDemo}
            aria-label="Voir une démonstration"
            className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-gradient-to-r from-brand-500 to-purple-500 text-white text-sm font-semibold shadow-lg shadow-brand-400/30"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.7, type: "spring", stiffness: 300, damping: 20 }}
            whileHover={{ scale: 1.06, boxShadow: "0 8px 24px -4px rgba(192,38,211,0.45)" }}
            whileTap={{ scale: 0.95 }}
          >
            ▶ Voir une démo
          </motion.button>
        </motion.header>

        {/* Glass card */}
        <motion.div
          ref={cardRef}
          className="w-full max-w-xl glass dark:glass-dark rounded-3xl shadow-2xl shadow-brand-200/30 dark:shadow-purple-900/30 p-6 sm:p-8"
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
                <ProfileForm
                  onSubmit={handleSubmit}
                  loading={false}
                  recentSearches={recentSearches}
                  prefill={prefill}
                />
              </motion.div>
            )}

            {state.status === "loading" && (
              <motion.div
                key="loading"
                initial={{ opacity: 0, scale: 0.93 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.93 }}
                transition={{ duration: 0.3 }}
                aria-live="polite"
                aria-label="Analyse en cours"
              >
                <LoadingSpinner message={loadingMsg} progress={progress} />
              </motion.div>
            )}

            {state.status === "error" && (
              <motion.div
                key="error"
                role="alert"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                <motion.div
                  className="bg-red-50/80 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl p-4 text-sm text-red-700 dark:text-red-400"
                  initial={{ x: -8 }}
                  animate={{ x: 0 }}
                  transition={{ type: "spring", stiffness: 400, damping: 20 }}
                >
                  <strong className="font-semibold">Oups !</strong> {state.message}
                </motion.div>
                <motion.button
                  onClick={() => setState({ status: "idle" })}
                  className="w-full py-3 rounded-2xl border-2 border-brand-200 text-brand-600 font-semibold bg-white/50 dark:bg-gray-800/50 dark:border-brand-700 dark:text-brand-400"
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Réessayer
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
                  onReset={() => {
                    setState({ status: "idle" });
                    window.history.replaceState(null, "", window.location.pathname);
                  }}
                  showToast={showToast}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Footer */}
        <motion.footer
          className="mt-8 text-xs text-gray-400 dark:text-gray-500 text-center max-w-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
        >
          GiftSense n&apos;analyse que les données publiques des réseaux sociaux.
          Aucun mot de passe ni accès privé requis.
        </motion.footer>
      </main>

      {/* Global toast */}
      <Toast message={toast.message} type={toast.type} visible={toast.visible} onDismiss={dismissToast} />
    </>
  );
}
