/**
 * Affiliate URL builders.
 *
 * Priorité :
 *   1. Partenaire Awin avec la meilleure commission (lu depuis awin-cache.json)
 *   2. Amazon Associates (fallback universel)
 *
 * Pour mettre à jour le cache : npm run awin:scan
 */

import "server-only";
import * as fs from "fs";
import * as path from "path";
import { buildDeepLinkSafe, EnrichedProgramme } from "./awin-client";

// ─── Cache Awin ──────────────────────────────────────────────────────────────

interface AwinCache {
  updatedAt: string;
  programmes: EnrichedProgramme[];
}

let _cache: AwinCache | null = null;

function loadCache(): AwinCache | null {
  if (_cache) return _cache;
  try {
    const cachePath = path.join(process.cwd(), "awin-cache.json");
    if (!fs.existsSync(cachePath)) return null;
    _cache = JSON.parse(fs.readFileSync(cachePath, "utf-8")) as AwinCache;
    return _cache;
  } catch {
    return null;
  }
}

/**
 * Retourne le partenaire Awin le mieux rémunéré pour une catégorie donnée.
 * Les programmes sont déjà triés par commission décroissante dans le cache.
 */
function bestAwinPartner(category: string): EnrichedProgramme | null {
  const cache = loadCache();
  if (!cache) return null;
  return (
    cache.programmes.find(
      (p) => p.categories.includes(category.toLowerCase()) && p.commissionPct > 0
    ) ?? null
  );
}

// ─── Amazon (fallback universel) ─────────────────────────────────────────────

export function amazonUrl(query: string, tag?: string): string {
  const url = `https://www.amazon.fr/s?k=${encodeURIComponent(query)}`;
  return tag ? `${url}&tag=${tag}` : url;
}

// ─── URLs directes (si programme Awin non trouvé dans le cache) ───────────────

export function fnacUrl(query: string): string {
  return `https://recherche.fnac.com/SearchResult/ResultList.aspx?Search=${encodeURIComponent(query)}`;
}

export function etsyUrl(query: string): string {
  return `https://www.etsy.com/fr/search?q=${encodeURIComponent(query)}`;
}

export function decathlonUrl(query: string): string {
  return `https://www.decathlon.fr/search?Ntt=${encodeURIComponent(query)}`;
}

export function culturaUrl(query: string): string {
  return `https://www.cultura.com/search?q=${encodeURIComponent(query)}`;
}

// ─── Merchant styling ────────────────────────────────────────────────────────

const MERCHANT_STYLES: Record<
  string,
  { icon: string; className: string; hoverColor: string }
> = {
  fnac:       { icon: "🟡", className: "bg-yellow-50 text-yellow-800 border border-yellow-200", hoverColor: "#fef9c3" },
  decathlon:  { icon: "🏃", className: "bg-blue-50 text-blue-800 border border-blue-200",   hoverColor: "#dbeafe" },
  etsy:       { icon: "🛍️", className: "bg-orange-50 text-orange-800 border border-orange-200", hoverColor: "#fff7ed" },
  cultura:    { icon: "🎨", className: "bg-green-50 text-green-800 border border-green-200",  hoverColor: "#f0fdf4" },
  amazon:     { icon: "📦", className: "bg-amber-50 text-amber-800 border border-amber-200",  hoverColor: "#fffbeb" },
};

const DEFAULT_STYLE = { icon: "🏪", className: "bg-gray-50 text-gray-800 border border-gray-200", hoverColor: "#f9fafb" };

function styleFor(name: string) {
  const lower = name.toLowerCase();
  for (const [key, style] of Object.entries(MERCHANT_STYLES)) {
    if (lower.includes(key)) return style;
  }
  return DEFAULT_STYLE;
}

// ─── Fallbacks statiques par catégorie ───────────────────────────────────────

const STATIC_FALLBACK: Record<string, { label: string; url: (q: string) => string }> = {
  sport:      { label: "Decathlon", url: decathlonUrl },
  travel:     { label: "Decathlon", url: decathlonUrl },
  tech:       { label: "Fnac",      url: fnacUrl },
  books:      { label: "Cultura",   url: culturaUrl },
  art:        { label: "Cultura",   url: culturaUrl },
  home:       { label: "Etsy",      url: etsyUrl },
  fashion:    { label: "Etsy",      url: etsyUrl },
  beauty:     { label: "Etsy",      url: etsyUrl },
  experience: { label: "Etsy",      url: etsyUrl },
  food:       { label: "Etsy",      url: etsyUrl },
};

// ─── API publique ────────────────────────────────────────────────────────────

export type SecondMerchant = {
  label: string;
  icon: string;
  className: string;
  hoverColor: string;
  commissionPct: number;
  url: (query: string) => string;
};

/**
 * Retourne le meilleur partenaire affilié pour une catégorie.
 *
 * Ordre de priorité :
 *   1. Partenaire Awin le mieux rémunéré (depuis awin-cache.json)
 *   2. Fallback statique par catégorie
 *   3. Fnac en dernier recours
 */
export function secondMerchant(category: string): SecondMerchant {
  const cat = category.toLowerCase();

  // 1. Meilleur partenaire Awin
  const awin = bestAwinPartner(cat);
  if (awin) {
    const publisherId = process.env.AWIN_PUBLISHER_ID ?? "";
    const style = styleFor(awin.name);
    return {
      label: awin.name,
      ...style,
      commissionPct: awin.commissionPct,
      url: (query: string) => {
        const dest = `https://www.${awin.displayUrl}/search?q=${encodeURIComponent(query)}`;
        return buildDeepLinkSafe(awin.id, dest, publisherId) ?? dest;
      },
    };
  }

  // 2. Fallback statique
  const fallback = STATIC_FALLBACK[cat];
  if (fallback) {
    return {
      label: fallback.label,
      ...styleFor(fallback.label),
      commissionPct: 0,
      url: fallback.url,
    };
  }

  // 3. Dernier recours
  return {
    label: "Fnac",
    ...MERCHANT_STYLES.fnac,
    commissionPct: 0,
    url: fnacUrl,
  };
}

/**
 * Retourne tous les partenaires Awin disponibles pour une catégorie,
 * triés par commission décroissante. Utile pour afficher plusieurs options.
 */
export function allMerchantsForCategory(category: string): SecondMerchant[] {
  const cache = loadCache();
  if (!cache) return [secondMerchant(category)];

  const partners = cache.programmes.filter((p) =>
    p.categories.includes(category.toLowerCase())
  );

  if (partners.length === 0) return [secondMerchant(category)];

  const publisherId = process.env.AWIN_PUBLISHER_ID ?? "";
  return partners.map((p) => ({
    label: p.name,
    ...styleFor(p.name),
    commissionPct: p.commissionPct,
    url: (query: string) => {
      const dest = `https://www.${p.displayUrl}/search?q=${encodeURIComponent(query)}`;
      return buildDeepLinkSafe(p.id, dest, publisherId) ?? dest;
    },
  }));
}
