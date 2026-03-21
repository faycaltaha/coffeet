#!/usr/bin/env tsx
/**
 * Awin Bot — scanne tous les programmes Awin et génère un rapport
 * des partenaires recommandés par catégorie de cadeau.
 *
 * Usage:
 *   AWIN_API_KEY=xxx AWIN_PUBLISHER_ID=yyy npx tsx scripts/awin-bot.ts
 *
 * Options:
 *   --apply    (désactivé par défaut) — imprime les liens d'inscription aux programmes
 *   --country  (défaut: FR)           — code pays Awin
 *   --format   json | table (défaut: table)
 */

import {
  fetchProgrammes,
  fetchTransactions,
  buildDeepLink,
  matchesCategory,
  CATEGORY_SECTORS,
  AwinProgramme,
} from "../src/lib/awin-client";

// ─── Config ──────────────────────────────────────────────────────────────────

const GIFT_CATEGORIES = Object.keys(CATEGORY_SECTORS);
const COUNTRY = process.argv.includes("--country")
  ? process.argv[process.argv.indexOf("--country") + 1]
  : "FR";
const FORMAT = process.argv.includes("--format")
  ? process.argv[process.argv.indexOf("--format") + 1]
  : "table";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function printTable(rows: Record<string, string>[]) {
  if (rows.length === 0) {
    console.log("  (aucun résultat)");
    return;
  }
  const keys = Object.keys(rows[0]);
  const widths = keys.map((k) =>
    Math.max(k.length, ...rows.map((r) => (r[k] ?? "").length))
  );
  const line = widths.map((w) => "─".repeat(w + 2)).join("┼");
  const header = keys.map((k, i) => ` ${k.padEnd(widths[i])} `).join("│");
  console.log(`┌${widths.map((w) => "─".repeat(w + 2)).join("┬")}┐`);
  console.log(`│${header}│`);
  console.log(`├${line}┤`);
  for (const row of rows) {
    const cells = keys.map((k, i) => ` ${(row[k] ?? "").padEnd(widths[i])} `).join("│");
    console.log(`│${cells}│`);
  }
  console.log(`└${widths.map((w) => "─".repeat(w + 2)).join("┴")}┘`);
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main() {
  console.log("\n🤖 Awin Bot — Scan des partenaires\n");

  // 1. Programmes déjà rejoints
  console.log("📋 Chargement des programmes rejoints...");
  let joined: AwinProgramme[] = [];
  try {
    joined = await fetchProgrammes("joined", COUNTRY);
    console.log(`   ✓ ${joined.length} programmes actifs\n`);
  } catch (err) {
    console.error("   ✗ Erreur API Awin:", (err as Error).message);
    console.log("   → Vérifiez AWIN_API_KEY et AWIN_PUBLISHER_ID\n");
    process.exit(1);
  }

  // 2. Programmes disponibles (non rejoints)
  console.log("🔍 Scan des programmes disponibles...");
  let available: AwinProgramme[] = [];
  try {
    available = await fetchProgrammes("notjoined", COUNTRY);
    console.log(`   ✓ ${available.length} programmes disponibles à rejoindre\n`);
  } catch {
    console.log("   ⚠ Impossible de charger les programmes non-rejoints\n");
  }

  // 3. Transactions récentes (revenus)
  console.log("💶 Revenus des 30 derniers jours...");
  try {
    const txs = await fetchTransactions({ status: "approved" });
    const total = txs.reduce((sum, t) => sum + t.commissionAmount.amount, 0);
    console.log(`   ✓ ${txs.length} transactions approuvées — Total: ${total.toFixed(2)} €\n`);
  } catch {
    console.log("   ⚠ Impossible de charger les transactions\n");
  }

  // 4. Rapport par catégorie
  console.log("━".repeat(70));
  console.log("📊 PROGRAMMES REJOINTS PAR CATÉGORIE DE CADEAU");
  console.log("━".repeat(70));

  const report: Record<
    string,
    { joined: AwinProgramme[]; recommended: AwinProgramme[] }
  > = {};

  for (const cat of GIFT_CATEGORIES) {
    const catJoined = joined.filter((p) => matchesCategory(p, cat));
    const catAvailable = available
      .filter((p) => matchesCategory(p, cat))
      .slice(0, 5); // top 5 recommandations

    report[cat] = { joined: catJoined, recommended: catAvailable };
  }

  if (FORMAT === "json") {
    const output = Object.entries(report).map(([cat, data]) => ({
      category: cat,
      joined: data.joined.map((p) => ({
        id: p.id,
        name: p.name,
        sector: p.primarySector,
        deepLinkExample: buildDeepLink(p.id, `https://www.${p.displayUrl}`),
      })),
      recommended: data.recommended.map((p) => ({
        id: p.id,
        name: p.name,
        sector: p.primarySector,
        applyUrl: `https://ui.awin.com/merchant-programme/${p.id}`,
      })),
    }));
    console.log(JSON.stringify(output, null, 2));
    return;
  }

  // Table format
  for (const [cat, data] of Object.entries(report)) {
    console.log(`\n🏷  ${cat.toUpperCase()}`);

    if (data.joined.length > 0) {
      console.log("\n  ✅ Partenaires actifs (deep links disponibles) :");
      printTable(
        data.joined.map((p) => ({
          ID: String(p.id),
          Nom: p.name,
          Secteur: p.primarySector ?? "—",
          "Deep Link": buildDeepLink(p.id, `https://www.${p.displayUrl}`).slice(0, 60) + "…",
        }))
      );
    } else {
      console.log("  ⚪ Aucun partenaire actif pour cette catégorie");
    }

    if (data.recommended.length > 0) {
      console.log("\n  🆕 Recommandés à rejoindre :");
      printTable(
        data.recommended.map((p) => ({
          ID: String(p.id),
          Nom: p.name,
          Secteur: p.primarySector ?? "—",
          "Lien candidature": `https://ui.awin.com/merchant-programme/${p.id}`,
        }))
      );
    }
  }

  // 5. Résumé global
  console.log("\n" + "━".repeat(70));
  console.log("📌 RÉSUMÉ");
  console.log("━".repeat(70));

  const joinedCount = new Set(
    GIFT_CATEGORIES.flatMap((cat) => report[cat].joined.map((p) => p.id))
  ).size;

  const recommendedCount = new Set(
    GIFT_CATEGORIES.flatMap((cat) => report[cat].recommended.map((p) => p.id))
  ).size;

  console.log(`\n  Programmes actifs couvrant les catégories cadeaux : ${joinedCount}`);
  console.log(`  Programmes suggérés à rejoindre                   : ${recommendedCount}`);

  const uncoveredCats = GIFT_CATEGORIES.filter(
    (cat) => report[cat].joined.length === 0
  );
  if (uncoveredCats.length > 0) {
    console.log(
      `\n  ⚠ Catégories sans partenaire actif : ${uncoveredCats.join(", ")}`
    );
    console.log("    → Rejoignez les programmes recommandés ci-dessus pour maximiser les revenus");
  }

  console.log("\n✅ Scan terminé.\n");
}

main().catch((err) => {
  console.error("Erreur fatale:", err);
  process.exit(1);
});
