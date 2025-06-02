import ctypes
import time
import platform
import subprocess
from ctypes import wintypes
# from PyQt5.QtWidgets import QApplication
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)


def lock_screen() -> None:
    """
    Блокирует экран.

    Кроссплатформенно: работает на Windows, Linux и macOS.
    """
    system = platform.system()
    logger.debug(f"DEBUG: Текущая система — {system}")

    if system == "Windows":
        logger.debug("DEBUG: Вызываем блокировку экрана на Windows")
        ctypes.windll.user32.LockWorkStation()
    elif system == "Darwin":  # macOS
        logger.debug("DEBUG: Вызываем блокировку экрана на macOS")
        subprocess.run([
            "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession",
            "-suspend"
        ], check=False)
    elif system == "Linux":
        logger.debug("DEBUG: Вызываем блокировку экрана на Linux")
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
                logger.debug(f"DEBUG: Успешно выполнили команду: {' '.join(cmd)}")
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        else:
            logger.debug("ERROR: Не удалось заблокировать экран на Linux")
    else:
        raise NotImplementedError(f"Блокировка экрана не поддерживается для системы: {system}")
    
    
# def is_screen_locked_windows() -> bool:
#     WTS_CURRENT_SERVER_HANDLE = ctypes.c_void_p(0)
#     WTS_CURRENT_SESSION = -1
#     WTSConnectStateClass = 0  # Enum: WTSConnectState

#     WTSActive = 0
#     WTSDisconnected = 4
#     WTSLocked = 8  # <-- этот код может не работать на всех системах, зависит от версии Windows

#     wtsapi32 = ctypes.WinDLL('Wtsapi32.dll')
#     kernel32 = ctypes.WinDLL('kernel32.dll')

#     WTSQuerySessionInformationW = wtsapi32.WTSQuerySessionInformationW
#     WTSFreeMemory = wtsapi32.WTSFreeMemory

#     session_id = kernel32.WTSGetActiveConsoleSessionId()

#     buffer = ctypes.c_void_p()
#     bytes_returned = ctypes.wintypes.DWORD()

#     success = WTSQuerySessionInformationW(
#         WTS_CURRENT_SERVER_HANDLE,
#         session_id,
#         WTSConnectStateClass,
#         ctypes.byref(buffer),
#         ctypes.byref(bytes_returned)
#     )

#     if not success:
#         print("DEBUG: Не удалось получить состояние сессии")
#         return False

#     state = ctypes.cast(buffer, ctypes.POINTER(ctypes.wintypes.DWORD)).contents.value
#     WTSFreeMemory(buffer)

#     if state == WTSActive:
#         # print("DEBUG: Сессия активна")
#         return False
#     else:
#         print(f"DEBUG: Сессия неактивна, состояние: {state}")
#         return True


# def is_screen_locked_windows() -> bool:
#     # Константы WTS
#     WTS_CURRENT_SERVER_HANDLE = ctypes.c_void_p(0)
#     WTS_CURRENT_SESSION = -1
#     WTS_CONNECTSTATE_CLASS = 4  # WTSConnectState

#     # Возможные состояния сессии
#     WTSActive = 0
#     WTSConnected = 1
#     WTSConnectQuery = 2
#     WTSShadow = 3
#     WTSDisconnected = 4
#     WTSIdle = 5
#     WTSListen = 6
#     WTSReset = 7
#     WTSDown = 8
#     WTSInit = 9
#     # WTSLocked отсутствует в явном виде, но может быть связано с WTSDisconnected

#     # Загрузка библиотек
#     wtsapi32 = ctypes.WinDLL('wtsapi32.dll')
#     kernel32 = ctypes.WinDLL('kernel32.dll')

#     # Определение прототипов функций
#     WTSQuerySessionInformationW = wtsapi32.WTSQuerySessionInformationW
#     WTSQuerySessionInformationW.argtypes = [
#         wintypes.HANDLE,
#         wintypes.DWORD,
#         wintypes.DWORD,
#         ctypes.POINTER(ctypes.c_void_p),
#         ctypes.POINTER(wintypes.DWORD)
#     ]
#     WTSQuerySessionInformationW.restype = wintypes.BOOL

#     WTSFreeMemory = wtsapi32.WTSFreeMemory
#     WTSFreeMemory.argtypes = [ctypes.c_void_p]
#     WTSFreeMemory.restype = None

#     WTSGetActiveConsoleSessionId = kernel32.WTSGetActiveConsoleSessionId
#     WTSGetActiveConsoleSessionId.restype = wintypes.DWORD

#     # Получение ID сессии
#     session_id = WTSGetActiveConsoleSessionId()
#     # print(f"DEBUG: Session ID: {session_id}")

#     buffer = ctypes.c_void_p()
#     bytes_returned = wintypes.DWORD()

#     # Запрос состояния сессии
#     success = WTSQuerySessionInformationW(
#         WTS_CURRENT_SERVER_HANDLE,
#         session_id,
#         WTS_CONNECTSTATE_CLASS,
#         ctypes.byref(buffer),
#         ctypes.byref(bytes_returned)
#     )

#     if not success:
#         error_code = ctypes.get_last_error()
#         print(f"DEBUG: Не удалось получить состояние сессии, ошибка: {error_code}")
#         return False

#     # Получение значения состояния
#     state = ctypes.cast(buffer, ctypes.POINTER(wintypes.DWORD)).contents.value
#     WTSFreeMemory(buffer)

#     # Отладочная информация
#     state_map = {
#         WTSActive: "WTSActive",
#         WTSConnected: "WTSConnected",
#         WTSConnectQuery: "WTSConnectQuery",
#         WTSShadow: "WTSShadow",
#         WTSDisconnected: "WTSDisconnected",
#         WTSIdle: "WTSIdle",
#         WTSListen: "WTSListen",
#         WTSReset: "WTSReset",
#         WTSDown: "WTSDown",
#         WTSInit: "WTSInit"
#     }
#     state_name = state_map.get(state, f"Unknown state: {state}")
#     if state != 1:
#         print(f"DEBUG: Состояние сессии: {state_name} ({state})")

#     # Проверка на заблокированный экран
#     # Экран считается заблокированным, если состояние не WTSActive
#     return state != WTSActive


# def is_screen_locked_windows() -> bool:
#     user32 = ctypes.WinDLL('user32.dll')
#     OpenInputDesktop = user32.OpenInputDesktop
#     OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
#     OpenInputDesktop.restype = wintypes.HDESK

#     CloseDesktop = user32.CloseDesktop
#     CloseDesktop.argtypes = [wintypes.HDESK]
#     CloseDesktop.restype = wintypes.BOOL

#     # Пытаемся открыть текущий рабочий стол
#     desktop = OpenInputDesktop(0, False, 0)
#     if not desktop:
#         print("DEBUG: Не удалось открыть рабочий стол")
#         return True  # Экран, скорее всего, заблокирован

#     # Получаем имя рабочего стола
#     buffer = ctypes.create_unicode_buffer(256)
#     user32.GetUserObjectInformationW(
#         desktop, 2, buffer, 256, None  # 2 = UOI_NAME
#     )
#     desktop_name = buffer.value
#     CloseDesktop(desktop)

#     print(f"DEBUG: Имя рабочего стола: {desktop_name}")
#     # Если имя рабочего стола "Default", экран не заблокирован
#     return desktop_name != "Default"


# def is_screen_locked_windows() -> bool:
#     # Константы WTS
#     WTS_CURRENT_SERVER_HANDLE = ctypes.c_void_p(0)
#     WTS_CONNECTSTATE_CLASS = 4  # WTSConnectState
#     WTS_SESSIONSTATE_CLASS = 24  # WTSSessionState (Windows 10/11)

#     # Возможные состояния сессии
#     WTSActive = 0
#     WTSConnected = 1
#     WTSDisconnected = 4
#     WTSLocked = 8  # Не всегда используется

#     # Загрузка библиотек
#     wtsapi32 = ctypes.WinDLL('wtsapi32.dll')
#     kernel32 = ctypes.WinDLL('kernel32.dll')

#     # Определение прототипов функций
#     WTSQuerySessionInformationW = wtsapi32.WTSQuerySessionInformationW
#     WTSQuerySessionInformationW.argtypes = [
#         wintypes.HANDLE,
#         wintypes.DWORD,
#         wintypes.DWORD,
#         ctypes.POINTER(ctypes.c_void_p),
#         ctypes.POINTER(wintypes.DWORD)
#     ]
#     WTSQuerySessionInformationW.restype = wintypes.BOOL

#     WTSFreeMemory = wtsapi32.WTSFreeMemory
#     WTSFreeMemory.argtypes = [ctypes.c_void_p]
#     WTSFreeMemory.restype = None

#     WTSGetActiveConsoleSessionId = kernel32.WTSGetActiveConsoleSessionId
#     WTSGetActiveConsoleSessionId.restype = wintypes.DWORD

#     # Получение ID сессии
#     session_id = WTSGetActiveConsoleSessionId()
#     print(f"DEBUG: Session ID: {session_id}")

#     buffer = ctypes.c_void_p()
#     bytes_returned = wintypes.DWORD()

#     # Запрос состояния подключения
#     success = WTSQuerySessionInformationW(
#         WTS_CURRENT_SERVER_HANDLE,
#         session_id,
#         WTS_CONNECTSTATE_CLASS,
#         ctypes.byref(buffer),
#         ctypes.byref(bytes_returned)
#     )

#     if not success:
#         error_code = ctypes.get_last_error()
#         print(f"DEBUG: Не удалось получить состояние сессии, ошибка: {error_code}")
#         return False

#     state = ctypes.cast(buffer, ctypes.POINTER(wintypes.DWORD)).contents.value
#     WTSFreeMemory(buffer)

#     state_map = {
#         WTSActive: "WTSActive",
#         WTSConnected: "WTSConnected",
#         WTSDisconnected: "WTSDisconnected",
#         WTSLocked: "WTSLocked"
#     }
#     print(f"DEBUG: Состояние сессии: {state_map.get(state, f'Unknown state: {state}')} ({state})")

#     # Дополнительная проверка состояния блокировки (Windows 10/11)
#     buffer = ctypes.c_void_p()
#     bytes_returned = wintypes.DWORD()

#     success = WTSQuerySessionInformationW(
#         WTS_CURRENT_SERVER_HANDLE,
#         session_id,
#         WTS_SESSIONSTATE_CLASS,  # Проверка состояния блокировки
#         ctypes.byref(buffer),
#         ctypes.byref(bytes_returned)
#     )

#     if success:
#         lock_state = ctypes.cast(buffer, ctypes.POINTER(wintypes.DWORD)).contents.value
#         WTSFreeMemory(buffer)
#         print(f"DEBUG: Состояние блокировки: {lock_state} (0=Active, 1=Locked, 2=Unlocked)")
#         return lock_state == 1  # 1 = SessionLocked
#     else:
#         error_code = ctypes.get_last_error()
#         print(f"DEBUG: Не удалось получить состояние блокировки, ошибка: {error_code}")

#     # Если WTSSessionState недоступно, используем состояние сессии
#     return state == WTSDisconnected


# def is_screen_locked_windows() -> bool:
#     user32 = ctypes.WinDLL('user32.dll')
#     OpenInputDesktop = user32.OpenInputDesktop
#     OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
#     OpenInputDesktop.restype = wintypes.HDESK

#     CloseDesktop = user32.CloseDesktop
#     CloseDesktop.argtypes = [wintypes.HDESK]
#     CloseDesktop.restype = wintypes.BOOL

#     desktop = OpenInputDesktop(0, False, 0)
#     if not desktop:
#         print("DEBUG: Не удалось открыть рабочий стол")
#         return True

#     buffer = ctypes.create_unicode_buffer(256)
#     user32.GetUserObjectInformationW(desktop, 2, buffer, 256, None)  # 2 = UOI_NAME
#     desktop_name = buffer.value
#     CloseDesktop(desktop)

#     print(f"DEBUG: Имя рабочего стола: {desktop_name}")
#     return desktop_name != "Default"

# wtsapi32 = ctypes.WinDLL('wtsapi32')

# class WTSINFOEX_LEVEL1(ctypes.Structure):
#     _fields_ = [
#         ("SessionId", wintypes.DWORD),
#         ("SessionState", wintypes.DWORD),
#         ("SessionFlags", wintypes.DWORD),
#     ]

# class WTSINFOEX(ctypes.Structure):
#     _fields_ = [
#         ("Level", wintypes.DWORD),
#         ("Data", WTSINFOEX_LEVEL1),
#     ]

# def is_screen_locked_windows():
#     WTS_CURRENT_SERVER_HANDLE = 0
#     WTS_CURRENT_SESSION = -1
#     WTSSessionInfoEx = 14

#     buffer = ctypes.c_void_p()
#     bytes_returned = wintypes.DWORD()

#     success = wtsapi32.WTSQuerySessionInformationW(
#         WTS_CURRENT_SERVER_HANDLE,
#         WTS_CURRENT_SESSION,
#         WTSSessionInfoEx,
#         ctypes.byref(buffer),
#         ctypes.byref(bytes_returned)
#     )

#     if not success:
#         error_code = ctypes.get_last_error()
#         print(f"Не удалось запросить информацию о сессии, код ошибки: {error_code}")
#         return None

#     try:
#         info = ctypes.cast(buffer, ctypes.POINTER(WTSINFOEX)).contents
#         if info.Level != 1:
#             print(f"Неожиданный уровень: {info.Level}")
#             return None

#         session_flags = info.Data.SessionFlags
#         if session_flags == 0:
#             return True  # Заблокировано
#         elif session_flags == 1:
#             return False  # Разблокировано
#         else:
#             print(f"Неизвестный флаг сессии: {session_flags}")
#             return None
#     finally:
#         wtsapi32.WTSFreeMemory(buffer)


process_name='LogonUI.exe'
callall='TASKLIST'
# def is_screen_locked_windows():
#     outputall=subprocess.check_output(callall)
#     outputstringall=str(outputall)
#     if process_name in outputstringall:
#         logger.debug("Locked.")
#         return True
#     else: 
#         logger.debug("Unlocked.")
#         return False
def is_screen_locked_windows():
    try:
        # Используем TASKLIST с CREATE_NO_WINDOW
        result = subprocess.run(
            ['tasklist'],
            capture_output=True,
            text=True,
            shell=False,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        output = result.stdout
        if 'LogonUI.exe' in output:
            logger.debug("Locked.")
            return True
        logger.debug("Unlocked.")
        return False
    except Exception as e:
        logger.debug(f"Error checking screen lock: {e}")
        return False


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
            return is_screen_locked_windows()

        except Exception as e:
            logger.debug(f"DEBUG: Ошибка проверки блокировки экрана в Windows: {e}")
            return False
    elif system == "Darwin":
        try:
            output = subprocess.run(
                ["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-s"],
                capture_output=True,
                text=True
            ).stdout

            if "Locked = 1" in output:
                logger.debug("DEBUG: Экран заблокирован (macOS: CGSession reports Locked=1)")
                return True
            else:
                logger.debug("DEBUG: Экран разблокирован (macOS)")
                return False
        except Exception as e:
            logger.debug(f"DEBUG: Ошибка проверки состояния экрана в macOS: {e}")
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
                logger.debug("DEBUG: Не удалось найти активную сессию пользователя")
                return False

            output = subprocess.run(
                ["loginctl", "show-session", session_id, "-p", "LockedHint"],
                capture_output=True,
                text=True
            ).stdout

            if "LockedHint=yes" in output:
                logger.debug("DEBUG: Экран заблокирован (Linux: LockedHint=yes)")
                return True
            else:
                logger.debug("DEBUG: Экран разблокирован (Linux)")
                return False

        except Exception as e:
            logger.debug(f"DEBUG: Ошибка проверки состояния экрана в Linux: {e}")
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
        logger.debug(f"DEBUG: Найден ID сессии: {session_id}")
        return session_id
    except Exception as e:
        logger.debug(f"DEBUG: Ошибка получения ID сессии: {e}")
        raise RuntimeError("Не удалось получить ID текущей сессии")


def get_current_uid() -> int:
    """
    Возвращает UID текущего пользователя в Linux.
    """
    import os
    uid = os.getuid()
    logger.debug(f"DEBUG: Текущий UID: {uid}")
    return uid


# def wait_for_unlock():
#     """Ожидание разблокировки экрана"""
#     system = platform.system()

#     if system == "Windows":
#         import ctypes
#         from ctypes import wintypes

#         user32 = ctypes.WinDLL('user32', use_last_error=True)
#         WTS_CURRENT_SERVER_HANDLE = 0
#         WTS_SESSION_LOCK = 0x7
#         WTS_SESSION_UNLOCK = 0x8

#         def register_session_notification():
#             user32.WTSRegisterSessionNotification.restype = wintypes.BOOL
#             user32.WTSRegisterSessionNotification.argtypes = [wintypes.HWND, wintypes.DWORD]
#             return user32.WTSRegisterSessionNotification(0, 0)

#         if not register_session_notification():
#             print("Ошибка регистрации уведомлений")
#             return False

#         msg = wintypes.MSG()
#         while True:
#             if user32.GetMessageW(ctypes.byref(msg), 0, 0, 0):
#                 if msg.message == 0x02B1:  # WM_WTSSESSION_CHANGE
#                     if msg.wParam == WTS_SESSION_UNLOCK:
#                         print("Экран разблокирован!")
#                         return True
#                     elif msg.wParam == WTS_SESSION_LOCK:
#                         print("Экран заблокирован")
#             time.sleep(0.1)

#     elif system == "Linux":
#         try:
#             import dbus
#             from dbus.mainloop.glib import DBusGMainLoop
#             from gi.repository import GLib
#         except ImportError:
#             print("Требуются пакеты python-dbus и pygobject")
#             return False

#         def screen_saver_handler(active):
#             if not active:
#                 print("Экран разблокирован!")
#                 loop.quit()

#         DBusGMainLoop(set_as_default=True)
#         bus = dbus.SessionBus()
#         bus.add_signal_receiver(
#             screen_saver_handler,
#             signal_name="ActiveChanged",
#             dbus_interface="org.gnome.ScreenSaver"
#         )
#         loop = GLib.MainLoop()
#         loop.run()
#         return True

#     elif system == "Darwin":  # macOS
#         try:
#             from AppKit import NSWorkspace
#         except ImportError:
#             print("Требуется pyobjc-framework-Cocoa")
#             return False

#         workspace = NSWorkspace.sharedWorkspace()
#         while True:
#             if not workspace.isScreenLocked():
#                 print("Экран разблокирован!")
#                 return True
#             time.sleep(0.1)

#     else:
#         print(f"Операционная система {system} не поддерживается")
#         return False


def wait_for_unlock():
    """Ожидание разблокировки экрана"""
    logger.debug("DEBUG: Ожидаем разблокировку экрана")
    # app = QApplication.instance()
    while is_screen_locked():
        # if app:
        #     app.processEvents()  # Обрабатываем события PyQt5
        time.sleep(0.1)  # Проверяем каждую секунду
    logger.debug("DEBUG: Экран разблокирован, возобновляем анализ")


# def wait_for_unlock():
#     """Ожидание разблокировки экрана"""
#     print("DEBUG: Ожидаем разблокировку экрана")
#     while is_screen_locked():
#         time.sleep(0.1)  # Проверяем каждую секунду
#     print("DEBUG: Экран разблокирован, возобновляем анализ")
