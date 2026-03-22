import { Suspense } from "react";
import type { Metadata } from "next";
import WishlistContent from "@/components/WishlistContent";

export const metadata: Metadata = {
  title: "Liste de cadeaux partagée",
  description: "Découvrez une liste de cadeaux personnalisée générée par GiftSense.",
  robots: { index: false, follow: false },
};

export default function WishlistPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-4xl animate-pulse">🎁</div>
        </div>
      }
    >
      <WishlistContent />
    </Suspense>
  );
}
