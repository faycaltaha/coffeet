import type { AnalyzeRequest, AnalysisResult } from "@/types";

export interface RecentSearch {
  label: string;
  data: AnalyzeRequest;
  ts: number;
}

// ─── Cache AI results (24h TTL) ──────────────────────────────────────────────

function cacheKey(data: AnalyzeRequest): string {
  try {
    return btoa(JSON.stringify(data)).slice(0, 80);
  } catch { return ""; }
}

export function loadFromCache(data: AnalyzeRequest): AnalysisResult | null {
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

export function saveToCache(data: AnalyzeRequest, result: AnalysisResult) {
  try {
    const key = cacheKey(data);
    if (!key) return;
    localStorage.setItem(`gift_cache_${key}`, JSON.stringify({ result, ts: Date.now() }));
  } catch {}
}

// ─── Recent searches ─────────────────────────────────────────────────────────

export function loadRecentSearches(): RecentSearch[] {
  try { return JSON.parse(localStorage.getItem("gift_recent") || "[]"); }
  catch { return []; }
}

export function saveRecentSearch(data: AnalyzeRequest) {
  try {
    const recent = loadRecentSearches().filter(
      (r) => r.data.recipientName !== data.recipientName
    );
    const label = `${data.recipientName} · ${data.occasion} · ${data.budget}`;
    recent.unshift({ label, data, ts: Date.now() });
    localStorage.setItem("gift_recent", JSON.stringify(recent.slice(0, 3)));
  } catch {}
}

// ─── URL params ──────────────────────────────────────────────────────────────

export function encodeFormToUrl(data: AnalyzeRequest): string {
  const params = new URLSearchParams();
  params.set("name", data.recipientName);
  params.set("occasion", data.occasion);
  params.set("budget", data.budget);
  params.set("relationship", data.relationship);
  if (data.interests?.length) params.set("interests", data.interests.join(","));
  for (const p of data.profiles) params.set(p.platform, p.handle);
  return params.toString();
}

export function decodeUrlToForm(): AnalyzeRequest | null {
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
