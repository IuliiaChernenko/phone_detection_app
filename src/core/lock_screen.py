import ctypes
import time
import platform
import subprocess
from PyQt5.QtWidgets import QApplication


def lock_screen() -> None:
    """
    Блокирует экран.

    Кроссплатформенно: работает на Windows, Linux и macOS.
    """
    system = platform.system()
    print(f"DEBUG: Текущая система — {system}")

    if system == "Windows":
        print("DEBUG: Вызываем блокировку экрана на Windows")
        ctypes.windll.user32.LockWorkStation()
    elif system == "Darwin":  # macOS
        print("DEBUG: Вызываем блокировку экрана на macOS")
        subprocess.run([
            "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession",
            "-suspend"
        ], check=False)
    elif system == "Linux":
        print("DEBUG: Вызываем блокировку экрана на Linux")
        # Пробуем использовать несколько стандартных команд
        commands = [
            ["xdg-screensaver", "lock"],
            ["gnome-screensaver-command", "-l"],
            ["dm-tool", "lock"],
            ["loginctl", "lock-session"],
        ]
        for cmd in commands:
            try:
                subprocess.run(cmd, check=True)
                print(f"DEBUG: Успешно выполнили команду: {' '.join(cmd)}")
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        else:
            print("ERROR: Не удалось заблокировать экран на Linux")
    else:
        raise NotImplementedError(f"Блокировка экрана не поддерживается для системы: {system}")
    
    
def is_screen_locked_windows() -> bool:
    WTS_CURRENT_SERVER_HANDLE = ctypes.c_void_p(0)
    WTS_CURRENT_SESSION = -1
    WTSConnectStateClass = 0  # Enum: WTSConnectState

    WTSActive = 0
    WTSDisconnected = 4
    WTSLocked = 8  # <-- этот код может не работать на всех системах, зависит от версии Windows

    wtsapi32 = ctypes.WinDLL('Wtsapi32.dll')
    kernel32 = ctypes.WinDLL('kernel32.dll')

    WTSQuerySessionInformationW = wtsapi32.WTSQuerySessionInformationW
    WTSFreeMemory = wtsapi32.WTSFreeMemory

    session_id = kernel32.WTSGetActiveConsoleSessionId()

    buffer = ctypes.c_void_p()
    bytes_returned = ctypes.wintypes.DWORD()

    success = WTSQuerySessionInformationW(
        WTS_CURRENT_SERVER_HANDLE,
        session_id,
        WTSConnectStateClass,
        ctypes.byref(buffer),
        ctypes.byref(bytes_returned)
    )

    if not success:
        print("DEBUG: Не удалось получить состояние сессии")
        return False

    state = ctypes.cast(buffer, ctypes.POINTER(ctypes.wintypes.DWORD)).contents.value
    WTSFreeMemory(buffer)

    if state == WTSActive:
        # print("DEBUG: Сессия активна")
        return False
    else:
        print(f"DEBUG: Сессия неактивна, состояние: {state}")
        return True


def is_screen_locked() -> bool:
    """
    Проверяет, заблокирован ли экран.

    Кроссплатформенно: работает на Windows, Linux и macOS.
    
    :return: True если экран заблокирован, иначе False
    """
    system = platform.system()
    # print(f"DEBUG: Текущая система — {system}")
    if system == "Windows":
        try:
            is_screen_locked_windows()

        except Exception as e:
            print(f"DEBUG: Ошибка проверки блокировки экрана в Windows: {e}")
            return False
    elif system == "Darwin":
        try:
            output = subprocess.run(
                ["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-s"],
                capture_output=True,
                text=True
            ).stdout

            if "Locked = 1" in output:
                print("DEBUG: Экран заблокирован (macOS: CGSession reports Locked=1)")
                return True
            else:
                print("DEBUG: Экран разблокирован (macOS)")
                return False
        except Exception as e:
            print(f"DEBUG: Ошибка проверки состояния экрана в macOS: {e}")
            return False
    elif system == "Linux":
        try:
            import getpass

            user = getpass.getuser()
            session_list = subprocess.run(
                ["loginctl", "list-sessions", "--no-legend"],
                capture_output=True,
                text=True
            ).stdout

            for line in session_list.strip().splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1] == user:
                    session_id = parts[0]
                    break
            else:
                print("DEBUG: Не удалось найти активную сессию пользователя")
                return False

            output = subprocess.run(
                ["loginctl", "show-session", session_id, "-p", "LockedHint"],
                capture_output=True,
                text=True
            ).stdout

            if "LockedHint=yes" in output:
                print("DEBUG: Экран заблокирован (Linux: LockedHint=yes)")
                return True
            else:
                print("DEBUG: Экран разблокирован (Linux)")
                return False

        except Exception as e:
            print(f"DEBUG: Ошибка проверки состояния экрана в Linux: {e}")
            return False

    # if system == "Windows":
    #     try:
    #         import win32gui

    #         # Проверяем окно блокировки
    #         hwnd = win32gui.FindWindow(None, "Windows Security")
    #         if hwnd != 0:
    #             print("DEBUG: Экран заблокирован (обнаружено окно 'Windows Security')")
    #             return True

    #         # Альтернативная проверка: если нет активного окна
    #         foreground = win32gui.GetForegroundWindow()
    #         if foreground == 0:
    #             print("DEBUG: Экран заблокирован (нет активного окна)")
    #             return True

    #         # print("DEBUG: Экран разблокирован")
    #         return False
    #     except Exception as e:
    #         print(f"DEBUG: Ошибка проверки состояния экрана в Windows: {e}")
    #         return False

    # elif system == "Darwin":  # macOS
    #     try:
    #         output = subprocess.run(
    #             ["ioreg", "-n", "IOHIDSystem"],
    #             capture_output=True,
    #             text=True
    #         ).stdout
    #         if "IOUserSessionLocked" in output and "Yes" in output:
    #             print("DEBUG: Экран заблокирован (macOS: IOUserSessionLocked=Yes)")
    #             return True
    #         else:
    #             print("DEBUG: Экран разблокирован (macOS)")
    #             return False
    #     except Exception as e:
    #         print(f"DEBUG: Ошибка проверки состояния экрана в macOS: {e}")
    #         return False

    # elif system == "Linux":
    #     try:
    #         # loginctl используется для проверки статуса сессии
    #         output = subprocess.run(
    #             ["loginctl", "show-session", str(get_current_session_id()), "-p", "LockedHint"],
    #             capture_output=True,
    #             text=True
    #         ).stdout
    #         if "LockedHint=yes" in output:
    #             print("DEBUG: Экран заблокирован (Linux: LockedHint=yes)")
    #             return True
    #         else:
    #             print("DEBUG: Экран разблокирован (Linux)")
    #             return False
    #     except Exception as e:
    #         print(f"DEBUG: Ошибка проверки состояния экрана в Linux: {e}")
    #         return False
    # else:
    #     raise NotImplementedError(f"Проверка блокировки экрана не поддерживается для системы: {system}")


def get_current_session_id() -> int:
    """
    Возвращает ID текущей сессии пользователя в Linux (для loginctl).
    """
    try:
        output = subprocess.run(
            ["loginctl", "show-user", str(get_current_uid()), "-p", "Sessions"],
            capture_output=True,
            text=True
        ).stdout
        # Пример ответа: "Sessions=2"
        session_line = output.strip()
        session_id = int(session_line.split("=")[-1])
        print(f"DEBUG: Найден ID сессии: {session_id}")
        return session_id
    except Exception as e:
        print(f"DEBUG: Ошибка получения ID сессии: {e}")
        raise RuntimeError("Не удалось получить ID текущей сессии")


def get_current_uid() -> int:
    """
    Возвращает UID текущего пользователя в Linux.
    """
    import os
    uid = os.getuid()
    print(f"DEBUG: Текущий UID: {uid}")
    return uid


def wait_for_unlock():
    """Ожидание разблокировки экрана"""
    print("DEBUG: Ожидаем разблокировку экрана")
    app = QApplication.instance()
    while is_screen_locked():
        if app:
            app.processEvents()  # Обрабатываем события PyQt5
        time.sleep(0.1)  # Проверяем каждую секунду
    print("DEBUG: Экран разблокирован, возобновляем анализ")