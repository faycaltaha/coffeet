"use client";

import type { AnalysisResult, GiftIdea } from "@/types";

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

function categoryColor(cat: string) {
  return CATEGORY_COLORS[cat.toLowerCase()] ?? CATEGORY_COLORS.default;
}

function GiftCard({ gift, index }: { gift: GiftIdea; index: number }) {
  const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(gift.searchQuery)}`;

  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-shadow flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{["🎁", "🎀", "💝", "✨", "🌟", "💫", "🎊", "🛍️"][index % 8]}</span>
          <h3 className="font-bold text-gray-900 leading-snug">{gift.title}</h3>
        </div>
        <span className="shrink-0 text-sm font-semibold text-brand-600 bg-brand-50 px-3 py-1 rounded-full">
          {gift.priceRange}
        </span>
      </div>

      <p className="text-gray-600 text-sm leading-relaxed">{gift.description}</p>

      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full capitalize ${categoryColor(gift.category)}`}>
          {gift.category}
        </span>
        <span className="text-xs text-gray-400 italic">{gift.reason}</span>
      </div>

      <a
        href={searchUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-auto inline-flex items-center gap-1.5 text-sm font-medium text-brand-600 hover:text-brand-700 transition"
      >
        Find this gift →
      </a>
    </div>
  );
}

interface Props {
  result: AnalysisResult;
  recipientName: string;
  onReset: () => void;
}

export default function GiftResults({ result, recipientName, onReset }: Props) {
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

      {/* Gift grid */}
      <div>
        <h2 className="text-lg font-bold text-gray-900 mb-4">
          🎁 {result.giftIdeas.length} Perfect Gift Ideas
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {result.giftIdeas.map((gift, i) => (
            <GiftCard key={i} gift={gift} index={i} />
          ))}
        </div>
      </div>

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
