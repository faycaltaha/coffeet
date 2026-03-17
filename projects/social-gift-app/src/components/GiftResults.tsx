"use client";

import { useState } from "react";
import type { AnalysisResult, GiftIdea } from "@/types";
import { amazonUrl, fnacUrl } from "@/lib/affiliate";

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

function categoryColor(cat: string) {
  return CATEGORY_COLORS[cat.toLowerCase()] ?? CATEGORY_COLORS.default;
}

/** Extract the lower bound of a price range like "€30–€75" → 30 */
function parseLowerPrice(range: string): number {
  const match = range.match(/\d+/);
  return match ? parseInt(match[0], 10) : 0;
}

const BUDGET_FILTERS = [
  { label: "All", max: Infinity },
  { label: "< €50", max: 50 },
  { label: "< €100", max: 100 },
  { label: "< €200", max: 200 },
];

const TREND_SOURCE_COLORS: Record<string, string> = {
  "TikTok Viral": "bg-[#010101] text-white",
  "Instagram Trending": "bg-gradient-to-r from-purple-500 to-pink-500 text-white",
  "Pinterest Popular": "bg-red-600 text-white",
};

function GiftCard({ gift, index }: { gift: GiftIdea; index: number }) {
  const trendColor = gift.trendSource
    ? (TREND_SOURCE_COLORS[gift.trendSource] ?? "bg-orange-500 text-white")
    : null;

  return (
    <div className={`bg-white rounded-2xl p-5 shadow-sm border hover:shadow-md transition-shadow flex flex-col gap-3 group ${gift.trending ? "border-orange-300 ring-1 ring-orange-200" : "border-gray-100"}`}>
      {/* Trending banner */}
      {gift.trending && gift.trendSource && (
        <div className={`-mx-5 -mt-5 px-4 py-1.5 rounded-t-2xl flex items-center gap-2 text-xs font-semibold ${trendColor}`}>
          <span>🔥</span>
          <span>Trending on {gift.trendSource.replace(" Viral", "").replace(" Trending", "").replace(" Popular", "")}</span>
        </div>
      )}

      {/* Title row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{CARD_EMOJIS[index % CARD_EMOJIS.length]}</span>
          <h3 className="font-bold text-gray-900 leading-snug">{gift.title}</h3>
        </div>
        <span className="shrink-0 text-sm font-semibold text-brand-600 bg-brand-50 px-3 py-1 rounded-full">
          {gift.priceRange}
        </span>
      </div>

      {/* Description */}
      <p className="text-gray-600 text-sm leading-relaxed">{gift.description}</p>

      {/* Tags */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full capitalize ${categoryColor(gift.category)}`}>
          {gift.category}
        </span>
        <span className="text-xs text-gray-400 italic">{gift.reason}</span>
      </div>

      {/* Affiliate CTAs */}
      <div className="mt-auto flex gap-2 pt-1">
        <a
          href={amazonUrl(gift.searchQuery, AMAZON_TAG)}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 text-center py-2 rounded-xl text-sm font-semibold bg-amber-400 hover:bg-amber-500 text-amber-900 transition shadow-sm"
        >
          🛒 Amazon.fr
        </a>
        <a
          href={fnacUrl(gift.searchQuery)}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 text-center py-2 rounded-xl text-sm font-semibold bg-yellow-50 hover:bg-yellow-100 text-yellow-800 border border-yellow-200 transition"
        >
          🟡 Fnac
        </a>
      </div>
    </div>
  );
}

interface Props {
  result: AnalysisResult;
  recipientName: string;
  onReset: () => void;
}

export default function GiftResults({ result, recipientName, onReset }: Props) {
  const [maxBudget, setMaxBudget] = useState(Infinity);
  const [trendingOnly, setTrendingOnly] = useState(false);

  const hasTrending = result.giftIdeas.some((g) => g.trending);

  const filtered = result.giftIdeas.filter((g) => {
    if (trendingOnly && !g.trending) return false;
    return parseLowerPrice(g.priceRange) < maxBudget;
  });

  return (
    <div className="space-y-6">
      {/* Profile summary */}
      <div className="bg-gradient-to-r from-brand-500 to-purple-600 rounded-2xl p-5 text-white shadow-lg">
        <h2 className="text-lg font-bold mb-1">Profile Summary for {recipientName}</h2>
        <p className="text-brand-100 text-sm leading-relaxed">{result.profileSummary}</p>

        {result.interests.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {result.interests.map((interest) => (
              <span key={interest} className="bg-white/20 text-white text-xs px-2.5 py-0.5 rounded-full">
                {interest}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-semibold text-gray-500 mr-1">Budget:</span>
        {BUDGET_FILTERS.map((f) => (
          <button
            key={f.label}
            onClick={() => setMaxBudget(f.max)}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition border ${
              maxBudget === f.max
                ? "bg-brand-500 text-white border-brand-500 shadow"
                : "bg-white text-gray-600 border-gray-200 hover:border-brand-300"
            }`}
          >
            {f.label}
          </button>
        ))}
        {hasTrending && (
          <button
            onClick={() => setTrendingOnly((v) => !v)}
            className={`ml-2 px-3 py-1 rounded-full text-xs font-semibold transition border flex items-center gap-1 ${
              trendingOnly
                ? "bg-orange-500 text-white border-orange-500 shadow"
                : "bg-white text-orange-500 border-orange-300 hover:border-orange-400"
            }`}
          >
            🔥 Trending only
          </button>
        )}
        <span className="ml-auto text-xs text-gray-400">{filtered.length} ideas</span>
      </div>

      {/* Gift grid */}
      <div>
        <h2 className="text-lg font-bold text-gray-900 mb-4">
          🎁 {filtered.length} Perfect Gift Ideas
        </h2>
        {filtered.length === 0 ? (
          <p className="text-center text-gray-400 text-sm py-8">
            No gifts in this range. Try a higher budget filter.
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {filtered.map((gift, i) => (
              <GiftCard key={i} gift={gift} index={i} />
            ))}
          </div>
        )}
      </div>

      {/* Affiliate disclaimer */}
      <p className="text-xs text-gray-400 text-center">
        Amazon links may include an affiliate tag — we earn a small commission at no extra cost to you.
      </p>

      {/* Reset */}
      <button
        onClick={onReset}
        className="w-full py-3 rounded-xl border-2 border-brand-200 text-brand-600 font-semibold hover:bg-brand-50 transition"
      >
        Search Again
      </button>
    </div>
  );
}
