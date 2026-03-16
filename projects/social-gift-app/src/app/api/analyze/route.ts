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

  const { profiles, recipientName, occasion, budget, relationship } = body;

  if (!profiles || profiles.length === 0) {
    return NextResponse.json({ success: false, error: "At least one social profile is required." }, { status: 400 });
  }

  const client = new OpenAI({
    baseURL: "https://openrouter.ai/api/v1",
    apiKey,
    defaultHeaders: {
      "HTTP-Referer": "https://coffeet.fr",
      "X-Title": "Coffeet Gift Recommender",
    },
  });

  // Build profile URL list for the model to search
  const profileList = profiles
    .map((p) => `- ${p.platform.charAt(0).toUpperCase() + p.platform.slice(1)}: ${PLATFORM_URLS[p.platform](p.handle)}`)
    .join("\n");

  const systemPrompt = `You are GiftSense, an expert halal-friendly gift advisor. Your job is to:
1. Search and browse each social media profile URL provided
2. Analyse the public content (posts, bio, highlights, saved content) to understand the person's interests, hobbies, aesthetic preferences, and lifestyle
3. Generate highly personalised gift recommendations

When searching profiles, look for:
- Bio/description
- Content themes and recurring topics
- Products/brands they mention or tag
- Activities and hobbies
- Aesthetic style (minimalist, bohemian, sporty, etc.)
- Food, travel, or cultural preferences

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
      "searchQuery": "Google search query to find this gift online"
    }
  ]
}

Generate 6–8 diverse gift ideas spanning different price points within the budget, ordered from most to least personalised.`;

  const userMessage = `Please search these social media profiles and suggest gifts for ${recipientName}:

${profileList}

Gift context:
- Occasion: ${occasion}
- Budget: ${budget}
- Relationship: ${relationship}

Search each profile URL, identify their interests, then generate gift ideas. Return only valid JSON.`;

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
