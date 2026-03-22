/**
 * Client-safe affiliate URL builders (no fs/path — browser compatible).
 * Used by GiftResults component.
 * Server-side Awin cache logic stays in affiliate.ts (API routes only).
 */

export function amazonUrl(query: string, tag?: string): string {
  const url = `https://www.amazon.fr/s?k=${encodeURIComponent(query)}`;
  return tag ? `${url}&tag=${tag}` : url;
}

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

const MERCHANT_STYLES: Record<string, { icon: string; className: string; hoverColor: string }> = {
  fnac:      { icon: "🟡", className: "bg-yellow-50 text-yellow-800 border border-yellow-200", hoverColor: "#fef9c3" },
  decathlon: { icon: "🏃", className: "bg-blue-50 text-blue-800 border border-blue-200",       hoverColor: "#dbeafe" },
  etsy:      { icon: "🛍️", className: "bg-orange-50 text-orange-800 border border-orange-200", hoverColor: "#fff7ed" },
  cultura:   { icon: "🎨", className: "bg-green-50 text-green-800 border border-green-200",    hoverColor: "#f0fdf4" },
};

const DEFAULT_STYLE = { icon: "🏪", className: "bg-gray-50 text-gray-800 border border-gray-200", hoverColor: "#f9fafb" };

function styleFor(name: string) {
  const lower = name.toLowerCase();
  for (const [key, style] of Object.entries(MERCHANT_STYLES)) {
    if (lower.includes(key)) return style;
  }
  return DEFAULT_STYLE;
}

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

export type SecondMerchant = {
  label: string;
  icon: string;
  className: string;
  hoverColor: string;
  url: (query: string) => string;
};

export function secondMerchant(category: string): SecondMerchant {
  const cat = category.toLowerCase();
  const fallback = STATIC_FALLBACK[cat];
  if (fallback) {
    return { label: fallback.label, ...styleFor(fallback.label), url: fallback.url };
  }
  return { label: "Fnac", ...MERCHANT_STYLES.fnac, url: fnacUrl };
}
