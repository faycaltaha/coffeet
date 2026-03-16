# ☕ Coffeet

Monorepo for all Coffeet projects — specialty Ethiopian Arabica (Grade 3) operations in Île-de-France.

---

## 📁 Structure

```
coffeet/
├── projects/
│   ├── outreach-idf/        — B2B prospect emails & sales pipeline (Paris IDF)
│   └── social-gift-app/     — AI gift recommender web app (Next.js)
└── automations/             — n8n workflow exports
```

---

## 🗂 Projects

### [`projects/outreach-idf/`](./projects/outreach-idf/)
B2B outreach campaign targeting specialty cafés, premium restaurants, and luxury hotels in Île-de-France.
- **`pipeline-suivi.md`** — 3-phase sales pipeline tracker
- **`semaine1–3/`** — weekly prospect email drafts (specialty cafés → restaurants → palaces)

### [`projects/social-gift-app/`](./projects/social-gift-app/)
Web app that analyses public social media profiles (Instagram, TikTok, Pinterest) to generate personalised gift ideas using AI with built-in web search.
- **Stack:** Next.js 15 · TypeScript · Tailwind CSS · OpenRouter (perplexity/sonar-pro)
- **Run:** `cd projects/social-gift-app && cp .env.local.example .env.local && npm run dev`

---

## ⚙️ Automations

### [`automations/`](./automations/)
n8n workflow exports for automated prospecting and outreach.

| File | Description |
|------|-------------|
| `coffeet-prospection-idf.json` | Active prospecting pipeline (IDF) — scheduled scraping + Notion CRM sync |
| `coffeet-outreach-arabica.json` | Outreach sequence for Arabica Grade 3 |

To import: open n8n → **Workflows → Import from file**.
