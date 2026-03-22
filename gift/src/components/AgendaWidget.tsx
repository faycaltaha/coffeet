"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { upcomingEvents, addEvent, deleteEvent, daysUntil } from "@/lib/agenda";
import type { AgendaEvent } from "@/types";
import type { AnalyzeRequest } from "@/types";

const OCCASIONS = [
  "Birthday", "Christmas", "Valentine's Day", "Anniversary",
  "Graduation", "Wedding", "Other",
];
const OCCASION_EMOJI: Record<string, string> = {
  "Birthday": "🎂",
  "Christmas": "🎄",
  "Valentine's Day": "💝",
  "Anniversary": "💑",
  "Graduation": "🎓",
  "Wedding": "💒",
  "Other": "🎉",
};

interface Props {
  onFindGift: (prefill: Pick<AnalyzeRequest, "recipientName" | "occasion">) => void;
}

export default function AgendaWidget({ onFindGift }: Props) {
  const [events, setEvents] = useState<AgendaEvent[]>([]);
  const [open, setOpen] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", occasion: "Birthday", date: "" });

  const refresh = () => setEvents(upcomingEvents(60));

  useEffect(() => { refresh(); }, []);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.date) return;
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    addEvent({ id, ...form });
    setForm({ name: "", occasion: "Birthday", date: "" });
    setShowForm(false);
    refresh();
  };

  const handleDelete = (id: string) => { deleteEvent(id); refresh(); };

  const hasEvents = events.length > 0;

  // Collapsed: show minimal prompt or first urgent event
  if (!open && !showForm) {
    const next = events[0];
    return (
      <motion.div className="w-full max-w-xl mb-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}>
        <button
          onClick={() => setOpen(true)}
          className="w-full flex items-center justify-between px-4 py-2.5 rounded-2xl border border-dashed border-stone-300/70 dark:border-stone-600/70 text-stone-400 dark:text-stone-500 text-sm hover:border-brand-300 hover:text-brand-500 transition-colors group"
        >
          <span className="flex items-center gap-2">
            <span>📅</span>
            {next ? (
              <span>
                <span className="font-semibold text-stone-600 dark:text-stone-300">{next.name}</span>
                {" · "}{OCCASION_EMOJI[next.occasion] ?? "🎉"}
                {" · "}
                <span className={daysUntil(next.date) <= 7 ? "text-red-500 font-semibold" : daysUntil(next.date) <= 14 ? "text-orange-500 font-semibold" : ""}>
                  {daysUntil(next.date) === 0 ? "Aujourd'hui !" : `dans ${daysUntil(next.date)} j`}
                </span>
                {events.length > 1 && <span className="text-stone-400"> +{events.length - 1}</span>}
              </span>
            ) : (
              <span>Ajouter un rappel anniversaire / événement</span>
            )}
          </span>
          <span className="text-xs opacity-60 group-hover:opacity-100">▼</span>
        </button>
      </motion.div>
    );
  }

  return (
    <motion.div
      className="w-full max-w-xl mb-4"
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="glass rounded-2xl p-4 space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>📅</span>
            <h2 className="font-semibold text-stone-700 dark:text-stone-200 text-sm">
              Agenda{hasEvents && <span className="ml-1 text-brand-500">({events.length})</span>}
            </h2>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowForm((v) => !v)}
              aria-label="Ajouter un événement"
              className="w-7 h-7 rounded-full flex items-center justify-center text-brand-500 hover:bg-brand-50 dark:hover:bg-brand-900/20 text-lg font-bold transition-colors"
            >
              {showForm ? "−" : "+"}
            </button>
            <button
              onClick={() => setOpen(false)}
              aria-label="Réduire"
              className="w-7 h-7 rounded-full flex items-center justify-center text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-800 text-xs transition-colors"
            >
              ▲
            </button>
          </div>
        </div>

        {/* Add form */}
        <AnimatePresence>
          {showForm && (
            <motion.form
              onSubmit={handleAdd}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-2 overflow-hidden"
            >
              <div className="flex gap-2">
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Prénom"
                  required
                  className="flex-1 px-3 py-2 rounded-xl border border-stone-200 dark:border-stone-600 bg-white/70 dark:bg-stone-800/70 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300 text-stone-800 dark:text-stone-100 placeholder:text-stone-400"
                />
                <input
                  type="date"
                  value={form.date}
                  onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                  required
                  className="flex-1 px-3 py-2 rounded-xl border border-stone-200 dark:border-stone-600 bg-white/70 dark:bg-stone-800/70 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300 text-stone-800 dark:text-stone-100"
                />
              </div>
              <div className="flex gap-2">
                <select
                  value={form.occasion}
                  onChange={(e) => setForm((f) => ({ ...f, occasion: e.target.value }))}
                  className="flex-1 px-3 py-2 rounded-xl border border-stone-200 dark:border-stone-600 bg-white/70 dark:bg-stone-800/70 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300 text-stone-800 dark:text-stone-100"
                >
                  {OCCASIONS.map((o) => (
                    <option key={o} value={o}>{OCCASION_EMOJI[o]} {o}</option>
                  ))}
                </select>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-brand-500 text-white text-sm font-semibold hover:bg-brand-600 transition-colors shadow-sm"
                >
                  ✓ Ajouter
                </button>
              </div>
            </motion.form>
          )}
        </AnimatePresence>

        {/* Event list */}
        {hasEvents && (
          <ul className="space-y-1.5">
            {events.map((event) => {
              const days = daysUntil(event.date);
              const urgencyClass = days <= 7
                ? "text-red-500 font-semibold"
                : days <= 14
                  ? "text-orange-500 font-semibold"
                  : "text-stone-400 dark:text-stone-500";
              const dateFmt = new Date(event.date).toLocaleDateString("fr-FR", {
                day: "numeric", month: "long",
              });
              return (
                <motion.li
                  key={event.id}
                  layout
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -8 }}
                  className="flex items-center gap-2 py-1"
                >
                  <span className="text-base shrink-0">{OCCASION_EMOJI[event.occasion] ?? "🎉"}</span>
                  <div className="flex-1 min-w-0">
                    <span className="font-semibold text-sm text-stone-800 dark:text-stone-100 truncate block">
                      {event.name}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-stone-400">{dateFmt}</span>
                      <span className={`text-xs ${urgencyClass}`}>
                        {days === 0 ? "Aujourd'hui !" : days === 1 ? "Demain !" : `dans ${days} j`}
                      </span>
                    </div>
                  </div>
                  <motion.button
                    onClick={() => onFindGift({ recipientName: event.name, occasion: event.occasion })}
                    className="shrink-0 px-2.5 py-1 rounded-lg bg-brand-500 text-white text-xs font-semibold hover:bg-brand-600 transition-colors"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    🎁
                  </motion.button>
                  <button
                    onClick={() => handleDelete(event.id)}
                    aria-label={`Supprimer l'événement de ${event.name}`}
                    className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-stone-300 hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors text-xs"
                  >
                    ✕
                  </button>
                </motion.li>
              );
            })}
          </ul>
        )}

        {!hasEvents && !showForm && (
          <p className="text-xs text-stone-400 dark:text-stone-500 text-center py-1">
            Aucun événement dans les 60 prochains jours
          </p>
        )}
      </div>
    </motion.div>
  );
}
