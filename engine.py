import time

import cv2
import easyocr
import numpy as np
import pyautogui
import pydirectinput
import pyperclip
import win32gui
from rapidfuzz import fuzz

from config import OCR_GPU, OCR_LANGS
from logger import log

reader = easyocr.Reader(OCR_LANGS, gpu=OCR_GPU)


class GameEngine:
    def __init__(self, window_name: str = "Login"):
        self.window_name = window_name
        self.left = self.top = self.width = self.height = 0
        self._init_window()

    def _init_window(self, window_name: str = None):
        name = window_name or self.window_name
        hwnd = win32gui.FindWindow(None, name)
        if hwnd == 0:
            raise RuntimeError(f"Окно '{name}' не найдено")
        rect = win32gui.GetClientRect(hwnd)
        left, top     = win32gui.ClientToScreen(hwnd, (rect[0], rect[1]))
        right, bottom = win32gui.ClientToScreen(hwnd, (rect[2], rect[3]))
        self.width, self.height = right - left, bottom - top
        self.left, self.top = left, top
        return hwnd

    def take_screenshot(self):
        screenshot = pyautogui.screenshot(region=(self.left, self.top, self.width, self.height))
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def find_text_positions(self, image, target_text: str, similarity_threshold: int = 68):
        positions = []
        for bbox, text, confidence in reader.readtext(image):
            score = fuzz.partial_ratio(target_text.lower(), text.lower())
            if score >= similarity_threshold:
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                x, y = min(xs), min(ys)
                w, h = max(xs) - x, max(ys) - y
                positions.append((x, y, w, h, text, confidence, score))
        return positions

    def click_center(self, x, y, w, h, offset_x=0, offset_y=0):
        cx = int(self.left + x + w / 2 + offset_x)
        cy = int(self.top  + y + h / 2 + offset_y)
        pydirectinput.moveTo(cx, cy)
        time.sleep(0.5)
        pydirectinput.leftClick(cx, cy)
        log.debug(f"click_center ({cx}, {cy})")
        return cx, cy

    def click_at(self, x: int, y: int):
        pydirectinput.moveTo(x, y)
        time.sleep(0.05)
        pydirectinput.leftClick(x, y)
        time.sleep(0.05)
        log.debug(f"click_at ({x}, {y})")

    def move_mouse(self, x: int, y: int):
        pydirectinput.moveTo(x, y)

    def type_text(self, text: str):
        pyperclip.copy(text)
        time.sleep(0.1)
        pydirectinput.keyDown("ctrl")
        pydirectinput.press("v")
        pydirectinput.keyUp("ctrl")
        log.debug(f"type  '{text}'")

    def press_key(self, key: str):
        pydirectinput.press(key)
        log.debug(f"press '{key}'")

    def scroll(self, amount: int):
        pyautogui.moveTo(self.left + self.width // 2, self.top + self.height // 2)
        pyautogui.scroll(amount)

    def wait_for_text(self, label: str, timeout: int = 30) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.find_text_positions(self.take_screenshot(), label):
                return True
            time.sleep(0.5)
        return False

    def debug_print_all_texts(self):
        log.debug("Все тексты на экране:")
        for bbox, text, conf in reader.readtext(self.take_screenshot()):
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            x, y = min(xs), min(ys)
            w, h = max(xs) - x, max(ys) - y
            log.debug(f"  '{text}'  conf={conf:.2f}  bbox=({x},{y},{w},{h})")
