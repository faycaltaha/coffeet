"use client";

import { useState, useEffect } from "react";
import { motion, type Transition, type TargetAndTransition } from "framer-motion";
import type { SocialProfile, AnalyzeRequest } from "@/types";
import type { RecentSearch } from "@/lib/storage";

const PLATFORMS: { id: SocialProfile["platform"]; label: string; icon: string; placeholder: string }[] = [
  { id: "instagram", label: "Instagram", icon: "📸", placeholder: "ex. natgeo" },
  { id: "tiktok", label: "TikTok", icon: "🎵", placeholder: "ex. charlidamelio" },
  { id: "pinterest", label: "Pinterest", icon: "📌", placeholder: "ex. anthropicai" },
  { id: "youtube", label: "YouTube", icon: "▶️", placeholder: "ex. mkbhd" },
];

const BUDGETS = ["Moins de €30", "€30–€75", "€75–€150", "€150–€300", "€300+"];

const OCCASIONS = [
  { id: "Birthday", label: "Anniversaire", icon: "🎂" },
  { id: "Christmas", label: "Noël", icon: "🎄" },
  { id: "Valentine's Day", label: "Saint-Valentin", icon: "💝" },
  { id: "Anniversary", label: "Anniversaire de couple", icon: "💑" },
  { id: "Just Because", label: "Juste parce que", icon: "🎁" },
  { id: "Graduation", label: "Diplôme", icon: "🎓" },
  { id: "Wedding", label: "Mariage", icon: "💒" },
  { id: "Sorry / Make It Up", label: "Me faire pardonner", icon: "🙏" },
  { id: "Housewarming", label: "Crémaillère", icon: "🏠" },
  { id: "Baby Shower", label: "Baby Shower", icon: "👶" },
  { id: "Other", label: "Autre", icon: "🎉" },
];

const RELATIONSHIPS = [
  { id: "Partner / Spouse", label: "Partenaire", icon: "💞" },
  { id: "Best Friend", label: "Meilleur ami", icon: "🤝" },
  { id: "Parent", label: "Parent", icon: "👪" },
  { id: "Sibling", label: "Frère / Sœur", icon: "👫" },
  { id: "Child", label: "Enfant", icon: "🧒" },
  { id: "Colleague", label: "Collègue", icon: "💼" },
  { id: "Other", label: "Autre", icon: "👤" },
];

const INTERESTS = [
  { id: "sport", label: "Sport & Fitness", icon: "🏋️" },
  { id: "gaming", label: "Gaming", icon: "🎮" },
  { id: "cooking", label: "Cuisine", icon: "🍳" },
  { id: "travel", label: "Voyage", icon: "✈️" },
  { id: "reading", label: "Lecture", icon: "📚" },
  { id: "music", label: "Musique", icon: "🎵" },
  { id: "art", label: "Art & Créativité", icon: "🎨" },
  { id: "cinema", label: "Cinéma & Séries", icon: "🎬" },
  { id: "fashion", label: "Mode & Style", icon: "👗" },
  { id: "photo", label: "Photo & Vidéo", icon: "📷" },
  { id: "diy", label: "DIY & Bricolage", icon: "🔧" },
  { id: "nature", label: "Nature & Randonnée", icon: "🌿" },
  { id: "wellness", label: "Bien-être & Yoga", icon: "🧘" },
  { id: "tech", label: "Tech & Gadgets", icon: "💻" },
  { id: "pets", label: "Animaux", icon: "🐾" },
  { id: "food", label: "Gastronomie", icon: "🍽️" },
];

// Only allow valid social handle characters
function isValidHandle(handle: string): boolean {
  return handle === "" || /^[\w.\-]{1,50}$/.test(handle);
}

function sectionAnim(i: number): { initial: TargetAndTransition; animate: TargetAndTransition; transition: Transition } {
  return {
    initial: { opacity: 0, y: 16 },
    animate: { opacity: 1, y: 0 },
    transition: { delay: i * 0.07, duration: 0.4 },
  };
}

interface Props {
  onSubmit: (data: AnalyzeRequest) => void;
  loading: boolean;
  recentSearches?: RecentSearch[];
  prefill?: AnalyzeRequest | null;
}

export default function ProfileForm({ onSubmit, loading, recentSearches, prefill }: Props) {
  const [recipientName, setRecipientName] = useState("");
  const [occasion, setOccasion] = useState(OCCASIONS[0].id);
  const [budget, setBudget] = useState(BUDGETS[1]);
  const [relationship, setRelationship] = useState(RELATIONSHIPS[0].id);
  const [selectedInterests, setSelectedInterests] = useState<string[]>([]);
  const [handles, setHandles] = useState<Record<SocialProfile["platform"], string>>({
    instagram: "",
    tiktok: "",
    pinterest: "",
    youtube: "",
  });
  const [handleErrors, setHandleErrors] = useState<Partial<Record<SocialProfile["platform"], string>>>({});

  // Pre-fill from URL params or recent search
  useEffect(() => {
    if (prefill) {
      setRecipientName(prefill.recipientName ?? "");
      if (prefill.occasion) setOccasion(prefill.occasion);
      if (prefill.budget) setBudget(prefill.budget);
      if (prefill.relationship) setRelationship(prefill.relationship);
      if (prefill.interests) setSelectedInterests(prefill.interests);
      if (prefill.profiles) {
        const newHandles: Record<SocialProfile["platform"], string> = { instagram: "", tiktok: "", pinterest: "", youtube: "" };
        for (const p of prefill.profiles) newHandles[p.platform] = p.handle;
        setHandles(newHandles);
      }
    }
  }, [prefill]);

  const validateHandle = (platform: SocialProfile["platform"], value: string) => {
    if (!isValidHandle(value)) {
      setHandleErrors((prev) => ({ ...prev, [platform]: "Caractères non valides" }));
    } else {
      setHandleErrors((prev) => { const next = { ...prev }; delete next[platform]; return next; });
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const profiles: SocialProfile[] = PLATFORMS
      .filter((p) => handles[p.id].trim() && isValidHandle(handles[p.id]))
      .map((p) => ({ platform: p.id, handle: handles[p.id].trim().replace(/^@/, "") }));
    if (profiles.length === 0 && selectedInterests.length === 0) return;
    onSubmit({ profiles, recipientName: recipientName.trim() || "votre proche", occasion, budget, relationship, interests: selectedInterests });
  };

  const hasHandle = Object.values(handles).some((h) => h.trim());
  const hasErrors = Object.keys(handleErrors).length > 0;
  const canSubmit = (hasHandle || selectedInterests.length > 0) && !hasErrors;

  const toggleInterest = (id: string) => {
    setSelectedInterests((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Recent searches */}
      {recentSearches && recentSearches.length > 0 && (
        <motion.div {...sectionAnim(0)}>
          <p className="text-xs font-semibold text-gray-500 mb-2">Recherches récentes</p>
          <div className="flex flex-wrap gap-2">
            {recentSearches.map((r, i) => (
              <motion.button
                key={i}
                type="button"
                onClick={() => onSubmit(r.data)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border bg-white/70 text-brand-600 border-brand-200 hover:border-brand-400 dark:bg-gray-800/70 dark:text-brand-300 dark:border-brand-700"
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.94 }}
              >
                🕐 {r.label}
              </motion.button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Recipient name */}
      <motion.div {...sectionAnim(recentSearches?.length ? 1 : 0)}>
        <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1.5">
          Pour qui est ce cadeau ?
        </label>
        <input
          type="text"
          value={recipientName}
          onChange={(e) => setRecipientName(e.target.value)}
          placeholder="ex. Alex"
          className="w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white/70 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-400 focus:border-transparent transition-all text-gray-800 placeholder:text-gray-400 dark:bg-gray-800/70 dark:border-gray-600 dark:text-gray-100 dark:placeholder:text-gray-500"
        />
      </motion.div>

      {/* Social handles */}
      <motion.div {...sectionAnim(1)}>
        <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">
          Profils réseaux sociaux <span className="text-gray-400 dark:text-gray-500 font-normal">(optionnel — améliore les résultats)</span>
        </label>
        <div className="space-y-2.5">
          {PLATFORMS.map((p, i) => (
            <motion.div
              key={p.id}
              className="flex flex-col gap-1"
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.08 + i * 0.06, duration: 0.35, ease: "easeOut" }}
            >
              <div className="flex items-center gap-3">
                <span className="text-xl w-8 text-center">{p.icon}</span>
                <div className={`flex-1 flex items-center border rounded-xl shadow-sm overflow-hidden transition-all focus-within:ring-2 focus-within:ring-brand-400 focus-within:border-transparent ${
                  handleErrors[p.id] ? "border-red-400 bg-red-50/50" : "border-gray-200/80 bg-white/70 dark:bg-gray-800/70 dark:border-gray-600"
                }`}>
                  <span className="pl-3 pr-1 text-gray-400 text-sm select-none">@</span>
                  <input
                    type="text"
                    value={handles[p.id]}
                    onChange={(e) => {
                      const v = e.target.value.replace(/^@/, "");
                      setHandles((prev) => ({ ...prev, [p.id]: v }));
                      validateHandle(p.id, v);
                    }}
                    placeholder={p.placeholder}
                    className="flex-1 py-2.5 pr-4 bg-transparent focus:outline-none text-gray-800 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 text-sm"
                  />
                </div>
              </div>
              {handleErrors[p.id] && (
                <p className="text-xs text-red-500 ml-11">{handleErrors[p.id]}</p>
              )}
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Interests */}
      <motion.div {...sectionAnim(2)}>
        <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1.5">
          Ses centres d&apos;intérêt <span className="text-gray-400 dark:text-gray-500 font-normal">(optionnel — requis sans profil)</span>
        </label>
        <div className="flex flex-wrap gap-2">
          {INTERESTS.map((interest) => {
            const active = selectedInterests.includes(interest.id);
            return (
              <motion.button
                key={interest.id}
                type="button"
                onClick={() => toggleInterest(interest.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                  active
                    ? "bg-brand-500 text-white border-brand-500 shadow-md shadow-brand-200/60"
                    : "bg-white/70 text-gray-600 border-gray-200 hover:border-brand-300 dark:bg-gray-800/70 dark:text-gray-300 dark:border-gray-600"
                }`}
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.94 }}
              >
                <span>{interest.icon}</span>
                <span>{interest.label}</span>
              </motion.button>
            );
          })}
        </div>
      </motion.div>

      {/* Occasion */}
      <motion.div {...sectionAnim(3)}>
        <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">Occasion</label>
        <div className="flex flex-wrap gap-2">
          {OCCASIONS.map((o) => (
            <motion.button
              key={o.id}
              type="button"
              onClick={() => setOccasion(o.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                occasion === o.id
                  ? "bg-brand-500 text-white border-brand-500 shadow-md shadow-brand-200/60"
                  : "bg-white/70 text-gray-600 border-gray-200 hover:border-brand-300 dark:bg-gray-800/70 dark:text-gray-300 dark:border-gray-600"
              }`}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.94 }}
            >
              <span>{o.icon}</span>
              <span>{o.label}</span>
            </motion.button>
          ))}
        </div>
      </motion.div>

      {/* Relationship */}
      <motion.div {...sectionAnim(4)}>
        <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">Relation</label>
        <div className="flex flex-wrap gap-2">
          {RELATIONSHIPS.map((r) => (
            <motion.button
              key={r.id}
              type="button"
              onClick={() => setRelationship(r.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                relationship === r.id
                  ? "bg-brand-500 text-white border-brand-500 shadow-md shadow-brand-200/60"
                  : "bg-white/70 text-gray-600 border-gray-200 hover:border-brand-300 dark:bg-gray-800/70 dark:text-gray-300 dark:border-gray-600"
              }`}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.94 }}
            >
              <span>{r.icon}</span>
              <span>{r.label}</span>
            </motion.button>
          ))}
        </div>
      </motion.div>

      {/* Budget */}
      <motion.div {...sectionAnim(5)}>
        <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">Budget</label>
        <div className="flex flex-wrap gap-2">
          {BUDGETS.map((b) => (
            <motion.button
              key={b}
              type="button"
              onClick={() => setBudget(b)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                budget === b
                  ? "bg-brand-500 text-white border-brand-500 shadow-md shadow-brand-200/60"
                  : "bg-white/70 text-gray-600 border-gray-200 hover:border-brand-300 dark:bg-gray-800/70 dark:text-gray-300 dark:border-gray-600"
              }`}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.94 }}
            >
              {b}
            </motion.button>
          ))}
        </div>
      </motion.div>

      {/* Submit */}
      <motion.div {...sectionAnim(6)}>
        <motion.button
          type="submit"
          disabled={!canSubmit || loading}
          className="w-full py-3.5 px-6 rounded-2xl font-semibold text-white bg-gradient-to-r from-brand-500 to-purple-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-brand-300/40"
          whileHover={canSubmit && !loading ? { scale: 1.02, boxShadow: "0 12px 32px -4px rgba(192,38,211,0.45)" } : {}}
          whileTap={canSubmit && !loading ? { scale: 0.97 } : {}}
          transition={{ type: "spring", stiffness: 400, damping: 20 }}
        >
          {loading ? "Analyse en cours…" : "✨ Trouver les cadeaux parfaits"}
        </motion.button>
        {!canSubmit && (
          <p className="text-xs text-gray-400 dark:text-gray-500 text-center mt-2">
            Ajoute un profil social ou sélectionne au moins un centre d&apos;intérêt
          </p>
        )}
      </motion.div>
    </form>
  );
}
