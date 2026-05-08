import json
import os
import re
import subprocess
import time

import cv2
import pydirectinput
import win32api
import win32con

from config import (
    LAUNCHER_EXE, LAUNCHER_SETTINGS, LAUNCHER_WINDOWS,
    AUTH_TIMEOUT, LAUNCHER_TIMEOUT, EDITION_TIMEOUT, MAX_CAPTCHA_RETRIES,
    VALID_FILE, INVALID_FILE, BLOCKED_FILE, ERROR_FILE, EDITIONS_FILE,
    CAPTCHA_PHRASES, BLOCKED_PHRASES, ERROR_PHRASES,
)
from engine import GameEngine, reader as ocr_reader
from logger import log


def _mouse_click():
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def _append_to_file(path: str, line: str):
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class TarkovBot:
    def __init__(self, engine: GameEngine):
        self.engine = engine


    def get_account_from_file(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return None

        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines:
            return None

        account_line = lines.pop(0).strip()
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        if ":" not in account_line:
            return None
        login, pwd = account_line.split(":", 1)
        return login.strip(), pwd.strip()

    def save_account(self, account, file_name: str):
        login, pwd = account
        _append_to_file(file_name, f"{login}:{pwd}")

    def save_valid(self, account, edition: str):
        login, pwd = account
        _append_to_file(VALID_FILE, f"{login}:{pwd} | Edition: {edition}")
        log.info(f"VALID    {login} | Edition: {edition}")

    def save_invalid(self, account):
        login, pwd = account
        _append_to_file(INVALID_FILE, f"{login}:{pwd}")
        log.info(f"INVALID  {login}")

    def save_blocked(self, account):
        login, pwd = account
        _append_to_file(BLOCKED_FILE, f"{login}:{pwd}")
        log.info(f"BLOCKED  {login}")


    def _calc_center(self, x, y, w, h, offset_x=0, offset_y=0):
        return (
            int(self.engine.left + x + w / 2 + offset_x),
            int(self.engine.top  + y + h / 2 + offset_y),
        )

    def _find_best(self, image, label: str, threshold: int = 68):
        positions = self.engine.find_text_positions(image, label, similarity_threshold=threshold)
        return max(positions, key=lambda p: p[6]) if positions else None

    def wait_and_click(self, label: str, offset_x=0, offset_y=0,
                       timeout=30, threshold=68, debug=False) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            image = self.engine.take_screenshot()
            if debug:
                self.engine.debug_print_all_texts()
            pos = self._find_best(image, label, threshold)
            if pos:
                x, y, w, h = pos[:4]
                cx, cy = self._calc_center(x, y, w, h, offset_x, offset_y)
                pydirectinput.moveTo(cx, cy, duration=0.15)
                time.sleep(0.1)
                _mouse_click()
                log.debug(f"click  '{pos[4]}'  ({cx},{cy})  score={pos[6]}")
                return True
            time.sleep(0.1)
        log.warning(f"timeout  '{label}'  ({timeout}s)")
        return False

    def input_field(self, label: str, value: str, offset_x=0, offset_y=0) -> bool:
        if not self.wait_and_click(label, offset_x=offset_x, offset_y=offset_y):
            log.error(f"Поле '{label}' не найдено")
            return False
        self.engine.press_key("ctrl+a")
        self.engine.press_key("backspace")
        self.engine.type_text(value)
        return True

    def hover_text(self, label: str, timeout=10, offset_x=0, offset_y=0, wobble=6):
        deadline = time.time() + timeout
        while time.time() < deadline:
            pos = self._find_best(self.engine.take_screenshot(), label)
            if pos:
                cx, cy = self._calc_center(*pos[:4], offset_x, offset_y)
                try:
                    for dx, dy in [(0,0),(wobble,0),(-wobble,0),(0,wobble),(0,-wobble)]:
                        win32api.SetCursorPos((cx + dx, cy + dy))
                        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy, 0, 0)
                        time.sleep(0.02)
                except Exception as e:
                    log.warning(f"hover  {e}")
                return cx, cy
            time.sleep(0.15)
        log.warning(f"hover timeout  '{label}'")
        return None

    def scroll_at(self, x: int, y: int, steps=5, amount=-120, pause=0.1) -> bool:
        try:
            win32api.SetCursorPos((x, y))
            time.sleep(0.05)
            for _ in range(steps):
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
                time.sleep(pause)
            return True
        except Exception as e:
            log.error(f"scroll_at  {e}")
            return False

    def scroll_until_found(self, hover_label: str, target_label: str,
                           lines_per_scroll=5, max_scrolls=20, timeout=30,
                           scroll_pause=0.1, offset_x=0, offset_y=0):
        hover_pos = self.hover_text(hover_label, timeout=min(10, timeout / 2),
                                    offset_x=offset_x, offset_y=offset_y)
        if not hover_pos:
            log.error(f"Не удалось навести мышь на '{hover_label}'")
            return None

        hx, hy = hover_pos
        deadline = time.time() + timeout

        for scrolls_done in range(max_scrolls):
            if time.time() > deadline:
                break
            pos = self._find_best(self.engine.take_screenshot(), target_label)
            if pos:
                log.debug(f"found  '{pos[4]}'  after {scrolls_done} scrolls  score={pos[6]}")
                return pos[:4]
            try:
                win32api.SetCursorPos((hx, hy))
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 0, 0, 0)
            except Exception:
                pass
            for _ in range(lines_per_scroll):
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120, 0)
                time.sleep(scroll_pause)
            time.sleep(0.12)

        log.warning(f"scroll timeout  '{target_label}'")
        return None


    @staticmethod
    def _extract_edition(full_text: str, texts: list) -> str | None:
        m = re.search(r'game\s*edition[:\s]+(.+?)(server|$)', full_text)
        if m:
            return m.group(1).replace(":", "").strip()
        for i, text in enumerate(texts):
            if "game edition" in text.lower():
                if ":" in text:
                    return text.split(":", 1)[1].strip()
                if i + 1 < len(texts):
                    return texts[i + 1].strip()
        for i, text in enumerate(texts):
            if "server" in text.lower() and i > 0:
                prev = texts[i - 1]
                if "edition" in prev.lower():
                    return prev.split(":", 1)[-1].strip()
        return None

    def parse_game_edition(self, timeout=EDITION_TIMEOUT, save_to_account=None) -> str | None:
        log.info("Парсим Game Edition...")
        deadline = time.time() + timeout

        while time.time() < deadline:
            image = self.engine.take_screenshot()
            if image is None or image.size == 0:
                time.sleep(0.5)
                continue

            h, w = image.shape[:2]
            crop = image[max(0, h - 120):h, max(0, w - 700):w]
            if crop.size == 0:
                time.sleep(0.5)
                continue

            ch, cw = crop.shape[:2]
            gray = cv2.cvtColor(
                cv2.resize(crop, (cw * 2, ch * 2), interpolation=cv2.INTER_CUBIC),
                cv2.COLOR_BGR2GRAY,
            )
            results = ocr_reader.readtext(gray)
            if not results:
                time.sleep(0.5)
                continue

            texts     = [t.strip() for _, t, _ in results]
            full_text = " ".join(texts).lower()
            log.debug(f"OCR edition: {texts}")

            edition = self._extract_edition(full_text, texts)
            if edition:
                log.info(f"Game Edition: {edition}")
                if save_to_account:
                    login, _ = save_to_account
                    _append_to_file(EDITIONS_FILE, f"{login}:{edition}")
                return edition

            time.sleep(0.5)

        log.warning("Game Edition не найден за timeout")
        return None



    def _clear_launcher_settings(self):
        if not os.path.exists(LAUNCHER_SETTINGS):
            log.warning("settings лаунчера не найден")
            return
        try:
            with open(LAUNCHER_SETTINGS, "r", encoding="utf-8") as f:
                data = json.load(f)
            removed = [k for k in ("login", "password") if data.pop(k, None) is not None]
            if removed:
                with open(LAUNCHER_SETTINGS, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                log.info(f"Очищены settings: {', '.join(removed)}")
        except Exception as e:
            log.error(f"Очистка settings: {e}")

    def restart_launcher(self) -> bool:
        log.info("Перезапуск лаунчера...")
        os.system("taskkill /f /im BsgLauncher.exe >nul 2>&1")
        time.sleep(2)
        self._clear_launcher_settings()

        if not os.path.exists(LAUNCHER_EXE):
            log.error(f"Лаунчер не найден: {LAUNCHER_EXE}")
            return False

        proc = subprocess.Popen([LAUNCHER_EXE])
        time.sleep(3)

        if proc.poll() is not None:
            log.error(f"Лаунчер упал, код: {proc.returncode}")
            return False

        log.info(f"Лаунчер запущен, PID: {proc.pid}")
        time.sleep(10)
        return True

    def _wait_for_login_window(self, timeout=LAUNCHER_TIMEOUT) -> bool:
        log.info("Ожидаем окно 'Login'...")
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                self.engine._init_window("Login")
                self.engine.window_name = "Login"
                log.info("Окно 'Login' найдено")
                return True
            except Exception:
                time.sleep(1)
        log.error("Окно 'Login' не появилось")
        return False


    def _check_screen_for_phrases(self, image, phrases: list,
                                   threshold: int, min_len: int = 4) -> str | None:
        for phrase in phrases:
            positions = self.engine.find_text_positions(image, phrase, similarity_threshold=threshold)
            if positions:
                found = positions[0][4].strip()
                if len(found) >= min_len:
                    return found
        return None

    def _is_blocked_screen(self, image) -> bool:
        texts    = ocr_reader.readtext(image, detail=0)
        all_text = " ".join(t.lower() for t in texts)
        log.debug(f"OCR screen: {texts}")
        return (
            "229"               in all_text
            or "рermапвпtу"    in all_text
            or "рermапвпtу ulacked" in all_text
        )

    def _do_login(self, account) -> bool:
        login, pwd = account
        log.info(f"Авторизация: {login}")
        if not self.input_field("E-mail or login", login):
            return False
        time.sleep(0.3)
        if not self.input_field("Password", pwd):
            return False
        time.sleep(0.3)
        return self.wait_and_click("Authorize", timeout=15)

    def _wait_for_auth_result(self) -> str:
        deadline = time.time() + AUTH_TIMEOUT

        while time.time() < deadline:
            for window_name in LAUNCHER_WINDOWS:
                try:
                    self.engine._init_window(window_name)
                    self.engine.window_name = window_name
                    log.info(f"Лаунчер открылся: {window_name}")
                    return "launched"
                except Exception:
                    pass

            image = self.engine.take_screenshot()

            found = self._check_screen_for_phrases(image, CAPTCHA_PHRASES, threshold=80)
            if found:
                log.warning(f"CAPTCHA: '{found}'")
                return "captcha"

            if self._is_blocked_screen(image):
                log.warning("BLOCKED: ERROR 229")
                return "blocked"

            found = self._check_screen_for_phrases(image, ERROR_PHRASES, threshold=85, min_len=6)
            if found:
                log.warning(f"INVALID: '{found}'")
                return "invalid"

            time.sleep(1)

        return "timeout"

    def run_account_scenario(self, account, max_captcha_retries=MAX_CAPTCHA_RETRIES) -> str | None:
        login, _ = account

        for attempt in range(1, max_captcha_retries + 1):
            log.info(f"Попытка {attempt}/{max_captcha_retries}: {login}")

            if not self._do_login(account):
                return None

            result = self._wait_for_auth_result()

            if result == "captcha":
                if attempt >= max_captcha_retries:
                    log.warning(f"Капча на всех {max_captcha_retries} попытках → Error")
                    self.save_account(account, ERROR_FILE)
                    return None
                log.info("Капча — перезапускаем лаунчер...")
                self.restart_launcher()
                if not self._wait_for_login_window():
                    return None
                continue

            if result == "blocked":
                self.save_blocked(account)
                return "blocked"

            if result == "invalid":
                self.save_invalid(account)
                return "invalid"

            if result == "launched":
                break

            log.warning("Нет ответа от сервера → Invalid")
            self.save_invalid(account)
            return "invalid"

        log.info("Ждём полной загрузки лаунчера...")
        time.sleep(5)

        edition = self.parse_game_edition(save_to_account=account)
        if edition:
            self.save_valid(account, edition)
            return "valid"

        log.warning("Game Edition не найден → Invalid")
        self.save_invalid(account)
        return "invalid"
