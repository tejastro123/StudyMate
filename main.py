"""
main.py
=======
StudyMate application entry point.

Bootstrap sequence:
1. Configure logging
2. Initialise database
3. Load configuration (API key, theme, etc.)
4. Build and show the MainWindow with all registered pages
"""

import sys
import logging
import json
import os
from pathlib import Path

try:
    import keyring
    _KEYRING_AVAILABLE = True
except ImportError:  # pragma: no cover
    keyring = None  # type: ignore
    _KEYRING_AVAILABLE = False

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

# ── Bootstrap logging before any other imports ─────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── Config path ────────────────────────────────────────────────────────────
_APPDATA = os.getenv("APPDATA", str(Path.home()))
_CONFIG_PATH = Path(_APPDATA) / "StudyMate" / "config.json"

DEFAULT_CONFIG = {
    "theme": "dark",
    "pomodoro_work": 25,
    "pomodoro_short_break": 5,
    "pomodoro_long_break": 15,
    "notifications_enabled": True,
    "ai_provider": "ollama",
    "ollama_model": "llama3",
    # NOTE: api_key is stored in the OS keyring, NOT in this dict.
}


_KEYRING_SERVICE = "StudyMate"
_KEYRING_USERNAME = "anthropic_api_key"


def get_secret(key_name: str) -> str:
    """Retrieve a generic secret from the OS keyring."""
    if _KEYRING_AVAILABLE:
        try:
            return keyring.get_password(_KEYRING_SERVICE, key_name) or ""
        except Exception as exc:
            logger.warning("keyring read failed for %s: %s", key_name, exc)
    return ""


def set_secret(key_name: str, value: str) -> None:
    """Store a generic secret in the OS keyring."""
    if _KEYRING_AVAILABLE:
        try:
            keyring.set_password(_KEYRING_SERVICE, key_name, value)
            logger.info("Secret %s stored in OS keyring.", key_name)
            return
        except Exception as exc:
            logger.warning("keyring write failed for %s: %s", key_name, exc)
    logger.warning("keyring not available — secret %s NOT saved securely.", key_name)


def load_config() -> dict:
    """Load config.json from APPDATA, creating it with defaults if absent."""
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _CONFIG_PATH.exists():
        _CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        logger.info("Created default config at %s", _CONFIG_PATH)
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        # Merge any missing keys from defaults
        updated = False
        for key, value in DEFAULT_CONFIG.items():
            if key not in cfg:
                cfg[key] = value
                updated = True
        # Inject secrets from keyring
        cfg["api_key"] = get_secret(_KEYRING_USERNAME)
        cfg["supabase_key"] = get_secret("supabase_key")
        return cfg
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load config: %s – using defaults", exc)
        return {**DEFAULT_CONFIG, "api_key": get_secret(_KEYRING_USERNAME), "supabase_key": get_secret("supabase_key")}


def save_config(cfg: dict) -> None:
    """Persist non-secret config to config.json; api_key goes to keyring."""
    try:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Strip secrets from the file
        secrets = {"api_key", "supabase_key"}
        file_cfg = {k: v for k, v in cfg.items() if k not in secrets}
        with open(_CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(file_cfg, fh, indent=2)
        # Persist secrets separately
        if "api_key" in cfg:
            set_secret(_KEYRING_USERNAME, cfg["api_key"])
        if "supabase_key" in cfg:
            set_secret("supabase_key", cfg["supabase_key"])
    except OSError as exc:
        logger.error("Failed to save config: %s", exc)


def load_stylesheet(theme: str = "dark") -> str:
    """Read the QSS theme file and return it as a string."""
    qss_path = Path(__file__).parent / "styles" / "theme.qss"
    try:
        return qss_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not load stylesheet: %s", exc)
        return ""


def main():
    # ── Database ───────────────────────────────────────────────────────
    from database.db import initialise_database
    initialise_database()

    # ── Config ─────────────────────────────────────────────────────────
    cfg = load_config()

    # ── Qt Application ─────────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("StudyMate")
    app.setApplicationVersion("1.0.0")

    # Global font
    font = QFont("Segoe UI", 13)
    app.setFont(font)

    # Stylesheet
    app.setStyleSheet(load_stylesheet(cfg.get("theme", "dark")))

    # ── Main Window ─────────────────────────────────────────────────────
    from ui.main_window import MainWindow
    window = MainWindow()

    # ── Pages ────────────────────────────────────────────────────────────
    from ui.dashboard_ui import DashboardPage
    from ui.flashcard_ui import FlashcardPage
    from ui.quiz_ui import QuizPage
    from ui.timetable_ui import TimetablePage
    from ui.timer_ui import TimerPage
    from ui.assistant_ui import AssistantPage
    from ui.settings_ui import SettingsPage

    dashboard = DashboardPage(navigate_fn=window.navigate_to)
    flashcards = FlashcardPage(cfg=cfg)
    quizzes = QuizPage()
    timetable = TimetablePage()
    timer = TimerPage(cfg=cfg, save_config_fn=save_config)
    assistant = AssistantPage(cfg=cfg, save_config_fn=save_config)
    settings = SettingsPage(cfg=cfg, save_config_fn=save_config, app=app)

    window.register_page("Dashboard", dashboard)
    window.register_page("Flashcards", flashcards)
    window.register_page("Quizzes", quizzes)
    window.register_page("Timetable", timetable)
    window.register_page("Focus Timer", timer)
    window.register_page("AI Assistant", assistant)
    window.register_page("Settings", settings)

    # Connect settings theme change signal
    settings.theme_changed.connect(lambda t: app.setStyleSheet(load_stylesheet(t)))

    # Start on Dashboard
    window.navigate_to("Dashboard")

    window.show()
    logger.info("StudyMate started.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
