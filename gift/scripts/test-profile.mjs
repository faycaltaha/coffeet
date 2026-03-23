/**
 * Test automatique — Analyse du profil Instagram faycal.taha9
 * Lancer depuis le terminal StackBlitz : node scripts/test-profile.mjs
 */

import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

// Lire .env.local
const __dir = dirname(fileURLToPath(import.meta.url));
const envPath = join(__dir, "../.env.local");
const envContent = readFileSync(envPath, "utf-8");
const apiKey = envContent.match(/OPENROUTER_API_KEY=(.+)/)?.[1]?.trim();

if (!apiKey) {
  console.error("❌ OPENROUTER_API_KEY introuvable dans .env.local");
  process.exit(1);
}

const HANDLE = "faycal.taha9";
const currentYear = new Date().getFullYear();

const systemPrompt = `You are GiftSense, an expert halal-friendly gift advisor. Your job is to:
1. Search and browse each social media profile URL provided
2. Analyse the public content (posts, bio, highlights, saved content) to understand the person's interests, hobbies, aesthetic preferences, and lifestyle
3. Search for currently trending gift products on TikTok, Instagram, and Pinterest that match the person's interests and the occasion
4. Generate highly personalised gift recommendations, mixing profile-matched picks with trending viral products

STRICT RULES — NEVER suggest: alcohol, tobacco, drugs, pork/gelatin, adult content, gambling.

Always respond with VALID JSON only (no markdown fences):
{
  "profileSummary": "2-3 sentence description",
  "interests": ["interest1", "interest2"],
  "giftIdeas": [
    {
      "title": "Gift name",
      "description": "2-3 sentence description",
      "priceRange": "€XX-€XX",
      "category": "fashion|tech|beauty|food|books|home|sport|travel|art|experience",
      "reason": "One sentence why this matches their profile",
      "searchQuery": "Google search query",
      "trending": true,
      "trendSource": "TikTok Viral or null"
    }
  ]
}
Generate 10-12 diverse gift ideas. Include at least 3-4 trending items. Order: trending first.`;

const userMessage = `Please search this Instagram profile and suggest birthday gifts for Faycal:

- Instagram: https://www.instagram.com/${HANDLE}/

Gift context:
- Occasion: Anniversaire
- Budget: 50-100€
- Relationship: ami

Steps:
1. Browse the profile and identify interests, style, personality
2. Search trending gifts on TikTok/Instagram/Pinterest matching their interests — use "viral gift [interest] TikTok ${currentYear}", "trending [interest] gifts Instagram ${currentYear}"
3. Combine profile insights with trending products

Return only valid JSON.`;

console.log(`🔍 Analyse du profil Instagram: @${HANDLE}`);
console.log("⏳ Connexion à OpenRouter (perplexity/sonar-pro)...\n");

const start = Date.now();

const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
    "HTTP-Referer": "https://coffeet.fr",
    "X-Title": "Coffeet Gift Recommender",
  },
  body: JSON.stringify({
    model: "perplexity/sonar-pro",
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userMessage },
    ],
    max_tokens: 4096,
  }),
});

const elapsed = ((Date.now() - start) / 1000).toFixed(1);

if (!res.ok) {
  const err = await res.text();
  console.error(`❌ Erreur HTTP ${res.status}:`, err);
  process.exit(1);
}

const data = await res.json();
const content = data.choices?.[0]?.message?.content;

if (!content) {
  console.error("❌ Réponse vide de l'IA:", JSON.stringify(data, null, 2));
  process.exit(1);
}

console.log(`✅ Réponse reçue en ${elapsed}s\n`);

// Parse JSON
const jsonMatch = content.match(/\{[\s\S]*\}/);
if (!jsonMatch) {
  console.error("❌ Impossible de parser le JSON. Réponse brute:");
  console.log(content);
  process.exit(1);
}

const result = JSON.parse(jsonMatch[0]);

// Display results
console.log("═".repeat(60));
console.log("👤 RÉSUMÉ DU PROFIL");
console.log("═".repeat(60));
console.log(result.profileSummary);

console.log("\n" + "═".repeat(60));
console.log("🎯 INTÉRÊTS DÉTECTÉS");
console.log("═".repeat(60));
console.log(result.interests?.join(" · ") || "(aucun)");

const gifts = result.giftIdeas || [];
console.log("\n" + "═".repeat(60));
console.log(`🎁 ${gifts.length} IDÉES CADEAUX`);
console.log("═".repeat(60));

const HARAM = ["alcohol","wine","beer","whisky","vodka","rum","gin","champagne",
  "tobacco","cigarette","cigar","vape","cannabis","marijuana","cbd","thc",
  "pork","bacon","ham","salami","chorizo","gelatin","lingerie","sex","adult",
  "erotic","gambling","casino"];

gifts.forEach((g, i) => {
  const text = `${g.title} ${g.description} ${g.searchQuery}`.toLowerCase();
  const haram = HARAM.some(k => text.includes(k));
  const trendBadge = g.trending ? ` 🔥 ${g.trendSource || "Trending"}` : "";
  const haramBadge = haram ? " ⚠️ HARAM FILTERED" : "";

  console.log(`\n${i + 1}. ${g.title} (${g.priceRange}) [${g.category}]${trendBadge}${haramBadge}`);
  console.log(`   ${g.description}`);
  console.log(`   → ${g.reason}`);
  if (!haram) {
    console.log(`   🔗 Amazon: https://www.amazon.fr/s?k=${encodeURIComponent(g.searchQuery)}`);
  }
});

const filtered = gifts.filter(g => {
  const text = `${g.title} ${g.description} ${g.searchQuery}`.toLowerCase();
  return HARAM.some(k => text.includes(k));
});

console.log("\n" + "═".repeat(60));
console.log(`✅ ${gifts.length - filtered.length} cadeaux halal validés`);
if (filtered.length > 0) {
  console.log(`⚠️  ${filtered.length} éléments filtrés (haram)`);
}
console.log("═".repeat(60));
