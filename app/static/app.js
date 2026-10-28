const f = document.getElementById("f"), msg = document.getElementById("msg"),
  go = document.getElementById("go"), tok = document.getElementById("token"), url = document.getElementById("url");
try { tok.value = localStorage.getItem("vd_token") || ""; } catch {}
f.addEventListener("submit", async (e) => {
  e.preventDefault();
  go.disabled = true; msg.textContent = "İndiriliyor, lütfen bekleyin…";
  try {
    const r = await fetch("/api/download", {
      method: "POST", headers: {"Content-Type": "application/json", ...(tok.value && {Authorization: "Bearer " + tok.value})},
      body: JSON.stringify({url: url.value}),
    });
    try { localStorage.setItem("vd_token", tok.value); } catch {}
    if (!r.ok) throw new Error((await r.json()).detail || "Hata");
    const name = (r.headers.get("content-disposition") || "").match(/filename="?([^";]+)/)?.[1] || "video.mp4";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
    URL.revokeObjectURL(a.href); msg.textContent = "Tamam ✓";
  } catch (err) { msg.textContent = err.message; }
  go.disabled = false;
});
