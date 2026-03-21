/**
 * Affiliate URL builders — no direct brand contact required.
 * Join networks: Amazon Associates (amazon.fr/associates), Awin (awin.com)
 *
 * When AWIN_API_KEY + AWIN_PUBLISHER_ID are set, the app uses real Awin
 * deep links (tracked, commission-generating). Otherwise falls back to
 * plain search URLs. Run `scripts/awin-bot.ts` to scan & join programmes.
 */

import { buildDeepLink } from "./awin-client";

/**
 * Known Awin programme IDs for our main merchants (FR).
 * Run the awin-bot to get the real IDs after joining.
 * Set to null until the programme is joined on Awin.
 */
export const AWIN_PROGRAMME_IDS: Record<string, number | null> = {
  fnac: null,       // Fnac — join at https://ui.awin.com/merchant-programme/2619
  decathlon: null,  // Decathlon — join at https://ui.awin.com/merchant-programme/15235
  etsy: null,       // Etsy — join at https://ui.awin.com/merchant-programme/12553
  cultura: null,    // Cultura — join at https://ui.awin.com/merchant-programme/9452
};

/** Wraps a URL with an Awin deep link if the programme is joined, else returns plain URL */
function withAwin(merchant: keyof typeof AWIN_PROGRAMME_IDS, url: string): string {
  const id = AWIN_PROGRAMME_IDS[merchant];
  if (!id || !process.env.AWIN_API_KEY || !process.env.AWIN_PUBLISHER_ID) return url;
  return buildDeepLink(id, url);
}

/** Amazon.fr search with optional affiliate tag (Amazon Associates) */
export function amazonUrl(query: string, tag?: string): string {
  const url = `https://www.amazon.fr/s?k=${encodeURIComponent(query)}`;
  return tag ? `${url}&tag=${tag}` : url;
}

/** Fnac.com search — tracked via Awin if joined */
export function fnacUrl(query: string): string {
  const plain = `https://recherche.fnac.com/SearchResult/ResultList.aspx?Search=${encodeURIComponent(query)}`;
  return withAwin("fnac", plain);
}

/** Etsy search — tracked via Awin if joined */
export function etsyUrl(query: string): string {
  const plain = `https://www.etsy.com/fr/search?q=${encodeURIComponent(query)}`;
  return withAwin("etsy", plain);
}

/** Decathlon search — tracked via Awin if joined */
export function decathlonUrl(query: string): string {
  const plain = `https://www.decathlon.fr/search?Ntt=${encodeURIComponent(query)}`;
  return withAwin("decathlon", plain);
}

/** Cultura search — tracked via Awin if joined */
export function culturaUrl(query: string): string {
  const plain = `https://www.cultura.com/search?q=${encodeURIComponent(query)}`;
  return withAwin("cultura", plain);
}

type SecondMerchant = {
  label: string;
  icon: string;
  className: string;
  hoverColor: string;
  url: (query: string) => string;
};

/** Returns the most relevant second merchant for a given gift category */
export function secondMerchant(category: string): SecondMerchant {
  const cat = category.toLowerCase();
  if (cat === "sport" || cat === "travel") {
    return {
      label: "Decathlon",
      icon: "🏃",
      className: "bg-blue-50 text-blue-800 border border-blue-200",
      hoverColor: "#dbeafe",
      url: decathlonUrl,
    };
  }
  if (cat === "tech") {
    return {
      label: "Fnac",
      icon: "🟡",
      className: "bg-yellow-50 text-yellow-800 border border-yellow-200",
      hoverColor: "#fef9c3",
      url: fnacUrl,
    };
  }
  if (cat === "books" || cat === "art") {
    return {
      label: "Cultura",
      icon: "🎨",
      className: "bg-green-50 text-green-800 border border-green-200",
      hoverColor: "#f0fdf4",
      url: culturaUrl,
    };
  }
  if (cat === "home" || cat === "fashion" || cat === "beauty" || cat === "experience" || cat === "food") {
    return {
      label: "Etsy",
      icon: "🛍️",
      className: "bg-orange-50 text-orange-800 border border-orange-200",
      hoverColor: "#fff7ed",
      url: etsyUrl,
    };
  }
  // Default fallback
  return {
    label: "Fnac",
    icon: "🟡",
    className: "bg-yellow-50 text-yellow-800 border border-yellow-200",
    hoverColor: "#fef9c3",
    url: fnacUrl,
  };
}
