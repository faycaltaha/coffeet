"use client";

import { useState } from "react";

type Status = "idle" | "loading" | "ok" | "error";

export default function HomePage() {
  const [name, setName] = useState("Alex");
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<string>("");

  const test = async () => {
    setStatus("loading");
    setResult("");
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recipientName: name,
          occasion: "Anniversaire",
          budget: "€30–€75",
          relationship: "Ami(e)",
          interests: ["tech", "musique"],
          profiles: [],
        }),
      });
      const json = await res.json();
      if (json.success && json.data) {
        const ideas = json.data.giftIdeas?.slice(0, 3) ?? [];
        setResult(
          `✅ API OK — ${ideas.length} idées reçues :\n` +
            ideas.map((g: { title: string }) => `• ${g.title}`).join("\n")
        );
        setStatus("ok");
      } else {
        setResult(`❌ Erreur API : ${json.error}`);
        setStatus("error");
      }
    } catch (e) {
      setResult(`❌ Erreur réseau : ${e instanceof Error ? e.message : String(e)}`);
      setStatus("error");
    }
  };

  return (
    <main style={{ maxWidth: 480, margin: "80px auto", padding: "0 16px", fontFamily: "sans-serif" }}>
      <h1 style={{ fontSize: 24, marginBottom: 8 }}>🎁 GiftSense — Test API</h1>
      <p style={{ color: "#777", fontSize: 14, marginBottom: 24 }}>
        Teste si la clé OpenRouter fonctionne.
      </p>

      <label style={{ display: "block", marginBottom: 8, fontWeight: 600, fontSize: 14 }}>
        Prénom du destinataire
      </label>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Alex"
        style={{
          width: "100%",
          padding: "10px 14px",
          borderRadius: 10,
          border: "1px solid #ddd",
          fontSize: 15,
          marginBottom: 16,
          boxSizing: "border-box",
        }}
      />

      <button
        onClick={test}
        disabled={status === "loading" || !name.trim()}
        style={{
          width: "100%",
          padding: "12px",
          borderRadius: 10,
          border: "none",
          background: status === "loading" ? "#ccc" : "#c88b5c",
          color: "#fff",
          fontWeight: 700,
          fontSize: 15,
          cursor: status === "loading" ? "not-allowed" : "pointer",
        }}
      >
        {status === "loading" ? "Analyse en cours…" : "Tester l'API OpenRouter"}
      </button>

      {result && (
        <pre
          style={{
            marginTop: 24,
            padding: 16,
            borderRadius: 10,
            background: status === "ok" ? "#f0fdf4" : "#fff0f0",
            border: `1px solid ${status === "ok" ? "#86efac" : "#fca5a5"}`,
            fontSize: 13,
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
