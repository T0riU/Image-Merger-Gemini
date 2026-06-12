import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
from PIL import Image, ImageDraw, ImageTk
import os, io, base64, threading, urllib.request, json, webbrowser

def _scale(base, factor): return max(1, round(base * factor))

import tkinter as _tk
_root_check = _tk.Tk()
_root_check.withdraw()
_SW = _root_check.winfo_screenwidth()
_SH = _root_check.winfo_screenheight()
_root_check.destroy()
del _root_check, _tk

_UI = _SH / 1080

PREVIEW_W  = _scale(300, _UI)
PREVIEW_H  = _scale(220, _UI)
FONT       = ("Segoe UI", _scale(12, _UI))
FONT_BIG   = ("Segoe UI", _scale(13, _UI), "bold")
FONT_LINK  = ("Segoe UI", _scale(9,  _UI), "underline")
FONT_SMALL = ("Segoe UI", _scale(9,  _UI))
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".image_merger_config.json")

DEFAULT_MODEL  = "gemini-2.0-flash-lite"
DEFAULT_PROMPT = "Опиши подробно что изображено на этой картинке на русском языке."

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)

# Только бесплатные модели
KNOWN_MODELS = [
    "gemini-2.0-flash-lite",   # самый быстрый, высокий бесплатный лимит
    "gemini-2.0-flash",        # быстрый, универсальный
    "gemini-flash-latest",     # всегда последняя Flash
]


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def friendly_api_error(e: Exception, model: str) -> str:
    msg = str(e)
    if hasattr(e, "code"):
        code = e.code
        try:
            body = e.read().decode("utf-8", errors="replace")
            err_json = json.loads(body)
            api_msg = (err_json.get("error", {}).get("message", "")
                       or err_json.get("message", ""))
        except Exception:
            api_msg = ""
        if code == 400:
            return f"❌ Ошибка 400 — Неверный запрос.\n\n{api_msg or 'Проверьте правильность промпта и формат данных.'}"
        if code == 401:
            return ("❌ Ошибка 401 — API ключ недействителен или отсутствует.\n\n"
                    "Проверьте ключ и попробуйте снова.\nПолучить ключ: aistudio.google.com/apikey")
        if code == 403:
            return (f"❌ Ошибка 403 — Доступ запрещён.\n\nВозможные причины:\n"
                    f"• API ключ не имеет прав на эту модель\n• Модель недоступна в вашем регионе\n"
                    f"• Текущая модель: {model}")
        if code == 404:
            return (f"❌ Ошибка 404 — Модель не найдена: «{model}»\n\nЧто можно сделать:\n"
                    "• Нажмите кнопку ✏ Модель и выберите другую\n"
                    "• Проверьте правильность названия модели\n"
                    "• Список доступных моделей: ai.google.dev/gemini-api/docs/models")
        if code == 429:
            return ("❌ Ошибка 429 — Превышен лимит запросов.\n\n"
                    "Подождите немного и попробуйте снова.\nИли используйте другой API ключ.")
        if code == 500:
            return "❌ Ошибка 500 — Внутренняя ошибка сервера Google.\n\nПопробуйте позже."
        if code == 503:
            return "❌ Ошибка 503 — Сервис временно недоступен.\n\nПопробуйте через несколько минут."
        return f"❌ HTTP ошибка {code}.\n\n{api_msg or msg}"
    if "timed out" in msg.lower() or "timeout" in msg.lower():
        return "❌ Превышено время ожидания ответа от сервера.\n\nПроверьте интернет-соединение."
    if "name or service not known" in msg.lower() or "getaddrinfo" in msg.lower():
        return "❌ Не удалось подключиться к серверам Google.\n\nПроверьте интернет-соединение."
    return f"❌ Неожиданная ошибка:\n\n{msg}"


def describe_image_gemini(api_key: str, model: str, prompt: str,
                          pil_img: Image.Image) -> str:
    buf = io.BytesIO()
    pil_img.convert("RGB").save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()
    payload = json.dumps({
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64}}
            ]
        }]
    }).encode()
    url = GEMINI_URL.format(model=model, key=api_key)
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ── Context menu mixin ─────────────────────────────────────────────────────────
def attach_context_menu(widget, is_text_widget=False):
    """Attach right-click context menu + toolbar support to Entry or Text widget."""

    def _copy(event=None):
        try:
            widget.event_generate("<<Copy>>")
        except Exception:
            pass

    def _cut(event=None):
        try:
            widget.event_generate("<<Cut>>")
        except Exception:
            pass

    def _paste(event=None):
        try:
            widget.event_generate("<<Paste>>")
        except Exception:
            pass

    def _select_all(event=None):
        if is_text_widget:
            widget.tag_add(tk.SEL, "1.0", tk.END)
            widget.mark_set(tk.INSERT, tk.END)
        else:
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)
        return "break"

    def _show_menu(event):
        menu = tk.Menu(widget, tearoff=0, font=FONT)
        menu.add_command(label="✂  Вырезать",    command=_cut)
        menu.add_command(label="📋  Копировать",  command=_copy)
        menu.add_command(label="📌  Вставить",    command=_paste)
        menu.add_separator()
        menu.add_command(label="☰  Выделить всё", command=_select_all)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    widget.bind("<Button-3>", _show_menu)
    widget.bind("<Control-a>", _select_all)
    widget.bind("<Control-A>", _select_all)
    # Ctrl+V / Ctrl+C / Ctrl+X are already handled natively by tkinter,
    # but we bind them explicitly for Entry widgets with show="●"
    if not is_text_widget:
        def _paste_entry(event):
            try:
                text = widget.clipboard_get()
                try:
                    sel_start = widget.index(tk.SEL_FIRST)
                    sel_end   = widget.index(tk.SEL_LAST)
                    widget.delete(sel_start, sel_end)
                except tk.TclError:
                    pass
                widget.insert(tk.INSERT, text)
            except tk.TclError:
                pass
            return "break"
        widget.bind("<Control-v>", _paste_entry)
        widget.bind("<Control-V>", _paste_entry)

    return {"copy": _copy, "cut": _cut, "paste": _paste, "select_all": _select_all}


# ── Edit toolbar ───────────────────────────────────────────────────────────────
def make_edit_toolbar(parent, widget, is_text_widget=False):
    """Create a small Copy/Cut/Paste/Select All toolbar row."""
    ops = attach_context_menu(widget, is_text_widget)
    bar = tk.Frame(parent, bg="#f0f0f0")

    btn_cfg = dict(font=FONT_SMALL, relief="flat", pady=2, padx=8,
                   bg="#e9ecef", activebackground="#dee2e6")
    tk.Button(bar, text="✂ Вырезать",    command=ops["cut"],        **btn_cfg).pack(side="left", padx=(0, 2))
    tk.Button(bar, text="📋 Копировать",  command=ops["copy"],       **btn_cfg).pack(side="left", padx=(0, 2))
    tk.Button(bar, text="📌 Вставить",    command=ops["paste"],      **btn_cfg).pack(side="left", padx=(0, 2))
    tk.Button(bar, text="☰ Выделить всё", command=ops["select_all"], **btn_cfg).pack(side="left")
    return bar


# ── Prompt dialog ──────────────────────────────────────────────────────────────
class PromptDialog(tk.Toplevel):
    def __init__(self, parent, current_prompt: str):
        super().__init__(parent)
        self.title("Редактировать промпт")
        self.resizable(True, True)
        self.result = None
        self.grab_set()
        self.configure(bg="#f0f0f0")

        tk.Label(self, text="Промпт для Gemini:", font=FONT_BIG,
                 bg="#f0f0f0").pack(anchor="w", padx=12, pady=(12, 4))

        self.text = tk.Text(self, font=FONT, width=60, height=8,
                            relief="solid", bd=1, wrap="word")
        self.text.pack(fill="both", expand=True, padx=12, pady=4)
        self.text.insert("1.0", current_prompt)

        tb = make_edit_toolbar(self, self.text, is_text_widget=True)
        tb.pack(fill="x", padx=12, pady=(0, 4))

        btn_row = tk.Frame(self, bg="#f0f0f0")
        btn_row.pack(fill="x", padx=12, pady=(4, 12))
        tk.Button(btn_row, text="Сохранить", font=FONT_BIG,
                  bg="#4a90d9", fg="white", relief="flat", pady=4, padx=20,
                  command=self._ok).pack(side="right", padx=(6, 0))
        tk.Button(btn_row, text="Отмена", font=FONT,
                  bg="#6c757d", fg="white", relief="flat", pady=4, padx=16,
                  command=self.destroy).pack(side="right")
        self._center(parent)

    def _ok(self):
        self.result = self.text.get("1.0", "end").strip()
        self.destroy()

    def _center(self, parent):
        self.update_idletasks()
        px = parent.winfo_x() + parent.winfo_width() // 2
        py = parent.winfo_y() + parent.winfo_height() // 2
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px - w // 2}+{py - h // 2}")


# ── Model dialog ───────────────────────────────────────────────────────────────
class ModelDialog(tk.Toplevel):
    def __init__(self, parent, current_model: str):
        super().__init__(parent)
        self.title("Выбор модели Gemini")
        self.resizable(True, True)
        self.result = None
        self.grab_set()
        self.configure(bg="#f0f0f0")

        tk.Label(self, text="Выберите модель (только бесплатные):", font=FONT_BIG,
                 bg="#f0f0f0").pack(anchor="w", padx=12, pady=(12, 4))

        self.var = tk.StringVar(value=current_model if current_model in KNOWN_MODELS else KNOWN_MODELS[0])
        for m in KNOWN_MODELS:
            tk.Radiobutton(self, text=m, variable=self.var, value=m,
                           font=FONT, bg="#f0f0f0", anchor="w",
                           activebackground="#e0e0e0").pack(fill="x", padx=20, pady=1)

        tk.Label(self, text="Или введите вручную:", font=FONT,
                 bg="#f0f0f0").pack(anchor="w", padx=12, pady=(8, 2))

        custom_frame = tk.Frame(self, bg="#f0f0f0")
        custom_frame.pack(fill="x", padx=12, pady=(0, 4))
        self.custom = tk.Entry(custom_frame, font=FONT, relief="solid", bd=1, width=40)
        self.custom.pack(fill="x")
        self.custom.bind("<FocusIn>", lambda e: self.var.set(""))
        attach_context_menu(self.custom)

        tb = make_edit_toolbar(self, self.custom)
        tb.pack(fill="x", padx=12, pady=(0, 4))

        btn_row = tk.Frame(self, bg="#f0f0f0")
        btn_row.pack(fill="x", padx=12, pady=(4, 12))
        tk.Button(btn_row, text="Применить", font=FONT_BIG,
                  bg="#4a90d9", fg="white", relief="flat", pady=4, padx=20,
                  command=self._ok).pack(side="right", padx=(6, 0))
        tk.Button(btn_row, text="Отмена", font=FONT,
                  bg="#6c757d", fg="white", relief="flat", pady=4, padx=16,
                  command=self.destroy).pack(side="right")

        tk.Label(self, text="Список моделей: ai.google.dev/gemini-api/docs/models",
                 font=("Segoe UI", 8), fg="#888", bg="#f0f0f0").pack(pady=(0, 6))
        self._center(parent)

    def _ok(self):
        custom = self.custom.get().strip()
        self.result = custom if custom else self.var.get()
        self.destroy()

    def _center(self, parent):
        self.update_idletasks()
        px = parent.winfo_x() + parent.winfo_width() // 2
        py = parent.winfo_y() + parent.winfo_height() // 2
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px - w // 2}+{py - h // 2}")


# ── Main app ───────────────────────────────────────────────────────────────────
class ImageMerger(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Merger")
        self.resizable(True, True)
        self.configure(bg="#f0f0f0")

        self.pil_images  = [None, None]
        self.tk_previews = [None, None]
        self.img_names   = ["", ""]
        self.result_pil  = None
        self.result_tk   = None
        self.direction   = tk.StringVar(value="horizontal")
        self._config     = load_config()

        saved_model = self._config.get("gemini_model", DEFAULT_MODEL)
        # Reset if saved model is not in free list
        self._model  = saved_model if saved_model in KNOWN_MODELS else DEFAULT_MODEL
        self._prompt = self._config.get("gemini_prompt", DEFAULT_PROMPT)

        # Divider settings
        self._divider_enabled = tk.BooleanVar(value=self._config.get("divider_enabled", False))
        self._divider_color   = self._config.get("divider_color", "#000000")
        self._divider_width   = tk.IntVar(value=self._config.get("divider_width", 4))

        # Compression settings
        self._compress_enabled = tk.BooleanVar(value=self._config.get("compress_enabled", False))
        self._compress_quality = tk.IntVar(value=self._config.get("compress_quality", 85))

        self._build_ui()
        self._restore_window()

        saved_key = self._config.get("gemini_api_key", "")
        if saved_key:
            self.api_key_var.set(saved_key)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        container = tk.Frame(self, bg="#f0f0f0")
        container.pack(fill="both", expand=True)

        vsb = tk.Scrollbar(container, orient="vertical")
        hsb = tk.Scrollbar(container, orient="horizontal")
        sc = tk.Canvas(container, bg="#f0f0f0", highlightthickness=0,
                       yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=sc.yview)
        hsb.config(command=sc.xview)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        sc.pack(side="left", fill="both", expand=True)

        main_frame = tk.Frame(sc, bg="#f0f0f0")
        self._scroll_win = sc.create_window((0, 0), window=main_frame, anchor="nw")

        def _on_canvas_resize(e):
            fw = main_frame.winfo_reqwidth()
            fh = main_frame.winfo_reqheight()
            x = max(0, (e.width - fw) // 2)
            y = max(0, (e.height - fh) // 2)
            sc.coords(self._scroll_win, x, y)

        sc.bind("<Configure>", _on_canvas_resize)
        main_frame.bind("<Configure>", lambda e: sc.configure(scrollregion=sc.bbox("all")))
        sc.bind_all("<MouseWheel>", lambda e: sc.yview_scroll(int(-1*(e.delta/120)), "units"))

        # ── LEFT ──────────────────────────────────────────────────────────────
        left = tk.Frame(main_frame, bg="#f0f0f0")
        left.pack(side="left", fill="y", padx=(0, 8))

        slots = tk.Frame(left, bg="#f0f0f0")
        slots.pack()
        self.canvases = []
        for i in range(2):
            col = tk.Frame(slots, bg="#f0f0f0")
            col.pack(side="left", padx=6)
            tk.Label(col, text=f"Изображение {i+1}", font=FONT_BIG,
                     bg="#f0f0f0").pack(pady=(0, 4))
            c = tk.Canvas(col, width=PREVIEW_W, height=PREVIEW_H,
                          bg="white", relief="solid", bd=1, cursor="hand2")
            c.pack()
            self._placeholder(c)
            c.bind("<Button-1>", lambda e, idx=i: self._load(idx))
            self.canvases.append(c)
            tk.Button(col, text="Выбрать файл", font=FONT, width=18, pady=4,
                      command=lambda idx=i: self._load(idx)).pack(pady=6)

        # Direction
        dir_frame = tk.Frame(left, bg="#f0f0f0")
        dir_frame.pack(pady=4)
        tk.Label(dir_frame, text="Направление склейки:", font=FONT_BIG,
                 bg="#f0f0f0").pack(side="left", padx=(0, 10))
        for txt, val in [("Горизонтально", "horizontal"), ("Вертикально", "vertical")]:
            tk.Radiobutton(dir_frame, text=txt, font=FONT,
                           variable=self.direction, value=val,
                           bg="#f0f0f0", indicatoron=0, width=16, pady=5,
                           selectcolor="#4a90d9", activebackground="#4a90d9",
                           fg="black").pack(side="left", padx=4)

        # ── Divider settings ──────────────────────────────────────────────────
        div_frame = tk.LabelFrame(left, text="Разделитель между картинками",
                                  font=FONT, bg="#f0f0f0", relief="groove", bd=1)
        div_frame.pack(fill="x", pady=(4, 2), padx=2)

        div_top = tk.Frame(div_frame, bg="#f0f0f0")
        div_top.pack(fill="x", padx=8, pady=(4, 2))

        tk.Checkbutton(div_top, text="Добавить линию-разделитель",
                       variable=self._divider_enabled, font=FONT,
                       bg="#f0f0f0", activebackground="#f0f0f0",
                       command=self._update_divider_state).pack(side="left")

        div_opts = tk.Frame(div_frame, bg="#f0f0f0")
        div_opts.pack(fill="x", padx=8, pady=(0, 6))

        tk.Label(div_opts, text="Толщина:", font=FONT, bg="#f0f0f0").pack(side="left")
        self._div_width_spin = tk.Spinbox(div_opts, textvariable=self._divider_width,
                                          from_=1, to=50, width=5, font=FONT,
                                          relief="solid", bd=1)
        self._div_width_spin.pack(side="left", padx=(4, 12))

        tk.Label(div_opts, text="px", font=FONT, bg="#f0f0f0").pack(side="left", padx=(0, 12))

        self._div_color_btn = tk.Button(div_opts, text="  Цвет  ", font=FONT,
                                        bg=self._divider_color, relief="solid", bd=1,
                                        command=self._pick_divider_color)
        self._div_color_btn.pack(side="left", padx=(0, 8))

        self._div_color_lbl = tk.Label(div_opts, text=self._divider_color,
                                       font=FONT_SMALL, bg="#f0f0f0", fg="#555")
        self._div_color_lbl.pack(side="left")

        self._update_divider_state()

        # ── Compression settings ──────────────────────────────────────────────
        comp_frame = tk.LabelFrame(left, text="Сжатие выходного изображения",
                                   font=FONT, bg="#f0f0f0", relief="groove", bd=1)
        comp_frame.pack(fill="x", pady=(4, 2), padx=2)

        comp_top = tk.Frame(comp_frame, bg="#f0f0f0")
        comp_top.pack(fill="x", padx=8, pady=(4, 2))

        tk.Checkbutton(comp_top, text="Сохранять как JPEG со сжатием",
                       variable=self._compress_enabled, font=FONT,
                       bg="#f0f0f0", activebackground="#f0f0f0",
                       command=self._update_compress_state).pack(side="left")

        comp_opts = tk.Frame(comp_frame, bg="#f0f0f0")
        comp_opts.pack(fill="x", padx=8, pady=(0, 2))

        tk.Label(comp_opts, text="Качество:", font=FONT, bg="#f0f0f0").pack(side="left")

        self._quality_scale = tk.Scale(comp_opts, variable=self._compress_quality,
                                       from_=10, to=100, orient="horizontal",
                                       length=160, font=FONT_SMALL,
                                       bg="#f0f0f0", highlightthickness=0,
                                       command=self._update_quality_label)
        self._quality_scale.pack(side="left", padx=(6, 4))

        self._quality_lbl = tk.Label(comp_opts, font=FONT, bg="#f0f0f0", width=4,
                                     text=f"{self._compress_quality.get()}%")
        self._quality_lbl.pack(side="left")

        comp_info = tk.Frame(comp_frame, bg="#f0f0f0")
        comp_info.pack(fill="x", padx=8, pady=(0, 6))
        self._comp_info_lbl = tk.Label(comp_info, font=FONT_SMALL, bg="#f0f0f0",
                                       fg="#555", text=self._get_quality_hint(self._compress_quality.get()))
        self._comp_info_lbl.pack(side="left")

        self._update_compress_state()

        # Merge button
        tk.Button(left, text="Склеить изображения", font=FONT_BIG,
                  bg="#4a90d9", fg="white", activebackground="#357abd",
                  relief="flat", pady=8, width=30,
                  command=self._merge).pack(pady=6)

        # Result
        tk.Label(left, text="Результат:", font=FONT_BIG,
                 bg="#f0f0f0").pack(anchor="w", pady=(4, 2))
        self.result_canvas = tk.Canvas(left, width=PREVIEW_W * 2 + 20,
                                       height=PREVIEW_H, bg="white",
                                       relief="solid", bd=1)
        self.result_canvas.pack()
        self._placeholder(self.result_canvas, "Здесь появится результат")

        # File info label
        self._file_info_lbl = tk.Label(left, text="", font=FONT_SMALL,
                                        fg="#555", bg="#f0f0f0")
        self._file_info_lbl.pack(anchor="w")

        # Save row
        save_row = tk.Frame(left, bg="#f0f0f0")
        save_row.pack(fill="x", pady=6)
        tk.Label(save_row, text="Имя файла:", font=FONT, bg="#f0f0f0").pack(side="left")
        self.filename_var = tk.StringVar(value="result")
        filename_entry = tk.Entry(save_row, textvariable=self.filename_var,
                                  font=FONT, width=28, relief="solid", bd=1)
        filename_entry.pack(side="left", padx=8)
        attach_context_menu(filename_entry)

        self._ext_lbl = tk.Label(save_row, text=".png", font=FONT, bg="#f0f0f0")
        self._ext_lbl.pack(side="left")
        tk.Button(save_row, text="Сохранить", font=FONT_BIG,
                  bg="#5cb85c", fg="white", activebackground="#449d44",
                  relief="flat", pady=4, padx=18,
                  command=self._save).pack(side="left", padx=12)

        # ── SEPARATOR ─────────────────────────────────────────────────────────
        tk.Frame(main_frame, bg="#cccccc", width=1).pack(side="left", fill="y", padx=8)

        # ── RIGHT ─────────────────────────────────────────────────────────────
        right = tk.Frame(main_frame, bg="#f0f0f0")
        right.pack(side="left", fill="both", expand=True)

        desc_header = tk.Frame(right, bg="#f0f0f0")
        desc_header.pack(fill="x", pady=(0, 4))
        tk.Label(desc_header, text="Описание (Gemini AI):", font=FONT_BIG,
                 bg="#f0f0f0").pack(side="left")
        tk.Button(desc_header, text="Копировать", font=FONT,
                  bg="#6c757d", fg="white", activebackground="#545b62",
                  relief="flat", pady=3, padx=12,
                  command=self._copy_desc).pack(side="right")

        # API key
        tk.Label(right, text="Gemini API ключ:", font=FONT,
                 bg="#f0f0f0", anchor="w").pack(fill="x", pady=(0, 2))

        key_row = tk.Frame(right, bg="#f0f0f0")
        key_row.pack(fill="x", pady=(0, 2))

        self.api_key_var = tk.StringVar()
        self.api_key_entry = tk.Entry(key_row, textvariable=self.api_key_var,
                                      font=FONT, relief="solid", bd=1, show="●")
        self.api_key_entry.pack(side="left", fill="x", expand=True)
        attach_context_menu(self.api_key_entry)

        self._key_hidden = True
        self.toggle_btn = tk.Button(key_row, text="👁", font=("Segoe UI", 11),
                                    bg="#f0f0f0", relief="flat", padx=6,
                                    command=self._toggle_key_visibility)
        self.toggle_btn.pack(side="left", padx=(4, 0))

        # Toolbar for API key entry
        key_tb = make_edit_toolbar(right, self.api_key_entry)
        key_tb.pack(fill="x", pady=(2, 4))

        # Link
        link_row = tk.Frame(right, bg="#f0f0f0")
        link_row.pack(fill="x", pady=(0, 8))
        tk.Label(link_row, text="Получить бесплатный ключ: ",
                 font=("Segoe UI", 9), fg="#555555", bg="#f0f0f0").pack(side="left")
        link = tk.Label(link_row, text="aistudio.google.com/apikey",
                        font=FONT_LINK, fg="#1a73e8", bg="#f0f0f0", cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/apikey"))
        link.bind("<Enter>", lambda e: link.configure(fg="#0b47a1"))
        link.bind("<Leave>", lambda e: link.configure(fg="#1a73e8"))

        # Model + Prompt
        settings_row = tk.Frame(right, bg="#f0f0f0")
        settings_row.pack(fill="x", pady=(0, 8))
        tk.Button(settings_row, text="✏  Модель", font=FONT,
                  bg="#6c757d", fg="white", activebackground="#545b62",
                  relief="flat", pady=5, padx=14,
                  command=self._edit_model).pack(side="left", padx=(0, 6))
        tk.Button(settings_row, text="✏  Промпт", font=FONT,
                  bg="#6c757d", fg="white", activebackground="#545b62",
                  relief="flat", pady=5, padx=14,
                  command=self._edit_prompt).pack(side="left")

        self.model_label = tk.Label(right, font=("Segoe UI", 9), fg="#555",
                                    bg="#f0f0f0", anchor="w")
        self.model_label.pack(fill="x", pady=(0, 4))
        self._refresh_model_label()

        tk.Button(right, text="▶  Описать изображение", font=FONT_BIG,
                  bg="#e8a020", fg="white", activebackground="#c7871a",
                  relief="flat", pady=8,
                  command=self._describe).pack(fill="x", pady=(0, 4))

        # Desc text toolbar
        self.desc_text = tk.Text(right, font=FONT, height=16,
                                 relief="solid", bd=1, wrap="word",
                                 state="disabled", bg="white")

        desc_tb = make_edit_toolbar(right, self.desc_text, is_text_widget=True)
        desc_tb.pack(fill="x", pady=(0, 2))

        self.desc_text.pack(fill="both", expand=True)

    # ── Divider helpers ────────────────────────────────────────────────────────
    def _update_divider_state(self):
        state = "normal" if self._divider_enabled.get() else "disabled"
        if hasattr(self, "_div_width_spin"):
            self._div_width_spin.configure(state=state)
        if hasattr(self, "_div_color_btn"):
            self._div_color_btn.configure(state=state)

    def _pick_divider_color(self):
        color = colorchooser.askcolor(color=self._divider_color,
                                      title="Цвет разделителя")[1]
        if color:
            self._divider_color = color
            self._div_color_btn.configure(bg=color)
            self._div_color_lbl.configure(text=color)

    # ── Compression helpers ────────────────────────────────────────────────────
    def _update_compress_state(self):
        state = "normal" if self._compress_enabled.get() else "disabled"
        if hasattr(self, "_quality_scale"):
            self._quality_scale.configure(state=state)
        ext = ".jpg" if self._compress_enabled.get() else ".png"
        if hasattr(self, "_ext_lbl"):
            self._ext_lbl.configure(text=ext)

    def _get_quality_hint(self, q: int) -> str:
        q = int(q)
        if q >= 90: return f"Качество {q}% — минимальные потери, большой файл"
        if q >= 75: return f"Качество {q}% — хороший баланс размера и качества"
        if q >= 50: return f"Качество {q}% — заметные артефакты, малый файл"
        return f"Качество {q}% — сильное сжатие, низкое качество"

    def _update_quality_label(self, val=None):
        q = self._compress_quality.get()
        self._quality_lbl.configure(text=f"{q}%")
        self._comp_info_lbl.configure(text=self._get_quality_hint(q))

    # ── misc helpers ───────────────────────────────────────────────────────────
    def _refresh_model_label(self):
        self.model_label.configure(text=f"Модель: {self._model}")

    def _placeholder(self, canvas, text="Нажмите для выбора"):
        w, h = int(canvas["width"]), int(canvas["height"])
        canvas.delete("all")
        canvas.create_text(w // 2, h // 2, text=text, fill="#aaaaaa", font=FONT)

    def _show_preview(self, canvas, pil_img):
        w, h = int(canvas["width"]), int(canvas["height"])
        img = pil_img.copy()
        img.thumbnail((w - 4, h - 4), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img)
        canvas.delete("all")
        canvas.create_image(w // 2, h // 2, anchor="center", image=tk_img)
        return tk_img

    def _update_filename(self):
        n1 = os.path.splitext(self.img_names[0])[0] if self.img_names[0] else ""
        n2 = os.path.splitext(self.img_names[1])[0] if self.img_names[1] else ""
        if n1 and n2:
            self.filename_var.set(f"{n1} + {n2}")
        elif n1:
            self.filename_var.set(n1)

    def _set_desc(self, text):
        self.desc_text.configure(state="normal")
        self.desc_text.delete("1.0", "end")
        self.desc_text.insert("end", text)
        self.desc_text.configure(state="disabled")

    def _toggle_key_visibility(self):
        self._key_hidden = not self._key_hidden
        self.api_key_entry.configure(show="●" if self._key_hidden else "")
        self.toggle_btn.configure(text="👁" if self._key_hidden else "🙈")

    def _do_save_config(self):
        self._config["gemini_api_key"]   = self.api_key_var.get().strip()
        self._config["gemini_model"]     = self._model
        self._config["gemini_prompt"]    = self._prompt
        self._config["divider_enabled"]  = self._divider_enabled.get()
        self._config["divider_color"]    = self._divider_color
        self._config["divider_width"]    = self._divider_width.get()
        self._config["compress_enabled"] = self._compress_enabled.get()
        self._config["compress_quality"] = self._compress_quality.get()
        save_config(self._config)

    def _on_close(self):
        self._save_window()
        self._do_save_config()
        self.destroy()

    def _edit_model(self):
        dlg = ModelDialog(self, self._model)
        self.wait_window(dlg)
        if dlg.result:
            self._model = dlg.result
            self._refresh_model_label()

    def _edit_prompt(self):
        dlg = PromptDialog(self, self._prompt)
        self.wait_window(dlg)
        if dlg.result is not None:
            self._prompt = dlg.result if dlg.result else DEFAULT_PROMPT

    # ── Logic ─────────────────────────────────────────────────────────────────
    def _load(self, idx):
        path = filedialog.askopenfilename(
            title=f"Выберите изображение {idx + 1}",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp"),
                       ("Все файлы", "*.*")]
        )
        if not path:
            return
        try:
            img = Image.open(path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{e}")
            return
        self.pil_images[idx]  = img
        self.img_names[idx]   = os.path.basename(path)
        self.tk_previews[idx] = self._show_preview(self.canvases[idx], img)
        self._update_filename()

    def _merge(self):
        if None in self.pil_images:
            messagebox.showwarning("Нет изображений", "Загрузите оба изображения.")
            return

        a, b = self.pil_images
        div_on    = self._divider_enabled.get()
        div_w     = max(1, self._divider_width.get()) if div_on else 0
        div_color = self._divider_color

        if self.direction.get() == "horizontal":
            h   = max(a.height, b.height)
            a_r = a.resize((int(a.width * h / a.height), h), Image.LANCZOS)
            b_r = b.resize((int(b.width * h / b.height), h), Image.LANCZOS)
            total_w = a_r.width + b_r.width + div_w
            out = Image.new("RGBA", (total_w, h), (0, 0, 0, 0))
            out.paste(a_r, (0, 0))
            if div_on and div_w > 0:
                draw = ImageDraw.Draw(out)
                r, g, bl = int(div_color[1:3], 16), int(div_color[3:5], 16), int(div_color[5:7], 16)
                draw.rectangle([a_r.width, 0, a_r.width + div_w - 1, h - 1],
                                fill=(r, g, bl, 255))
            out.paste(b_r, (a_r.width + div_w, 0))
        else:
            w   = max(a.width, b.width)
            a_r = a.resize((w, int(a.height * w / a.width)), Image.LANCZOS)
            b_r = b.resize((w, int(b.height * w / b.width)), Image.LANCZOS)
            total_h = a_r.height + b_r.height + div_w
            out = Image.new("RGBA", (w, total_h), (0, 0, 0, 0))
            out.paste(a_r, (0, 0))
            if div_on and div_w > 0:
                draw = ImageDraw.Draw(out)
                r, g, bl = int(div_color[1:3], 16), int(div_color[3:5], 16), int(div_color[5:7], 16)
                draw.rectangle([0, a_r.height, w - 1, a_r.height + div_w - 1],
                                fill=(r, g, bl, 255))
            out.paste(b_r, (0, a_r.height + div_w))

        self.result_pil = out
        self.result_tk  = self._show_preview(self.result_canvas, out)
        self._update_file_info()

    def _update_file_info(self):
        if self.result_pil is None:
            self._file_info_lbl.configure(text="")
            return
        w, h = self.result_pil.size
        # Estimate size
        if self._compress_enabled.get():
            buf = io.BytesIO()
            self.result_pil.convert("RGB").save(buf, format="JPEG",
                                                quality=self._compress_quality.get())
            size_kb = len(buf.getvalue()) / 1024
            fmt = "JPEG"
        else:
            buf = io.BytesIO()
            self.result_pil.save(buf, format="PNG")
            size_kb = len(buf.getvalue()) / 1024
            fmt = "PNG"
        if size_kb >= 1024:
            size_str = f"{size_kb / 1024:.1f} МБ"
        else:
            size_str = f"{size_kb:.0f} КБ"
        self._file_info_lbl.configure(
            text=f"Размер: {w}×{h} пикс. | Формат: {fmt} | ~{size_str}"
        )

    def _describe(self):
        if self.result_pil is None:
            messagebox.showwarning("Нет результата", "Сначала склейте изображения.")
            return
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("API ключ",
                                   "Введите Gemini API ключ.\n"
                                   "Получить бесплатно: aistudio.google.com/apikey")
            return

        self._set_desc("⏳ Описываю изображение...")
        self.update()
        model  = self._model
        prompt = self._prompt

        def worker():
            try:
                result = describe_image_gemini(api_key, model, prompt, self.result_pil)
                self.after(0, self._do_save_config)
                self.after(0, self._set_desc, result)
            except Exception as e:
                err_text = friendly_api_error(e, model)
                self.after(0, self._set_desc, err_text)

        threading.Thread(target=worker, daemon=True).start()

    def _copy_desc(self):
        text = self.desc_text.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def _save(self):
        if self.result_pil is None:
            messagebox.showwarning("Нет результата", "Сначала склейте изображения.")
            return

        use_jpeg = self._compress_enabled.get()
        quality  = self._compress_quality.get()
        name     = self.filename_var.get().strip() or "result"
        default_ext = ".jpg" if use_jpeg else ".png"

        path = filedialog.asksaveasfilename(
            title="Сохранить изображение",
            initialfile=name,
            defaultextension=default_ext,
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"), ("Все файлы", "*.*")]
                       if use_jpeg else
                       [("PNG", "*.png"), ("JPEG", "*.jpg"), ("Все файлы", "*.*")]
        )
        if not path:
            return
        try:
            img = self.result_pil
            if path.lower().endswith((".jpg", ".jpeg")) or use_jpeg:
                img = img.convert("RGB")
                img.save(path, format="JPEG", quality=quality, optimize=True)
            else:
                img.save(path, format="PNG", optimize=True)
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", str(e))

    def _restore_window(self):
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        geo = self._config.get("window_geometry")
        if geo:
            self.geometry(geo)
        else:
            self.geometry(f"{screen_w}x{screen_h}+0+0")

    def _save_window(self):
        self._config["window_geometry"] = self.geometry()


if __name__ == "__main__":
    ImageMerger().mainloop()