/**
 * Affiliate URL builders — no direct brand contact required.
 * Join networks: Amazon Associates (amazon.fr/associates), Awin (awin.com)
 */

/** Amazon.fr search with optional affiliate tag (Amazon Associates) */
export function amazonUrl(query: string, tag?: string): string {
  const url = `https://www.amazon.fr/s?k=${encodeURIComponent(query)}`;
  return tag ? `${url}&tag=${tag}` : url;
}

/** Fnac.com search — joinable via Awin network */
export function fnacUrl(query: string): string {
  return `https://recherche.fnac.com/SearchResult/ResultList.aspx?Search=${encodeURIComponent(query)}`;
}

/** Etsy search — artisanal / unique gifts */
export function etsyUrl(query: string): string {
  return `https://www.etsy.com/fr/search?q=${encodeURIComponent(query)}`;
}

/** Decathlon search — sport & outdoor */
export function decathlonUrl(query: string): string {
  return `https://www.decathlon.fr/search?Ntt=${encodeURIComponent(query)}`;
}

/** Cultura search — books, art, creativity */
export function culturaUrl(query: string): string {
  return `https://www.cultura.com/search?q=${encodeURIComponent(query)}`;
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
