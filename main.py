import time

from bot import TarkovBot
from config import ACCOUNTS_FILE, PROXIES_FILE, WINDOW_WAIT_TIMEOUT, ERROR_FILE
from engine import GameEngine
from logger import log
from proxifier_manager import apply_proxy

RESULT_LABELS = {
    "valid":   "VALID",
    "invalid": "INVALID",
    "blocked": "BLOCKED",
}


def load_first_proxy(file_path: str = PROXIES_FILE) -> dict | None:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        log.warning(f"Файл '{file_path}' не найден — без прокси")
        return None

    if not lines:
        log.warning("Файл прокси пуст — без прокси")
        return None

    parts = lines[0].split(":", 3)
    if len(parts) < 2:
        log.error(f"Неверный формат прокси: '{lines[0]}'")
        return None

    return {
        "ip":       parts[0],
        "port":     parts[1],
        "login":    parts[2] if len(parts) > 2 else "",
        "password": parts[3] if len(parts) > 3 else "",
        "address":  f"{parts[0]}:{parts[1]}",
    }


def wait_for_window(window_name: str, timeout: int = WINDOW_WAIT_TIMEOUT) -> GameEngine | None:
    log.info(f"Ожидаем окно '{window_name}'...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            engine = GameEngine(window_name=window_name)
            log.info(f"Окно '{window_name}' найдено  ({engine.width}x{engine.height})")
            return engine
        except Exception:
            time.sleep(1)
    log.error(f"Окно '{window_name}' не появилось за {timeout}с")
    return None


def main():
    proxy = load_first_proxy()
    if proxy:
        apply_proxy(proxy)
        log.info(f"Proxifier: {proxy['address']}")
    else:
        log.warning("Proxifier не запущен")

    tmp_bot = TarkovBot(engine=None)

    while True:
        account = tmp_bot.get_account_from_file(ACCOUNTS_FILE)
        if not account:
            log.info("Все аккаунты обработаны.")
            break

        login = account[0]
        log.info("=" * 48)
        log.info(f"Аккаунт: {login}")

        try:
            tmp_bot.restart_launcher()

            engine = wait_for_window("Login")
            if engine is None:
                log.error(f"Окно Login не появилось — пропускаем {login}")
                tmp_bot.save_account(account, ERROR_FILE)
                continue

            result = TarkovBot(engine).run_account_scenario(account)
            label  = RESULT_LABELS.get(result, "? ERROR")
            log.info(f"{label}  {login}")

            if result is None:
                tmp_bot.save_account(account, ERROR_FILE)

        except Exception as e:
            log.exception(f"Необработанная ошибка [{login}]: {e}")
            tmp_bot.save_account(account, ERROR_FILE)

        finally:
            log.info("=" * 48)
            time.sleep(2)

    log.info("Готово.")


if __name__ == "__main__":
    main()
