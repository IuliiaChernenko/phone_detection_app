import platform
import pyautogui
import time

def minimize_all_windows():
    system = platform.system().lower()
    
    # Задержка для безопасности
    pyautogui.PAUSE = 0.02
    
    if system == "windows":
        # Win + D для сворачивания всех окон
        pyautogui.hotkey("win", "d")
    elif system == "darwin":  # macOS
        # Command + Option + M или F11 для macOS
        pyautogui.hotkey("command", "option", "m")
        # Альтернатива: pyautogui.hotkey("f11")
    elif system == "linux":
        # Ctrl + Alt + D для GNOME (может отличаться для других окружений)
        pyautogui.hotkey("ctrl", "alt", "d")
    else:
        print("Операционная система не поддерживается")

if __name__ == "__main__":
    # Даём время переключиться на нужное окно
    print("Сворачивание всех окон через 2 секунды...")
    time.sleep(2)
    minimize_all_windows()