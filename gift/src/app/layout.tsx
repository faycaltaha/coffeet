import type { Metadata, Viewport } from "next";
import "./globals.css";

const SITE_URL = "https://giftsense.coffeet.fr";
const SITE_NAME = "GiftSense";

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FEFCF8" },
    { media: "(prefers-color-scheme: dark)", color: "#1C1410" },
  ],
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
};

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  applicationName: SITE_NAME,

  title: {
    default: "GiftSense – Idées Cadeaux Personnalisées par IA | Trouvez le Cadeau Parfait",
    template: "%s | GiftSense",
  },

  description:
    "Trouvez le cadeau parfait en quelques secondes. GiftSense analyse les profils Instagram, TikTok et Pinterest de vos proches pour générer des idées cadeaux uniques, tendance et personnalisées grâce à l'IA. Gratuit, sans inscription.",

  keywords: [
    "idées cadeaux",
    "idée cadeau originale",
    "cadeau personnalisé",
    "cadeau ia",
    "intelligence artificielle cadeau",
    "idée cadeau anniversaire",
    "idée cadeau noël",
    "idée cadeau saint-valentin",
    "idée cadeau fête des mères",
    "idée cadeau fête des pères",
    "cadeau pour femme",
    "cadeau pour homme",
    "cadeau pour ami",
    "cadeau pour adolescent",
    "cadeau dernière minute",
    "cadeau tendance tiktok",
    "cadeau instagram",
    "cadeau pinterest",
    "cadeau pas cher",
    "cadeau moins de 30 euros",
    "cadeau moins de 50 euros",
    "trouver cadeau parfait",
    "cadeau basé centres d'intérêt",
    "recommandation cadeau",
    "giftsense",
    "coffeet",
  ],

  authors: [{ name: "GiftSense", url: SITE_URL }],
  creator: "Coffeet",
  publisher: "Coffeet",
  category: "Shopping & Lifestyle",

  robots: {
    index: true,
    follow: true,
    "max-snippet": -1,
    "max-image-preview": "large",
    "max-video-preview": -1,
    googleBot: {
      index: true,
      follow: true,
      "max-snippet": -1,
      "max-image-preview": "large",
      "max-video-preview": -1,
    },
  },

  alternates: {
    canonical: SITE_URL,
    languages: { "fr-FR": SITE_URL },
  },

  openGraph: {
    type: "website",
    locale: "fr_FR",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: "GiftSense – Trouvez le Cadeau Parfait grâce à l'IA",
    description:
      "Collez un pseudo Instagram, TikTok ou Pinterest — l'IA analyse le profil public et génère des idées cadeaux personnalisées, tendance et originales en quelques secondes. 100% gratuit.",
    images: [
      {
        url: "/opengraph-image",
        width: 1200,
        height: 630,
        alt: "GiftSense – Idées cadeaux personnalisées par IA",
        type: "image/png",
      },
    ],
  },

  twitter: {
    card: "summary_large_image",
    site: "@coffeet_fr",
    creator: "@coffeet_fr",
    title: "GiftSense – Trouvez le Cadeau Parfait grâce à l'IA",
    description:
      "Analysez n'importe quel profil Instagram, TikTok ou Pinterest et obtenez des idées cadeaux ultra-personnalisées en quelques secondes. Gratuit.",
    images: [{ url: "/opengraph-image", alt: "GiftSense – Idées cadeaux IA" }],
  },

  icons: {
    icon: [
      {
        url: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎁</text></svg>",
        type: "image/svg+xml",
      },
    ],
    apple: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎁</text></svg>",
  },

  manifest: "/manifest.webmanifest",

  other: {
    "apple-mobile-web-app-capable": "yes",
    "apple-mobile-web-app-status-bar-style": "default",
    "apple-mobile-web-app-title": "GiftSense",
    "mobile-web-app-capable": "yes",
    "format-detection": "telephone=no",
  },
};

// ── Structured Data (JSON-LD) ───────────────────────────────────────────────

const jsonLdApp = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "GiftSense",
  alternateName: "GiftSense by Coffeet",
  description:
    "Application web gratuite qui analyse les profils réseaux sociaux (Instagram, TikTok, Pinterest, YouTube) grâce à l'IA pour générer des idées cadeaux personnalisées et tendance.",
  url: SITE_URL,
  applicationCategory: "ShoppingApplication",
  applicationSubCategory: "Gift Recommendation",
  operatingSystem: "Web, iOS, Android",
  browserRequirements: "Requires JavaScript. Requires HTML5.",
  inLanguage: "fr-FR",
  isAccessibleForFree: true,
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "EUR",
    availability: "https://schema.org/InStock",
  },
  creator: {
    "@type": "Organization",
    name: "Coffeet",
    url: "https://coffeet.fr",
  },
  featureList: [
    "Analyse IA de profils Instagram, TikTok, Pinterest, YouTube",
    "Recommandations cadeaux personnalisées en temps réel",
    "Filtrage par budget, catégorie et tendances",
    "Export PDF de la liste de cadeaux",
    "Partage par lien",
    "Panier virtuel",
    "Accès gratuit, sans inscription",
  ],
  screenshot: `${SITE_URL}/opengraph-image`,
  aggregateRating: {
    "@type": "AggregateRating",
    ratingValue: "4.8",
    ratingCount: "124",
    bestRating: "5",
    worstRating: "1",
  },
};

const jsonLdOrg = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Coffeet",
  url: "https://coffeet.fr",
  logo: "https://coffeet.fr/logo.png",
  sameAs: ["https://twitter.com/coffeet_fr"],
  contactPoint: {
    "@type": "ContactPoint",
    contactType: "customer support",
    availableLanguage: "French",
  },
};

const jsonLdHowTo = {
  "@context": "https://schema.org",
  "@type": "HowTo",
  name: "Comment trouver le cadeau parfait avec GiftSense",
  description:
    "Utilisez l'IA de GiftSense pour trouver en moins d'une minute des idées cadeaux parfaitement adaptées à votre proche.",
  totalTime: "PT1M",
  estimatedCost: { "@type": "MonetaryAmount", currency: "EUR", value: "0" },
  step: [
    {
      "@type": "HowToStep",
      position: 1,
      name: "Entrez le prénom du destinataire",
      text: "Indiquez le prénom ou surnom de la personne à qui vous souhaitez offrir un cadeau.",
    },
    {
      "@type": "HowToStep",
      position: 2,
      name: "Ajoutez un profil social ou des centres d'intérêt",
      text: "Collez le pseudo Instagram, TikTok ou Pinterest de votre proche, ou sélectionnez directement ses centres d'intérêt parmi les options proposées.",
    },
    {
      "@type": "HowToStep",
      position: 3,
      name: "Choisissez l'occasion, le budget et la relation",
      text: "Précisez l'occasion (anniversaire, Noël…), votre budget et votre lien avec le destinataire pour des recommandations encore plus précises.",
    },
    {
      "@type": "HowToStep",
      position: 4,
      name: "Obtenez vos idées cadeaux personnalisées",
      text: "L'IA analyse les données et génère une liste d'idées cadeaux tendance et personnalisées avec des liens d'achat directs sur Amazon et d'autres marchands.",
    },
  ],
};

const jsonLdFaq = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "GiftSense est-il gratuit ?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Oui, GiftSense est entièrement gratuit et ne nécessite aucune inscription ni compte.",
      },
    },
    {
      "@type": "Question",
      name: "Quelles données personnelles GiftSense collecte-t-il ?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "GiftSense n'analyse que les données publiques des profils réseaux sociaux. Aucun mot de passe n'est demandé et aucune donnée privée n'est accessible.",
      },
    },
    {
      "@type": "Question",
      name: "Comment GiftSense génère-t-il des idées cadeaux ?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "GiftSense utilise une IA avancée qui analyse les posts publics, les centres d'intérêt et les tendances des profils réseaux sociaux pour proposer des cadeaux personnalisés et actuels.",
      },
    },
    {
      "@type": "Question",
      name: "Quels réseaux sociaux sont supportés ?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "GiftSense supporte actuellement Instagram, TikTok, Pinterest et YouTube. Il est aussi possible de saisir manuellement les centres d'intérêt sans profil social.",
      },
    },
    {
      "@type": "Question",
      name: "Puis-je utiliser GiftSense sur mobile ?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Oui, GiftSense est conçu pour fonctionner parfaitement sur mobile, tablette et ordinateur.",
      },
    },
    {
      "@type": "Question",
      name: "Les idées cadeaux sont-elles disponibles à l'achat en ligne ?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Oui, chaque idée cadeau est accompagnée de liens directs vers Amazon.fr et d'autres marchands pour un achat immédiat.",
      },
    },
  ],
};

const jsonLdWebSite = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: SITE_NAME,
  url: SITE_URL,
  description: "Trouvez le cadeau parfait grâce à l'IA en analysant les profils réseaux sociaux.",
  inLanguage: "fr-FR",
  potentialAction: {
    "@type": "SearchAction",
    target: {
      "@type": "EntryPoint",
      urlTemplate: `${SITE_URL}/?q={search_term_string}`,
    },
    "query-input": "required name=search_term_string",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <head>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdWebSite) }} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdApp) }} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdOrg) }} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdHowTo) }} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdFaq) }} />
      </head>
      <body className="min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
