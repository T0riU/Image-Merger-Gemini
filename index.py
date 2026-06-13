import sys
import os
import io
import json
import math
import base64
import urllib.request

from PySide6.QtCore import Qt, QThread, Signal, QMimeData
from PySide6.QtGui import QPixmap, QImage, QColor, QAction, QIcon, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QFileDialog,
    QMessageBox, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton,
    QButtonGroup, QCheckBox, QSpinBox, QSlider, QLineEdit, QTextEdit, QDialog,
    QColorDialog, QScrollArea, QFrame, QGridLayout, QSizePolicy, QComboBox
)

from PIL import Image, ImageDraw

try:
    from deep_translator import GoogleTranslator
    DEEP_TRANSLATOR_AVAILABLE = True
except ImportError:
    DEEP_TRANSLATOR_AVAILABLE = False


# ── Constants ────────────────────────────────────────────────────────────────
CONFIG_PATH  = os.path.join(os.path.expanduser("~"), ".image_merger_config.json")
def _resource(rel):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

FAVICON_PATH = _resource(os.path.join("img", "favicon.ico"))
MAX_IMAGES   = 10

DEFAULT_MODEL = "gemini-2.0-flash-lite"
GEMINI_URL    = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
GEMINI_LIST_URL = "https://generativelanguage.googleapis.com/v1beta/models?key={key}&pageSize=200"
VISION_METHODS  = {"generateContent", "streamGenerateContent"}

# No hardcoded fallback models — list is populated only after API fetch
FALLBACK_MODELS: list[str] = []

# Languages available for translation (display name → deep-translator code)
TRANSLATE_LANGUAGES = {
    "English":             "en",
    "Русский":             "ru",
    "Deutsch":             "de",
    "Français":            "fr",
    "Español":             "es",
    "Italiano":            "it",
    "Português":           "pt",
    "Polski":              "pl",
    "Nederlands":          "nl",
    "Українська":          "uk",
    "Türkçe":              "tr",
    "العربية":             "ar",
    "中文 (简体)":          "zh-CN",
    "中文 (繁體)":          "zh-TW",
    "日本語":              "ja",
    "한국어":              "ko",
    "हिन्दी":              "hi",
    "Беларуская":          "be",
    "Čeština":             "cs",
    "Svenska":             "sv",
    "Norsk":               "no",
    "Suomi":               "fi",
    "Dansk":               "da",
    "Magyar":              "hu",
    "Română":              "ro",
    "Ελληνικά":            "el",
    "Bahasa Indonesia":    "id",
    "Tiếng Việt":          "vi",
    "ภาษาไทย":             "th",
}
# Separator marker stored inside the description text to split original from translation
_TRANSLATE_SEP = "\n\n─────────────────────\n"


# ── i18n ─────────────────────────────────────────────────────────────────────
STRINGS = {
    "en": {
        "window_title":        "Image Merger",
        "images_panel":        "Images (drag to reorder)",
        "add_images":          "+ Add images",
        "clear_all":           "Clear all",
        "merge_settings":      "Merge settings",
        "mode":                "Mode:",
        "mode_horizontal":     "Horizontal strip",
        "mode_vertical":       "Vertical strip",
        "mode_grid":           "Grid",
        "grid_cols":           "Columns:",
        "grid_padding":        "Padding:",
        "grid_bg":             "Background:",
        "cell_align":          "Cell align:",
        "align_fill":          "Fill",
        "align_fit":           "Fit",
        "divider":             "Divider",
        "thickness":           "Thickness:",
        "px":                  "px",
        "color_btn":           "  Color  ",
        "jpeg_compress":       "JPEG compression",
        "quality":             "Quality:",
        "merge_btn":           "Merge images",
        "result":              "Result:",
        "result_placeholder":  "Result will appear here",
        "save_btn":            "Save",
        "description_gemini":  "Description (Gemini AI):",
        "copy_btn":            "Copy",
        "extra_prompt_label":  "Extra context (optional):",
        "extra_prompt_hint":   "Additional details sent with the main prompt…",
        "describe_btn":        "▶  Describe image",
        "no_images":           "No images",
        "load_images":         "Please add at least 2 images.",
        "no_result":           "No result",
        "merge_first":         "Please merge images first.",
        "api_key_missing":     "API key",
        "enter_api_key":       "Enter a Gemini API key.\nGet one free at: aistudio.google.com/apikey",
        "describing":          "⏳ Describing image…",
        "error_open":          "Error",
        "failed_open":         "Failed to open file:\n{}",
        "save_error":          "Save error",
        "quality_90":          "Quality {}% — minimal loss, large file",
        "quality_75":          "Quality {}% — good size/quality balance",
        "quality_50":          "Quality {}% — noticeable artifacts, small file",
        "quality_low":         "Quality {}% — heavy compression, low quality",
        "size_info":           "Size: {}×{} px | Format: {} | ~{}",
        "mb":                  "{:.1f} MB",
        "kb":                  "{:.0f} KB",
        "model_current":       "Model: {}",
        "cancel":              "Cancel",
        "save":                "Save",
        "apply":               "Apply",
        "menu_language":       "Language",
        "menu_model":          "Model…",
        "menu_api_key":        "API key…",
        "menu_prompt":         "Main prompt…",
        "menu_translator":     "Translator",
        "menu_translator_provider": "Provider…",
        "model_title":         "Select Gemini model",
        "model_free_label":    "Select a model (vision-capable, free tier):",
        "model_custom_label":  "Or enter manually:",
        "model_fetch_btn":     "Fetch models from API…",
        "model_fetching":      "Fetching…",
        "model_fetch_ok":      "Loaded {} vision models.",
        "model_fetch_err":     "Error: {}",
        "models_link":         "Model list: ai.google.dev/gemini-api/docs/models",
        "prompt_title":        "Main prompt",
        "prompt_label":        "Prompt sent to Gemini with every request:",
        "apikey_title":        "Gemini API key",
        "apikey_label":        "Enter your API key (stored locally):",
        "apikey_link":         "Get a free key at aistudio.google.com/apikey",
        "translate_to":        "Translate to:",
        "translate_btn":       "🌐  Translate",
        "translating":         "⏳ Translating…",
        "no_text_to_translate":"No text to translate. Describe the image first.",
        "translate_error":     "Translation error: {}",
        "translator_not_available": "deep-translator is not installed.\nRun: pip install deep-translator",
        "translator_settings_title": "Translator settings",
        "translator_provider_label": "Translation provider:",
        "swap_btn":            "⇄ Swap",
        "swap_tooltip":        "Swap original ↔ translation and flip the target language",
        "err_400": "❌ Error 400 — Bad request.\n\n{}\nCheck your prompt and data format.",
        "err_401": "❌ Error 401 — API key invalid or missing.\n\nGet a key: aistudio.google.com/apikey",
        "err_403": "❌ Error 403 — Access forbidden.\n\nCurrent model: {}",
        "err_404": "❌ Error 404 — Model not found: «{}»\n\nOpen Settings → Model and select another.",
        "err_429": "❌ Error 429 — Rate limit exceeded.\n\nWait a moment and try again.",
        "err_500": "❌ Error 500 — Internal Google server error.\n\nTry again later.",
        "err_503": "❌ Error 503 — Service unavailable.\n\nTry again in a few minutes.",
        "err_timeout": "❌ Request timed out.\n\nCheck your internet connection.",
        "err_dns":     "❌ Could not connect to Google servers.\n\nCheck your internet connection.",
        "err_generic": "❌ Unexpected error:\n\n{}",
        "max_images":  "Maximum {} images allowed.",
    },
    "ru": {
        "window_title":        "Image Merger",
        "images_panel":        "Изображения (перетащите для сортировки)",
        "add_images":          "+ Добавить изображения",
        "clear_all":           "Очистить всё",
        "merge_settings":      "Настройки склейки",
        "mode":                "Режим:",
        "mode_horizontal":     "Горизонтальная лента",
        "mode_vertical":       "Вертикальная лента",
        "mode_grid":           "Сетка",
        "grid_cols":           "Колонок:",
        "grid_padding":        "Отступ:",
        "grid_bg":             "Фон:",
        "cell_align":          "Заполнение:",
        "align_fill":          "Растянуть",
        "align_fit":           "Вписать",
        "divider":             "Разделитель",
        "thickness":           "Толщина:",
        "px":                  "px",
        "color_btn":           "  Цвет  ",
        "jpeg_compress":       "JPEG сжатие",
        "quality":             "Качество:",
        "merge_btn":           "Склеить изображения",
        "result":              "Результат:",
        "result_placeholder":  "Здесь появится результат",
        "save_btn":            "Сохранить",
        "description_gemini":  "Описание (Gemini AI):",
        "copy_btn":            "Копировать",
        "extra_prompt_label":  "Дополнительный контекст (необязательно):",
        "extra_prompt_hint":   "Дополнительные сведения для промпта…",
        "describe_btn":        "▶  Описать изображение",
        "no_images":           "Нет изображений",
        "load_images":         "Добавьте не менее 2 изображений.",
        "no_result":           "Нет результата",
        "merge_first":         "Сначала склейте изображения.",
        "api_key_missing":     "API ключ",
        "enter_api_key":       "Введите Gemini API ключ.\nПолучить бесплатно: aistudio.google.com/apikey",
        "describing":          "⏳ Описываю изображение…",
        "error_open":          "Ошибка",
        "failed_open":         "Не удалось открыть файл:\n{}",
        "save_error":          "Ошибка сохранения",
        "quality_90":          "Качество {}% — минимальные потери, большой файл",
        "quality_75":          "Качество {}% — хороший баланс размера и качества",
        "quality_50":          "Качество {}% — заметные артефакты, малый файл",
        "quality_low":         "Качество {}% — сильное сжатие, низкое качество",
        "size_info":           "Размер: {}×{} пикс. | Формат: {} | ~{}",
        "mb":                  "{:.1f} МБ",
        "kb":                  "{:.0f} КБ",
        "model_current":       "Модель: {}",
        "cancel":              "Отмена",
        "save":                "Сохранить",
        "apply":               "Применить",
        "menu_language":       "Язык",
        "menu_model":          "Модель…",
        "menu_api_key":        "API ключ…",
        "menu_prompt":         "Главный промпт…",
        "menu_translator":     "Переводчик",
        "menu_translator_provider": "Провайдер…",
        "model_title":         "Выбор модели Gemini",
        "model_free_label":    "Выберите модель (с поддержкой изображений, бесплатные):",
        "model_custom_label":  "Или введите вручную:",
        "model_fetch_btn":     "Получить модели из API…",
        "model_fetching":      "Загрузка…",
        "model_fetch_ok":      "Загружено {} моделей с поддержкой изображений.",
        "model_fetch_err":     "Ошибка: {}",
        "models_link":         "Список моделей: ai.google.dev/gemini-api/docs/models",
        "prompt_title":        "Главный промпт",
        "prompt_label":        "Промпт, отправляемый в Gemini с каждым запросом:",
        "apikey_title":        "Gemini API ключ",
        "apikey_label":        "Введите ваш API ключ (хранится локально):",
        "apikey_link":         "Получить бесплатно на aistudio.google.com/apikey",
        "translate_to":        "Перевести на:",
        "translate_btn":       "🌐  Перевести",
        "translating":         "⏳ Перевожу…",
        "no_text_to_translate":"Нет текста для перевода. Сначала опишите изображение.",
        "translate_error":     "Ошибка перевода: {}",
        "translator_not_available": "deep-translator не установлен.\nВыполните: pip install deep-translator",
        "translator_settings_title": "Настройки переводчика",
        "translator_provider_label": "Провайдер перевода:",
        "swap_btn":            "⇄ Поменять",
        "swap_tooltip":        "Поменять исходный ↔ перевод и сменить язык перевода",
        "err_400": "❌ Ошибка 400 — Неверный запрос.\n\n{}\nПроверьте промпт и формат данных.",
        "err_401": "❌ Ошибка 401 — API ключ недействителен.\n\nПолучить ключ: aistudio.google.com/apikey",
        "err_403": "❌ Ошибка 403 — Доступ запрещён.\n\nТекущая модель: {}",
        "err_404": "❌ Ошибка 404 — Модель не найдена: «{}»\n\nОткройте Настройки → Модель.",
        "err_429": "❌ Ошибка 429 — Превышен лимит запросов.\n\nПодождите немного.",
        "err_500": "❌ Ошибка 500 — Внутренняя ошибка сервера.\n\nПопробуйте позже.",
        "err_503": "❌ Ошибка 503 — Сервис недоступен.\n\nПопробуйте через несколько минут.",
        "err_timeout": "❌ Превышено время ожидания.\n\nПроверьте интернет-соединение.",
        "err_dns":     "❌ Не удалось подключиться к серверам Google.\n\nПроверьте интернет-соединение.",
        "err_generic": "❌ Неожиданная ошибка:\n\n{}",
        "max_images":  "Максимально допустимо {} изображений.",
    },
}

DEFAULT_PROMPTS = {
    "en": "Describe in detail what is shown in this image in English.",
    "ru": "Опиши подробно что изображено на этой картинке на русском языке.",
}

# Available translation providers (display name → deep_translator class name)
TRANSLATOR_PROVIDERS = {
    "Google Translate":   "GoogleTranslator",
    "MyMemory":           "MyMemoryTranslator",
    "DeepL (free)":       "DeeplTranslator",
    "Linguee":            "LingueeTranslator",
    "Pons":               "PonsTranslator",
}


# ── Config ────────────────────────────────────────────────────────────────────
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


# ── API helpers ───────────────────────────────────────────────────────────────
def friendly_api_error(e: Exception, model: str, lang: str = "en") -> str:
    t   = STRINGS[lang]
    msg = str(e)
    if hasattr(e, "code"):
        code = e.code
        try:
            api_msg = json.loads(e.read().decode()).get("error", {}).get("message", "")
        except Exception:
            api_msg = ""
        if code == 400: return t["err_400"].format(api_msg)
        if code == 401: return t["err_401"]
        if code == 403: return t["err_403"].format(model)
        if code == 404: return t["err_404"].format(model)
        if code == 429: return t["err_429"]
        if code == 500: return t["err_500"]
        if code == 503: return t["err_503"]
        return t["err_generic"].format(f"HTTP {code}: {api_msg or msg}")
    if "timed out" in msg.lower() or "timeout" in msg.lower():
        return t["err_timeout"]
    if "getaddrinfo" in msg.lower() or "name or service" in msg.lower():
        return t["err_dns"]
    return t["err_generic"].format(msg)


def describe_image_gemini(api_key: str, model: str, prompt: str, pil_img: Image.Image) -> str:
    buf = io.BytesIO()
    pil_img.convert("RGB").save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()
    payload = json.dumps({"contents": [{"parts": [
        {"text": prompt},
        {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
    ]}]}).encode()
    req = urllib.request.Request(
        GEMINI_URL.format(model=model, key=api_key),
        data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def fetch_vision_models(api_key: str) -> list[str]:
    req = urllib.request.Request(
        GEMINI_LIST_URL.format(key=api_key),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    result = []
    for m in data.get("models", []):
        short   = m.get("name", "").replace("models/", "")
        methods = set(m.get("supportedGenerationMethods", []))
        is_free = any(k in short for k in ("flash", "lite", "nano"))
        if is_free and methods & VISION_METHODS:
            result.append(short)
    return sorted(result)


def do_translate(text: str, target_lang_code: str, provider_name: str) -> str:
    """Translate text using deep-translator. Returns translated string."""
    if not DEEP_TRANSLATOR_AVAILABLE:
        raise RuntimeError("deep-translator not installed")

    import deep_translator as dt

    # Map provider display name → class
    cls_map = {
        "GoogleTranslator":   dt.GoogleTranslator,
        "MyMemoryTranslator": dt.MyMemoryTranslator,
        "LingueeTranslator":  dt.LingueeTranslator,
        "PonsTranslator":     dt.PonsTranslator,
    }
    # DeepL optional
    try:
        cls_map["DeeplTranslator"] = dt.DeeplTranslator
    except AttributeError:
        pass

    cls = cls_map.get(provider_name, dt.GoogleTranslator)
    translator = cls(source="auto", target=target_lang_code)
    return translator.translate(text)


# ── Qt helpers ────────────────────────────────────────────────────────────────
def pil_to_pixmap(img: Image.Image) -> QPixmap:
    img  = img.convert("RGBA")
    raw  = img.tobytes("raw", "RGBA")
    qimg = QImage(raw, img.width, img.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())


class Scale:
    def __init__(self, factor: float):
        self.f = factor
    def __call__(self, base: int) -> int:
        return max(1, round(base * self.f))


def _shade(hex_color: str, factor: float) -> str:
    c = QColor(hex_color)
    return QColor(
        max(0, min(255, int(c.red()   * factor))),
        max(0, min(255, int(c.green() * factor))),
        max(0, min(255, int(c.blue()  * factor))),
    ).name()

def button_style(bg: str, fg: str = "white", hover: str = None,
                 pressed: str = None, extra: str = "") -> str:
    h = hover   or _shade(bg, 1.08)
    p = pressed or _shade(bg, 0.85)
    return (
        f"QPushButton{{background:{bg};color:{fg};border:none;border-radius:6px;{extra}}}"
        f"QPushButton:hover{{background:{h};}}"
        f"QPushButton:pressed{{background:{p};padding-top:2px;padding-bottom:0px;}}"
        f"QPushButton:disabled{{background:#ccc;color:#888;}}"
    )

NEUTRAL = button_style("#e9ecef", fg="#333333")

def _contrast(hex_color: str) -> str:
    c = QColor(hex_color)
    return "#000" if (c.red()*299 + c.green()*587 + c.blue()*114) / 1000 > 150 else "#fff"


# ── Image merge logic ─────────────────────────────────────────────────────────
def merge_horizontal(images: list[Image.Image], divider: tuple | None) -> Image.Image:
    h   = max(img.height for img in images)
    scaled = [img.resize((max(1, int(img.width * h / img.height)), h), Image.LANCZOS)
              for img in images]
    dw  = divider[0] if divider else 0
    dc  = divider[1] if divider else None
    total_w = sum(s.width for s in scaled) + dw * (len(scaled) - 1)
    out = Image.new("RGBA", (total_w, h), (0, 0, 0, 0))
    x = 0
    for i, s in enumerate(scaled):
        out.paste(s, (x, 0))
        x += s.width
        if divider and i < len(scaled) - 1:
            r, g, b = _hex_to_rgb(dc)
            ImageDraw.Draw(out).rectangle([x, 0, x + dw - 1, h - 1], fill=(r, g, b, 255))
            x += dw
    return out


def merge_vertical(images: list[Image.Image], divider: tuple | None) -> Image.Image:
    w   = max(img.width for img in images)
    scaled = [img.resize((w, max(1, int(img.height * w / img.width))), Image.LANCZOS)
              for img in images]
    dw  = divider[0] if divider else 0
    dc  = divider[1] if divider else None
    total_h = sum(s.height for s in scaled) + dw * (len(scaled) - 1)
    out = Image.new("RGBA", (w, total_h), (0, 0, 0, 0))
    y = 0
    for i, s in enumerate(scaled):
        out.paste(s, (0, y))
        y += s.height
        if divider and i < len(scaled) - 1:
            r, g, b = _hex_to_rgb(dc)
            ImageDraw.Draw(out).rectangle([0, y, w - 1, y + dw - 1], fill=(r, g, b, 255))
            y += dw
    return out


def merge_grid(images: list[Image.Image], cols: int, padding: int,
               bg_color: str, cell_fill: bool) -> Image.Image:
    n    = len(images)
    rows = math.ceil(n / cols)
    cell_w = max(img.width  for img in images)
    cell_h = max(img.height for img in images)

    total_w = cols * cell_w + (cols + 1) * padding
    total_h = rows * cell_h + (rows + 1) * padding

    bg_rgb = _hex_to_rgb(bg_color)
    out = Image.new("RGBA", (total_w, total_h), (*bg_rgb, 255))

    for idx, img in enumerate(images):
        row = idx // cols
        col = idx  % cols
        cx  = padding + col * (cell_w + padding)
        cy  = padding + row * (cell_h + padding)

        if cell_fill:
            scale = max(cell_w / img.width, cell_h / img.height)
            nw    = max(1, int(img.width  * scale))
            nh    = max(1, int(img.height * scale))
            thumb = img.resize((nw, nh), Image.LANCZOS)
            ox    = (nw - cell_w) // 2
            oy    = (nh - cell_h) // 2
            thumb = thumb.crop((ox, oy, ox + cell_w, oy + cell_h))
            out.paste(thumb, (cx, cy))
        else:
            scale = min(cell_w / img.width, cell_h / img.height)
            nw    = max(1, int(img.width  * scale))
            nh    = max(1, int(img.height * scale))
            thumb = img.resize((nw, nh), Image.LANCZOS)
            ox    = cx + (cell_w - nw) // 2
            oy    = cy + (cell_h - nh) // 2
            out.paste(thumb, (ox, oy))

    return out


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ── Workers ───────────────────────────────────────────────────────────────────
class DescribeWorker(QThread):
    finished_ok  = Signal(str)
    finished_err = Signal(str)

    def __init__(self, api_key, model, prompt, pil_img, lang):
        super().__init__()
        self.api_key = api_key; self.model = model
        self.prompt  = prompt;  self.pil_img = pil_img; self.lang = lang

    def run(self):
        try:
            self.finished_ok.emit(
                describe_image_gemini(self.api_key, self.model, self.prompt, self.pil_img))
        except Exception as e:
            self.finished_err.emit(friendly_api_error(e, self.model, self.lang))


class FetchModelsWorker(QThread):
    finished_ok  = Signal(list)
    finished_err = Signal(str)

    def __init__(self, api_key):
        super().__init__(); self.api_key = api_key

    def run(self):
        try:    self.finished_ok.emit(fetch_vision_models(self.api_key))
        except Exception as e: self.finished_err.emit(str(e))


class TranslateWorker(QThread):
    finished_ok  = Signal(str)
    finished_err = Signal(str)

    def __init__(self, text: str, target_lang: str, provider: str):
        super().__init__()
        self.text        = text
        self.target_lang = target_lang
        self.provider    = provider

    def run(self):
        try:
            result = do_translate(self.text, self.target_lang, self.provider)
            self.finished_ok.emit(result)
        except Exception as e:
            self.finished_err.emit(str(e))


# ── Thumbnail card widget ─────────────────────────────────────────────────────
class ThumbCard(QWidget):
    remove_requested = Signal(int)
    move_left        = Signal(int)
    move_right       = Signal(int)

    THUMB = 90

    def __init__(self, idx: int, img: Image.Image, filename: str, scale: Scale):
        super().__init__()
        self._idx  = idx
        self._img  = img
        sz = scale(self.THUMB)
        self.setFixedWidth(sz + scale(4))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(scale(2))

        pix     = pil_to_pixmap(img)
        thumb   = pix.scaled(sz, sz, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
        img_lbl = QLabel()
        img_lbl.setPixmap(thumb)
        img_lbl.setFixedSize(sz, sz)
        img_lbl.setStyleSheet("border:1px solid #bbb; background:white;")
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(img_lbl)

        name = filename if len(filename) <= 12 else filename[:10] + "…"
        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        name_lbl.setStyleSheet("font-size:8px; color:#555;")
        root.addWidget(name_lbl)

        ctrl = QHBoxLayout()
        ctrl.setContentsMargins(0, 0, 0, 0)
        ctrl.setSpacing(scale(2))

        self._left_btn = QPushButton("◀")
        self._left_btn.setFixedWidth(scale(22))
        self._left_btn.setStyleSheet(NEUTRAL + f"QPushButton{{padding:1px;}}")
        self._left_btn.clicked.connect(lambda: self.move_left.emit(self._idx))

        self._num_lbl = QLabel(str(idx + 1))
        self._num_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._num_lbl.setStyleSheet("font-size:9px; color:#444;")
        self._num_lbl.setFixedWidth(scale(18))

        self._right_btn = QPushButton("▶")
        self._right_btn.setFixedWidth(scale(22))
        self._right_btn.setStyleSheet(NEUTRAL + f"QPushButton{{padding:1px;}}")
        self._right_btn.clicked.connect(lambda: self.move_right.emit(self._idx))

        rm_btn = QPushButton("✕")
        rm_btn.setFixedWidth(scale(22))
        rm_btn.setStyleSheet(button_style("#dc3545", extra="padding:1px;"))
        rm_btn.clicked.connect(lambda: self.remove_requested.emit(self._idx))

        ctrl.addWidget(self._left_btn)
        ctrl.addWidget(self._num_lbl)
        ctrl.addWidget(self._right_btn)
        ctrl.addStretch()
        ctrl.addWidget(rm_btn)
        root.addLayout(ctrl)

    def update_index(self, idx: int):
        self._idx = idx
        self._num_lbl.setText(str(idx + 1))


# ── Dialogs ───────────────────────────────────────────────────────────────────
class PromptDialog(QDialog):
    def __init__(self, parent, current: str, scale: Scale, tr):
        super().__init__(parent)
        self.setWindowTitle(tr("prompt_title"))
        self.result_text = None
        s = scale
        root = QVBoxLayout(self)
        root.setSpacing(s(8))
        root.addWidget(QLabel(tr("prompt_label")))
        self.text = QTextEdit()
        self.text.setPlainText(current)
        self.text.setMinimumSize(s(480), s(160))
        root.addWidget(self.text)
        row = QHBoxLayout(); row.addStretch()
        cancel = QPushButton(tr("cancel"))
        cancel.setStyleSheet(button_style("#6c757d", extra=f"padding:{s(6)}px {s(16)}px;"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("save"))
        ok.setStyleSheet(button_style("#4a90d9", extra=f"padding:{s(6)}px {s(20)}px; font-weight:bold;"))
        ok.clicked.connect(self._ok)
        row.addWidget(cancel); row.addWidget(ok)
        root.addLayout(row)

    def _ok(self):
        self.result_text = self.text.toPlainText().strip()
        self.accept()


class ApiKeyDialog(QDialog):
    def __init__(self, parent, current: str, scale: Scale, tr):
        super().__init__(parent)
        self.setWindowTitle(tr("apikey_title"))
        self.result_key = None
        s = scale
        root = QVBoxLayout(self)
        root.setSpacing(s(8))
        root.addWidget(QLabel(tr("apikey_label")))
        row = QHBoxLayout()
        self.edit = QLineEdit(current)
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setMinimumWidth(s(340))
        row.addWidget(self.edit)
        self._hidden = True
        eye = QPushButton("👁"); eye.setFixedWidth(s(36)); eye.setStyleSheet(NEUTRAL)
        eye.clicked.connect(self._toggle)
        row.addWidget(eye)
        root.addLayout(row)
        link = QLabel(f'<a href="https://aistudio.google.com/apikey">{tr("apikey_link")}</a>')
        link.setOpenExternalLinks(True); link.setStyleSheet("color:#888; font-size:10px;")
        root.addWidget(link)
        br = QHBoxLayout(); br.addStretch()
        cancel = QPushButton(tr("cancel"))
        cancel.setStyleSheet(button_style("#6c757d", extra=f"padding:{s(6)}px {s(16)}px;"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("apply"))
        ok.setStyleSheet(button_style("#4a90d9", extra=f"padding:{s(6)}px {s(20)}px; font-weight:bold;"))
        ok.clicked.connect(self._ok)
        br.addWidget(cancel); br.addWidget(ok)
        root.addLayout(br)

    def _toggle(self):
        self._hidden = not self._hidden
        self.edit.setEchoMode(
            QLineEdit.EchoMode.Password if self._hidden else QLineEdit.EchoMode.Normal)

    def _ok(self):
        self.result_key = self.edit.text().strip()
        self.accept()


class ModelDialog(QDialog):
    def __init__(self, parent, current: str, known: list, scale: Scale, tr, api_key: str):
        super().__init__(parent)
        self.setWindowTitle(tr("model_title"))
        self.result_model  = None
        self._tr           = tr
        self._api_key      = api_key
        self._known        = list(known)
        self._worker       = None
        s = scale
        root = QVBoxLayout(self); root.setSpacing(s(6))
        root.addWidget(QLabel(tr("model_free_label")))
        self.group  = QButtonGroup(self)
        self.radios: list[QRadioButton] = []
        self._rbox  = QVBoxLayout()
        root.addLayout(self._rbox)
        self._rebuild(current)
        root.addWidget(QLabel(tr("model_custom_label")))
        self.custom = QLineEdit()
        if current not in self._known: self.custom.setText(current)
        root.addWidget(self.custom)
        self.fetch_btn = QPushButton(tr("model_fetch_btn"))
        self.fetch_btn.setStyleSheet(button_style("#6c757d", extra=f"padding:{s(5)}px {s(12)}px;"))
        self.fetch_btn.clicked.connect(self._fetch)
        root.addWidget(self.fetch_btn)
        self.status_lbl = QLabel(""); self.status_lbl.setStyleSheet("color:#555; font-size:10px;")
        root.addWidget(self.status_lbl)
        br = QHBoxLayout(); br.addStretch()
        cancel = QPushButton(tr("cancel"))
        cancel.setStyleSheet(button_style("#6c757d", extra=f"padding:{s(6)}px {s(16)}px;"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("apply"))
        ok.setStyleSheet(button_style("#4a90d9", extra=f"padding:{s(6)}px {s(20)}px; font-weight:bold;"))
        ok.clicked.connect(self._ok)
        br.addWidget(cancel); br.addWidget(ok)
        root.addLayout(br)
        link = QLabel(f'<a href="https://ai.google.dev/gemini-api/docs/models">{tr("models_link")}</a>')
        link.setOpenExternalLinks(True); link.setStyleSheet("color:#888; font-size:10px;")
        root.addWidget(link)

    def _rebuild(self, current: str):
        for rb in self.radios:
            self._rbox.removeWidget(rb); self.group.removeButton(rb); rb.deleteLater()
        self.radios.clear()
        for m in self._known:
            rb = QRadioButton(m)
            if m == current: rb.setChecked(True)
            self.group.addButton(rb); self.radios.append(rb); self._rbox.addWidget(rb)

    def _fetch(self):
        if not self._api_key:
            self.status_lbl.setText("⚠ Enter API key first (Settings → API key)."); return
        self.fetch_btn.setEnabled(False)
        self.status_lbl.setText(self._tr("model_fetching"))
        self._worker = FetchModelsWorker(self._api_key)
        self._worker.finished_ok.connect(self._on_ok)
        self._worker.finished_err.connect(self._on_err)
        self._worker.start()

    def _on_ok(self, models: list):
        self.fetch_btn.setEnabled(True)
        if models:
            self._known = models
            cur = next((rb.text() for rb in self.radios if rb.isChecked()), "")
            self._rebuild(cur)
            self.status_lbl.setText(self._tr("model_fetch_ok").format(len(models)))
        else:
            self.status_lbl.setText("No vision models found.")

    def _on_err(self, err: str):
        self.fetch_btn.setEnabled(True)
        self.status_lbl.setText(self._tr("model_fetch_err").format(err[:80]))

    def _ok(self):
        custom = self.custom.text().strip()
        self.result_model = custom if custom else next(
            (rb.text() for rb in self.radios if rb.isChecked()), None)
        self.accept()


class TranslatorSettingsDialog(QDialog):
    """Dialog for choosing the translation provider."""

    def __init__(self, parent, current_provider: str, scale: Scale, tr):
        super().__init__(parent)
        self.setWindowTitle(tr("translator_settings_title"))
        self.result_provider = None
        s = scale

        root = QVBoxLayout(self)
        root.setSpacing(s(8))
        root.addWidget(QLabel(tr("translator_provider_label")))

        self.combo = QComboBox()
        self.combo.setMinimumWidth(s(260))
        for display_name in TRANSLATOR_PROVIDERS:
            self.combo.addItem(display_name)
        # Pre-select current
        for i, cls_name in enumerate(TRANSLATOR_PROVIDERS.values()):
            if cls_name == current_provider:
                self.combo.setCurrentIndex(i)
                break
        root.addWidget(self.combo)

        if not DEEP_TRANSLATOR_AVAILABLE:
            warn = QLabel("⚠ deep-translator not installed.\npip install deep-translator")
            warn.setStyleSheet("color:#c00; font-size:10px;")
            root.addWidget(warn)

        br = QHBoxLayout(); br.addStretch()
        cancel = QPushButton(tr("cancel"))
        cancel.setStyleSheet(button_style("#6c757d", extra=f"padding:{s(6)}px {s(16)}px;"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("apply"))
        ok.setStyleSheet(button_style("#4a90d9", extra=f"padding:{s(6)}px {s(20)}px; font-weight:bold;"))
        ok.clicked.connect(self._ok)
        br.addWidget(cancel); br.addWidget(ok)
        root.addLayout(br)

    def _ok(self):
        display = self.combo.currentText()
        self.result_provider = TRANSLATOR_PROVIDERS.get(display, "GoogleTranslator")
        self.accept()


# ── Main window ───────────────────────────────────────────────────────────────
class ImageMerger(QMainWindow):
    def __init__(self):
        super().__init__()

        self._images:   list[Image.Image] = []
        self._names:    list[str]         = []
        self.result_pil: Image.Image | None = None

        self._config        = load_config()
        self._lang          = self._config.get("language", "en")
        self._api_key       = self._config.get("gemini_api_key", "")
        self._model         = self._config.get("gemini_model", DEFAULT_MODEL)
        self._prompt        = self._config.get("gemini_prompt", DEFAULT_PROMPTS[self._lang])
        self._divider_color = self._config.get("divider_color", "#000000")
        self._grid_bg_color = self._config.get("grid_bg_color", "#ffffff")
        # No hardcoded models — only loaded from API
        self._known_models  = self._config.get("known_models", [])
        self._translator_provider = self._config.get("translator_provider", "GoogleTranslator")
        self._worker: DescribeWorker | None = None
        self._translate_worker: TranslateWorker | None = None
        # Stores only the original (pre-translation) description text
        self._original_description: str = ""
        # Lang-pair tracking for ⇄ swap:
        # _swap_lang_to   = display name of the language last translated INTO (shown in combo)
        # _swap_lang_from = display name of the language last translated FROM
        self._swap_lang_to:   str = ""
        self._swap_lang_from: str = ""
        self._current_source_for_translation: str = ""

        geo    = QApplication.primaryScreen().availableGeometry()
        factor = max(0.7, min(1.6, min(geo.width() / 1920, geo.height() / 1080)))
        self.s = Scale(factor)
        self.setStyleSheet(f"QWidget{{font-size:{self.s(10)}pt;}}")

        if os.path.exists(FAVICON_PATH):
            self.setWindowIcon(QIcon(FAVICON_PATH))

        self._build_ui()
        self._restore_window()
        self._apply_language()

    def tr(self, key: str) -> str:
        return STRINGS[self._lang].get(key, STRINGS["en"].get(key, key))

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        s = self.s

        # Menu bar
        mb = self.menuBar()

        # 1. Language menu
        self._menu_lang = mb.addMenu("")
        for lang, label in [("en", "English"), ("ru", "Русский")]:
            a = QAction(label, self); a.triggered.connect(lambda _, l=lang: self._set_language(l))
            self._menu_lang.addAction(a)

        # 2. Settings menu (Gemini)
        self._menu_settings = mb.addMenu("")
        self._act_model  = QAction("", self); self._act_model.triggered.connect(self._open_model_dialog)
        self._act_apikey = QAction("", self); self._act_apikey.triggered.connect(self._open_apikey_dialog)
        self._act_prompt = QAction("", self); self._act_prompt.triggered.connect(self._open_prompt_dialog)
        self._menu_settings.addAction(self._act_model)
        self._menu_settings.addAction(self._act_apikey)
        self._menu_settings.addSeparator()
        self._menu_settings.addAction(self._act_prompt)

        # 3. Translator menu
        self._menu_translator = mb.addMenu("")
        self._act_translator_provider = QAction("", self)
        self._act_translator_provider.triggered.connect(self._open_translator_settings)
        self._menu_translator.addAction(self._act_translator_provider)

        # Root layout
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.setCentralWidget(scroll)
        root_widget = QWidget(); scroll.setWidget(root_widget)
        root = QHBoxLayout(root_widget)
        root.setContentsMargins(s(10), s(10), s(10), s(10))
        root.setSpacing(s(10))

        # ── LEFT ─────────────────────────────────────────────────────────────
        left_widget = QWidget(); left_widget.setMaximumWidth(s(620))
        left = QVBoxLayout(left_widget); left.setSpacing(s(8))

        # Images panel
        self._images_box = QGroupBox()
        images_layout = QVBoxLayout(self._images_box)
        images_layout.setSpacing(s(6))

        thumb_scroll = QScrollArea()
        thumb_scroll.setWidgetResizable(True)
        thumb_scroll.setFixedHeight(s(170))
        thumb_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        thumb_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._thumb_widget = QWidget()
        self._thumb_layout = QHBoxLayout(self._thumb_widget)
        self._thumb_layout.setContentsMargins(s(4), s(4), s(4), s(4))
        self._thumb_layout.setSpacing(s(6))
        self._thumb_layout.addStretch()
        thumb_scroll.setWidget(self._thumb_widget)
        images_layout.addWidget(thumb_scroll)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton()
        self.add_btn.setStyleSheet(button_style("#4a90d9", extra=f"padding:{s(6)}px {s(14)}px;"))
        self.add_btn.clicked.connect(self._add_images)
        btn_row.addWidget(self.add_btn)
        self.clear_btn = QPushButton()
        self.clear_btn.setStyleSheet(button_style("#dc3545", extra=f"padding:{s(6)}px {s(14)}px;"))
        self.clear_btn.clicked.connect(self._clear_images)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        images_layout.addLayout(btn_row)
        left.addWidget(self._images_box)

        # ── Merge settings ────────────────────────────────────────────────────
        self.settings_box = QGroupBox()
        sg = QVBoxLayout(self.settings_box); sg.setSpacing(s(4))

        mode_row = QHBoxLayout()
        self._mode_lbl = QLabel()
        mode_row.addWidget(self._mode_lbl)
        self._mode_group = QButtonGroup(self)
        self._rb_horizontal = QRadioButton(); self._rb_horizontal.setChecked(True)
        self._rb_vertical   = QRadioButton()
        self._rb_grid       = QRadioButton()
        for rb in (self._rb_horizontal, self._rb_vertical, self._rb_grid):
            self._mode_group.addButton(rb); mode_row.addWidget(rb)
        mode_row.addStretch()
        sg.addLayout(mode_row)
        self._mode_group.buttonClicked.connect(self._on_mode_changed)

        sg.addWidget(self._hline())

        self._grid_box = QGroupBox()
        gb = QHBoxLayout(self._grid_box); gb.setSpacing(s(8))
        self._grid_cols_lbl = QLabel()
        gb.addWidget(self._grid_cols_lbl)
        self.grid_cols = QSpinBox(); self.grid_cols.setRange(1, 10)
        self.grid_cols.setValue(self._config.get("grid_cols", 2))
        self.grid_cols.setMinimumWidth(s(70))
        gb.addWidget(self.grid_cols)

        self._grid_pad_lbl = QLabel()
        gb.addWidget(self._grid_pad_lbl)
        self.grid_padding = QSpinBox(); self.grid_padding.setRange(0, 100)
        self.grid_padding.setValue(self._config.get("grid_padding", 8))
        self.grid_padding.setMinimumWidth(s(70))
        self.grid_padding.setSuffix(" px")
        gb.addWidget(self.grid_padding)

        self._grid_align_lbl = QLabel()
        gb.addWidget(self._grid_align_lbl)
        self.grid_align = QComboBox(); self.grid_align.setMinimumWidth(s(70))
        gb.addWidget(self.grid_align)

        self._grid_bg_lbl = QLabel()
        gb.addWidget(self._grid_bg_lbl)
        self.grid_bg_btn = QPushButton()
        self.grid_bg_btn.clicked.connect(self._pick_grid_bg)
        gb.addWidget(self.grid_bg_btn)
        gb.addStretch()
        sg.addWidget(self._grid_box)
        self._refresh_grid_bg_btn()

        sg.addWidget(self._hline())

        div_row = QHBoxLayout()
        self.divider_enabled = QCheckBox()
        self.divider_enabled.setChecked(self._config.get("divider_enabled", False))
        self.divider_enabled.toggled.connect(self._update_divider_state)
        div_row.addWidget(self.divider_enabled)
        self._thick_lbl = QLabel(); div_row.addWidget(self._thick_lbl)
        self.divider_width = QSpinBox(); self.divider_width.setRange(1, 50)
        self.divider_width.setValue(self._config.get("divider_width", 4))
        self.divider_width.setMinimumWidth(s(72))
        div_row.addWidget(self.divider_width)
        self._px_lbl = QLabel(); div_row.addWidget(self._px_lbl)
        self.divider_color_btn = QPushButton()
        self.divider_color_btn.clicked.connect(self._pick_divider_color)
        div_row.addWidget(self.divider_color_btn)
        self.divider_color_lbl = QLabel(self._divider_color)
        self.divider_color_lbl.setStyleSheet("color:#555;")
        div_row.addWidget(self.divider_color_lbl)
        div_row.addStretch()
        sg.addLayout(div_row)
        self._refresh_divider_btn()
        self._update_divider_state()

        sg.addWidget(self._hline())

        comp_row = QHBoxLayout()
        self.compress_enabled = QCheckBox()
        self.compress_enabled.setChecked(self._config.get("compress_enabled", False))
        self.compress_enabled.toggled.connect(self._update_compress_state)
        comp_row.addWidget(self.compress_enabled)
        self._quality_lbl = QLabel(); comp_row.addWidget(self._quality_lbl)
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(10, 100)
        self.quality_slider.setValue(self._config.get("compress_quality", 85))
        self.quality_slider.setFixedWidth(s(140))
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        comp_row.addWidget(self.quality_slider)
        self.quality_val_lbl = QLabel(); self.quality_val_lbl.setFixedWidth(s(36))
        comp_row.addWidget(self.quality_val_lbl); comp_row.addStretch()
        sg.addLayout(comp_row)
        self.comp_hint_lbl = QLabel(); self.comp_hint_lbl.setStyleSheet("color:#555; font-size:10px;")
        sg.addWidget(self.comp_hint_lbl)
        self._update_compress_state()

        left.addWidget(self.settings_box)

        self.merge_btn = QPushButton()
        self.merge_btn.setStyleSheet(button_style("#4a90d9", extra=f"font-weight:bold; padding:{s(10)}px;"))
        self.merge_btn.clicked.connect(self._merge)
        left.addWidget(self.merge_btn)

        self._result_title = QLabel()
        left.addWidget(self._result_title)

        # ── FIX: result_label expands horizontally to match buttons width ────
        preview_h = self.s(220)
        self.result_label = QLabel()
        self.result_label.setFixedHeight(preview_h)
        self.result_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.result_label.setStyleSheet("background:white; border:1px solid #999; color:#aaa;")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self.result_label)

        self.file_info_lbl = QLabel(); self.file_info_lbl.setStyleSheet("color:#555; font-size:10px;")
        left.addWidget(self.file_info_lbl)
        self.save_btn = QPushButton()
        self.save_btn.setStyleSheet(button_style("#5cb85c", extra=f"font-weight:bold; padding:{s(10)}px;"))
        self.save_btn.clicked.connect(self._save)
        left.addWidget(self.save_btn)
        left.addStretch()
        root.addWidget(left_widget)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine); sep.setStyleSheet("color:#ccc;")
        root.addWidget(sep)

        # ── RIGHT ─────────────────────────────────────────────────────────────
        right_widget = QWidget()
        right = QVBoxLayout(right_widget); right.setSpacing(s(6))

        desc_row = QHBoxLayout()
        self._desc_title_lbl = QLabel(); desc_row.addWidget(self._desc_title_lbl)
        desc_row.addStretch()
        self.copy_btn = QPushButton()
        self.copy_btn.setStyleSheet(button_style("#6c757d", extra=f"padding:{s(4)}px {s(12)}px;"))
        self.copy_btn.clicked.connect(self._copy_desc)
        desc_row.addWidget(self.copy_btn)
        right.addLayout(desc_row)

        self.model_lbl = QLabel(); self.model_lbl.setStyleSheet("color:#555; font-size:10px;")
        right.addWidget(self.model_lbl)

        self._extra_lbl = QLabel(); right.addWidget(self._extra_lbl)
        extra_row = QHBoxLayout()
        self.extra_prompt = QLineEdit(); extra_row.addWidget(self.extra_prompt)
        clr = QPushButton("✕"); clr.setFixedWidth(s(30)); clr.setStyleSheet(NEUTRAL)
        clr.clicked.connect(self.extra_prompt.clear); extra_row.addWidget(clr)
        right.addLayout(extra_row)

        self.describe_btn = QPushButton()
        self.describe_btn.setStyleSheet(button_style("#e8a020", extra=f"font-weight:bold; padding:{s(10)}px;"))
        self.describe_btn.clicked.connect(self._describe)
        right.addWidget(self.describe_btn)

        self.desc_text = QTextEdit(); self.desc_text.setReadOnly(True)
        right.addWidget(self.desc_text)

        # ── Translation row ───────────────────────────────────────────────────
        right.addWidget(self._hline())

        translate_row = QHBoxLayout()
        self._translate_to_lbl = QLabel()
        translate_row.addWidget(self._translate_to_lbl)

        self.translate_lang_combo = QComboBox()
        self.translate_lang_combo.setMinimumWidth(s(160))
        lang_names = list(TRANSLATE_LANGUAGES.keys())
        for ln in lang_names:
            self.translate_lang_combo.addItem(ln)
        # Restore saved selection
        saved_tl = self._config.get("translate_target_lang", "Русский")
        if saved_tl in lang_names:
            self.translate_lang_combo.setCurrentText(saved_tl)
        self.translate_lang_combo.currentTextChanged.connect(self._on_translate_lang_changed)
        translate_row.addWidget(self.translate_lang_combo)

        translate_row.addStretch()

        self.swap_btn = QPushButton()
        self.swap_btn.setStyleSheet(
            button_style("#6c757d", extra=f"padding:{s(6)}px {s(10)}px;"))
        self.swap_btn.setEnabled(False)   # enabled only after a successful translation
        self.swap_btn.clicked.connect(self._swap_texts)
        translate_row.addWidget(self.swap_btn)

        self.translate_btn = QPushButton()
        self.translate_btn.setStyleSheet(
            button_style("#5b6abf", extra=f"font-weight:bold; padding:{s(6)}px {s(14)}px;"))
        self.translate_btn.clicked.connect(self._translate)
        translate_row.addWidget(self.translate_btn)

        right.addLayout(translate_row)
        root.addWidget(right_widget, stretch=1)

        # Restore mode
        saved_mode = self._config.get("merge_mode", "horizontal")
        if saved_mode == "vertical":  self._rb_vertical.setChecked(True)
        elif saved_mode == "grid":    self._rb_grid.setChecked(True)
        self._on_mode_changed()

    # ── Static helpers ────────────────────────────────────────────────────────
    def _hline(self) -> QFrame:
        f = QFrame(); f.setFrameShape(QFrame.Shape.HLine); f.setStyleSheet("color:#ddd;"); return f

    def _current_mode(self) -> str:
        if self._rb_vertical.isChecked(): return "vertical"
        if self._rb_grid.isChecked():     return "grid"
        return "horizontal"

    def _on_mode_changed(self, *_):
        is_grid = self._rb_grid.isChecked()
        self._grid_box.setVisible(is_grid)
        self.divider_enabled.setEnabled(not is_grid)
        self._update_divider_state()

    # ── Language ──────────────────────────────────────────────────────────────
    def _set_language(self, lang: str):
        self._lang = lang
        self._apply_language()
        self._do_save_config()

    def _apply_language(self):
        tr = self.tr
        self.setWindowTitle(tr("window_title"))
        self._menu_lang.setTitle(tr("menu_language"))
        self._menu_settings.setTitle("Settings" if self._lang == "en" else "Настройки")
        self._act_model.setText(tr("menu_model"))
        self._act_apikey.setText(tr("menu_api_key"))
        self._act_prompt.setText(tr("menu_prompt"))

        self._menu_translator.setTitle(tr("menu_translator"))
        self._act_translator_provider.setText(tr("menu_translator_provider"))

        self._images_box.setTitle(tr("images_panel"))
        self.add_btn.setText(tr("add_images"))
        self.clear_btn.setText(tr("clear_all"))

        self.settings_box.setTitle(tr("merge_settings"))
        self._mode_lbl.setText(tr("mode"))
        self._rb_horizontal.setText(tr("mode_horizontal"))
        self._rb_vertical.setText(tr("mode_vertical"))
        self._rb_grid.setText(tr("mode_grid"))

        self._grid_cols_lbl.setText(tr("grid_cols"))
        self._grid_pad_lbl.setText(tr("grid_padding"))
        self._grid_align_lbl.setText(tr("cell_align"))
        self._grid_bg_lbl.setText(tr("grid_bg"))
        cur_idx = self.grid_align.currentIndex()
        self.grid_align.blockSignals(True)
        self.grid_align.clear()
        self.grid_align.addItem(tr("align_fill"))
        self.grid_align.addItem(tr("align_fit"))
        self.grid_align.setCurrentIndex(max(0, cur_idx))
        self.grid_align.blockSignals(False)

        self.divider_enabled.setText(tr("divider"))
        self._thick_lbl.setText(tr("thickness"))
        self._px_lbl.setText(tr("px"))
        self.divider_color_btn.setText(tr("color_btn"))
        self.compress_enabled.setText(tr("jpeg_compress"))
        self._quality_lbl.setText(tr("quality"))
        self.merge_btn.setText(tr("merge_btn"))
        self._result_title.setText(tr("result"))
        if not self.result_pil:
            self.result_label.setText(tr("result_placeholder"))
        self.save_btn.setText(tr("save_btn"))
        self._desc_title_lbl.setText(tr("description_gemini"))
        self.copy_btn.setText(tr("copy_btn"))
        self._extra_lbl.setText(tr("extra_prompt_label"))
        self.extra_prompt.setPlaceholderText(tr("extra_prompt_hint"))
        self.describe_btn.setText(tr("describe_btn"))
        self._translate_to_lbl.setText(tr("translate_to"))
        self.swap_btn.setText(tr("swap_btn"))
        self.swap_btn.setToolTip(tr("swap_tooltip"))
        self.translate_btn.setText(tr("translate_btn"))
        self._refresh_model_lbl()
        self._on_quality_changed(self.quality_slider.value())

    # ── Thumbnail list management ─────────────────────────────────────────────
    def _rebuild_thumbs(self):
        while self._thumb_layout.count() > 1:
            item = self._thumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, (img, name) in enumerate(zip(self._images, self._names)):
            card = ThumbCard(i, img, name, self.s)
            card.remove_requested.connect(self._remove_image)
            card.move_left.connect(self._move_left)
            card.move_right.connect(self._move_right)
            self._thumb_layout.insertWidget(i, card)

    def _add_images(self):
        remaining = MAX_IMAGES - len(self._images)
        if remaining <= 0:
            QMessageBox.warning(self, "", self.tr("max_images").format(MAX_IMAGES))
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self, self.tr("add_images"), "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp);;All files (*.*)")
        for path in paths[:remaining]:
            try:
                img = Image.open(path).convert("RGBA")
                self._images.append(img)
                self._names.append(os.path.basename(path))
            except Exception as e:
                QMessageBox.critical(self, self.tr("error_open"), self.tr("failed_open").format(e))
        self._rebuild_thumbs()

    def _remove_image(self, idx: int):
        if 0 <= idx < len(self._images):
            self._images.pop(idx); self._names.pop(idx)
            self._rebuild_thumbs()

    def _move_left(self, idx: int):
        if idx > 0:
            self._images[idx-1], self._images[idx] = self._images[idx], self._images[idx-1]
            self._names[idx-1],  self._names[idx]  = self._names[idx],  self._names[idx-1]
            self._rebuild_thumbs()

    def _move_right(self, idx: int):
        if idx < len(self._images) - 1:
            self._images[idx+1], self._images[idx] = self._images[idx], self._images[idx+1]
            self._names[idx+1],  self._names[idx]  = self._names[idx],  self._names[idx+1]
            self._rebuild_thumbs()

    def _clear_images(self):
        self._images.clear(); self._names.clear()
        self._rebuild_thumbs()

    # ── Color pickers ─────────────────────────────────────────────────────────
    def _pick_divider_color(self):
        color = QColorDialog.getColor(QColor(self._divider_color), self, "Divider color")
        if color.isValid():
            self._divider_color = color.name()
            self._refresh_divider_btn()
            self.divider_color_lbl.setText(self._divider_color)

    def _refresh_divider_btn(self):
        self.divider_color_btn.setStyleSheet(
            button_style(self._divider_color, fg=_contrast(self._divider_color),
                         extra=f"padding:{self.s(4)}px {self.s(10)}px;"))

    def _pick_grid_bg(self):
        color = QColorDialog.getColor(QColor(self._grid_bg_color), self, "Grid background")
        if color.isValid():
            self._grid_bg_color = color.name()
            self._refresh_grid_bg_btn()

    def _refresh_grid_bg_btn(self):
        self.grid_bg_btn.setStyleSheet(
            button_style(self._grid_bg_color, fg=_contrast(self._grid_bg_color),
                         extra=f"padding:{self.s(4)}px {self.s(10)}px;"))
        self.grid_bg_btn.setText(self._grid_bg_color)

    def _update_divider_state(self):
        on = self.divider_enabled.isChecked() and self.divider_enabled.isEnabled()
        self.divider_width.setEnabled(on)
        self.divider_color_btn.setEnabled(on)

    # ── Compression ───────────────────────────────────────────────────────────
    def _update_compress_state(self):
        self.quality_slider.setEnabled(self.compress_enabled.isChecked())

    def _on_quality_changed(self, val: int):
        self.quality_val_lbl.setText(f"{val}%")
        tr = self.tr
        if val >= 90:   hint = tr("quality_90")
        elif val >= 75: hint = tr("quality_75")
        elif val >= 50: hint = tr("quality_50")
        else:           hint = tr("quality_low")
        self.comp_hint_lbl.setText(hint.format(val))

    # ── Menu dialogs ──────────────────────────────────────────────────────────
    def _open_model_dialog(self):
        dlg = ModelDialog(self, self._model, self._known_models, self.s, self.tr, self._api_key)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_model:
            self._model = dlg.result_model
            for m in dlg._known: self._known_models = list(dict.fromkeys(self._known_models + [m]))
            self._refresh_model_lbl()

    def _open_apikey_dialog(self):
        dlg = ApiKeyDialog(self, self._api_key, self.s, self.tr)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._api_key = dlg.result_key or ""; self._do_save_config()

    def _open_prompt_dialog(self):
        dlg = PromptDialog(self, self._prompt, self.s, self.tr)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_text is not None:
            self._prompt = dlg.result_text or DEFAULT_PROMPTS[self._lang]

    def _open_translator_settings(self):
        dlg = TranslatorSettingsDialog(self, self._translator_provider, self.s, self.tr)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_provider:
            self._translator_provider = dlg.result_provider
            self._do_save_config()

    def _refresh_model_lbl(self):
        self.model_lbl.setText(self.tr("model_current").format(self._model))

    # ── Preview helper ────────────────────────────────────────────────────────
    def _show_preview(self, label: QLabel, img: Image.Image):
        pix    = pil_to_pixmap(img)
        scaled = pix.scaled(label.width() - 4, label.height() - 4,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(scaled)
        label.setStyleSheet("background:white; border:1px solid #999;")

    # ── Merge ─────────────────────────────────────────────────────────────────
    def _merge(self):
        if len(self._images) < 2:
            QMessageBox.warning(self, self.tr("no_images"), self.tr("load_images"))
            return

        mode = self._current_mode()

        if self.divider_enabled.isChecked() and self.divider_enabled.isEnabled():
            divider = (self.divider_width.value(), self._divider_color)
        else:
            divider = None

        if mode == "horizontal":
            out = merge_horizontal(self._images, divider)
        elif mode == "vertical":
            out = merge_vertical(self._images, divider)
        else:
            cols      = self.grid_cols.value()
            padding   = self.grid_padding.value()
            cell_fill = self.grid_align.currentIndex() == 0
            out = merge_grid(self._images, cols, padding, self._grid_bg_color, cell_fill)

        self.result_pil = out
        self._show_preview(self.result_label, out)
        self._update_file_info()

    # ── File info ─────────────────────────────────────────────────────────────
    def _update_file_info(self):
        img = self.result_pil
        if img is None:
            self.file_info_lbl.setText(""); return
        w, h = img.size
        buf  = io.BytesIO()
        if self.compress_enabled.isChecked():
            img.convert("RGB").save(buf, format="JPEG", quality=self.quality_slider.value())
            fmt = "JPEG"
        else:
            img.save(buf, format="PNG"); fmt = "PNG"
        kb = len(buf.getvalue()) / 1024
        size_str = self.tr("mb").format(kb / 1024) if kb >= 1024 else self.tr("kb").format(kb)
        self.file_info_lbl.setText(self.tr("size_info").format(w, h, fmt, size_str))

    # ── Describe ──────────────────────────────────────────────────────────────
    def _describe(self):
        if self.result_pil is None:
            QMessageBox.warning(self, self.tr("no_result"), self.tr("merge_first")); return
        if not self._api_key:
            QMessageBox.warning(self, self.tr("api_key_missing"), self.tr("enter_api_key")); return
        extra = self.extra_prompt.text().strip()
        full_prompt = self._prompt + ("\n\nAdditional context: " + extra if extra else "")
        self.desc_text.setReadOnly(True)
        self.desc_text.setPlainText(self.tr("describing"))
        self._original_description = ""   # reset while fetching
        self._worker = DescribeWorker(self._api_key, self._model, full_prompt, self.result_pil, self._lang)
        self._worker.finished_ok.connect(self._on_describe_ok)
        self._worker.finished_err.connect(self._on_describe_err)
        self._worker.start()

    def _on_describe_ok(self, text: str):
        self._do_save_config()
        self._original_description = text   # store clean original
        self.desc_text.setReadOnly(False)
        self.desc_text.setPlainText(text)
        # Reset swap state: new description means no translation yet
        self._swap_lang_from = ""
        self._swap_lang_to   = self.translate_lang_combo.currentText()
        self.swap_btn.setEnabled(False)

    def _on_describe_err(self, text: str):
        self._original_description = ""
        self.desc_text.setReadOnly(False)
        self.desc_text.setPlainText(text)

    def _copy_desc(self):
        text = self.desc_text.toPlainText().strip()
        if text: QApplication.clipboard().setText(text)

    # ── Translation ───────────────────────────────────────────────────────────
    def _on_translate_lang_changed(self, _lang_name: str):
        # User manually changed the target language — reset the swap pair
        self._swap_lang_from = ""
        self._swap_lang_to   = _lang_name
        self.swap_btn.setEnabled(False)
        self._do_save_config()

    def _get_source_text(self) -> str:
        """
        Return the text that should be translated.
        If the text field contains a separator (previous translation present),
        take whatever is ABOVE the separator (the user may have edited it).
        Otherwise use the full field content.
        Falls back to _original_description if the field is empty.
        """
        full = self.desc_text.toPlainText()
        if _TRANSLATE_SEP in full:
            above = full.split(_TRANSLATE_SEP)[0].strip()
            return above if above else self._original_description.strip()
        text = full.strip()
        return text if text else self._original_description.strip()

    def _translate(self):
        if not DEEP_TRANSLATOR_AVAILABLE:
            QMessageBox.warning(self, self.tr("menu_translator"),
                                self.tr("translator_not_available"))
            return

        source_text = self._get_source_text()
        if not source_text:
            QMessageBox.information(self, self.tr("menu_translator"),
                                    self.tr("no_text_to_translate"))
            return

        self._current_source_for_translation = source_text

        # ── Remember the lang pair so swap can invert it precisely ──────────
        # _swap_lang_to   = display name of language we are translating INTO
        # _swap_lang_from = display name of language we are translating FROM
        #
        # On the very first translation _swap_lang_from is "". We resolve it
        # here by comparing the target with all known UI languages. We assume
        # the source is the app's current UI language; if the UI language equals
        # the target, we fall back to "English" as the source display name.
        new_target = self.translate_lang_combo.currentText()

        if not self._swap_lang_from:
            # Infer source display-name from the current UI language code
            ui_code = {"en": "en", "ru": "ru"}.get(self._lang, "en")
            inferred = next(
                (name for name, code in TRANSLATE_LANGUAGES.items() if code == ui_code),
                "English"
            )
            self._swap_lang_from = inferred if inferred != new_target else "English"

        self._swap_lang_to = new_target
        target_code = TRANSLATE_LANGUAGES.get(new_target, "en")

        self.translate_btn.setEnabled(False)
        self.swap_btn.setEnabled(False)
        self.desc_text.setReadOnly(True)
        self.desc_text.setPlainText(source_text + _TRANSLATE_SEP + self.tr("translating"))

        self._translate_worker = TranslateWorker(source_text, target_code,
                                                  self._translator_provider)
        self._translate_worker.finished_ok.connect(self._on_translate_ok)
        self._translate_worker.finished_err.connect(self._on_translate_err)
        self._translate_worker.start()

    def _on_translate_ok(self, translated: str):
        self.translate_btn.setEnabled(True)
        self.desc_text.setReadOnly(False)
        source = self._current_source_for_translation
        combined = source + _TRANSLATE_SEP + translated
        self.desc_text.setPlainText(combined)
        self.swap_btn.setEnabled(True)

    def _on_translate_err(self, err: str):
        self.translate_btn.setEnabled(True)
        self.desc_text.setReadOnly(False)
        source = getattr(self, "_current_source_for_translation", self._original_description)
        combined = source + _TRANSLATE_SEP + self.tr("translate_error").format(err)
        self.desc_text.setPlainText(combined)
        self.swap_btn.setEnabled(False)

    def _swap_texts(self):
        """
        Swap the upper (source) and lower (translation) blocks.
        Also swap the remembered lang pair and update the combo to the new target.
        Works correctly on repeated presses (toggles back and forth).
        """
        full = self.desc_text.toPlainText()
        if _TRANSLATE_SEP not in full:
            return

        parts = full.split(_TRANSLATE_SEP, 1)
        old_source = parts[0].strip()
        old_translation = parts[1].strip()
        if not old_translation:
            return

        # ── Swap text blocks ──────────────────────────────────────────────────
        self.desc_text.setPlainText(old_translation + _TRANSLATE_SEP + old_source)

        # Update internal source tracker
        self._original_description = old_translation
        self._current_source_for_translation = old_translation

        # ── Swap language pair ────────────────────────────────────────────────
        # old_lang_to   = language that was the target  (shown in combo right now)
        # old_lang_from = language that was the source
        old_lang_to   = self._swap_lang_to    # e.g. "Русский"
        old_lang_from = self._swap_lang_from  # e.g. "English"

        # After swap: old target → new source, old source → new target
        self._swap_lang_from = old_lang_to
        self._swap_lang_to   = old_lang_from

        # Apply the new target language to the combo box (always — both sides are known)
        if old_lang_from and old_lang_from in TRANSLATE_LANGUAGES:
            self.translate_lang_combo.blockSignals(True)
            self.translate_lang_combo.setCurrentText(old_lang_from)
            self.translate_lang_combo.blockSignals(False)
            self._do_save_config()

    # ── Save ──────────────────────────────────────────────────────────────────
    def _auto_filename(self) -> str:
        from datetime import datetime
        return "result_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def _save(self):
        if self.result_pil is None:
            QMessageBox.warning(self, self.tr("no_result"), self.tr("merge_first")); return
        use_jpeg = self.compress_enabled.isChecked()
        filt = ("JPEG (*.jpg);;PNG (*.png);;All files (*.*)" if use_jpeg
                else "PNG (*.png);;JPEG (*.jpg);;All files (*.*)")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save image", self._auto_filename() + (".jpg" if use_jpeg else ".png"), filt)
        if not path: return
        try:
            img = self.result_pil
            if path.lower().endswith((".jpg", ".jpeg")) or use_jpeg:
                if not path.lower().endswith((".jpg", ".jpeg")): path += ".jpg"
                img.convert("RGB").save(path, format="JPEG",
                                        quality=self.quality_slider.value(), optimize=True)
            else:
                if not path.lower().endswith(".png"): path += ".png"
                img.save(path, format="PNG", optimize=True)
        except Exception as e:
            QMessageBox.critical(self, self.tr("save_error"), str(e))

    # ── Config ────────────────────────────────────────────────────────────────
    def _do_save_config(self):
        self._config.update({
            "gemini_api_key":         self._api_key,
            "gemini_model":           self._model,
            "gemini_prompt":          self._prompt,
            "divider_enabled":        self.divider_enabled.isChecked(),
            "divider_color":          self._divider_color,
            "divider_width":          self.divider_width.value(),
            "compress_enabled":       self.compress_enabled.isChecked(),
            "compress_quality":       self.quality_slider.value(),
            "language":               self._lang,
            "known_models":           self._known_models,
            "merge_mode":             self._current_mode(),
            "grid_cols":              self.grid_cols.value(),
            "grid_padding":           self.grid_padding.value(),
            "grid_bg_color":          self._grid_bg_color,
            "translator_provider":    self._translator_provider,
            "translate_target_lang":  self.translate_lang_combo.currentText(),
        })
        save_config(self._config)

    def closeEvent(self, event):
        self._config["window_geometry"] = bytes(self.saveGeometry()).hex()
        self._do_save_config()
        super().closeEvent(event)

    def _restore_window(self):
        geo = self._config.get("window_geometry")
        if geo:
            try: self.restoreGeometry(bytes.fromhex(geo)); return
            except Exception: pass
        self.setGeometry(QApplication.primaryScreen().availableGeometry())


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    win = ImageMerger()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()