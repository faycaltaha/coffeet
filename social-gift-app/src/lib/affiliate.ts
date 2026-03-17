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
