from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent / ".env")

def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)

def _get_int(key: str, default: int = 0) -> int:
    return int(os.getenv(key, default))

def _get_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ("true", "1", "yes")

LAUNCHER_EXE      = _get("LAUNCHER_EXE")
LAUNCHER_SETTINGS = _get("LAUNCHER_SETTINGS")

#
AUTH_TIMEOUT        = _get_int("AUTH_TIMEOUT",        60)
LAUNCHER_TIMEOUT    = _get_int("LAUNCHER_TIMEOUT",    100)
EDITION_TIMEOUT     = _get_int("EDITION_TIMEOUT",     30)
WINDOW_WAIT_TIMEOUT = _get_int("WINDOW_WAIT_TIMEOUT", 100)

MAX_CAPTCHA_RETRIES = _get_int("MAX_CAPTCHA_RETRIES", 5)
OCR_GPU             = _get_bool("OCR_GPU",  True)
OCR_LANGS           = _get("OCR_LANGS", "en,ru").split(",")

ACCOUNTS_FILE = _get("ACCOUNTS_FILE", "accounts.txt")
PROXIES_FILE  = _get("PROXIES_FILE",  "proxies.txt")
VALID_FILE    = _get("VALID_FILE",    "Valid.txt")
INVALID_FILE  = _get("INVALID_FILE",  "Invalid.txt")
BLOCKED_FILE  = _get("BLOCKED_FILE",  "Blocked.txt")
ERROR_FILE    = _get("ERROR_FILE",    "Error.txt")
EDITIONS_FILE = _get("EDITIONS_FILE", "GameEditions.txt")
LOG_FILE      = _get("LOG_FILE",      "checker.log")

LAUNCHER_WINDOWS = ("Battlestate Games Launcher", "BsgLauncher")

CAPTCHA_PHRASES = [
    "you haven't solved the captcha",
    "captcha",
    "i'm not a robot",
    "im not a robot",
    "error: 214",
    "recaptcha",
]

BLOCKED_PHRASES = [
    "рermапвпtу ulacked",
    "рermапвпtу",
    "error 229",
    "error: 229",
    "229",
]

ERROR_PHRASES = [
    "attempts left",
    "EFRUF",
    "206",
    "account not found",
    "аккаунт не найден",
    "invalid credentials",
    "failed to sign in",
    "sign in failed",
    "incorrect password",
]
