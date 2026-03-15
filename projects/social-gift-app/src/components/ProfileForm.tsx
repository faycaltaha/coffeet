"use client";

import { useState } from "react";
import type { SocialProfile, AnalyzeRequest } from "@/types";

const PLATFORMS: { id: SocialProfile["platform"]; label: string; icon: string; placeholder: string }[] = [
  { id: "instagram", label: "Instagram", icon: "📸", placeholder: "e.g. natgeo" },
  { id: "tiktok", label: "TikTok", icon: "🎵", placeholder: "e.g. charlidamelio" },
  { id: "pinterest", label: "Pinterest", icon: "📌", placeholder: "e.g. anthropicai" },
];

const BUDGETS = ["Under €30", "€30–€75", "€75–€150", "€150–€300", "€300+"];
const OCCASIONS = ["Birthday", "Christmas", "Valentine's Day", "Anniversary", "Just Because", "Graduation", "Wedding", "Other"];
const RELATIONSHIPS = ["Partner / Spouse", "Best Friend", "Parent", "Sibling", "Child", "Colleague", "Other"];

interface Props {
  onSubmit: (data: AnalyzeRequest) => void;
  loading: boolean;
}

export default function ProfileForm({ onSubmit, loading }: Props) {
  const [recipientName, setRecipientName] = useState("");
  const [occasion, setOccasion] = useState(OCCASIONS[0]);
  const [budget, setBudget] = useState(BUDGETS[1]);
  const [relationship, setRelationship] = useState(RELATIONSHIPS[0]);
  const [handles, setHandles] = useState<Record<SocialProfile["platform"], string>>({
    instagram: "",
    tiktok: "",
    pinterest: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const profiles: SocialProfile[] = PLATFORMS
      .filter((p) => handles[p.id].trim())
      .map((p) => ({ platform: p.id, handle: handles[p.id].trim().replace(/^@/, "") }));

    if (profiles.length === 0) return;
    onSubmit({ profiles, recipientName: recipientName.trim() || "your person", occasion, budget, relationship });
  };

  const hasHandle = Object.values(handles).some((h) => h.trim());

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Recipient name */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-1.5">
          Who is this gift for?
        </label>
        <input
          type="text"
          value={recipientName}
          onChange={(e) => setRecipientName(e.target.value)}
          placeholder="e.g. Alex"
          className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-400 transition text-gray-800 placeholder:text-gray-400"
        />
      </div>

      {/* Social handles */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-3">
          Social media profiles <span className="text-gray-400 font-normal">(at least one)</span>
        </label>
        <div className="space-y-3">
          {PLATFORMS.map((p) => (
            <div key={p.id} className="flex items-center gap-3">
              <span className="text-xl w-8 text-center">{p.icon}</span>
              <div className="flex-1 flex items-center border border-gray-200 bg-white rounded-xl shadow-sm overflow-hidden focus-within:ring-2 focus-within:ring-brand-400 transition">
                <span className="pl-3 pr-1 text-gray-400 text-sm select-none">@</span>
                <input
                  type="text"
                  value={handles[p.id]}
                  onChange={(e) => setHandles((prev) => ({ ...prev, [p.id]: e.target.value }))}
                  placeholder={p.placeholder}
                  className="flex-1 py-2.5 pr-4 bg-transparent focus:outline-none text-gray-800 placeholder:text-gray-400 text-sm"
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Occasion + Relationship */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1.5">Occasion</label>
          <select
            value={occasion}
            onChange={(e) => setOccasion(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-400 transition text-gray-800 text-sm"
          >
            {OCCASIONS.map((o) => <option key={o}>{o}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1.5">Relationship</label>
          <select
            value={relationship}
            onChange={(e) => setRelationship(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-400 transition text-gray-800 text-sm"
          >
            {RELATIONSHIPS.map((r) => <option key={r}>{r}</option>)}
          </select>
        </div>
      </div>

      {/* Budget */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-2">Budget</label>
        <div className="flex flex-wrap gap-2">
          {BUDGETS.map((b) => (
            <button
              key={b}
              type="button"
              onClick={() => setBudget(b)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition border ${
                budget === b
                  ? "bg-brand-500 text-white border-brand-500 shadow-md"
                  : "bg-white text-gray-600 border-gray-200 hover:border-brand-300"
              }`}
            >
              {b}
            </button>
          ))}
        </div>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={!hasHandle || loading}
        className="w-full py-3 px-6 rounded-xl font-semibold text-white bg-gradient-to-r from-brand-500 to-purple-500 hover:from-brand-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg hover:shadow-xl active:scale-[0.98]"
      >
        {loading ? "Analyzing…" : "✨ Find Perfect Gifts"}
      </button>
    </form>
  );
}
