const f = document.getElementById("f"), msg = document.getElementById("msg"),
  go = document.getElementById("go"), url = document.getElementById("url");
f.addEventListener("submit", async (e) => {
  e.preventDefault();
  go.disabled = true; msg.textContent = "İndiriliyor, lütfen bekleyin…";
  try {
    const r = await fetch("/api/download", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({url: url.value}),
    });
    if (!r.ok) throw new Error((await r.json()).detail || "Hata");
    const name = (r.headers.get("content-disposition") || "").match(/filename="?([^";]+)/)?.[1] || "video.mp4";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
    URL.revokeObjectURL(a.href); msg.textContent = "Tamam ✓";
  } catch (err) { msg.textContent = err.message; }
  go.disabled = false;
});
