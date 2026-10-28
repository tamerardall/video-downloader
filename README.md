# video-downloader

Reklamsız, takipsiz, kendi makinende çalışan sosyal medya video indirici (TikTok, Instagram, YouTube, X, ...). Motor: [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Fedora kurulumu

```bash
sudo dnf install -y python3 ffmpeg   # ffmpeg için RPM Fusion gerekebilir
git clone https://github.com/tamerardall/video-downloader && cd video-downloader
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Tarayıcıda http://127.0.0.1:8000 aç. Güncelleme: `pip install -U yt-dlp` (siteler sık değişir).

## Güvenlik

- Sadece http/https; kullanıcı bilgili, yerel/özel IP'li (SSRF) ve izin listesi dışı alan adları reddedilir (`ALLOWED_DOMAINS` env ile değiştirilebilir, virgülle ayrılmış).
- IP başına dakikada 10 istek, en çok 500 MB dosya, indirmeler geçici klasörde tutulup sonra silinir.
- Harici script/font/tracker yok; CSP ile sadece kendi kaynakları. Varsayılan olarak yalnızca 127.0.0.1'e bağlanır.
- İnternete açma; açacaksan arkasına kimlik doğrulama koy.

## Test

```bash
pytest
```

Not: Özel hesap içerikleri (Instagram giriş gerektirenler) çalışmaz. Platform kullanım şartlarına ve telif haklarına uy; kişisel kullanım içindir.
