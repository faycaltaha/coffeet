"use client";

import { useState } from "react";

type Status = "idle" | "loading" | "ok" | "error";

const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";

export default function HomePage() {
  const [apiKey, setApiKey] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState("");

  const test = async () => {
    if (!apiKey.trim()) return;
    setStatus("loading");
    setResult("");

    try {
      const res = await fetch(OPENROUTER_URL, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey.trim()}`,
          "Content-Type": "application/json",
          "HTTP-Referer": "https://coffeet.fr",
        },
        body: JSON.stringify({
          model: "perplexity/sonar-pro",
          messages: [
            {
              role: "user",
              content:
                'Suggest 3 gift ideas for a friend who likes tech. Reply in JSON: {"gifts": [{"title":"...","price":"..."}]}',
            },
          ],
          max_tokens: 300,
        }),
      });

      const json = await res.json();

      if (!res.ok) {
        setResult(`❌ HTTP ${res.status}: ${json.error?.message ?? JSON.stringify(json)}`);
        setStatus("error");
        return;
      }

      const content = json.choices?.[0]?.message?.content ?? "";
      setResult(`✅ API OK !\n\nRéponse du modèle :\n${content}`);
      setStatus("ok");
    } catch (e) {
      setResult(`❌ Erreur réseau : ${e instanceof Error ? e.message : String(e)}`);
      setStatus("error");
    }
  };

  return (
    <main style={{ maxWidth: 480, margin: "60px auto", padding: "0 20px" }}>
      <h1 style={{ fontSize: 22, marginBottom: 6 }}>🎁 GiftSense — Test clé OpenRouter</h1>
      <p style={{ color: "#888", fontSize: 13, marginBottom: 24 }}>
        Appel direct au modèle depuis le navigateur (test uniquement).
      </p>

      <label style={{ display: "block", fontWeight: 600, fontSize: 13, marginBottom: 6 }}>
        Clé API OpenRouter
      </label>
      <input
        type="password"
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        placeholder="sk-or-..."
        style={{
          width: "100%",
          padding: "10px 14px",
          borderRadius: 8,
          border: "1px solid #ddd",
          fontSize: 14,
          marginBottom: 16,
          boxSizing: "border-box",
        }}
      />

      <button
        onClick={test}
        disabled={status === "loading" || !apiKey.trim()}
        style={{
          width: "100%",
          padding: "12px",
          borderRadius: 8,
          border: "none",
          background: status === "loading" || !apiKey.trim() ? "#ccc" : "#c88b5c",
          color: "#fff",
          fontWeight: 700,
          fontSize: 14,
          cursor: status === "loading" || !apiKey.trim() ? "not-allowed" : "pointer",
        }}
      >
        {status === "loading" ? "Appel en cours…" : "Tester la clé"}
      </button>

      {result && (
        <pre
          style={{
            marginTop: 20,
            padding: 16,
            borderRadius: 8,
            background: status === "ok" ? "#f0fdf4" : "#fff0f0",
            border: `1px solid ${status === "ok" ? "#86efac" : "#fca5a5"}`,
            fontSize: 12,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {result}
        </pre>
      )}
    </main>
  );
}
