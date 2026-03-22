"use client";
import { useState } from "react";

export default function TestPage() {
  const [message, setMessage] = useState("Donne-moi une idée de cadeau pour une femme de 30 ans");
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);

  async function test() {
    setLoading(true);
    setResult("");
    try {
      const res = await fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (e: any) {
      setResult("Erreur: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 40, fontFamily: "sans-serif", maxWidth: 700 }}>
      <h1>Test API /recommend</h1>
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        rows={4}
        style={{ width: "100%", fontSize: 16, padding: 8 }}
      />
      <br />
      <button
        onClick={test}
        disabled={loading}
        style={{ marginTop: 12, padding: "10px 24px", fontSize: 16, cursor: "pointer" }}
      >
        {loading ? "Chargement..." : "Tester"}
      </button>
      <pre
        style={{
          marginTop: 24,
          background: "#f4f4f4",
          padding: 16,
          borderRadius: 8,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {result || "Le résultat apparaîtra ici"}
      </pre>
    </div>
  );
}
