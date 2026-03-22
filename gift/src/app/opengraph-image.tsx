import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "GiftSense – Idées Cadeaux Personnalisées par IA";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(150deg, #FEFCF8 0%, #FAF5EC 50%, #FDF8F2 100%)",
          fontFamily: "system-ui, -apple-system, sans-serif",
          padding: "60px",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Orb top-left */}
        <div
          style={{
            position: "absolute",
            top: -120,
            left: -120,
            width: 500,
            height: 500,
            borderRadius: "50%",
            background: "rgba(240,212,187,0.45)",
            filter: "blur(90px)",
          }}
        />
        {/* Orb bottom-right */}
        <div
          style={{
            position: "absolute",
            bottom: -100,
            right: -100,
            width: 450,
            height: 450,
            borderRadius: "50%",
            background: "rgba(250,240,230,0.55)",
            filter: "blur(80px)",
          }}
        />
        {/* Orb center */}
        <div
          style={{
            position: "absolute",
            top: "30%",
            left: "40%",
            width: 360,
            height: 360,
            borderRadius: "50%",
            background: "rgba(245,232,218,0.35)",
            filter: "blur(70px)",
          }}
        />

        {/* Gift emoji */}
        <div style={{ fontSize: 96, marginBottom: 18, display: "flex", lineHeight: 1 }}>🎁</div>

        {/* Title */}
        <div
          style={{
            fontSize: 80,
            fontWeight: 900,
            color: "#7A4D28",
            marginBottom: 16,
            letterSpacing: "-2px",
            display: "flex",
          }}
        >
          GiftSense
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: 28,
            color: "#78716c",
            textAlign: "center",
            maxWidth: 780,
            lineHeight: 1.45,
            marginBottom: 44,
            display: "flex",
          }}
        >
          Trouvez le cadeau parfait grâce à l&apos;IA — personnalisé, tendance, en quelques secondes
        </div>

        {/* Feature chips */}
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", justifyContent: "center" }}>
          {[
            "📸 Instagram",
            "🎵 TikTok",
            "📌 Pinterest",
            "🔥 Tendances",
            "✨ 100% Gratuit",
          ].map((text) => (
            <div
              key={text}
              style={{
                background: "rgba(255, 252, 248, 0.85)",
                border: "1.5px solid rgba(200, 139, 92, 0.28)",
                borderRadius: 40,
                padding: "10px 24px",
                fontSize: 22,
                color: "#57534e",
                fontWeight: 600,
                display: "flex",
                boxShadow: "0 2px 12px rgba(200,139,92,0.10)",
              }}
            >
              {text}
            </div>
          ))}
        </div>

        {/* Bottom URL */}
        <div
          style={{
            position: "absolute",
            bottom: 28,
            right: 50,
            fontSize: 19,
            color: "#a8a29e",
            display: "flex",
            fontWeight: 500,
          }}
        >
          giftsense.coffeet.fr
        </div>

        {/* Top-left subtle label */}
        <div
          style={{
            position: "absolute",
            top: 28,
            left: 50,
            fontSize: 17,
            color: "#C88B5C",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            display: "flex",
          }}
        >
          by Coffeet
        </div>
      </div>
    ),
    { ...size }
  );
}
