/**
 * GET /api/awin?category=food
 * Returns joined Awin programmes matching a gift category,
 * with ready-to-use deep links.
 *
 * GET /api/awin?relationship=notjoined
 * Returns available programmes to join.
 *
 * Required env: AWIN_API_KEY, AWIN_PUBLISHER_ID
 */

import { NextRequest, NextResponse } from "next/server";
import {
  fetchProgrammes,
  buildDeepLink,
  matchesCategory,
  AwinRelationship,
} from "@/lib/awin-client";

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const category = searchParams.get("category");
  const relationship = (searchParams.get("relationship") ?? "joined") as AwinRelationship;
  const country = searchParams.get("country") ?? "FR";

  try {
    const programmes = await fetchProgrammes(relationship, country);

    const filtered = category
      ? programmes.filter((p) => matchesCategory(p, category))
      : programmes;

    const result = filtered.map((p) => ({
      id: p.id,
      name: p.name,
      sector: p.primarySector,
      logo: p.logoUrl,
      status: p.status,
      deepLink: relationship === "joined"
        ? buildDeepLink(p.id, `https://www.${p.displayUrl}`)
        : null,
      applyUrl: relationship !== "joined"
        ? `https://ui.awin.com/merchant-programme/${p.id}`
        : null,
    }));

    return NextResponse.json({ ok: true, count: result.length, programmes: result });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Awin API error";
    return NextResponse.json({ ok: false, error: message }, { status: 502 });
  }
}
