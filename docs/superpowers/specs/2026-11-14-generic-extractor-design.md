# Genel çıkarıcı: site listesini kaldırma + çıkarılan adres denetimi (kısa tasarım)

Tarih: 2026-11-14. Boyut: küçük değişiklik. Seçilen yaklaşım: B.

## Amaç ve neden
Uygulama yalnızca 12 siteyi kabul ediyor (`app/security.py`, `DEFAULT_ALLOWED`). Kullanıcı yt-dlp'nin genel çıkarıcısından yararlanıp listede olmayan sitelerden de (sayfada açıkta duran `mp4`/`m3u8` videosu olanlar) indirebilmek istiyor. Genel çıkarıcı yt-dlp içinde hazır; engel yalnızca `validate_url` içindeki site kapısı. Kapı kalkınca genel çıkarıcı sayfa içi iframe ve bağlantıları izleyeceği için SSRF korumasının ikinci bir katmana ihtiyacı var.

## Hedefler
- Varsayılan olarak her genel (public) http/https adresi kabul edilir.
- `ALLOWED_DOMAINS` isteğe bağlı kalır: doluysa kısıtlar, boşsa/ayarsızsa kısıtlama yoktur.
- Çıkarıcının bulduğu gerçek medya adresi (seçilen formatın `url`'i, birleştirilecekse `requested_formats` içindekilerin hepsi) indirme başlamadan denetlenir: sunucu çözümlenir, özel/yerel adres varsa indirme reddedilir.

## Hedef dışı
- DRM'li içerik (Netflix vb.): çalışmaz, desteklenmez.
- Süzgeçli proxy ile yt-dlp'nin sayfa çözümleme sırasındaki ara isteklerini (yönlendirme, iframe) denetlemek.
- `m3u8`/DASH manifestlerinin içindeki segment adreslerini tek tek denetlemek.
- DNS rebinding'e karşı koruma (çözümleme ile indirme arasında adres değişebilir).
- İndirme arayüzü, çerez ve token davranışında değişiklik.

## Başarısızlık sayılacak durumlar
- Özel/yerel IP veya kimlik bilgili URL'nin kabul edilmesi.
- Çıkarılan format adresi özel/yerel bir sunucuya çıkıyorsa indirmenin başlaması.
- `ALLOWED_DOMAINS` doluyken kısıtın çalışmaması.

## Kısıtlar
- İlk adresin sunucusu çözümlenip public mi diye bakılmaya devam eder (`resolve=True`).
- Hız sınırı, `API_TOKEN` ve `127.0.0.1` varsayılanı değişmez.
- `/api/download` tek adımda `extract_info(url, download=True)` çağırıyor; çıkarma ile indirme arasına yt-dlp'nin `before_dl` PostProcessor aşamasıyla girilir (akışı iki adıma bölmek gerekmedi).

## Yaklaşımlar
- A (elendi): yalnızca listeyi kaldır. En küçük değişiklik, ama çıkarılan adresler hiç denetlenmez.
- **B (seçildi):** A + çıkarılan format adreslerini denetle. Artı: yerel ağa indirme isteği gitmez. Eksi: manifest içi segmentler ve çözümleme sırasındaki ara istekler yine denetlenmez.
- C (elendi): süzgeçli proxy. Bu özellik için fazla ağır.

## Tasarım
- `app/security.py`: `DEFAULT_ALLOWED` kaldırılır. `ALLOWED_DOMAINS` ayarsız/boşsa boş demet olur; `_domain_allowed` boş demet için `True`, doluysa mevcut eşleşme. Yeni `check_media_url(url)`: şema http/https, kimlik bilgisi yok, sunucu çözümlenir ve tüm adresler public olmalı; site listesi burada uygulanmaz (CDN'ler farklı alan adında olur). Başarısızlıkta `InvalidURL`.
- `app/main.py` `/api/download`: `MediaUrlGuard` (PostProcessor) `before_dl` aşamasında `requested_formats` (yoksa `url`) için `check_media_url` çağırır; reddedilirse `PostProcessingError` ile indirme başlamaz, günlük kaydı yazılır ve mevcut hata yolundan 422 döner. `/api/info` yalnızca meta veri çıkarır, medya indirmez; değişmez (küçük resim zaten `_is_public_ip` ile korunuyor).
- `.env.example`, `README.md`, `README.tr.md`: `ALLOWED_DOMAINS` açıklaması (satır 57) ve güvenlik notu (satır 165) güncellenir. Açık kalan kenarlar (manifest içi segmentler, çözümleme sırasındaki yönlendirmeler, DNS rebinding) ve DRM'li sitelerin çalışmadığı dürüstçe yazılır.
- Testler: ayarsız listeyle rastgele public alan adı kabul; özel IP ve kimlik bilgili URL red; liste doluyken listedeki kabul/dışındaki red; `check_media_url` için public/özel/çözülemeyen sunucu; indirme akışında özel adrese çıkan format reddi (yt-dlp sahte bilgiyle taklit edilir).

## Builder'a bırakılanlar
Test dosyalarının adları ve düzeni, README cümlelerinin tam metni, `requested_formats` boşken `url` seçimi, `ALLOWED_DOMAINS` boş dizge ile ayarsızı aynı saymak (önerilen: aynı).
