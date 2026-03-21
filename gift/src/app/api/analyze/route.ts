import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";
import type { AnalyzeRequest, AnalyzeResponse, AnalysisResult, GiftIdea } from "@/types";

// Keywords that flag a gift as haram — checked against title + description + searchQuery
const HARAM_KEYWORDS = [
  // Alcohol
  "alcohol", "wine", "beer", "whisky", "whiskey", "vodka", "rum", "gin", "champagne",
  "prosecco", "cocktail", "spirits", "liquor", "brandy", "bourbon", "sake", "mead",
  // Tobacco & smoking
  "tobacco", "cigarette", "cigar", "vape", "vaping", "hookah", "shisha", "nicotine",
  "e-cigarette", "smoke kit",
  // Drugs
  "cannabis", "marijuana", "weed", "cbd", "thc", "drug",
  // Pork & non-halal food
  "pork", "bacon", "ham", "prosciutto", "salami", "chorizo", "lard", "pepperoni",
  "charcuterie", "gelatin",
  // Adult / gambling
  "lingerie", "sex", "adult", "erotic", "porn", "gambling", "casino", "lottery",
];

function isHaram(gift: GiftIdea): boolean {
  const text = `${gift.title} ${gift.description} ${gift.searchQuery}`.toLowerCase();
  return HARAM_KEYWORDS.some((kw) => text.includes(kw));
}

function filterHalal(gifts: GiftIdea[]): GiftIdea[] {
  return gifts.filter((g) => !isHaram(g));
}

const PLATFORM_URLS: Record<string, (handle: string) => string> = {
  instagram: (h) => `https://www.instagram.com/${h}/`,
  tiktok: (h) => `https://www.tiktok.com/@${h}`,
  pinterest: (h) => `https://www.pinterest.com/${h}/`,
  youtube: (h) => `https://www.youtube.com/@${h}`,
};

export async function POST(req: NextRequest): Promise<NextResponse<AnalyzeResponse>> {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ success: false, error: "OpenRouter API key not configured." }, { status: 500 });
  }

  let body: AnalyzeRequest;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ success: false, error: "Invalid request body." }, { status: 400 });
  }

  const { profiles, recipientName, occasion, budget, relationship, interests } = body;

  if (!profiles) {
    return NextResponse.json({ success: false, error: "Invalid profiles field." }, { status: 400 });
  }

  const client = new OpenAI({
    baseURL: "https://openrouter.ai/api/v1",
    apiKey,
    defaultHeaders: {
      "HTTP-Referer": "https://coffeet.fr",
      "X-Title": "Coffeet Gift Recommender",
    },
  });

  const currentYear = new Date().getFullYear();

  const hasProfiles = profiles.length > 0;

  // Build profile URL list for the model to search
  const profileList = profiles
    .map((p) => `- ${p.platform.charAt(0).toUpperCase() + p.platform.slice(1)}: ${PLATFORM_URLS[p.platform](p.handle)}`)
    .join("\n");

  const systemPrompt = `You are GiftSense, an expert halal-friendly gift advisor. Your job is to:
${hasProfiles ? `1. Search and browse each social media profile URL provided
2. Analyse the public content (posts, bio, highlights, saved content) to understand the person's interests, hobbies, aesthetic preferences, and lifestyle
3. Search for currently trending gift products on TikTok, Instagram, and Pinterest that match the person's interests and the occasion
4. Generate highly personalised gift recommendations, mixing profile-matched picks with trending viral products they may have already seen on their feed

When searching profiles, look for:
- Bio/description
- Content themes and recurring topics
- Products/brands they mention or tag
- Activities and hobbies
- Aesthetic style (minimalist, bohemian, sporty, etc.)
- Food, travel, or cultural preferences` : `1. Use the provided interests, occasion, relationship and budget to understand what gifts would be most fitting
2. Search for currently trending gift products on TikTok, Instagram, and Pinterest that match the interests and the occasion
3. Generate creative and personalised gift recommendations based on the known interests and context`}

When searching for trending products:
- Search TikTok Shop, Instagram Shopping, and Pinterest trends for the person's interest categories
- Search "trending gifts [category] ${currentYear}" and "viral [category] products TikTok ${currentYear}"
- Identify products that are currently viral or widely shared on social media
- Look for products that appear in gift guides, "things I bought" TikToks, or Pinterest boards
- For each trending item found, note the platform where it is trending

STRICT CONTENT RULES — NEVER suggest anything involving:
- Alcohol, wine, beer, spirits, or any intoxicating beverages
- Tobacco, cigarettes, cigars, vapes, hookahs, or smoking accessories
- Drugs, cannabis, CBD products, or any controlled substances
- Pork, gelatin of unknown origin, or non-halal food products
- Adult/sexual content, lingerie, or explicit material
- Gambling, lottery, or games of chance
- Any content that could be considered haram (forbidden in Islam)

If the person's profile interests point toward any of the above, substitute with a halal alternative in the same spirit (e.g. mocktail kit instead of cocktail kit, halal snack box instead of charcuterie).

Always respond with VALID JSON only (no markdown fences) in this exact structure:
{
  "profileSummary": "2-3 sentence description of the person based on their social presence",
  "interests": ["interest1", "interest2", ...],
  "giftIdeas": [
    {
      "title": "Gift name",
      "description": "2-3 sentence description of the gift and why it's great",
      "priceRange": "€XX–€XX",
      "category": "one of: experience|fashion|tech|beauty|food|books|home|sport|travel|art",
      "reason": "One sentence: why this matches their profile",
      "searchQuery": "Google search query to find this gift online",
      "trending": true or false,
      "trendSource": "e.g. TikTok Viral, Instagram Trending, Pinterest Popular — or null if not trending"
    }
  ]
}

Generate 6–8 diverse gift ideas spanning different price points within the budget. Include at least 2–3 currently trending items if relevant. Order: trending items first, then most-personalised, then general.`;

  const interestsLine = interests && interests.length > 0
    ? `- Known interests: ${interests.join(", ")}`
    : "";

  const userMessage = hasProfiles
    ? `Please search these social media profiles and suggest gifts for ${recipientName}:

${profileList}

Gift context:
- Occasion: ${occasion}
- Budget: ${budget}
- Relationship: ${relationship}
${interestsLine}

Steps to follow:
1. Browse each profile URL and identify their interests, style, and personality
2. Search for products currently trending on TikTok, Instagram, and Pinterest that match their interests and the "${occasion}" occasion — use queries like "viral gift [interest] TikTok ${currentYear}", "trending [interest] gifts Instagram ${currentYear}", "best gift [interest] Pinterest ${currentYear}"
3. Combine profile insights with trending products to generate personalised recommendations
${interests && interests.length > 0 ? "4. Use the known interests as strong hints to guide both profile analysis and trend searches." : ""}

Return only valid JSON.`
    : `Please suggest gifts for ${recipientName} based on the following context:

Gift context:
- Occasion: ${occasion}
- Budget: ${budget}
- Relationship: ${relationship}
${interestsLine}

Steps to follow:
1. Search for products currently trending on TikTok, Instagram, and Pinterest that match the interests and the "${occasion}" occasion — use queries like "viral gift [interest] TikTok ${currentYear}", "trending [interest] gifts Instagram ${currentYear}", "best gift [interest] Pinterest ${currentYear}"
2. Generate personalised and creative recommendations based on the interests and occasion
${interests && interests.length > 0 ? "3. Prioritise ideas that directly reflect the known interests." : "3. Suggest diverse ideas that would suit someone for this occasion."}

Return only valid JSON. Set profileSummary to a short description of the gift recipient based on the provided interests and context (not based on any profile).`;

  try {
    const response = await client.chat.completions.create({
      model: "perplexity/sonar-pro",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userMessage },
      ],
      max_tokens: 4096,
    });

    const finalText = response.choices[0]?.message?.content ?? "";

    if (!finalText) {
      return NextResponse.json({ success: false, error: "No response from AI." }, { status: 500 });
    }

    // Extract JSON from text (strip any accidental markdown)
    const jsonMatch = finalText.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return NextResponse.json({ success: false, error: "Could not parse AI response." }, { status: 500 });
    }

    const analysisResult: AnalysisResult = JSON.parse(jsonMatch[0]);

    // Safety net: strip any haram items the AI may have slipped through
    analysisResult.giftIdeas = filterHalal(analysisResult.giftIdeas);

    return NextResponse.json({ success: true, data: analysisResult });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
