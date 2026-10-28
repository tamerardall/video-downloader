# video-downloader

**English** | [Türkçe](README.tr.md)

A self-hosted, ad-free, tracker-free video downloader for social media (TikTok, Instagram, YouTube, X, Facebook, Reddit, Vimeo, Pinterest, Twitch). It runs on your own computer, has a small web UI in English and Turkish, and works from an iPhone share sheet through a Shortcut. Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

- Paste a link in the browser, or share a video from the TikTok/Instagram/YouTube app on your iPhone.
- Picks H.264 + AAC so videos save straight to the iPhone Photos app.
- Optional access key, SSRF protection and rate limiting; nothing is sent to third parties.

## Requirements

- Python 3.10 or newer
- [ffmpeg](https://ffmpeg.org/) (merges video and audio)

The JavaScript runtime YouTube needs ([Deno](https://deno.com/)) is installed into the virtual environment from `requirements.txt`; you don't need to install it separately.

## Installation

### Linux

```bash
# Fedora (ffmpeg comes from RPM Fusion)
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

Install [Homebrew](https://brew.sh/) first if you don't have it.

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
# Close and reopen PowerShell so python, ffmpeg and git are on PATH
git clone https://github.com/tamerardall/video-downloader
cd video-downloader
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\python -m app
```

Open http://127.0.0.1:8000 in your browser.

Always start the app with the Python inside `.venv` (as above). A system-wide `uvicorn` or `python` won't see the installed packages and fails with `ModuleNotFoundError: No module named 'yt_dlp'`.

**Updating:** sites change often, so update yt-dlp regularly: `.venv/bin/pip install -U -r requirements.txt` (Windows: `.venv\Scripts\pip install -U -r requirements.txt`), then restart the app.

## Configuration

All settings live in the `.env` file in the project folder (copied from `.env.example`). Edit it with any text editor (Windows: `notepad .env`) and restart the app after changes.

| Setting | Default | Description |
|---|---|---|
| `HOST` | `127.0.0.1` | Address to listen on. Use your Tailscale IP for phone access (see below). Never `0.0.0.0`. |
| `PORT` | `8000` | Port to listen on. |
| `API_TOKEN` | empty | If set, every `/api/*` request needs `Authorization: Bearer <token>`. **Required** when `HOST` is not `127.0.0.1`. |
| `COOKIES_FROM_BROWSER` | empty | Read login cookies from a browser: `firefox`, `chrome`, `brave`, `edge`, `safari`, ... or `browser:/path/to/profile`. |
| `COOKIES_FILE` | empty | Path to a Netscape-format `cookies.txt`. |
| `ALLOWED_DOMAINS` | common sites | Comma-separated list of allowed sites. |

Generate an `API_TOKEN`:

```bash
python3 -c "import secrets; print(secrets.token_hex(24))"   # Windows: py -c "..."
```

## Instagram and other sites that need login

Instagram doesn't serve videos to logged-out requests (yt-dlp reports *"Instagram sent an empty media response"*; the app tells you to set cookies). Log in to Instagram in a browser on the computer running the app, then set **one** of these in `.env`:

```ini
# Cookies straight from the browser (Firefox is the most reliable)
COOKIES_FROM_BROWSER=firefox

# Browser installed as a Flatpak, or a non-default profile: "browser:/profile/path"
COOKIES_FROM_BROWSER=brave:/home/me/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/Default

# Or a cookies.txt exported with a browser extension such as "Get cookies.txt LOCALLY"
COOKIES_FILE=/home/me/.config/video-downloader/cookies.txt
```

Platform notes:

- **Windows:** recent Chrome and Edge versions encrypt cookies in a way yt-dlp often can't read. Use Firefox, or export a `cookies.txt`.
- **macOS:** reading Safari cookies needs *Full Disk Access* for your terminal (System Settings → Privacy & Security). Chrome-based browsers ask for your Keychain password the first time.
- **Linux:** Chrome-based browsers store the key in GNOME Keyring or KWallet; your desktop session must be unlocked.

Cookies give access to your account: never share a `cookies.txt` or commit it (`.gitignore` already ignores `cookies*.txt`). Consider a secondary account; heavy downloading can get an account rate-limited. If you log out in the browser, downloads start failing with the login message again.

## Using it from your phone (Tailscale)

[Tailscale](https://tailscale.com/download) puts your computer and phone on a private network without opening any ports to the internet.

1. Install Tailscale on the computer and the phone, and sign in with the same account.
2. Find the computer's Tailscale address: `tailscale ip -4` (e.g. `100.x.y.z`). On Windows/macOS it is also shown in the Tailscale menu.
3. In `.env` set `HOST=100.x.y.z` and an `API_TOKEN` (see *Configuration*), then restart the app.
4. Allow the connection through the firewall if asked:
   - **Linux (firewalld):** open the port only on the Tailscale interface, e.g. `sudo firewall-cmd --zone=trusted --add-interface=tailscale0`.
   - **Windows:** when Windows Defender Firewall asks about Python, allow *Private networks*.
   - **macOS:** if the application firewall is on, allow incoming connections for Python.
5. Test from the phone's browser: `http://100.x.y.z:8000` (enter the token under **Key**).

Don't bind to `0.0.0.0` and don't forward the port on your router.

## iPhone Shortcut

The Shortcut sends the shared link to the server and saves the returned video to Photos, or shows the server's error message.

Add each action by typing its name into the search box at the bottom of the Shortcuts editor:

1. **Shortcuts** app → **+** → name it **Download Video**.
2. Tap **ⓘ** (Details) → turn on **Show in Share Sheet**. In the "Receives … input" box at the top keep only **URLs** and **Text**.
3. Add **Get Contents of URL**. Set the URL to `http://100.x.y.z:8000/api/download`, then tap the **>** arrow:
   - **Method:** POST
   - **Headers:** Add new header → key `Authorization`, value `Bearer <your API_TOKEN>` (note the space after Bearer)
   - **Request Body:** JSON → Add new field → **Text** → key `url`, value: tap the field → **Select Variable** → **Shortcut Input**
4. Add **Get Details of Files** → tap the blue "Detail" → **File Extension**. Its input becomes **Contents of URL** automatically.
5. Add **If** → condition: *File Extension* **is** `json`.
   - Between **If** and **Otherwise**: **Get Dictionary Value** → key `detail`, dictionary **Contents of URL**; then **Show Alert** → message **Dictionary Value**.
   - Between **Otherwise** and **End If**: **Save to Photo Album** → input **Contents of URL**.

The finished Shortcut:

```
Get Contents of URL  (POST, Authorization header, url = Shortcut Input)
Get Details of Files  (File Extension)
If  File Extension is json
    Get Dictionary Value  (detail, Contents of URL)
    Show Alert  (Dictionary Value)
Otherwise
    Save to Photo Album  (Contents of URL)
End If
```

Use it from TikTok/Instagram/YouTube/Safari: **Share → Download Video**. If the share sheet sends the link together with caption text, the server picks the first link out of it.

Why the extension check: on success the server returns an `.mp4`; on errors it returns `error.json`. *Get Contents of URL* doesn't stop on HTTP errors, so without the check an error either disappears silently or *Get Dictionary Value* fails on a video. Long videos can take a few minutes; the Shortcut waits.

## Troubleshooting

The terminal running the app logs every request:

| Log line | Meaning |
|---|---|
| `Downloaded: abc.mp4 (4.2 MB, video avc1..., audio mp4a...)` | The server produced the file. If video isn't `avc1` (H.264), the iPhone may refuse to save it. |
| `WARNING ... This site requires login` | Set `COOKIES_FROM_BROWSER` or `COOKIES_FILE` (see above). |
| `WARNING Invalid or missing API token` | The token in the Shortcut/web UI doesn't match `API_TOKEN`. |
| `WARNING URL rejected` | Not a supported site, a private address, or not a link. |
| `WARNING Rate limit exceeded` | More than 10 requests per minute from one IP. |
| `WARNING Invalid request body` | The Shortcut's request body isn't JSON with a `url` field. |

- **`POST /api/download ... 200 OK` but nothing in Photos:** the problem is on the phone: check the Shortcut steps. iPhone Photos can't save VP9/AV1 videos; the app prefers H.264 to avoid this.
- **YouTube: "No video formats found":** the Deno runtime is missing. Reinstall with `pip install -r requirements.txt` and make sure you start the app with the Python from `.venv`.
- **Slow or interrupted transfers to the phone:** run `tailscale status`; the phone should show `direct`. `relay` connections are much slower.

## Security

- Only http/https links to allowed sites are accepted; links with credentials and local/private IPs (SSRF) are rejected. Change the site list with `ALLOWED_DOMAINS`.
- 10 requests per minute per IP, at most 500 MB per file. Downloads are kept in a temporary folder and deleted after sending.
- The web UI loads no external scripts, fonts or trackers (strict CSP). Thumbnails are fetched by the server, so your browser never contacts the video CDN.
- With `API_TOKEN` set, every `/api/*` request needs `Authorization: Bearer <token>` (constant-time comparison).
- By default the app only listens on `127.0.0.1`. Don't expose it to the internet; use Tailscale for remote access.

## Development

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest
```

Tests run on Linux, macOS and Windows in GitHub Actions. They don't need network access or ffmpeg (yt-dlp is mocked).

## Legal

For personal use only. Respect each platform's terms of service and copyright; download only content you have the right to save.

## License

[MIT](LICENSE). The bundled Bricolage Grotesque font is under the [SIL Open Font License](app/static/fonts/OFL.txt).
