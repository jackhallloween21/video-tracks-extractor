#!/usr/bin/env python3
"""
Stream Extractor - a modern GUI tool built on ffmpeg/ffprobe.

Open a video file (or drag it onto the window), see every embedded
stream - video, all audio tracks (e.g. dual audio), and all subtitle
tracks - pick which ones you want, rename the output files if you like,
and extract each selected stream with a live progress bar.

Requirements:
    - Python 3.8+
    - ffmpeg and ffprobe (the app will help you locate/install these
      on first run if they're not already on your PATH)
    - Optional, for drag-and-drop: pip install tkinterdnd2
      (the app works fine without it - just use "Open file..." instead)

Run:
    python stream_extractor.py
"""

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import queue
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Drag-and-drop is optional. Fall back gracefully if the package is missing.
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False

APP_TITLE = "Stream Extractor (ffmpeg GUI)"
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".stream_extractor_config.json")
FFMPEG_DOWNLOAD_URL = "https://ffmpeg.org/download.html"

# Embedded app icon (PNG, base64) so the window/taskbar icon works
# identically whether this runs as a raw script or a frozen .exe -
# no external asset file needs to ship alongside it.
APP_ICON_PNG_B64 = (
    "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"
)

TEXT_SUB_CODECS = {"subrip", "srt", "ass", "ssa", "webvtt", "mov_text"}
IMAGE_SUB_CODECS = {"hdmv_pgs_subtitle", "dvd_subtitle", "dvb_subtitle"}
EXE_SUFFIX = ".exe" if sys.platform == "win32" else ""

# ---------------------------------------------------------------- themes ---

THEMES = {
    "light": {
        "bg": "#f4f4f6", "fg": "#1c1c1e", "panel": "#ffffff",
        "field": "#ffffff", "border": "#d8d8dc", "accent": "#3366ff",
        "accent_fg": "#ffffff", "tree_bg": "#ffffff", "tree_alt": "#f0f1f5",
        "tree_sel": "#3366ff", "tree_sel_fg": "#ffffff", "log_bg": "#ffffff",
        "log_fg": "#1c1c1e", "muted": "#65656b", "good": "#1e8e3e", "bad": "#c5221f",
        "drop_bg": "#eef1ff", "drop_border": "#9fb2ff",
    },
    "dark": {
        "bg": "#1e1f24", "fg": "#e8e8ea", "panel": "#26272d",
        "field": "#2c2d34", "border": "#3a3b42", "accent": "#5c8dff",
        "accent_fg": "#0d0d10", "tree_bg": "#26272d", "tree_alt": "#2b2c33",
        "tree_sel": "#5c8dff", "tree_sel_fg": "#0d0d10", "log_bg": "#17181c",
        "log_fg": "#d7d7db", "muted": "#9a9aa2", "good": "#5ec98a", "bad": "#ff6b6b",
        "drop_bg": "#22283a", "drop_border": "#465a92",
    },
}


# ------------------------------------------------------------- utilities ---

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    existing = load_config()
    existing.update(cfg)
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass


def tool_works(path):
    if not path:
        return False
    try:
        subprocess.run([path, "-version"], stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


def guess_ffprobe_from_ffmpeg(ffmpeg_path):
    folder = os.path.dirname(ffmpeg_path)
    name = os.path.basename(ffmpeg_path)
    guess = os.path.join(folder, name.replace("ffmpeg", "ffprobe"))
    return guess if tool_works(guess) else ""


def resolve_tool(configured_path, tool_name):
    if configured_path and tool_works(configured_path):
        return configured_path
    on_path = shutil.which(tool_name)
    if on_path and tool_works(on_path):
        return on_path
    return ""


def human_audio_desc(stream):
    ch = stream.get("channels")
    layout = stream.get("channel_layout", "")
    bits = []
    if ch:
        bits.append(f"{ch}ch")
    if layout:
        bits.append(layout)
    if stream.get("sample_rate"):
        bits.append(f"{stream['sample_rate']}Hz")
    return " / ".join(bits)


def stream_label(stream):
    idx = stream["index"]
    ctype = stream.get("codec_type", "?")
    codec = stream.get("codec_name", "?")
    tags = stream.get("tags", {}) or {}
    lang = tags.get("language", "")
    title = tags.get("title", "")

    if ctype == "video":
        w, h = stream.get("width"), stream.get("height")
        fps = stream.get("r_frame_rate", "")
        try:
            num, den = fps.split("/")
            fps_val = f"{float(num) / float(den):.2f} fps" if float(den) else ""
        except Exception:
            fps_val = ""
        extra = f"{w}x{h} {fps_val}".strip()
    elif ctype == "audio":
        extra = human_audio_desc(stream)
    elif ctype == "subtitle":
        extra = "text-based" if codec in TEXT_SUB_CODECS else (
            "image-based" if codec in IMAGE_SUB_CODECS else "")
    else:
        extra = ""

    return {"index": idx, "type": ctype, "codec": codec, "lang": lang,
            "title": title, "extra": extra}


def default_extension(ctype, codec, audio_fmt, sub_fmt):
    if ctype == "video":
        return "mkv"
    if ctype == "audio":
        if audio_fmt == "copy":
            return {"aac": "aac", "ac3": "ac3", "eac3": "eac3", "dts": "dts",
                     "mp3": "mp3", "flac": "flac"}.get(codec, "mka")
        return audio_fmt
    if ctype == "subtitle":
        if codec in IMAGE_SUB_CODECS:
            return "sup" if codec == "hdmv_pgs_subtitle" else "sub"
        if sub_fmt == "srt":
            return "srt"
        return {"ass": "ass", "ssa": "ssa", "webvtt": "vtt", "mov_text": "srt"}.get(codec, "srt")
    return "bin"


def default_output_name(base, stream, audio_fmt, sub_fmt):
    idx = stream["index"]
    ctype = stream.get("codec_type")
    codec = stream.get("codec_name", "")
    tags = stream.get("tags", {}) or {}
    lang = tags.get("language", "")
    suffix = f"_{lang}" if lang else ""
    ext = default_extension(ctype, codec, audio_fmt, sub_fmt)
    tag = {"video": "video", "audio": f"audio{idx}", "subtitle": f"sub{idx}"}.get(ctype, f"stream{idx}")
    return f"{base}_{tag}{suffix}.{ext}"


def parse_time_to_seconds(ts):
    """Parse ffmpeg's HH:MM:SS.microseconds into seconds."""
    m = re.match(r"(\d+):(\d+):(\d+(?:\.\d+)?)", ts)
    if not m:
        return None
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)


def apply_app_icon(window):
    """
    Set the window/taskbar icon on any Toplevel or Tk root, using the
    embedded PNG so it works the same as a plain script or a frozen
    .exe (built via the PyInstaller --icon flag, which only covers the
    Explorer/taskbar icon before launch - this covers it at runtime too).
    """
    try:
        data = base64.b64decode(APP_ICON_PNG_B64)
        icon_image = tk.PhotoImage(data=data)
        window.iconphoto(True, icon_image)
        window._app_icon_ref = icon_image  # keep a reference alive
    except Exception:
        pass  # non-fatal - app still runs fine without a window icon


# --------------------------------------------------------- ffmpeg dialog ---

class FfmpegSetupDialog(tk.Toplevel):
    def __init__(self, parent, palette, reason=""):
        super().__init__(parent)
        self.title("Locate ffmpeg")
        apply_app_icon(self)
        self.resizable(False, False)
        self.configure(bg=palette["bg"])
        self.result_ffmpeg = ""
        self.result_ffprobe = ""
        self.grab_set()
        self.transient(parent)

        pad = {"padx": 16, "pady": 8}
        msg = reason or "ffmpeg / ffprobe could not be found on your system."
        tk.Label(self, text=msg, wraplength=420, justify="left",
                 bg=palette["bg"], fg=palette["fg"]).pack(**pad)
        tk.Label(self, bg=palette["bg"], fg=palette["muted"], wraplength=420, justify="left",
                 text="This app needs ffmpeg (and ffprobe, which ships with it) "
                      "to inspect and extract media streams.").pack(padx=16, pady=(0, 8))

        btns = ttk.Frame(self)
        btns.pack(fill="x", **pad)
        ttk.Button(btns, text="Browse for ffmpeg executable...", command=self.browse).pack(fill="x", pady=4)
        ttk.Button(btns, text="Open ffmpeg download page", command=self.open_download).pack(fill="x", pady=4)
        ttk.Button(btns, text="I'll set this up later", command=self.skip).pack(fill="x", pady=(12, 0))

        self.protocol("WM_DELETE_WINDOW", self.skip)
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx()+40}+{parent.winfo_rooty()+40}")
        self.wait_window(self)

    def browse(self):
        filetypes = [("ffmpeg executable", f"ffmpeg{EXE_SUFFIX}"), ("All files", "*.*")]
        path = filedialog.askopenfilename(title="Select the ffmpeg executable", filetypes=filetypes)
        if not path:
            return
        if not tool_works(path):
            messagebox.showerror("Not a valid ffmpeg", f"Could not run:\n{path}")
            return
        ffprobe_guess = guess_ffprobe_from_ffmpeg(path)
        if not ffprobe_guess:
            messagebox.showwarning("ffprobe not found",
                                    "Found ffmpeg, but no matching ffprobe nearby. "
                                    "Please locate it separately.")
            ffprobe_path = filedialog.askopenfilename(
                title="Select the ffprobe executable",
                filetypes=[("ffprobe executable", f"ffprobe{EXE_SUFFIX}"), ("All files", "*.*")])
            if not ffprobe_path or not tool_works(ffprobe_path):
                messagebox.showerror("Not set", "ffprobe was not set; configure it later.")
                self.result_ffmpeg, self.result_ffprobe = path, ""
                self.destroy()
                return
            ffprobe_guess = ffprobe_path
        self.result_ffmpeg, self.result_ffprobe = path, ffprobe_guess
        self.destroy()

    def open_download(self):
        webbrowser.open(FFMPEG_DOWNLOAD_URL)
        messagebox.showinfo("Download ffmpeg",
                             "Opened the ffmpeg download page in your browser.\n\n"
                             "After installing, click 'Browse for ffmpeg executable...' "
                             "to point this app at it.")

    def skip(self):
        self.result_ffmpeg, self.result_ffprobe = "", ""
        self.destroy()


# ------------------------------------------------------------- main app ---

class ExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        apply_app_icon(self.root)
        self.root.geometry("960x680")
        self.root.minsize(820, 560)

        cfg = load_config()
        self.dark_mode = tk.BooleanVar(value=cfg.get("dark_mode", False))
        self.ffmpeg_path = tk.StringVar(value=cfg.get("ffmpeg_path", ""))
        self.ffprobe_path = tk.StringVar(value=cfg.get("ffprobe_path", ""))

        self.filepath = tk.StringVar()
        self.outdir = tk.StringVar()
        self.audio_format = tk.StringVar(value="copy")
        self.sub_format = tk.StringVar(value="copy")

        self.streams = []
        self.row_to_stream = {}
        self.edited_names = set()   # item_ids whose output name the user manually changed
        self.log_queue = queue.Queue()
        self.duration = None
        self.name_editor = None     # active inline Entry widget, if any

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self._build_ui()
        self.apply_theme()
        self._poll_log_queue()
        self._setup_dnd()

        self.root.after(150, self.ensure_ffmpeg_ready)

    # ---------------- theming ----------------

    def palette(self):
        return THEMES["dark"] if self.dark_mode.get() else THEMES["light"]

    def toggle_theme(self):
        self.dark_mode.set(not self.dark_mode.get())
        save_config({"dark_mode": self.dark_mode.get()})
        self.apply_theme()

    def apply_theme(self):
        p = self.palette()
        self.root.configure(bg=p["bg"])

        s = self.style
        s.configure(".", background=p["bg"], foreground=p["fg"], fieldbackground=p["field"])
        s.configure("TFrame", background=p["bg"])
        s.configure("TLabel", background=p["bg"], foreground=p["fg"])
        s.configure("Muted.TLabel", background=p["bg"], foreground=p["muted"])
        s.configure("Good.TLabel", background=p["bg"], foreground=p["good"])
        s.configure("Bad.TLabel", background=p["bg"], foreground=p["bad"])
        s.configure("TLabelframe", background=p["bg"], foreground=p["fg"])
        s.configure("TLabelframe.Label", background=p["bg"], foreground=p["fg"])
        s.configure("TButton", background=p["panel"], foreground=p["fg"], padding=6, borderwidth=0)
        s.map("TButton", background=[("active", p["accent"])], foreground=[("active", p["accent_fg"])])
        s.configure("Accent.TButton", background=p["accent"], foreground=p["accent_fg"], padding=8)
        s.map("Accent.TButton", background=[("active", p["accent"])])

        # Comboboxes: the "readonly" and "disabled" states are drawn from their
        # own style.map entries and otherwise ignore .configure(), which is
        # what left them white in dark mode. Set every state explicitly,
        # including the field, the arrow button, and text selection colors.
        s.configure("TCombobox", fieldbackground=p["field"], background=p["panel"],
                    foreground=p["fg"], arrowcolor=p["fg"], bordercolor=p["border"],
                    lightcolor=p["field"], darkcolor=p["field"], insertcolor=p["fg"])
        s.map(
            "TCombobox",
            fieldbackground=[("readonly", p["field"]), ("disabled", p["field"]), ("!disabled", p["field"])],
            foreground=[("readonly", p["fg"]), ("disabled", p["muted"]), ("!disabled", p["fg"])],
            selectbackground=[("readonly", p["field"]), ("!focus", p["field"])],
            selectforeground=[("readonly", p["fg"]), ("!focus", p["fg"])],
            background=[("readonly", p["panel"]), ("active", p["panel"]), ("!disabled", p["panel"])],
            arrowcolor=[("readonly", p["fg"]), ("disabled", p["muted"])],
        )
        # The dropdown list itself is a plain Tk Listbox in a separate
        # popup window and is only reachable via option database entries.
        self.root.option_add("*TCombobox*Listbox.background", p["field"])
        self.root.option_add("*TCombobox*Listbox.foreground", p["fg"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", p["accent"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", p["accent_fg"])
        self.root.option_add("*TCombobox*Listbox.font", "TkDefaultFont")

        s.configure("TEntry", fieldbackground=p["field"], foreground=p["fg"], insertcolor=p["fg"])
        s.map("TEntry", fieldbackground=[("readonly", p["field"]), ("disabled", p["field"])],
              foreground=[("readonly", p["fg"]), ("disabled", p["muted"])])

        s.configure("Treeview", background=p["tree_bg"], fieldbackground=p["tree_bg"],
                    foreground=p["fg"], rowheight=26, borderwidth=0)
        s.configure("Treeview.Heading", background=p["panel"], foreground=p["fg"], borderwidth=0)
        s.map("Treeview", background=[("selected", p["tree_sel"])],
              foreground=[("selected", p["tree_sel_fg"])])
        s.configure("Horizontal.TProgressbar", background=p["accent"], troughcolor=p["field"],
                    borderwidth=0, lightcolor=p["accent"], darkcolor=p["accent"])

        self.tree.tag_configure("even", background=p["tree_bg"])
        self.tree.tag_configure("odd", background=p["tree_alt"])

        self.log_text.configure(bg=p["log_bg"], fg=p["log_fg"], insertbackground=p["fg"])
        self.drop_frame.configure(bg=p["drop_bg"], highlightbackground=p["drop_border"],
                                   highlightcolor=p["drop_border"])
        self.drop_label.configure(bg=p["drop_bg"], fg=p["muted"])

        # Theme toggle button: a plain tk.Button so we fully control its
        # colors (a ttk.Checkbutton's indicator is OS-drawn on some
        # platforms and ignores style overrides, which caused the white
        # hover box). Icon shows the mode a click will switch TO.
        icon = "\u2600" if self.dark_mode.get() else "\u263D"  # ☀ or ☽
        self.theme_btn.configure(
            text=icon, bg=p["bg"], fg=p["fg"],
            activebackground=p["panel"], activeforeground=p["fg"],
            highlightbackground=p["bg"], highlightcolor=p["bg"],
        )

        self.update_status_label()

    # ---------------- ffmpeg location ----------------

    def ensure_ffmpeg_ready(self, force_dialog=False):
        resolved_ffmpeg = resolve_tool(self.ffmpeg_path.get(), "ffmpeg")
        resolved_ffprobe = resolve_tool(self.ffprobe_path.get(), "ffprobe")

        if resolved_ffmpeg and resolved_ffprobe and not force_dialog:
            self.ffmpeg_path.set(resolved_ffmpeg)
            self.ffprobe_path.set(resolved_ffprobe)
            self.update_status_label()
            return True

        reason = ("Set up ffmpeg for this app." if force_dialog else
                  "Couldn't find ffmpeg/ffprobe on your system PATH.")
        dlg = FfmpegSetupDialog(self.root, self.palette(), reason=reason)
        if dlg.result_ffmpeg:
            self.ffmpeg_path.set(dlg.result_ffmpeg)
            self.ffprobe_path.set(dlg.result_ffprobe)
            save_config({"ffmpeg_path": dlg.result_ffmpeg, "ffprobe_path": dlg.result_ffprobe})
            self.log(f"Using ffmpeg: {dlg.result_ffmpeg}")
            self.log(f"Using ffprobe: {dlg.result_ffprobe}")
            self.update_status_label()
            return True
        self.update_status_label()
        return False

    def open_ffmpeg_settings(self):
        self.ensure_ffmpeg_ready(force_dialog=True)

    def update_status_label(self):
        ok = tool_works(self.ffmpeg_path.get()) and tool_works(self.ffprobe_path.get())
        if ok:
            self.status_label.configure(text=f"ffmpeg: {self.ffmpeg_path.get()}", style="Good.TLabel")
        else:
            self.status_label.configure(text="ffmpeg not configured - click 'ffmpeg settings...'",
                                         style="Bad.TLabel")

    # ---------------- UI construction ----------------

    def _build_ui(self):
        pad = {"padx": 8, "pady": 6}

        top = ttk.Frame(self.root)
        top.pack(fill="x", **pad)
        ttk.Button(top, text="Open file...", command=self.choose_file).pack(side="left")
        ttk.Entry(top, textvariable=self.filepath, state="readonly").pack(
            side="left", fill="x", expand=True, padx=8)
        ttk.Button(top, text="ffmpeg settings...", command=self.open_ffmpeg_settings).pack(side="left")

        # Plain tk.Button (not ttk.Checkbutton) so hover/active colors are
        # fully under our control instead of drawn by the OS theme.
        self.theme_btn = tk.Button(
            top, text="\u263D", relief="flat", bd=0, highlightthickness=0,
            font=("Segoe UI Symbol", 13), cursor="hand2", width=3,
            command=self.toggle_theme,
        )
        self.theme_btn.pack(side="left", padx=(8, 0))

        status_row = ttk.Frame(self.root)
        status_row.pack(fill="x", padx=8)
        self.status_label = ttk.Label(status_row, text="Checking for ffmpeg...")
        self.status_label.pack(anchor="w")

        # Drag & drop zone
        self.drop_frame = tk.Frame(self.root, highlightthickness=2, bd=0)
        self.drop_frame.pack(fill="x", padx=8, pady=(4, 6))
        dnd_hint = "" if DND_AVAILABLE else "  (install 'tkinterdnd2' to enable this)"
        self.drop_label = tk.Label(
            self.drop_frame,
            text="Drag & drop a video file here" + dnd_hint,
            pady=14,
        )
        self.drop_label.pack(fill="x")

        # Stream list
        list_frame = ttk.Frame(self.root)
        list_frame.pack(fill="both", expand=True, padx=8, pady=6)

        columns = ("sel", "index", "type", "codec", "lang", "title", "extra", "outname", "progress")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="none")
        headers = {"sel": "✔", "index": "#", "type": "Type", "codec": "Codec", "lang": "Lang",
                   "title": "Title", "extra": "Details", "outname": "Output filename", "progress": "Progress"}
        widths = {"sel": 34, "index": 34, "type": 64, "codec": 80, "lang": 50, "title": 110,
                  "extra": 150, "outname": 230, "progress": 90}
        stretch_cols = {"title", "extra", "outname"}
        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="w", stretch=(col in stretch_cols))

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        ttk.Label(
            self.root,
            text="Click a row to select/deselect it. Double-click the filename to rename it.",
            style="Muted.TLabel",
        ).pack(anchor="w", padx=8)

        # Options row
        opts = ttk.Frame(self.root)
        opts.pack(fill="x", **pad)
        ttk.Label(opts, text="Audio output:").pack(side="left")
        self.audio_combo = ttk.Combobox(opts, textvariable=self.audio_format, state="readonly", width=10,
                                         values=["copy", "aac", "mp3", "wav", "flac"])
        self.audio_combo.pack(side="left", padx=(4, 16))
        self.audio_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_default_names())

        ttk.Label(opts, text="Subtitle output:").pack(side="left")
        self.sub_combo = ttk.Combobox(opts, textvariable=self.sub_format, state="readonly", width=10,
                                       values=["copy", "srt"])
        self.sub_combo.pack(side="left", padx=(4, 16))
        self.sub_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_default_names())

        ttk.Button(opts, text="Select all", command=lambda: self.set_all(True)).pack(side="left", padx=4)
        ttk.Button(opts, text="Select none", command=lambda: self.set_all(False)).pack(side="left", padx=4)
        ttk.Button(opts, text="Reset filenames", command=self.reset_all_names).pack(side="left", padx=4)

        # Output dir row
        outrow = ttk.Frame(self.root)
        outrow.pack(fill="x", **pad)
        ttk.Button(outrow, text="Output folder...", command=self.choose_outdir).pack(side="left")
        ttk.Entry(outrow, textvariable=self.outdir, state="readonly").pack(
            side="left", fill="x", expand=True, padx=8)
        self.extract_btn = ttk.Button(outrow, text="Extract selected", style="Accent.TButton",
                                       command=self.start_extraction)
        self.extract_btn.pack(side="left", padx=4)

        # Overall progress
        prog_row = ttk.Frame(self.root)
        prog_row.pack(fill="x", padx=8, pady=(0, 4))
        self.overall_progress = ttk.Progressbar(prog_row, orient="horizontal", mode="determinate")
        self.overall_progress.pack(fill="x", side="left", expand=True)
        self.progress_pct_label = ttk.Label(prog_row, text="", width=6, anchor="e")
        self.progress_pct_label.pack(side="left", padx=(8, 0))

        # Log
        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=False, padx=8, pady=(0, 8))
        self.log_text = tk.Text(log_frame, height=8, state="disabled", wrap="word", borderwidth=0)
        self.log_text.pack(fill="both", expand=True)

    # ---------------- drag & drop ----------------

    def _setup_dnd(self):
        if not DND_AVAILABLE:
            return
        try:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind("<<Drop>>", self.on_drop)
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self.on_drop)
        except Exception as e:
            self.log(f"Drag & drop setup failed: {e}")

    def on_drop(self, event):
        raw = event.data
        # Tk gives paths possibly wrapped in {}, possibly several space-separated
        paths = re.findall(r"\{[^}]*\}|\S+", raw)
        paths = [p.strip("{}") for p in paths]
        if not paths:
            return
        path = paths[0]
        if not os.path.isfile(path):
            messagebox.showwarning("Not a file", f"Could not open:\n{path}")
            return
        if not self.ensure_ffmpeg_ready():
            messagebox.showwarning("ffmpeg required", "Set up ffmpeg first via 'ffmpeg settings...'.")
            return
        self.filepath.set(path)
        if not self.outdir.get():
            self.outdir.set(os.path.dirname(path))
        self.load_streams(path)

    # ---------------- file handling ----------------

    def choose_file(self):
        if not self.ensure_ffmpeg_ready():
            messagebox.showwarning("ffmpeg required",
                                    "Set up ffmpeg first via 'ffmpeg settings...'.")
            return
        path = filedialog.askopenfilename(
            title="Choose a media file",
            filetypes=[("Video files", "*.mkv *.mp4 *.mov *.avi *.webm *.ts *.m2ts *.wmv"),
                       ("All files", "*.*")])
        if not path:
            return
        self.filepath.set(path)
        if not self.outdir.get():
            self.outdir.set(os.path.dirname(path))
        self.load_streams(path)

    def choose_outdir(self):
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self.outdir.set(d)

    def probe_file(self, path):
        cmd = [self.ffprobe_path.get(), "-v", "quiet", "-print_format", "json",
               "-show_format", "-show_streams", path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode(errors="ignore"))
        return json.loads(result.stdout.decode(errors="ignore"))

    def load_streams(self, path):
        self.tree.delete(*self.tree.get_children())
        self.row_to_stream.clear()
        self.edited_names.clear()
        try:
            info = self.probe_file(path)
        except Exception as e:
            messagebox.showerror("ffprobe error", str(e))
            return

        try:
            self.duration = float(info.get("format", {}).get("duration", 0)) or None
        except Exception:
            self.duration = None

        base = os.path.splitext(os.path.basename(path))[0]
        self.streams = info.get("streams", [])
        count = 0
        for s in self.streams:
            if s.get("codec_type") not in ("video", "audio", "subtitle"):
                continue
            row = stream_label(s)
            outname = default_output_name(base, s, self.audio_format.get(), self.sub_format.get())
            tag = "even" if count % 2 == 0 else "odd"
            item_id = self.tree.insert(
                "", "end",
                values=("☐", row["index"], row["type"], row["codec"], row["lang"],
                        row["title"], row["extra"], outname, ""),
                tags=(tag,))
            self.row_to_stream[item_id] = s
            count += 1
        self.log(f"Loaded {count} streams from {os.path.basename(path)}")

    # ---------------- selection / inline rename ----------------

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        col = self.tree.identify_column(event.x)
        item_id = self.tree.identify_row(event.y)
        self._close_name_editor(commit=True)
        if region != "cell" or not item_id:
            return
        if col == "#8":  # outname column - don't toggle selection on single click
            return
        self.toggle_row(item_id)

    def on_tree_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        col = self.tree.identify_column(event.x)
        item_id = self.tree.identify_row(event.y)
        if region != "cell" or not item_id:
            return
        if col == "#8":  # outname column
            self._start_name_editor(item_id, col)

    def _start_name_editor(self, item_id, col):
        self._close_name_editor(commit=True)
        bbox = self.tree.bbox(item_id, col)
        if not bbox:
            return
        x, y, w, h = bbox
        values = self.tree.item(item_id, "values")
        current_name = values[7]

        p = self.palette()
        editor = tk.Entry(self.tree, borderwidth=1, bg=p["field"], fg=p["fg"],
                           insertbackground=p["fg"])
        editor.insert(0, current_name)
        editor.select_range(0, "end")
        editor.place(x=x, y=y, width=w, height=h)
        editor.focus_set()

        def commit(event=None):
            new_name = editor.get().strip()
            if new_name:
                vals = list(self.tree.item(item_id, "values"))
                vals[7] = new_name
                self.tree.item(item_id, values=vals)
                self.edited_names.add(item_id)
            self._close_name_editor(commit=False)

        def cancel(event=None):
            self._close_name_editor(commit=False)

        editor.bind("<Return>", commit)
        editor.bind("<Escape>", cancel)
        editor.bind("<FocusOut>", commit)
        self.name_editor = editor

    def _close_name_editor(self, commit=True):
        if self.name_editor is not None:
            editor = self.name_editor
            self.name_editor = None
            try:
                editor.destroy()
            except Exception:
                pass

    def toggle_row(self, item_id):
        vals = list(self.tree.item(item_id, "values"))
        vals[0] = "☐" if vals[0] == "☑" else "☑"
        self.tree.item(item_id, values=vals)

    def set_all(self, selected):
        mark = "☑" if selected else "☐"
        for item_id in self.tree.get_children():
            vals = list(self.tree.item(item_id, "values"))
            vals[0] = mark
            self.tree.item(item_id, values=vals)

    def refresh_default_names(self):
        """Regenerate default output names for any row the user hasn't manually renamed."""
        base = os.path.splitext(os.path.basename(self.filepath.get()))[0] if self.filepath.get() else "output"
        for item_id in self.tree.get_children():
            if item_id in self.edited_names:
                continue
            stream = self.row_to_stream.get(item_id)
            if not stream:
                continue
            vals = list(self.tree.item(item_id, "values"))
            vals[7] = default_output_name(base, stream, self.audio_format.get(), self.sub_format.get())
            self.tree.item(item_id, values=vals)

    def reset_all_names(self):
        self.edited_names.clear()
        self.refresh_default_names()

    def get_selected_rows(self):
        selected = []
        for item_id in self.tree.get_children():
            vals = self.tree.item(item_id, "values")
            if vals[0] == "☑":
                selected.append((item_id, self.row_to_stream[item_id], vals[7]))
        return selected

    def set_row_progress(self, item_id, text):
        vals = list(self.tree.item(item_id, "values"))
        vals[8] = text
        self.tree.item(item_id, values=vals)

    # ---------------- extraction ----------------

    def start_extraction(self):
        self._close_name_editor(commit=True)
        if not self.ensure_ffmpeg_ready():
            messagebox.showwarning("ffmpeg required", "Set up ffmpeg first via 'ffmpeg settings...'.")
            return
        src = self.filepath.get()
        outdir = self.outdir.get()
        if not src:
            messagebox.showwarning("No file", "Open a media file first.")
            return
        if not outdir:
            messagebox.showwarning("No output folder", "Choose an output folder first.")
            return
        selected = self.get_selected_rows()
        if not selected:
            messagebox.showwarning("Nothing selected", "Select at least one stream to extract.")
            return

        names = [name for _, _, name in selected]
        if len(set(names)) != len(names):
            messagebox.showwarning("Duplicate filenames",
                                    "Two or more selected streams have the same output filename. "
                                    "Please rename them so each is unique.")
            return

        self.extract_btn.state(["disabled"])
        self.overall_progress["value"] = 0
        self.progress_pct_label.configure(text="0%")
        thread = threading.Thread(
            target=self.run_extraction,
            args=(src, outdir, selected, self.audio_format.get(), self.sub_format.get()),
            daemon=True)
        thread.start()

    def run_extraction(self, src, outdir, selected, audio_fmt, sub_fmt):
        ffmpeg = self.ffmpeg_path.get()
        os.makedirs(outdir, exist_ok=True)
        total = len(selected)

        for i, (item_id, stream, outname) in enumerate(selected):
            idx = stream["index"]
            ctype = stream.get("codec_type")
            codec = stream.get("codec_name", "")
            out_path = os.path.join(outdir, outname)

            if ctype == "video":
                cmd = [ffmpeg, "-y", "-i", src, "-map", f"0:{idx}", "-c", "copy",
                       "-progress", "pipe:1", "-nostats", out_path]
            elif ctype == "audio":
                if audio_fmt == "copy":
                    cmd = [ffmpeg, "-y", "-i", src, "-map", f"0:{idx}", "-c", "copy",
                           "-progress", "pipe:1", "-nostats", out_path]
                else:
                    cmd = [ffmpeg, "-y", "-i", src, "-map", f"0:{idx}",
                           "-progress", "pipe:1", "-nostats", out_path]
            elif ctype == "subtitle":
                if codec in IMAGE_SUB_CODECS or sub_fmt != "srt":
                    cmd = [ffmpeg, "-y", "-i", src, "-map", f"0:{idx}", "-c", "copy",
                           "-progress", "pipe:1", "-nostats", out_path]
                else:
                    cmd = [ffmpeg, "-y", "-i", src, "-map", f"0:{idx}",
                           "-progress", "pipe:1", "-nostats", out_path]
            else:
                continue

            self.log(f"Extracting stream #{idx} ({ctype}/{codec}) -> {outname}")
            self.log("  $ " + " ".join(cmd))
            self.log_queue.put(("row", item_id, "0%"))

            ok = self._run_with_progress(cmd, item_id, i, total)
            if ok:
                self.log(f"  done: {outname}")
                self.log_queue.put(("row", item_id, "done"))
            else:
                self.log_queue.put(("row", item_id, "failed"))

            self.log_queue.put(("overall", None, int(100 * (i + 1) / total)))

        self.log("All selected streams processed.")
        self.log_queue.put(("__enable_button__", None, None))

    def _run_with_progress(self, cmd, item_id, index, total):
        errfile = tempfile.TemporaryFile(mode="w+")
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errfile,
                                     text=True, bufsize=1)
        except Exception as e:
            errfile.close()
            self.log(f"  FAILED to launch ffmpeg: {e}")
            return False

        for line in proc.stdout:
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key == "out_time" and self.duration:
                secs = parse_time_to_seconds(value)
                if secs is not None:
                    pct = max(0, min(100, int(100 * secs / self.duration)))
                    self.log_queue.put(("row", item_id, f"{pct}%"))
                    overall = int(100 * (index + pct / 100) / total)
                    self.log_queue.put(("overall", None, overall))
            elif key == "progress" and value == "end":
                self.log_queue.put(("row", item_id, "99%"))

        proc.wait()
        errfile.seek(0)
        err_text = errfile.read()
        errfile.close()

        if proc.returncode != 0:
            self.log(f"  FAILED: {err_text.strip()[-500:]}")
            return False
        return True

    # ---------------- logging / queue polling ----------------

    def log(self, msg):
        self.log_queue.put(("msg", msg, None))

    def _poll_log_queue(self):
        try:
            while True:
                kind, a, b = self.log_queue.get_nowait()
                if kind == "__enable_button__":
                    self.extract_btn.state(["!disabled"])
                elif kind == "row":
                    item_id, text = a, b
                    if self.tree.exists(item_id):
                        self.set_row_progress(item_id, text)
                elif kind == "overall":
                    pct = b
                    self.overall_progress["value"] = pct
                    self.progress_pct_label.configure(text=f"{pct}%")
                else:
                    self.log_text.configure(state="normal")
                    self.log_text.insert("end", a + "\n")
                    self.log_text.see("end")
                    self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log_queue)


def main():
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = ExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
