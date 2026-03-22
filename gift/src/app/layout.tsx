import type { Metadata } from "next";
import "./globals.css";

const SITE_URL = "https://giftsense.coffeet.fr";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "GiftSense – Idées cadeaux IA personnalisées",
    template: "%s | GiftSense",
  },
  description:
    "Trouvez le cadeau parfait grâce à l'IA. Analysez les profils Instagram, TikTok et Pinterest de vos proches pour des idées uniques, tendance et 100% halal.",
  keywords: [
    "idées cadeaux",
    "cadeau personnalisé",
    "cadeau halal",
    "intelligence artificielle",
    "cadeau anniversaire",
    "cadeau noel",
    "cadeau saint-valentin",
    "giftsense",
    "coffeet",
  ],
  authors: [{ name: "GiftSense by Coffeet" }],
  creator: "Coffeet",
  publisher: "Coffeet",
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  },
  alternates: {
    canonical: SITE_URL,
    languages: { "fr-FR": SITE_URL },
  },
  openGraph: {
    type: "website",
    locale: "fr_FR",
    url: SITE_URL,
    siteName: "GiftSense",
    title: "GiftSense – Idées cadeaux IA personnalisées",
    description:
      "Analysez n'importe quel profil Instagram, TikTok ou Pinterest et obtenez des idées cadeaux personnalisées, tendance et halal en quelques secondes.",
    images: [
      {
        url: "/opengraph-image",
        width: 1200,
        height: 630,
        alt: "GiftSense – Idées cadeaux IA personnalisées",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "GiftSense – Idées cadeaux IA personnalisées",
    description:
      "Découvrez le cadeau parfait grâce à l'IA. Profils sociaux analysés, idées tendance, 100% halal.",
    images: ["/opengraph-image"],
    creator: "@coffeet_fr",
  },
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎁</text></svg>",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "GiftSense",
  description:
    "Outil IA de recommandation de cadeaux personnalisés basé sur l'analyse des profils réseaux sociaux.",
  url: SITE_URL,
  applicationCategory: "LifestyleApplication",
  operatingSystem: "Web",
  inLanguage: "fr-FR",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "EUR",
  },
  creator: {
    "@type": "Organization",
    name: "Coffeet",
    url: "https://coffeet.fr",
  },
  featureList: [
    "Analyse de profils Instagram, TikTok, Pinterest, YouTube",
    "Recommandations cadeaux personnalisées par IA",
    "Filtrage halal garanti",
    "Produits tendance en temps réel",
    "Export PDF de la liste",
    "Partage par lien",
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="min-h-screen bg-gradient-to-br from-brand-50 via-purple-50 to-pink-50 antialiased dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
        {children}
      </body>
    </html>
  );
}
