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
  primarySector?: string;
  commissionRange?: { min: number; max: number };
}

export interface AwinCommissionGroup {
  groupId: number;
  groupName: string;
  type: "percentage" | "fixed";
  value: number;
}

export interface AwinTransaction {
  id: number;
  advertiserId: number;
  commissionAmount: { amount: number; currency: string };
  saleAmount: { amount: number; currency: string };
  transactionDate: string;
  status: string;
}

/** Enriched programme with resolved commission rate (%) */
export interface EnrichedProgramme extends AwinProgramme {
  /** Best commission rate in % (max across commission groups) */
  commissionPct: number;
  /** Awin deep link to merchant homepage */
  deepLink: string;
  /** Categories this programme matches */
  categories: string[];
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

async function awinFetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const { apiKey } = getCredentials();
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    ...opts,
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      ...(opts?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Awin API ${res.status} ${path}: ${body}`);
  }
  return res.json() as Promise<T>;
}

/** Fetch programmes by relationship */
export async function fetchProgrammes(
  relationship: AwinRelationship = "joined",
  countryCode = "FR"
): Promise<AwinProgramme[]> {
  const { publisherId } = getCredentials();
  return awinFetch<AwinProgramme[]>(
    `/publishers/${publisherId}/programmes?relationship=${relationship}&countryCode=${countryCode}`
  );
}

/** Fetch commission groups for a specific programme */
export async function fetchCommissions(
  programmeId: number
): Promise<AwinCommissionGroup[]> {
  const { publisherId } = getCredentials();
  try {
    return await awinFetch<AwinCommissionGroup[]>(
      `/publishers/${publisherId}/commissiongroups?advertiserId=${programmeId}`
    );
  } catch {
    return [];
  }
}

/**
 * Apply to join a programme on Awin.
 * Returns the new relationship status.
 * Note: some programmes are auto-approved, others go to "pending".
 */
export async function joinProgramme(programmeId: number): Promise<{ status: string }> {
  const { publisherId } = getCredentials();
  return awinFetch<{ status: string }>(
    `/publishers/${publisherId}/programmes/${programmeId}/join`,
    { method: "POST" }
  );
}

/** Fetch recent transactions */
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

/** Build an Awin tracked deep link */
export function buildDeepLink(programmeId: number, destinationUrl: string): string {
  const { publisherId } = getCredentials();
  const encoded = encodeURIComponent(destinationUrl);
  return `https://www.awin1.com/cread.php?awinmid=${programmeId}&awinaffid=${publisherId}&p=${encoded}`;
}

// ─── Category → Awin sector mapping ─────────────────────────────────────────

export const CATEGORY_SECTORS: Record<string, string[]> = {
  tech: ["electrical", "computing", "mobile phones", "electronics", "gaming"],
  sport: ["sports", "outdoor", "fitness", "cycling"],
  travel: ["travel", "hotels", "accommodation", "luggage"],
  fashion: ["fashion", "clothing", "women", "men", "accessories"],
  beauty: ["health & beauty", "cosmetics", "skincare", "perfume"],
  home: ["home", "garden", "kitchen", "furniture", "decoration"],
  food: ["food & drink", "confectionery", "wine", "spirits", "gourmet"],
  books: ["books", "stationery", "music", "film", "education"],
  art: ["arts & crafts", "hobbies", "creative"],
  experience: ["entertainment", "tickets", "events", "experiences", "leisure"],
};

export function matchesCategory(programme: AwinProgramme, category: string): boolean {
  const keywords = CATEGORY_SECTORS[category.toLowerCase()] ?? [];
  const sector = (programme.primarySector ?? "").toLowerCase();
  const name = programme.name.toLowerCase();
  return keywords.some(
    (k) => sector.includes(k.toLowerCase()) || name.includes(k.toLowerCase())
  );
}

/** Extract best commission % from commission groups */
export function bestCommissionPct(groups: AwinCommissionGroup[]): number {
  const pctGroups = groups.filter((g) => g.type === "percentage");
  if (pctGroups.length === 0) return 0;
  return Math.max(...pctGroups.map((g) => g.value));
}
