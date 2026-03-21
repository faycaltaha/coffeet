#!/usr/bin/env tsx
/**
 * Awin Bot — auto-rejoint TOUS les programmes Awin disponibles,
 * récupère les taux de commission et génère un cache trié par rémunération.
 *
 * Usage:
 *   AWIN_API_KEY=xxx AWIN_PUBLISHER_ID=yyy npx tsx scripts/awin-bot.ts
 *   AWIN_API_KEY=xxx AWIN_PUBLISHER_ID=yyy npm run awin:scan
 *
 * Ce que fait le bot :
 *   1. Récupère tous les programmes Awin FR disponibles
 *   2. Auto-rejoint chaque programme (POST /join)
 *   3. Récupère les taux de commission de chaque programme
 *   4. Trie par commission décroissante
 *   5. Sauvegarde dans gift/awin-cache.json (lu par affiliate.ts)
 *   6. Affiche un rapport
 *
 * Options:
 *   --dry-run   Scanne sans rejoindre
 *   --country   Code pays (défaut: FR)
 */

import * as fs from "fs";
import * as path from "path";
import {
  fetchProgrammes,
  fetchCommissions,
  fetchTransactions,
  joinProgramme,
  buildDeepLink,
  matchesCategory,
  bestCommissionPct,
  CATEGORY_SECTORS,
  AwinProgramme,
  EnrichedProgramme,
} from "../src/lib/awin-client";

// ─── Config ──────────────────────────────────────────────────────────────────

const DRY_RUN = process.argv.includes("--dry-run");
const COUNTRY = process.argv.includes("--country")
  ? process.argv[process.argv.indexOf("--country") + 1]
  : "FR";
const GIFT_CATEGORIES = Object.keys(CATEGORY_SECTORS);
const CACHE_PATH = path.join(__dirname, "../awin-cache.json");

// Pause entre chaque join pour ne pas flood l'API
const JOIN_DELAY_MS = 300;

// ─── Helpers ─────────────────────────────────────────────────────────────────

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function bar(pct: number, width = 20): string {
  const filled = Math.round((pct / 30) * width); // 30% = barre pleine
  return "█".repeat(Math.min(filled, width)) + "░".repeat(Math.max(0, width - filled));
}

function printTable(rows: Record<string, string>[]) {
  if (rows.length === 0) { console.log("  (aucun résultat)"); return; }
  const keys = Object.keys(rows[0]);
  const widths = keys.map((k) => Math.max(k.length, ...rows.map((r) => (r[k] ?? "").length)));
  const sep = (l: string, m: string, r: string) =>
    l + widths.map((w) => "─".repeat(w + 2)).join(m) + r;
  console.log(sep("┌", "┬", "┐"));
  console.log("│" + keys.map((k, i) => ` ${k.padEnd(widths[i])} `).join("│") + "│");
  console.log(sep("├", "┼", "┤"));
  for (const row of rows) {
    console.log("│" + keys.map((k, i) => ` ${(row[k] ?? "").padEnd(widths[i])} `).join("│") + "│");
  }
  console.log(sep("└", "┴", "┘"));
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main() {
  console.log("\n🤖 Awin Bot" + (DRY_RUN ? " [DRY RUN]" : "") + "\n");

  // ── 1. Revenus actuels ──────────────────────────────────────────────────────
  console.log("💶 Revenus des 30 derniers jours...");
  try {
    const txs = await fetchTransactions({ status: "approved" });
    const total = txs.reduce((s, t) => s + t.commissionAmount.amount, 0);
    console.log(`   ${txs.length} transactions → ${total.toFixed(2)} € approuvés\n`);
  } catch {
    console.log("   ⚠ Pas de données de transactions\n");
  }

  // ── 2. Programmes déjà rejoints ─────────────────────────────────────────────
  console.log("📋 Programmes déjà rejoints...");
  let joined: AwinProgramme[] = [];
  try {
    joined = await fetchProgrammes("joined", COUNTRY);
    console.log(`   ✓ ${joined.length} actifs\n`);
  } catch (err) {
    console.error("   ✗ Erreur API:", (err as Error).message);
    console.log("   → Vérifiez AWIN_API_KEY et AWIN_PUBLISHER_ID");
    process.exit(1);
  }

  // ── 3. Programmes disponibles ───────────────────────────────────────────────
  console.log("🔍 Scan des programmes disponibles...");
  let available: AwinProgramme[] = [];
  try {
    available = await fetchProgrammes("notjoined", COUNTRY);
    console.log(`   ✓ ${available.length} programmes à rejoindre\n`);
  } catch {
    console.log("   ⚠ Impossible de charger les programmes disponibles\n");
  }

  // ── 4. Auto-join ────────────────────────────────────────────────────────────
  const joinResults: { programme: AwinProgramme; status: string }[] = [];

  if (!DRY_RUN && available.length > 0) {
    console.log(`🚀 Auto-join de ${available.length} programmes...\n`);
    let done = 0;
    for (const p of available) {
      try {
        const result = await joinProgramme(p.id);
        joinResults.push({ programme: p, status: result.status });
        const icon = result.status === "joined" ? "✅" : "⏳";
        process.stdout.write(`\r   ${icon} [${++done}/${available.length}] ${p.name.slice(0, 40).padEnd(40)} — ${result.status}`);
        await sleep(JOIN_DELAY_MS);
      } catch {
        joinResults.push({ programme: p, status: "error" });
        process.stdout.write(`\r   ❌ [${++done}/${available.length}] ${p.name.slice(0, 40).padEnd(40)} — erreur`);
        await sleep(JOIN_DELAY_MS);
      }
    }
    console.log("\n");

    const autoApproved = joinResults.filter((r) => r.status === "joined").length;
    const pending = joinResults.filter((r) => r.status === "pending").length;
    const errors = joinResults.filter((r) => r.status === "error").length;
    console.log(`   ✅ Auto-approuvés : ${autoApproved}`);
    console.log(`   ⏳ En attente    : ${pending}`);
    console.log(`   ❌ Erreurs       : ${errors}\n`);
  } else if (DRY_RUN) {
    console.log(`ℹ️  DRY RUN: ${available.length} programmes identifiés (non rejoints)\n`);
  }

  // ── 5. Récupérer commissions pour tous les programmes rejoints ───────────────
  const allJoined = [
    ...joined,
    ...joinResults.filter((r) => r.status === "joined").map((r) => r.programme),
  ];

  console.log(`📊 Récupération des commissions (${allJoined.length} programmes)...`);
  const enriched: EnrichedProgramme[] = [];

  for (let i = 0; i < allJoined.length; i++) {
    const p = allJoined[i];
    process.stdout.write(`\r   [${i + 1}/${allJoined.length}] ${p.name.slice(0, 50).padEnd(50)}`);
    const groups = await fetchCommissions(p.id);
    const commissionPct = bestCommissionPct(groups);
    const categories = GIFT_CATEGORIES.filter((cat) => matchesCategory(p, cat));
    enriched.push({
      ...p,
      commissionPct,
      deepLink: buildDeepLink(p.id, `https://www.${p.displayUrl}`),
      categories,
    });
    await sleep(100);
  }
  console.log("\n");

  // ── 6. Trier par commission décroissante ────────────────────────────────────
  enriched.sort((a, b) => b.commissionPct - a.commissionPct);

  // ── 7. Sauvegarder le cache ─────────────────────────────────────────────────
  const cache = {
    updatedAt: new Date().toISOString(),
    count: enriched.length,
    programmes: enriched,
  };

  fs.writeFileSync(CACHE_PATH, JSON.stringify(cache, null, 2));
  console.log(`💾 Cache sauvegardé → awin-cache.json (${enriched.length} programmes)\n`);

  // ── 8. Rapport par catégorie trié par commission ────────────────────────────
  console.log("━".repeat(72));
  console.log("🏆 TOP PARTENAIRES PAR CATÉGORIE (triés par commission)");
  console.log("━".repeat(72));

  for (const cat of GIFT_CATEGORIES) {
    const catProgrammes = enriched
      .filter((p) => p.categories.includes(cat))
      .slice(0, 5);

    console.log(`\n🏷  ${cat.toUpperCase()}`);

    if (catProgrammes.length === 0) {
      console.log("   ⚪ Aucun partenaire pour cette catégorie");
      continue;
    }

    printTable(
      catProgrammes.map((p) => ({
        "#": `${p.commissionPct.toFixed(1)}%`,
        "Commission": bar(p.commissionPct),
        "Partenaire": p.name.slice(0, 30),
        "Secteur": (p.primarySector ?? "—").slice(0, 25),
        "Statut": p.status,
      }))
    );
  }

  // ── 9. Top 10 global ────────────────────────────────────────────────────────
  console.log("\n" + "━".repeat(72));
  console.log("🥇 TOP 10 GLOBAL (meilleure commission toutes catégories)");
  console.log("━".repeat(72) + "\n");

  printTable(
    enriched.slice(0, 10).map((p, i) => ({
      Rang: `#${i + 1}`,
      Commission: `${p.commissionPct.toFixed(1)}%`,
      Barre: bar(p.commissionPct),
      Partenaire: p.name.slice(0, 35),
      Catégories: p.categories.join(", ").slice(0, 30) || "—",
    }))
  );

  // ── 10. Catégories sans couverture ──────────────────────────────────────────
  const uncovered = GIFT_CATEGORIES.filter(
    (cat) => !enriched.some((p) => p.categories.includes(cat))
  );
  if (uncovered.length > 0) {
    console.log(`\n⚠  Catégories sans partenaire Awin : ${uncovered.join(", ")}`);
    console.log("   → Amazon Associates couvre ces catégories en fallback");
  }

  console.log(`\n✅ Bot terminé — ${enriched.length} partenaires actifs trackés\n`);
}

main().catch((err) => {
  console.error("\n❌ Erreur fatale:", err);
  process.exit(1);
});
