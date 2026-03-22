"use client";

import { useState } from "react";
import ProfileForm from "@/components/ProfileForm";
import LoadingSpinner from "@/components/LoadingSpinner";
import type { AnalyzeRequest, AnalyzeResponse, GiftIdea } from "@/types";

export default function Page() {
  const [loading, setLoading] = useState(false);
  const [gifts, setGifts] = useState<GiftIdea[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(data: AnalyzeRequest) {
    setLoading(true);
    setGifts(null);
    setError(null);

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const json: AnalyzeResponse = await res.json();
      if (json.success && json.data) {
        setGifts(json.data.giftIdeas);
      } else {
        setError(json.error ?? "Erreur inconnue");
      }
    } catch {
      setError("Impossible de contacter le serveur.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-stone-50 py-10 px-4">
      <div className="max-w-xl mx-auto">
        <h1 className="text-2xl font-bold text-center mb-8 text-stone-800">
          🎁 Trouve le cadeau parfait
        </h1>

        {!loading && !gifts && (
          <ProfileForm onSubmit={handleSubmit} loading={loading} />
        )}

        {loading && (
          <LoadingSpinner message="L'IA analyse les profils et cherche des idées…" />
        )}

        {error && (
          <div className="mt-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}

        {gifts && (
          <div className="mt-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-stone-700">
                {gifts.length} idées cadeaux
              </h2>
              <button
                onClick={() => setGifts(null)}
                className="text-sm text-stone-500 underline"
              >
                ← Nouvelle recherche
              </button>
            </div>
            {gifts.map((gift, i) => (
              <div key={i} className="bg-white rounded-2xl shadow-sm border border-stone-100 p-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-stone-800">{gift.title}</h3>
                  <span className="text-sm font-medium text-stone-500 shrink-0">{gift.priceRange}</span>
                </div>
                <p className="text-sm text-stone-600">{gift.description}</p>
                <p className="text-xs text-stone-400 italic">{gift.reason}</p>
                {gift.trending && (
                  <span className="inline-block text-xs bg-pink-100 text-pink-600 px-2 py-0.5 rounded-full font-medium">
                    🔥 Tendance {gift.trendSource}
                  </span>
                )}
                {gift.affiliateLinks && (
                  <div className="flex gap-2 pt-1">
                    <a
                      href={gift.affiliateLinks.amazon}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs bg-amber-400 hover:bg-amber-500 text-white px-3 py-1.5 rounded-lg font-medium transition-colors"
                    >
                      Amazon
                    </a>
                    <a
                      href={gift.affiliateLinks.secondary.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs bg-stone-700 hover:bg-stone-800 text-white px-3 py-1.5 rounded-lg font-medium transition-colors"
                    >
                      {gift.affiliateLinks.secondary.label}
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
