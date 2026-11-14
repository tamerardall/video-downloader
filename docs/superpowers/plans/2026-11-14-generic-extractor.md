# Genel çıkarıcı Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Site listesini varsayılan olarak kaldırıp yt-dlp'nin genel çıkarıcısıyla her genel siteden indirmeyi mümkün kılmak; çıkarılan medya adreslerini indirme öncesi denetlemek.

**Architecture:** `ALLOWED_DOMAINS` boşsa kısıtsız olur. `/api/download` içinde yt-dlp'nin `before_dl` PostProcessor aşaması, format seçildikten sonra ve indirme başlamadan önce her medya adresinin sunucusunun public olduğunu doğrular.

**Tech Stack:** Python, FastAPI, yt-dlp 2026.10.26, pytest, uv.

**Spec:** `docs/superpowers/specs/2026-11-14-generic-extractor-design.md`

## Global Constraints

- Hız sınırı, `API_TOKEN`, `HOST=127.0.0.1` varsayılanı ve `/api/info` davranışı değişmez.
- İlk adres denetimi (`validate_url`, `resolve=True`) kalır: şema http/https, kimlik bilgisi yok, sunucu public.
- `check_media_url` site listesini uygulamaz.
- DRM'li içerik desteklenmez, README'de belirtilir.
- Açık kalan kenarlar README'de yazılır: manifest içi segmentler, çözümleme sırasındaki yönlendirmeler, DNS rebinding.
- Kod ve testler mevcut stile uyar (İngilizce kod/iletiler; README'ler hem `README.md` hem `README.tr.md`).

## Review Focus

- `ALLOWED_DOMAINS=` (boş dizge) ayarsızla aynı: kısıtsız. Test: Task 1.
- Format adresinin sunucusu özel IP'ye çözülüyor: indirme başlamadan reddedilir. Test: Task 2.
- Tek parça (birleştirilmeyen) format: `requested_formats` yok, `url` denetlenir. Test: Task 2.
- Formatta `url` yok (ör. yalnızca parçalar): çökmeden geçer. Test: Task 2.
- IPv6 loopback `http://[::1]/` medya adresi olarak reddedilir. Test: Task 1.
- `file://` veya `rtmp://` gibi http dışı medya adresi reddedilir. Test: Task 1.

---

### Task 1: İsteğe bağlı site listesi ve `check_media_url`

**Files:**
- Modify: `app/security.py:9-26,44-46`
- Test: `tests/test_security.py`

**Interfaces:**
- Produces: `check_media_url(url: str, resolve: bool = True) -> str` (aynı `InvalidURL`'i fırlatır, site listesini uygulamaz, geçerliyse `url`'i döndürür). `_domain_allowed(host)` ALLOWED_DOMAINS boşsa `True` döner.

- [ ] **Step 1: Mevcut `test_rejects`'i güncelle ve yeni testleri yaz.** `test_rejects` listesinden site-listesine bağlı olanları (`https://evil.com/`, `https://tiktok.com.evil.com/`) ayır: yeni `test_allowlist_rejects` bunları `monkeypatch.setattr(security, "ALLOWED_DOMAINS", ("tiktok.com",))` ile reddettiğini doğrular. `test_accepts` aynı monkeypatch ile `tiktok.com` kabulünü doğrular. Yeni testler:
  - `test_no_allowlist_accepts_any_public_host`: `ALLOWED_DOMAINS=()` iken `validate_url("https://example.org/v.mp4", resolve=False)` döner.
  - `test_empty_env_means_unrestricted`: `ALLOWED_DOMAINS=""` ortamıyla `security`'yi `importlib.reload` edip `security.ALLOWED_DOMAINS == ()`; test sonunda reload ile eski haline dön.
  - `test_still_rejects_private_and_credentials_without_allowlist`: boş listeyle `http://127.0.0.1/`, `https://user:pw@example.org/` hâlâ `InvalidURL`.
  - `test_check_media_url_rejects`: parametrize `["file:///etc/passwd", "rtmp://example.org/x", "http://[::1]/", "http://localhost/x.mp4", "https://u:p@example.org/x", ""]`, `resolve=False` ile `InvalidURL`.
  - `test_check_media_url_ignores_allowlist`: `ALLOWED_DOMAINS=("tiktok.com",)` iken `check_media_url("https://cdn.example.org/v.mp4", resolve=False)` döner.
  - `test_check_media_url_rejects_private_resolution`: `monkeypatch.setattr(security.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("10.0.0.5", 0))])` ile `check_media_url("https://cdn.example.org/v.mp4")` `InvalidURL` fırlatır; genel IP döndürünce geçer.
- [ ] **Step 2:** `uv run pytest tests/test_security.py -v` çalıştır. Beklenen: yeni testler FAIL (`check_media_url` yok, liste hâlâ zorunlu).
- [ ] **Step 3: Uygula.** `DEFAULT_ALLOWED` kaldır; `ALLOWED_DOMAINS` tanımı `os.environ.get("ALLOWED_DOMAINS", "")` kullanır (boş/ayarsız → `()`). `_domain_allowed` boş demet için `True`. Kimlik bilgisi/şema/IP kontrollerini `validate_url` ile paylaşan küçük bir iç yardımcıya çıkar, `check_media_url` onu kullanır (site listesi hariç).
- [ ] **Step 4:** `uv run pytest tests/test_security.py -v`. Beklenen: hepsi PASS.
- [ ] **Step 5: Commit**
```bash
git add app/security.py tests/test_security.py
git commit -m "Güvenlik: site listesi isteğe bağlı, check_media_url eklendi"
```

### Task 2: İndirme öncesi medya adresi denetimi

**Files:**
- Modify: `app/main.py:154-162` (ve `from .security import` satırı)
- Test: `tests/test_api.py` (mevcut `Fake` sınıfları `add_post_processor(self, pp, when=None)` metodu kazanır)

**Interfaces:**
- Consumes: `check_media_url(url, resolve=True)` ve `InvalidURL` (Task 1).
- Produces: `MediaUrlGuard(yt_dlp.postprocessor.common.PostProcessor)` in `app/main.py`; `run(self, info) -> tuple[list, dict]` her `info.get("requested_formats") or [info]` öğesinin `url`'ini (yoksa atlar) `check_media_url` ile denetler, `InvalidURL`'i `yt_dlp.utils.PostProcessingError`'a çevirir, aksi halde `([], info)` döndürür. `/api/download` içinde `ydl.add_post_processor(MediaUrlGuard(), when="before_dl")` çağrılır.

- [ ] **Step 1: Testleri yaz** (`tests/test_api.py`):
  - Mevcut `Fake` sınıflarına (satır ~47, ~68, ~96, ~129 ve `test_thumbnail.py` içindeki `FakeYDL`) `def add_post_processor(self, *a, **k): pass` ekle; böylece mevcut testler yeni akışla da geçer.
  - `test_guard_rejects_private_requested_format`: `MediaUrlGuard().run({"requested_formats": [{"url": "https://cdn.example.org/v"}, {"url": "http://10.0.0.5/a"}]})` `PostProcessingError` fırlatır (`check_media_url`'i monkeypatch ile `10.0.0.5`'te `InvalidURL` fırlatacak şekilde sahtele).
  - `test_guard_checks_url_when_not_merged`: `requested_formats` yokken `{"url": "http://10.0.0.5/a"}` reddedilir.
  - `test_guard_skips_format_without_url`: `{"requested_formats": [{"format_id": "x"}]}` hata vermez, `([], info)` döner.
  - `test_download_registers_guard`: sahte `YoutubeDL` `add_post_processor` çağrısını kaydeder; `/api/download` sonrası bir `MediaUrlGuard` örneğinin `when="before_dl"` ile eklendiği doğrulanır.
- [ ] **Step 2:** `uv run pytest tests/test_api.py -v`. Beklenen: yeni testler FAIL (`MediaUrlGuard` yok).
- [ ] **Step 3: Uygula** `MediaUrlGuard` ve kaydı. Reddedilen indirmenin mevcut `except Exception` yolundan 422 JSON ile (ayrıntılı iletiyle) döndüğünü doğrula; `log.warning` ile reddedilen host'u kaydet.
- [ ] **Step 4:** `uv run pytest -v`. Beklenen: tüm testler PASS.
- [ ] **Step 5: Commit**
```bash
git add app/main.py tests/test_api.py tests/test_thumbnail.py
git commit -m "İndirme: çıkarılan medya adreslerini indirme öncesi denetle"
```

### Task 3: Belgeler

**Files:**
- Modify: `.env.example` (ALLOWED_DOMAINS yorumu), `README.md:57,165`, `README.tr.md:57,165`, `docs/superpowers/specs/2026-11-14-generic-extractor-design.md` (Kısıtlar ve Tasarım: `before_dl` PostProcessor, 422)

- [ ] **Step 1:** `.env.example`: `# ALLOWED_DOMAINS=` yorumunu "boşsa her site, doluysa yalnızca listedekiler" olarak yaz. README tablosu (satır 57) ve güvenlik notu (satır 165) iki dilde güncellenir: varsayılan kısıtsız; çıkarılan medya adresleri denetlenir; açık kalan kenarlar (manifest içi segmentler, çözümleme sırasındaki yönlendirmeler, DNS rebinding) ve DRM'li sitelerin çalışmadığı yazılır.
- [ ] **Step 2:** Tasarım belgesinde "tek adımda extract_info" kısıtını ve iki adım ifadesini, `before_dl` PostProcessor ve 422 yanıtıyla uyumlu hale getir.
- [ ] **Step 3:** `uv run pytest -v` hâlâ PASS; `grep -rn "ALLOWED_DOMAINS" README.md README.tr.md .env.example` yeni ifadeyi gösterir.
- [ ] **Step 4: Commit**
```bash
git add .env.example README.md README.tr.md docs
git commit -m "Docs: genel çıkarıcı ve site listesinin isteğe bağlı olması"
```
