import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GiftSense – AI Gift Recommender",
  description:
    "Analyze social media profiles to find the perfect gift ideas for your loved ones.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gradient-to-br from-brand-50 via-purple-50 to-pink-50 antialiased">
        {children}
      </body>
    </html>
  );
}
