export function trackClick(title: string, merchant: string) {
  try {
    const raw = localStorage.getItem("gift_clicks") || "[]";
    const clicks: { title: string; merchant: string; ts: number }[] = JSON.parse(raw);
    clicks.push({ title, merchant, ts: Date.now() });
    localStorage.setItem("gift_clicks", JSON.stringify(clicks.slice(-200)));
  } catch {}
}
