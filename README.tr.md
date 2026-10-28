# video-downloader

[English](README.md) | **Türkçe**

Kendi bilgisayarında çalışan, reklamsız ve takipsiz sosyal medya video indirici (TikTok, Instagram, YouTube, X, Facebook, Reddit, Vimeo, Pinterest, Twitch). İngilizce ve Türkçe küçük bir web arayüzü var; iPhone'da paylaş menüsünden bir Kısayol ile de çalışır. Motor: [yt-dlp](https://github.com/yt-dlp/yt-dlp).

- Linki tarayıcıya yapıştır ya da iPhone'da TikTok/Instagram/YouTube uygulamasından videoyu paylaş.
- iPhone Fotoğraflar'a doğrudan kaydedilebilsin diye H.264 + AAC seçer.
- İsteğe bağlı erişim anahtarı, SSRF koruması ve istek sınırı; hiçbir veri üçüncü taraflara gitmez.

## Gereksinimler

- Python 3.10 veya üstü
- [ffmpeg](https://ffmpeg.org/) (görüntü ve sesi birleştirir)

YouTube'un istediği JavaScript çalışma ortamı ([Deno](https://deno.com/)) `requirements.txt` ile sanal ortamın içine kurulur; ayrıca kurmana gerek yok.

## Kurulum

### Linux

```bash
# Fedora (ffmpeg RPM Fusion'dan gelir)
sudo dnf install -y python3 ffmpeg
# Debian / Ubuntu
sudo apt install -y python3 python3-venv ffmpeg

git clone https://github.com/tamerardall/video-downloader
cd video-downloader
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m app
```

### macOS

Yoksa önce [Homebrew](https://brew.sh/) kur.

```bash
brew install python ffmpeg
git clone https://github.com/tamerardall/video-downloader
cd video-downloader
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m app
```

### Windows (PowerShell)

```powershell
winget install Python.Python.3.12 Gyan.FFmpeg Git.Git
# python, ffmpeg ve git PATH'e girsin diye PowerShell'i kapatıp yeniden aç
git clone https://github.com/tamerardall/video-downloader
cd video-downloader
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\python -m app
```

Tarayıcıda http://127.0.0.1:8000 adresini aç.

Uygulamayı her zaman yukarıdaki gibi `.venv` içindeki Python ile başlat. Sistemdeki `uvicorn` ya da `python` kurulu paketleri görmez ve `ModuleNotFoundError: No module named 'yt_dlp'` hatası verir.

**Güncelleme:** Siteler sık değiştiği için yt-dlp'yi düzenli güncelle: `.venv/bin/pip install -U -r requirements.txt` (Windows: `.venv\Scripts\pip install -U -r requirements.txt`), sonra uygulamayı yeniden başlat.

## Ayarlar

Tüm ayarlar proje klasöründeki `.env` dosyasında (`.env.example`'dan kopyalanır). Herhangi bir metin düzenleyiciyle düzenle (Windows: `notepad .env`) ve değişiklikten sonra uygulamayı yeniden başlat.

| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `HOST` | `127.0.0.1` | Dinlenecek adres. Telefondan erişim için Tailscale IP'n (aşağıya bak). Asla `0.0.0.0` değil. |
| `PORT` | `8000` | Dinlenecek port. |
| `API_TOKEN` | boş | Tanımlıysa her `/api/*` isteği `Authorization: Bearer <anahtar>` ister. `HOST` `127.0.0.1` değilse **zorunlu**. |
| `COOKIES_FROM_BROWSER` | boş | Giriş çerezlerini tarayıcıdan oku: `firefox`, `chrome`, `brave`, `edge`, `safari`, ... ya da `tarayıcı:/profil/yolu`. |
| `COOKIES_FILE` | boş | Netscape formatında `cookies.txt` dosyasının yolu. |
| `ALLOWED_DOMAINS` | yaygın siteler | İzin verilen siteler, virgülle ayrılmış. |

`API_TOKEN` üretmek için:

```bash
python3 -c "import secrets; print(secrets.token_hex(24))"   # Windows: py -c "..."
```

## Instagram ve giriş isteyen diğer siteler

Instagram giriş yapılmamış isteklere video vermiyor (yt-dlp *"Instagram sent an empty media response"* der; uygulama da çerez tanımlamanı söyler). Uygulamanın çalıştığı bilgisayardaki bir tarayıcıda Instagram'a giriş yap, sonra `.env`'de **bunlardan birini** ayarla:

```ini
# Çerezleri doğrudan tarayıcıdan oku (en sorunsuzu Firefox)
COOKIES_FROM_BROWSER=firefox

# Flatpak olarak kurulu tarayıcı ya da varsayılan olmayan profil: "tarayıcı:/profil/yolu"
COOKIES_FROM_BROWSER=brave:/home/ben/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/Default

# Ya da "Get cookies.txt LOCALLY" gibi bir eklentiyle dışa aktarılmış cookies.txt
COOKIES_FILE=/home/ben/.config/video-downloader/cookies.txt
```

Platform notları:

- **Windows:** Chrome ve Edge'in yeni sürümleri çerezleri yt-dlp'nin çoğu zaman okuyamadığı biçimde şifreliyor. Firefox kullan ya da `cookies.txt` dışa aktar.
- **macOS:** Safari çerezlerini okumak için terminaline *Tam Disk Erişimi* vermen gerekir (Sistem Ayarları → Gizlilik ve Güvenlik). Chrome tabanlı tarayıcılar ilk seferde Anahtar Zinciri parolanı ister.
- **Linux:** Chrome tabanlı tarayıcılar anahtarı GNOME Anahtarlığı'nda ya da KWallet'ta tutar; masaüstü oturumunun açık olması gerekir.

Çerezler hesabına erişim sağlar: `cookies.txt` dosyasını kimseyle paylaşma, depoya ekleme (`.gitignore` `cookies*.txt`'yi zaten dışarıda bırakıyor). İkincil bir hesap kullanmayı düşün; yoğun indirme hesabın kısıtlanmasına yol açabilir. Tarayıcıda oturumu kapatırsan indirmeler yine giriş hatası vermeye başlar.

## Telefondan kullanım (Tailscale)

[Tailscale](https://tailscale.com/download) bilgisayarını ve telefonunu, internete port açmadan özel bir ağa bağlar.

1. Tailscale'i bilgisayara ve telefona kur, ikisinde de aynı hesapla giriş yap.
2. Bilgisayarın Tailscale adresini bul: `tailscale ip -4` (ör. `100.x.y.z`). Windows/macOS'ta Tailscale menüsünde de görünür.
3. `.env`'de `HOST=100.x.y.z` ve bir `API_TOKEN` ayarla (bkz. *Ayarlar*), uygulamayı yeniden başlat.
4. Sorulursa güvenlik duvarından izin ver:
   - **Linux (firewalld):** portu yalnızca Tailscale arayüzünde aç, ör. `sudo firewall-cmd --zone=trusted --add-interface=tailscale0`.
   - **Windows:** Windows Defender Güvenlik Duvarı Python için sorduğunda *Özel ağlar*'a izin ver.
   - **macOS:** uygulama güvenlik duvarı açıksa Python'a gelen bağlantılara izin ver.
5. Telefonun tarayıcısından dene: `http://100.x.y.z:8000` (anahtarı **Anahtar** kısmına gir).

`0.0.0.0`'a bağlama ve modemde port yönlendirme yapma.

## iPhone Kısayolu

Kısayol paylaşılan linki sunucuya gönderir ve dönen videoyu Fotoğraflar'a kaydeder ya da sunucunun hata mesajını gösterir.

Her eylemi, Kısayollar düzenleyicisinin altındaki arama kutusuna adını yazarak ekle:

1. **Kısayollar** uygulaması → **+** → adı **Video İndir**.
2. **ⓘ** (Ayrıntılar) → **Paylaşım Sayfasında Göster**'i aç. Üstteki "… girdi alır" kutusunda yalnızca **URL'ler** ve **Metin** seçili kalsın.
3. **URL'nin İçeriğini Al** ekle. URL'ye `http://100.x.y.z:8000/api/download` yaz, sonra **>** okuna dokun:
   - **Yöntem:** POST
   - **Başlıklar:** Başlık Ekle → anahtar `Authorization`, değer `Bearer <API_TOKEN'ın>` (Bearer'dan sonra bir boşluk var)
   - **İstek Gövdesi:** JSON → Yeni Alan Ekle → **Metin** → anahtar `url`, değer: alana dokun → **Değişken Seç** → **Kısayol Girdisi**
4. **Dosyaların Ayrıntılarını Al** ekle → mavi "Ayrıntı" yazısına dokun → **Dosya Uzantısı**. Girdisi kendiliğinden **URL'nin İçeriği** olur.
5. **Eğer** ekle → koşul: *Dosya Uzantısı* **şudur** `json`.
   - **Eğer** ile **Değilse** arasına: **Sözlük Değerini Al** → anahtar `detail`, sözlük **URL'nin İçeriği**; ardından **Uyarı Göster** → mesaj **Sözlük Değeri**.
   - **Değilse** ile **Eğer Sonu** arasına: **Fotoğraf Albümüne Kaydet** → girdi **URL'nin İçeriği**.

Bitmiş Kısayol:

```
URL'nin İçeriğini Al  (POST, Authorization başlığı, url = Kısayol Girdisi)
Dosyaların Ayrıntılarını Al  (Dosya Uzantısı)
Eğer  Dosya Uzantısı şudur json
    Sözlük Değerini Al  (detail, URL'nin İçeriği)
    Uyarı Göster  (Sözlük Değeri)
Değilse
    Fotoğraf Albümüne Kaydet  (URL'nin İçeriği)
Eğer Sonu
```

TikTok/Instagram/YouTube/Safari'den kullan: **Paylaş → Video İndir**. Paylaş menüsü linki açıklama metniyle birlikte gönderirse sunucu içindeki ilk linki kullanır.

Uzantı kontrolü neden var: Başarılı olunca sunucu `.mp4`, hata olunca `error.json` döndürür. *URL'nin İçeriğini Al* HTTP hatalarında durmaz; kontrol olmazsa hata ya sessizce kaybolur ya da *Sözlük Değerini Al* videodan sözlük okumaya çalışıp hata verir. Uzun videolar birkaç dakika sürebilir; Kısayol bekler.

## Sorun giderme

Uygulamanın çalıştığı terminal her isteği yazar:

| Log satırı | Anlamı |
|---|---|
| `Downloaded: abc.mp4 (4.2 MB, video avc1..., audio mp4a...)` | Sunucu dosyayı üretti. Görüntü `avc1` (H.264) değilse iPhone kaydetmeyebilir. |
| `WARNING ... This site requires login` | `COOKIES_FROM_BROWSER` ya da `COOKIES_FILE` ayarla (yukarıya bak). |
| `WARNING Invalid or missing API token` | Kısayoldaki/web arayüzündeki anahtar `API_TOKEN` ile aynı değil. |
| `WARNING URL rejected` | Desteklenmeyen site, özel adres ya da link değil. |
| `WARNING Rate limit exceeded` | Bir IP'den dakikada 10'dan fazla istek. |
| `WARNING Invalid request body` | Kısayolun istek gövdesi `url` alanı olan bir JSON değil. |

- **`POST /api/download ... 200 OK` var ama Fotoğraflar'da video yok:** sorun telefonda; Kısayol adımlarını kontrol et. iPhone Fotoğraflar VP9/AV1 videoları kaydedemez; uygulama bunu önlemek için H.264 tercih eder.
- **YouTube: "No video formats found":** Deno çalışma ortamı eksik. `pip install -r requirements.txt` ile yeniden kur ve uygulamayı `.venv` içindeki Python ile başlattığından emin ol.
- **Telefona aktarım yavaş ya da yarıda kalıyor:** `tailscale status` çalıştır; telefon `direct` görünmeli. `relay` bağlantılar çok daha yavaştır.

## Güvenlik

- Yalnızca izin verilen sitelere giden http/https linkleri kabul edilir; kullanıcı bilgisi içeren linkler ve yerel/özel IP'ler (SSRF) reddedilir. Site listesini `ALLOWED_DOMAINS` ile değiştirebilirsin.
- IP başına dakikada 10 istek, dosya başına en çok 500 MB. İndirmeler geçici bir klasörde tutulur ve gönderildikten sonra silinir.
- Web arayüzü harici script, font ya da takipçi yüklemez (sıkı CSP). Küçük resimleri sunucu alır; tarayıcın video CDN'ine hiç bağlanmaz.
- `API_TOKEN` tanımlıysa her `/api/*` isteği `Authorization: Bearer <anahtar>` ister (sabit zamanlı karşılaştırma).
- Varsayılan olarak uygulama yalnızca `127.0.0.1`'i dinler. İnternete açma; uzaktan erişim için Tailscale kullan.

## Geliştirme

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest
```

Testler GitHub Actions'ta Linux, macOS ve Windows üzerinde çalışır. Ağ bağlantısı ya da ffmpeg gerektirmezler (yt-dlp taklit edilir).

## Yasal not

Yalnızca kişisel kullanım içindir. Platformların kullanım koşullarına ve telif haklarına uy; yalnızca kaydetme hakkın olan içerikleri indir.

## Lisans

[MIT](LICENSE). Pakete dahil Bricolage Grotesque fontu [SIL Open Font License](app/static/fonts/OFL.txt) altındadır.
