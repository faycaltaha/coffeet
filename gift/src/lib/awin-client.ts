/**
 * Awin Publisher API client
 * Docs: https://wiki.awin.com/index.php/Publisher_API
 *
 * Required env vars:
 *   AWIN_API_KEY        — your publisher API token
 *   AWIN_PUBLISHER_ID   — your publisher numeric ID
 */

const BASE_URL = "https://api.awin.com";

export type AwinRelationship = "joined" | "notjoined" | "pending" | "rejected";

export interface AwinProgramme {
  id: number;
  name: string;
  displayUrl: string;
  primaryRegion: { countryCode: string };
  logoUrl?: string;
  currencyCode: string;
  status: string;
  /** Sector taxonomy provided by Awin */
  primarySector?: string;
  /** Commission groups summary */
  commissionRange?: {
    min: number;
    max: number;
  };
}

export interface AwinTransaction {
  id: number;
  advertiserId: number;
  commissionAmount: { amount: number; currency: string };
  saleAmount: { amount: number; currency: string };
  transactionDate: string;
  status: string;
}

function getCredentials() {
  const apiKey = process.env.AWIN_API_KEY;
  const publisherId = process.env.AWIN_PUBLISHER_ID;
  if (!apiKey || !publisherId) {
    throw new Error(
      "Missing AWIN_API_KEY or AWIN_PUBLISHER_ID environment variables"
    );
  }
  return { apiKey, publisherId };
}

async function awinFetch<T>(path: string): Promise<T> {
  const { apiKey } = getCredentials();
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Awin API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

/** Fetch programmes by relationship. Default: joined. */
export async function fetchProgrammes(
  relationship: AwinRelationship = "joined",
  countryCode = "FR"
): Promise<AwinProgramme[]> {
  const { publisherId } = getCredentials();
  return awinFetch<AwinProgramme[]>(
    `/publishers/${publisherId}/programmes?relationship=${relationship}&countryCode=${countryCode}`
  );
}

/** Fetch recent transactions (earnings) */
export async function fetchTransactions(opts?: {
  startDate?: string;
  endDate?: string;
  status?: "pending" | "approved" | "declined";
}): Promise<AwinTransaction[]> {
  const { publisherId } = getCredentials();
  const params = new URLSearchParams({
    startDate: opts?.startDate ?? new Date(Date.now() - 30 * 86400000).toISOString().split("T")[0],
    endDate: opts?.endDate ?? new Date().toISOString().split("T")[0],
    ...(opts?.status ? { status: opts.status } : {}),
    timezone: "UTC",
  });
  return awinFetch<AwinTransaction[]>(
    `/publishers/${publisherId}/transactions/?${params}`
  );
}

/**
 * Build an Awin deep link for a merchant URL.
 * Requires the merchant's Awin programme ID.
 */
export function buildDeepLink(
  programmeId: number,
  destinationUrl: string
): string {
  const { publisherId } = getCredentials();
  const encoded = encodeURIComponent(destinationUrl);
  return `https://www.awin1.com/cread.php?awinmid=${programmeId}&awinaffid=${publisherId}&p=${encoded}`;
}

// ─── Category → Awin sector mapping ─────────────────────────────────────────

/** Gift categories → Awin primary sectors keywords */
export const CATEGORY_SECTORS: Record<string, string[]> = {
  tech: ["Electrical & Accessories", "Computing", "Mobile Phones & Accessories"],
  sport: ["Sports", "Outdoor & Garden"],
  travel: ["Travel", "Hotels & Accommodation", "Travel Accessories"],
  fashion: ["Fashion", "Women", "Men", "Clothing"],
  beauty: ["Health & Beauty", "Cosmetics"],
  home: ["Home & Garden", "Kitchen & Dining", "Furniture"],
  food: ["Food & Drink", "Confectionery", "Wine & Spirits"],
  books: ["Books", "Stationery", "Music & Film"],
  art: ["Arts & Crafts", "Hobbies"],
  experience: ["Entertainment", "Tickets & Events", "Experiences"],
};

/** Return true if a programme matches a gift category */
export function matchesCategory(
  programme: AwinProgramme,
  category: string
): boolean {
  const keywords = CATEGORY_SECTORS[category.toLowerCase()] ?? [];
  const sector = (programme.primarySector ?? "").toLowerCase();
  const name = programme.name.toLowerCase();
  return keywords.some(
    (k) => sector.includes(k.toLowerCase()) || name.includes(k.toLowerCase())
  );
}
