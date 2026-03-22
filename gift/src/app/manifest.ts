import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "GiftSense – Idées Cadeaux par IA",
    short_name: "GiftSense",
    description:
      "Trouvez le cadeau parfait en quelques secondes grâce à l'IA. Analysez les profils Instagram, TikTok et Pinterest.",
    start_url: "/",
    display: "standalone",
    background_color: "#FEFCF8",
    theme_color: "#C88B5C",
    orientation: "portrait-primary",
    lang: "fr",
    categories: ["shopping", "lifestyle", "utilities"],
    icons: [
      {
        src: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎁</text></svg>",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any maskable",
      },
    ],
    screenshots: [
      {
        src: "/opengraph-image",
        sizes: "1200x630",
        type: "image/png",
        // @ts-expect-error – form_factor is not yet in Next.js types but valid in spec
        form_factor: "wide",
        label: "GiftSense sur desktop",
      },
    ],
    prefer_related_applications: false,
  };
}
