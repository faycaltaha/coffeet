"use client";

import { useState } from "react";
import ProfileForm from "@/components/ProfileForm";
import GiftResults from "@/components/GiftResults";
import LoadingSpinner from "@/components/LoadingSpinner";
import type { AnalyzeRequest, AnalysisResult } from "@/types";

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

export default function HomePage() {
  const [state, setState] = useState<State>({ status: "idle" });
  const [loadingMsg, setLoadingMsg] = useState(LOADING_MESSAGES[0]);

  const handleSubmit = async (data: AnalyzeRequest) => {
    setState({ status: "loading" });

    // Cycle loading messages
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
    <main className="min-h-screen flex flex-col items-center py-12 px-4">
      {/* Header */}
      <div className="text-center mb-10">
        <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-purple-600 mb-2">
          🎁 GiftSense
        </h1>
        <p className="text-gray-600 max-w-md mx-auto text-sm">
          Paste a social media handle and our AI scans their public profile to
          surface personalised gift ideas they'll actually love.
        </p>

        <div className="flex justify-center gap-6 mt-5 text-xs text-gray-500">
          {[
            { icon: "📸", label: "Instagram" },
            { icon: "🎵", label: "TikTok" },
            { icon: "📌", label: "Pinterest" },
          ].map(({ icon, label }) => (
            <span key={label} className="flex items-center gap-1 font-medium">
              {icon} {label}
            </span>
          ))}
        </div>
      </div>

      {/* Card */}
      <div className="w-full max-w-xl bg-white rounded-3xl shadow-xl shadow-brand-100/50 border border-brand-100 p-6 sm:p-8">
        {state.status === "idle" && (
          <ProfileForm onSubmit={handleSubmit} loading={false} />
        )}
        {state.status === "loading" && (
          <LoadingSpinner message={loadingMsg} />
        )}
        {state.status === "error" && (
          <div className="space-y-4">
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
              <strong className="font-semibold">Oops!</strong> {state.message}
            </div>
            <button
              onClick={() => setState({ status: "idle" })}
              className="w-full py-3 rounded-xl border-2 border-brand-200 text-brand-600 font-semibold hover:bg-brand-50 transition"
            >
              Try Again
            </button>
          </div>
        )}
        {state.status === "result" && (
          <GiftResults
            result={state.data}
            recipientName={state.recipientName}
            onReset={() => setState({ status: "idle" })}
          />
        )}
      </div>

      {/* Footer */}
      <p className="mt-8 text-xs text-gray-400 text-center max-w-sm">
        GiftSense only analyses publicly available social media data.
        No passwords or private access required.
      </p>
    </main>
  );
}
