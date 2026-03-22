import type { AgendaEvent } from "@/types";

const KEY = "gift_agenda";

function load(): AgendaEvent[] {
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); }
  catch { return []; }
}

function save(events: AgendaEvent[]) {
  try { localStorage.setItem(KEY, JSON.stringify(events)); } catch {}
}

export function loadAgenda(): AgendaEvent[] { return load(); }

export function addEvent(event: AgendaEvent) {
  save([...load().filter((e) => e.id !== event.id), event]);
}

export function deleteEvent(id: string) {
  save(load().filter((e) => e.id !== id));
}

export function upcomingEvents(withinDays = 60): AgendaEvent[] {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const cutoff = new Date(today);
  cutoff.setDate(cutoff.getDate() + withinDays);

  return load()
    .filter((e) => {
      const d = new Date(e.date);
      return d >= today && d <= cutoff;
    })
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
}

export function daysUntil(dateStr: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateStr);
  target.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}
