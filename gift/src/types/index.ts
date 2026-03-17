export interface SocialProfile {
  platform: "instagram" | "tiktok" | "pinterest" | "youtube";
  handle: string;
}

export interface GiftIdea {
  title: string;
  description: string;
  priceRange: string;
  category: string;
  reason: string;
  searchQuery: string;
  trending?: boolean;
  trendSource?: string;
}

export interface AnalysisResult {
  profileSummary: string;
  interests: string[];
  giftIdeas: GiftIdea[];
  occasion?: string;
}

export interface AnalyzeRequest {
  profiles: SocialProfile[];
  recipientName: string;
  occasion: string;
  budget: string;
  relationship: string;
  interests: string[];
}

export interface AnalyzeResponse {
  success: boolean;
  data?: AnalysisResult;
  error?: string;
}
