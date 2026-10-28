# video-downloader

Reklamsız, takipsiz, kendi makinende çalışan sosyal medya video indirici (TikTok, Instagram, YouTube, X, ...). Motor: [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Fedora kurulumu

```bash
sudo dnf install -y python3 ffmpeg   # ffmpeg için RPM Fusion gerekebilir
git clone https://github.com/tamerardall/video-downloader && cd video-downloader
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Not: Komutlar proje klasöründen çalıştırılmalı. Düz `uvicorn` yazarsan ve venv aktif değilse sistemdeki `/usr/bin/uvicorn` çalışır ve `ModuleNotFoundError: No module named 'yt_dlp'` hatası verir; bu yüzden `.venv/bin/uvicorn` kullan (ya da önce `. .venv/bin/activate`).

Tarayıcıda http://127.0.0.1:8000 aç. Güncelleme: `pip install -U yt-dlp` (siteler sık değişir).

### Instagram (çerez gerekli)

Instagram giriş yapılmamış isteklere video vermiyor ("Instagram sent an empty media response"). Instagram'a giriş yapılmış bir tarayıcının çerezlerini yt-dlp'ye ver:

```bash
# Seçenek 1: çerezleri doğrudan tarayıcıdan oku (Instagram'a o tarayıcıda giriş yapmış ol)
COOKIES_FROM_BROWSER=firefox .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000

# Flatpak tarayıcılarda profil yolunu "tarayıcı:yol" biçiminde ver (ör. Flatpak Brave)
COOKIES_FROM_BROWSER="brave:$HOME/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/Default" .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000

# Seçenek 2: Netscape formatında cookies.txt dosyası (ör. "Get cookies.txt LOCALLY" eklentisiyle dışa aktar)
COOKIES_FILE=$HOME/.config/video-downloader/cookies.txt .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Çerezler hesabına erişim sağlar: dosyayı `chmod 600` yap, repoya ekleme, kimseyle paylaşma. Mümkünse ayrı/ikincil bir Instagram hesabı kullan (yoğun indirme hesabın kısıtlanmasına yol açabilir).

## Güvenlik

- Sadece http/https; kullanıcı bilgili, yerel/özel IP'li (SSRF) ve izin listesi dışı alan adları reddedilir (`ALLOWED_DOMAINS` env ile değiştirilebilir, virgülle ayrılmış).
- IP başına dakikada 10 istek, en çok 500 MB dosya, indirmeler geçici klasörde tutulup sonra silinir.
- Harici script/font/tracker yok; CSP ile sadece kendi kaynakları. Varsayılan olarak yalnızca 127.0.0.1'e bağlanır.
- `API_TOKEN` tanımlıysa tüm `/api/*` istekleri `Authorization: Bearer <anahtar>` ister (sabit zamanlı karşılaştırma). 127.0.0.1 dışına bağlanacaksan mutlaka ayarla.
- Portu internete açma; uzaktan erişim için Tailscale kullan.

## iPhone Kısayolu (Tailscale ile)

1. Fedora ve iPhone'a [Tailscale](https://tailscale.com/download) kur, aynı hesapla giriş yap. Fedora'nın Tailscale adresini al: `tailscale ip -4` (örn. `100.x.y.z`).
2. Fedora'da gizli anahtar üret ve uygulamayı Tailscale adresine bağlayarak başlat:
   ```bash
   cd video-downloader
   export API_TOKEN=$(openssl rand -hex 24); echo $API_TOKEN   # bir yere not al
   .venv/bin/uvicorn app.main:app --host $(tailscale ip -4) --port 8000
   ```
   `API_TOKEN` aynı terminalde export edilmeli; yeni terminal açarsan tekrar ayarla (yeni anahtar üretirsen Kısayol'daki anahtarı da güncelle).
   Not: `--host 0.0.0.0` kullanma, sadece Tailscale arayüzüne bağla. Firewalld varsa 8000'i yalnızca `tailscale0` bölgesinde aç.
3. iPhone'da Kısayolu kur (eylemler sırayla, her biri üstteki arama kutusuna adı yazılarak eklenir):
   1. **Kısayollar** → sağ üstte **+** → adı **Video İndir**.
   2. Alttaki **ⓘ** (Ayrıntılar) → **Paylaşım Sayfasında Göster** açık. Üstte beliren "… girdi alır" kutusunda yalnızca **URL'ler** ve **Metin** seçili kalsın.
   3. **URL'nin İçeriğini Al** eylemini ekle. Mavi **URL** alanına `http://100.x.y.z:8000/api/download` yaz. Eylemdeki **>** (Daha fazla göster) oku:
      - **Yöntem:** POST
      - **Başlıklar:** Başlık Ekle → anahtar `Authorization`, değer `Bearer <ANAHTAR>` (Bearer'dan sonra bir boşluk)
      - **İstek Gövdesi:** JSON → Yeni Alan Ekle → **Metin** → anahtar `url`, değer: değer kutusuna dokun → klavyenin üstündeki **Değişken Seç** → **Kısayol Girdisi**
   4. **Dosyaların Ayrıntılarını Al** eylemini ekle → mavi "Ayrıntı" yazısına dokun → **Dosya Uzantısı**. Girdisi otomatik **URL'nin İçeriği** olur.
   5. **Eğer** eylemini ekle → koşul: *Dosya Uzantısı* **şudur** `json`.
      - Eğer ile Değilse arasına: **Sözlük Değerini Al** → anahtar `detail`, sözlük **URL'nin İçeriği**; ardından **Uyarı Göster** → mesaj: **Sözlük Değeri**.
      - **Değilse** ile **Eğer Sonu** arasına: **Fotoğraf Albümüne Kaydet** → girdi: **URL'nin İçeriği** (Değişken Seç ile).

   Neden böyle: indirme başarılıysa sunucu `.mp4` gönderir, hata varsa `hata.json` gönderir. "URL'nin İçeriğini Al" hatada kendisi durmaz; uzantı kontrolü olmadan hata ya sessizce kaybolur ya da videodan sözlük okunmaya çalışılıp "sözlük değeri alınamıyor" hatası çıkar. Sunucu her hatayı terminale de `WARNING` satırı olarak yazar.
4. TikTok/Instagram/Safari'de **Paylaş → Video İndir**. Paylaşım sayfası bağlantıyı açıklama metniyle birlikte gönderse de sunucu metnin içindeki ilk bağlantıyı kullanır.

Uzun videolarda zaman aşımı olursa kısayol eylemi bekler, birkaç dakika sürebilir. Anahtarı kimseyle paylaşma; sızarsa `API_TOKEN`'ı değiştirip yeniden başlat.

## Test

```bash
pytest
```

Not: Özel hesap içerikleri (Instagram giriş gerektirenler) çalışmaz. Platform kullanım şartlarına ve telif haklarına uy; kişisel kullanım içindir.
