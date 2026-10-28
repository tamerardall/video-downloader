const $ = (id) => document.getElementById(id);
const f = $("f"), msg = $("msg"), go = $("go"), goLabel = $("go-label"), tok = $("token"), url = $("url"), paste = $("paste"),
  frame = $("frame"), gate = $("gate"), img = $("p-img"), empty = $("p-empty"), emptyText = $("p-empty-text"), cap = $("p-cap"),
  bar = $("bar"), again = $("again"), settings = $("settings");
const EMPTY = emptyText.textContent;
try { tok.value = localStorage.getItem("vd_token") || ""; } catch {}

const headers = () => ({"Content-Type": "application/json", ...(tok.value && {Authorization: "Bearer " + tok.value})});
const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const status = (text, kind = "") => { msg.textContent = text; msg.className = kind; };
const saveToken = () => { try { localStorage.setItem("vd_token", tok.value); } catch {} };
const errorText = async (r) => {
  if (r.status === 401) { settings.open = true; tok.focus(); return "Erişim anahtarı eksik ya da yanlış. Sağ üstteki Anahtar'dan gir."; }
  try { return (await r.json()).detail || "Hata"; } catch { return "Hata"; }
};

// Adımlar: 1 Link, 2 Önizleme, 3 İndirme. Her biri "", "active" ya da "done".
function steps(a = "", b = "", c = "") {
  [a, b, c].forEach((state, i) => {
    const li = $("s" + (i + 1));
    li.className = state;
    if (state === "active") li.setAttribute("aria-current", "step"); else li.removeAttribute("aria-current");
  });
}

// Linkteki siteyi tanıyıp çipini işaretle.
const SITES = {tiktok: /(^|\.)tiktok\.com$/, instagram: /(^|\.)instagram\.com$/, youtube: /(^|\.)(youtube\.com|youtu\.be)$/, x: /(^|\.)(x\.com|twitter\.com)$/};
function markSite(u) {
  let host = "";
  try { host = new URL(u).hostname; } catch {}
  document.querySelectorAll(".sites [data-site]").forEach((li) => li.classList.toggle("on", !!host && SITES[li.dataset.site].test(host)));
}

// Önizleme: aynı URL'yi tekrar sorgulama (rate limit önizlemeyi de sayar).
let lastQueried = "", timer, ctrl;
function schedulePreview() {
  clearTimeout(timer);
  const u = url.value.trim();
  markSite(u);
  again.hidden = true;
  if (!u || !url.checkValidity()) { resetFrame(); lastQueried = ""; steps(u ? "active" : ""); return; }
  if (u === lastQueried) return;
  steps("done");
  timer = setTimeout(() => loadPreview(u), 500);
}
function resetFrame(text = EMPTY) {
  frame.classList.remove("loading"); img.hidden = true; img.removeAttribute("src");
  gate.classList.remove("has"); gate.style.removeProperty("--thumb");
  cap.hidden = true; empty.hidden = false; emptyText.textContent = text;
}
async function loadPreview(u) {
  lastQueried = u;
  ctrl?.abort(); ctrl = new AbortController();
  resetFrame("Video bilgisi alınıyor…"); frame.classList.add("loading"); steps("done", "active");
  try {
    const r = await fetch("/api/info", {method: "POST", headers: headers(), body: JSON.stringify({url: u}), signal: ctrl.signal});
    if (!r.ok) throw new Error(await errorText(r));
    const d = await r.json();
    if (msg.className === "err") status("");
    frame.classList.remove("loading");
    if (d.thumbnail) {
      img.src = d.thumbnail; img.hidden = false; empty.hidden = true;
      gate.style.setProperty("--thumb", `url("${d.thumbnail}")`); gate.classList.add("has");
    } else emptyText.textContent = "Küçük resim yok";
    $("p-title").textContent = d.title || "Başlıksız video";
    $("p-up").textContent = d.uploader || "";
    $("p-dur").textContent = d.duration ? fmt(d.duration) : "";
    $("p-src").textContent = d.extractor || "";
    cap.hidden = false;
    if (!go.disabled) steps("done", "done");
  } catch (err) {
    if (err.name === "AbortError") return;
    resetFrame("Bu link için önizleme alınamadı. İndir'i yine de deneyebilirsin.");
    if (!go.disabled) { status(err.message, "err"); steps("done"); }
  }
}
url.addEventListener("input", schedulePreview);
tok.addEventListener("change", () => { saveToken(); lastQueried = ""; schedulePreview(); });

if (navigator.clipboard?.readText) {
  paste.hidden = false;
  paste.addEventListener("click", async () => {
    try { url.value = (await navigator.clipboard.readText()).trim(); schedulePreview(); url.focus(); }
    catch { status("Pano okunamadı. Linki alana elle yapıştır.", "err"); }
  });
}

again.addEventListener("click", () => {
  url.value = ""; status(""); schedulePreview(); url.focus();
});

f.addEventListener("submit", async (e) => {
  e.preventDefault();
  go.disabled = true; goLabel.textContent = "İndiriliyor…"; bar.hidden = false; again.hidden = true;
  const s2 = $("s2").className === "done" ? "done" : "";
  steps("done", s2, "active");
  const start = Date.now(), tick = () => status(`İndiriliyor… ${fmt((Date.now() - start) / 1000)}`, "loading");
  tick(); const clock = setInterval(tick, 1000);
  try {
    const r = await fetch("/api/download", {method: "POST", headers: headers(), body: JSON.stringify({url: url.value.trim()})});
    saveToken();
    if (!r.ok) throw new Error(await errorText(r));
    const name = (r.headers.get("content-disposition") || "").match(/filename="?([^";]+)/)?.[1] || "video.mp4";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
    URL.revokeObjectURL(a.href);
    status(`İndirildi: ${name} (${fmt((Date.now() - start) / 1000)} sürdü)`, "ok");
    steps("done", s2, "done"); again.hidden = false;
  } catch (err) { status(err.message, "err"); steps("done", s2); }
  clearInterval(clock);
  go.disabled = false; goLabel.textContent = "İndir"; bar.hidden = true;
});
