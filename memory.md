# Instagram indirme sorunu – yapılanlar (2026-10-28)

Belirti: Instagram videoları önce hiç inmiyordu, sonra iPhone Kısayolunda hata göstermeden yarıda kalıyordu. TikTok ve X sorunsuzdu. Sonuç: düzeltildi, iPhone'dan Instagram indirmesi çalışıyor.

## Sorunlar ve çözümler

| # | Sorun | Sebep | Çözüm | Commit |
|---|---|---|---|---|
| 1 | Instagram hiç inmiyordu | Instagram giriş yapılmamış isteklere medya vermiyor ("empty media response") | `COOKIES_FILE` / `COOKIES_FROM_BROWSER` ortam değişkenleriyle yt-dlp'ye çerez verilir | `85ba256` |
| 2 | Brave çerezleri bulunamıyordu | Brave Flatpak olarak kurulu; yt-dlp varsayılan yolda (`~/.config/BraveSoftware`) arıyor | `COOKIES_FROM_BROWSER` artık `tarayıcı:profil_yolu` biçimini kabul ediyor | `2067516` |
| 3 | Hata nedeni görünmüyordu | Uygulama yt-dlp hatasını yutup genel mesaj dönüyordu | yt-dlp mesajı yanıtta gösterilir ve terminale `WARNING` olarak yazılır | `3d2a504` |
| 4 | Kısayoldan gelen bağlantı reddedilebiliyordu, retler log'a düşmüyordu | Paylaş menüsü bağlantıyı açıklama metniyle gönderebiliyor | Metindeki ilk `http(s)://` bağlantısı alınır; 400/401/429 ve hatalı gövde terminale yazılır | `981392d` |
| 5 | Kısayolda "sözlük değeri alınamıyor" | Başarılı indirmede yanıt video; Kısayol videodan sözlük okumaya çalışıyordu | Hata yanıtları `hata.json` adıyla döner; Kısayol önce dosya uzantısına bakar (README'de Türkçe adım adım) | `6e2f9fc` |
| 6 | Kısayol hata vermeden yarıda kalıyordu (asıl sorun) | Instagram `mp4` uzantılı VP9 video sunabiliyor; eski format seçimi uzantıya baktığı için VP9 seçiyordu, iPhone Fotoğraflar VP9/AV1 kaydetmiyor | `format_sort=["vcodec:h264", "acodec:aac", "ext:mp4:m4a"]` ile H.264 + AAC tercih edilir; indirilen dosyanın kodlaması ve boyutu terminale yazılır | `e1228e9` |

Testlerde istek sınırlayıcı (dakikada 10 istek) testler arasında taştığı için `tests/conftest.py` her testten önce onu sıfırlıyor.

## Sunucuyu başlatma

Kod değişince sunucu yeniden başlatılmalı (`--reload` yok). `API_TOKEN` aynı terminalde export edilmiş olmalı.

```bash
cd ~/Projeler/video-downloader && COOKIES_FROM_BROWSER="brave:$HOME/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/Default" .venv/bin/uvicorn app.main:app --host $(tailscale ip -4) --port 8000
```

Çerezler Brave'deki Instagram oturumundan okunur (KWallet ile çözülür). Brave'de Instagram'dan çıkış yapılırsa indirme yeniden "giriş gerekiyor" hatası verir.

## Sorun giderme

- Terminalde `İndirildi: … (görüntü …, ses …)` satırı: sunucu dosyayı üretti. Görüntü `avc1` değilse iPhone kaydedemeyebilir.
- `WARNING` satırları: reddedilen URL, yanlış anahtar, yt-dlp hatası vb.
- `POST /api/download … 200 OK` görünüyor ama iPhone'da kayıt yoksa sorun iPhone tarafında (kodlama, Kısayol adımları).
- `tailscale status`: iPhone bağlantısı `direct` olmalı; `relay` ise büyük dosyalarda zaman aşımı olabilir.

## Açık konular

- YouTube çalışmıyor ("No video formats found"): yt-dlp YouTube için bir JavaScript çalışma ortamı (ör. deno) istiyor, sistemde yok.
- Eski `worktree-*` dalları GitHub'da duruyor (içerikleri `main`'de); silinebilir.
