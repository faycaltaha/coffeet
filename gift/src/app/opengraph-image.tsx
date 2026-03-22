import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "GiftSense – Idées cadeaux IA personnalisées";
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
          background: "linear-gradient(135deg, #fdf4ff 0%, #f5f3ff 40%, #fdf2f8 100%)",
          fontFamily: "system-ui, -apple-system, sans-serif",
          padding: "60px",
          position: "relative",
        }}
      >
        {/* Decorative blobs */}
        <div
          style={{
            position: "absolute",
            top: -80,
            left: -80,
            width: 400,
            height: 400,
            borderRadius: "50%",
            background: "rgba(217,70,239,0.18)",
            filter: "blur(80px)",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: -60,
            right: -60,
            width: 360,
            height: 360,
            borderRadius: "50%",
            background: "rgba(168,85,247,0.18)",
            filter: "blur(70px)",
          }}
        />

        {/* Gift emoji */}
        <div style={{ fontSize: 100, marginBottom: 20, display: "flex" }}>🎁</div>

        {/* Title */}
        <div
          style={{
            fontSize: 76,
            fontWeight: 900,
            color: "#c026d3",
            marginBottom: 20,
            letterSpacing: "-2px",
            display: "flex",
          }}
        >
          GiftSense
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: 30,
            color: "#6b7280",
            textAlign: "center",
            maxWidth: 760,
            lineHeight: 1.4,
            marginBottom: 40,
            display: "flex",
          }}
        >
          Idées cadeaux personnalisées grâce à l&apos;IA
        </div>

        {/* Feature chips */}
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center" }}>
          {["📸 Instagram", "🎵 TikTok", "📌 Pinterest", "✅ 100% Halal", "🔥 Tendances"].map((text) => (
            <div
              key={text}
              style={{
                background: "rgba(255,255,255,0.8)",
                border: "1.5px solid rgba(192,38,211,0.25)",
                borderRadius: 40,
                padding: "10px 22px",
                fontSize: 22,
                color: "#374151",
                fontWeight: 600,
                display: "flex",
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
            bottom: 30,
            right: 50,
            fontSize: 20,
            color: "#9ca3af",
            display: "flex",
          }}
        >
          giftsense.coffeet.fr
        </div>
      </div>
    ),
    { ...size }
  );
}
