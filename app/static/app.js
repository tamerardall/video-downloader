// UI strings. The language follows the browser (Turkish if it starts with "tr", else English).
// index.html carries the English text so the page still reads fine without JS.
const T = {
  en: {
    title: "Video Downloader", key: "Key", keyLabel: "Access key", keyPh: "API_TOKEN, if required",
    keyHelp: "Needed if the server was started with <code>API_TOKEN</code>. Stored in this browser.",
    h1: "Paste a link,<br>get the video.", sub: "No ads, no tracking. Runs on your own machine.",
    urlLabel: "Video link", paste: "Paste", download: "Download", sites: "Supported sites", more: "and more",
    preview: "Preview", steps: "Steps", step1: "Link", step3: "Download", empty: "The preview will appear here.",
    again: "Another video", foot: "For personal use. Respect each platform's terms and copyright.",
    badKey: "Access key missing or wrong. Enter it under Key at the top right.", error: "Error",
    loadingInfo: "Getting video info…", noThumb: "No thumbnail", untitled: "Untitled video",
    noPreview: "Couldn't load a preview for this link. You can still try Download.",
    noClipboard: "Couldn't read the clipboard. Paste the link into the field manually.",
    downloading: "Downloading…", done: (name, time) => `Downloaded: ${name} (took ${time})`,
  },
  tr: {
    title: "Video İndirici", key: "Anahtar", keyLabel: "Erişim anahtarı", keyPh: "Gerekiyorsa API_TOKEN",
    keyHelp: "Sunucu <code>API_TOKEN</code> ile başlatıldıysa gerekir. Bu tarayıcıda saklanır.",
    h1: "Linki yapıştır,<br>videoyu al.", sub: "Reklam yok, takip yok. Kendi makinende çalışır.",
    urlLabel: "Video linki", paste: "Yapıştır", download: "İndir", sites: "Desteklenen siteler", more: "ve daha fazlası",
    preview: "Önizleme", steps: "Adımlar", step1: "Link", step3: "İndirme", empty: "Önizleme burada görünecek.",
    again: "Başka bir video", foot: "Kişisel kullanım içindir. Platform kurallarına ve telif haklarına uy.",
    badKey: "Erişim anahtarı eksik ya da yanlış. Sağ üstteki Anahtar'dan gir.", error: "Hata",
    loadingInfo: "Video bilgisi alınıyor…", noThumb: "Küçük resim yok", untitled: "Başlıksız video",
    noPreview: "Bu link için önizleme alınamadı. İndir'i yine de deneyebilirsin.",
    noClipboard: "Pano okunamadı. Linki alana elle yapıştır.",
    downloading: "İndiriliyor…", done: (name, time) => `İndirildi: ${name} (${time} sürdü)`,
  },
};
const lang = (navigator.language || "en").toLowerCase().startsWith("tr") ? "tr" : "en";
const t = (k) => T[lang][k];
document.documentElement.lang = lang;
// Translations are static strings from this file, so innerHTML is safe for the two keys that need markup.
document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
document.querySelectorAll("[data-i18n-html]").forEach((el) => { el.innerHTML = t(el.dataset.i18nHtml); });
document.querySelectorAll("[data-i18n-ph]").forEach((el) => { el.placeholder = t(el.dataset.i18nPh); });
document.querySelectorAll("[data-i18n-aria]").forEach((el) => { el.setAttribute("aria-label", t(el.dataset.i18nAria)); });

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
  if (r.status === 401) { settings.open = true; tok.focus(); return t("badKey"); }
  try { return (await r.json()).detail || t("error"); } catch { return t("error"); }
};

// Steps: 1 Link, 2 Preview, 3 Download. Each is "", "active" or "done".
function steps(a = "", b = "", c = "") {
  [a, b, c].forEach((state, i) => {
    const li = $("s" + (i + 1));
    li.className = state;
    if (state === "active") li.setAttribute("aria-current", "step"); else li.removeAttribute("aria-current");
  });
}

// Recognise the site in the link and highlight its chip.
const SITES = {tiktok: /(^|\.)tiktok\.com$/, instagram: /(^|\.)instagram\.com$/, youtube: /(^|\.)(youtube\.com|youtu\.be)$/, x: /(^|\.)(x\.com|twitter\.com)$/};
function markSite(u) {
  let host = "";
  try { host = new URL(u).hostname; } catch {}
  document.querySelectorAll(".sites [data-site]").forEach((li) => li.classList.toggle("on", !!host && SITES[li.dataset.site].test(host)));
}

// Preview: don't query the same URL twice (the rate limit counts previews too).
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
  resetFrame(t("loadingInfo")); frame.classList.add("loading"); steps("done", "active");
  try {
    const r = await fetch("/api/info", {method: "POST", headers: headers(), body: JSON.stringify({url: u}), signal: ctrl.signal});
    if (!r.ok) throw new Error(await errorText(r));
    const d = await r.json();
    if (msg.className === "err") status("");
    frame.classList.remove("loading");
    if (d.thumbnail) {
      img.src = d.thumbnail; img.hidden = false; empty.hidden = true;
      gate.style.setProperty("--thumb", `url("${d.thumbnail}")`); gate.classList.add("has");
    } else emptyText.textContent = t("noThumb");
    $("p-title").textContent = d.title || t("untitled");
    $("p-up").textContent = d.uploader || "";
    $("p-dur").textContent = d.duration ? fmt(d.duration) : "";
    $("p-src").textContent = d.extractor || "";
    cap.hidden = false;
    if (!go.disabled) steps("done", "done");
  } catch (err) {
    if (err.name === "AbortError") return;
    resetFrame(t("noPreview"));
    if (!go.disabled) { status(err.message, "err"); steps("done"); }
  }
}
url.addEventListener("input", schedulePreview);
tok.addEventListener("change", () => { saveToken(); lastQueried = ""; schedulePreview(); });

if (navigator.clipboard?.readText) {
  paste.hidden = false;
  paste.addEventListener("click", async () => {
    try { url.value = (await navigator.clipboard.readText()).trim(); schedulePreview(); url.focus(); }
    catch { status(t("noClipboard"), "err"); }
  });
}

again.addEventListener("click", () => {
  url.value = ""; status(""); schedulePreview(); url.focus();
});

f.addEventListener("submit", async (e) => {
  e.preventDefault();
  go.disabled = true; goLabel.textContent = t("downloading"); bar.hidden = false; again.hidden = true;
  const s2 = $("s2").className === "done" ? "done" : "";
  steps("done", s2, "active");
  const start = Date.now(), tick = () => status(`${t("downloading")} ${fmt((Date.now() - start) / 1000)}`, "loading");
  tick(); const clock = setInterval(tick, 1000);
  try {
    const r = await fetch("/api/download", {method: "POST", headers: headers(), body: JSON.stringify({url: url.value.trim()})});
    saveToken();
    if (!r.ok) throw new Error(await errorText(r));
    const name = (r.headers.get("content-disposition") || "").match(/filename="?([^";]+)/)?.[1] || "video.mp4";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
    URL.revokeObjectURL(a.href);
    status(T[lang].done(name, fmt((Date.now() - start) / 1000)), "ok");
    steps("done", s2, "done"); again.hidden = false;
  } catch (err) { status(err.message, "err"); steps("done", s2); }
  clearInterval(clock);
  go.disabled = false; goLabel.textContent = t("download"); bar.hidden = true;
});
