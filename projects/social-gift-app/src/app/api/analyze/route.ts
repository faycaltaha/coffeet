import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
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
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ success: false, error: "API key not configured." }, { status: 500 });
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

  const client = new Anthropic({ apiKey });

  // Build profile URL list for Claude to search
  const profileList = profiles
    .map((p) => `- ${p.platform.charAt(0).toUpperCase() + p.platform.slice(1)}: ${PLATFORM_URLS[p.platform](p.handle)}`)
    .join("\n");

  const systemPrompt = `You are GiftSense, an expert halal-friendly gift advisor. Your job is to:
1. Use the web_search tool to look up each social media profile provided
2. Analyze the public content (posts, bio, highlights, saved content) to understand the person's interests, hobbies, aesthetic preferences, and lifestyle
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

  const userMessage = `Please analyse these social media profiles and suggest gifts for ${recipientName}:

${profileList}

Gift context:
- Occasion: ${occasion}
- Budget: ${budget}
- Relationship: ${relationship}

Search each profile, identify their interests, then generate gift ideas. Return only valid JSON.`;

  try {
    // Use agentic loop with web search
    const messages: Anthropic.MessageParam[] = [
      { role: "user", content: userMessage },
    ];

    let finalText = "";
    let iterations = 0;
    const MAX_ITERATIONS = 8;

    while (iterations < MAX_ITERATIONS) {
      iterations++;

      const response = await client.messages.create({
        model: "claude-opus-4-6",
        max_tokens: 8192,
        system: systemPrompt,
        tools: [
          { type: "web_search_20260209" as const, name: "web_search" },
        ],
        messages,
      });

      // Collect text blocks
      const textBlocks = response.content.filter((b) => b.type === "text");
      if (textBlocks.length > 0) {
        finalText = textBlocks.map((b) => (b as Anthropic.TextBlock).text).join("\n");
      }

      if (response.stop_reason === "end_turn") {
        break;
      }

      if (response.stop_reason === "pause_turn") {
        messages.push({ role: "assistant", content: response.content });
        continue;
      }

      // Handle tool use
      if (response.stop_reason === "tool_use") {
        messages.push({ role: "assistant", content: response.content });

        const toolResults: Anthropic.ToolResultBlockParam[] = response.content
          .filter((b): b is Anthropic.ToolUseBlock => b.type === "tool_use")
          .map((tool) => ({
            type: "tool_result" as const,
            tool_use_id: tool.id,
            content: `Tool ${tool.name} executed with input: ${JSON.stringify(tool.input)}`,
          }));

        if (toolResults.length > 0) {
          messages.push({ role: "user", content: toolResults });
        }
      } else {
        break;
      }
    }

    // Parse the JSON response
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
