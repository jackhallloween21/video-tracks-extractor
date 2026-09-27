<p align="center">
  <img src="assets/icon.png" width="96" alt="Stream Extractor icon">
</p>

<h1 align="center">Stream Extractor</h1>

<p align="center">
  A small, modern desktop GUI for pulling individual video, audio (including dual/multi audio),
  and subtitle tracks out of a media file — built on <a href="https://ffmpeg.org">ffmpeg</a>.
</p>

---

## Features

- **Inspect any media file** — see every embedded video, audio, and subtitle stream (codec, language, channels/resolution) before you touch anything.
- **Dual / multi-audio support** — each audio track is listed and extracted separately.
- **Subtitle extraction** — text-based subtitles (SubRip/ASS/mov_text) can be copied as-is or converted to `.srt`; image-based subtitles (PGS/VobSub) are always kept in their native format.
- **Drag & drop** a file straight onto the window (optional, see below).
- **Editable output filenames** — double-click any row's filename to rename it before extracting.
- **Light / dark theme**, toggled with the ☽ / ☀ button.
- **Live progress bars** — per-stream and overall, while ffmpeg runs in the background.
- **No install needed on the client machine** — the released `.exe` bundles Python and every dependency inside it.

## Download

Grab the latest `StreamExtractor.exe` from the [Releases](../../releases) page. No Python, pip, or ffmpeg-on-PATH setup is required to run it — on first launch it will ask you to locate an ffmpeg install or open the ffmpeg download page if it can't find one automatically.

## Running from source

```bash
git clone <this-repo-url>
cd <this-repo>
pip install -r requirements.txt   # tkinterdnd2 is optional, see below
python stream_extractor.py
```

Requirements:
- Python 3.8+
- `ffmpeg` / `ffprobe` — installed separately, or point the app at them via **"ffmpeg settings..."** on first run
- On Linux, tkinter itself may need a system package: `sudo apt install python3-tk`
- Optional, for drag-and-drop: `pip install tkinterdnd2` — the app works fine without it, you just use **"Open file..."** instead

## Building the .exe yourself

```bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --name StreamExtractor --icon assets/icon.ico stream_extractor.py
```

The result lands in `dist/StreamExtractor.exe`, with ffmpeg-dependency-free packaging: everything the app needs (Python runtime, tkinter, dependencies) is bundled inside. ffmpeg itself is **not** bundled — it's a separate, much larger download, so the app locates or helps the user install it on first run instead.

## CI: building and releasing automatically

Two GitHub Actions workflows live in `.github/workflows/`:

| Workflow | Trigger | What it does |
|---|---|---|
| `release.yml` | Pushing a tag like `v1.0.0` | Builds the `.exe`, then creates a GitHub Release for that tag with the `.exe` attached. |
| `test-build.yml` | Manual — **Actions tab → "Build & Test EXE (manual)" → Run workflow** | Builds the `.exe`, launches it on the runner to confirm it doesn't crash on startup, and uploads it as a downloadable workflow artifact. No release is created, so it's safe to run anytime while developing. |

### Cutting a release

```bash
git tag v1.0.0
git push origin v1.0.0
```

That's it — the workflow builds and publishes the `.exe` to a new GitHub Release automatically.

### Testing a build without releasing

Go to the **Actions** tab → select **"Build & Test EXE (manual)"** → **Run workflow**. When it finishes, download the `StreamExtractor-windows-exe` artifact from the run's summary page to try it locally.

## Project structure

```
stream_extractor.py          the app
assets/icon.ico               Windows .exe / taskbar icon
assets/icon.png                same icon, used in this README and as the in-app window icon
requirements.txt              runtime + build dependencies
.github/workflows/release.yml       tag-triggered build + release
.github/workflows/test-build.yml    manual build + smoke test
```

## License

Add a `LICENSE` file with whichever license you'd like this project to use (MIT is a common default for small tools like this).
