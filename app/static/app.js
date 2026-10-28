const $ = (id) => document.getElementById(id);
const f = $("f"), msg = $("msg"), go = $("go"), tok = $("token"), url = $("url"), paste = $("paste"),
  frame = $("frame"), img = $("p-img"), empty = $("p-empty"), cap = $("p-cap"), settings = $("settings");
const EMPTY = empty.textContent;
try { tok.value = localStorage.getItem("vd_token") || ""; } catch {}
settings.open = !tok.value;

const headers = () => ({"Content-Type": "application/json", ...(tok.value && {Authorization: "Bearer " + tok.value})});
const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const status = (text, kind = "") => { msg.textContent = text; msg.className = kind; };
const saveToken = () => { try { localStorage.setItem("vd_token", tok.value); } catch {} };
const errorText = async (r) => {
  if (r.status === 401) { settings.open = true; return "Erişim anahtarı eksik ya da yanlış. Ayarlar'dan gir."; }
  try { return (await r.json()).detail || "Hata"; } catch { return "Hata"; }
};

// Önizleme: aynı URL'yi tekrar sorgulama (rate limit önizlemeyi de sayar).
let lastQueried = "", timer, ctrl;
function schedulePreview() {
  clearTimeout(timer);
  const u = url.value.trim();
  if (!u || !url.checkValidity()) { resetFrame(); lastQueried = ""; return; }
  if (u === lastQueried) return;
  timer = setTimeout(() => loadPreview(u), 500);
}
function resetFrame(text = EMPTY) {
  frame.classList.remove("loading"); img.hidden = true; img.removeAttribute("src");
  cap.hidden = true; empty.hidden = false; empty.textContent = text;
}
async function loadPreview(u) {
  lastQueried = u;
  ctrl?.abort(); ctrl = new AbortController();
  resetFrame("Video bilgisi alınıyor…"); frame.classList.add("loading");
  try {
    const r = await fetch("/api/info", {method: "POST", headers: headers(), body: JSON.stringify({url: u}), signal: ctrl.signal});
    if (!r.ok) throw new Error(await errorText(r));
    const d = await r.json();
    if (msg.className === "err") status("");
    frame.classList.remove("loading");
    if (d.thumbnail) { img.src = d.thumbnail; img.hidden = false; empty.hidden = true; }
    else empty.textContent = "Küçük resim yok";
    $("p-title").textContent = d.title || "Başlıksız video";
    $("p-up").textContent = d.uploader || "";
    $("p-dur").textContent = d.duration ? fmt(d.duration) : "";
    $("p-src").textContent = d.extractor || "";
    cap.hidden = false;
  } catch (err) {
    if (err.name === "AbortError") return;
    resetFrame("Bu link için önizleme alınamadı. İndir'i yine de deneyebilirsin.");
    if (!go.disabled) status(err.message, "err");
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

f.addEventListener("submit", async (e) => {
  e.preventDefault();
  go.disabled = true; frame.classList.add("rolling");
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
    status(`İndirildi, ${fmt((Date.now() - start) / 1000)} sürdü.`, "ok");
  } catch (err) { status(err.message, "err"); }
  clearInterval(clock);
  go.disabled = false; frame.classList.remove("rolling");
});
