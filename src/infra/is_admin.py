import os
import sys
import ctypes


def get_run_path():
    # Получение пути до основного исполняемого файла или скрипта
    if getattr(sys, 'frozen', False):  # Если упакован PyInstaller
        return os.path.abspath(sys.executable)
    # Если запускается как Python-скрипт
    # sys.argv[0] указывает на путь к главному скрипту, запущенному из консоли
    return os.path.abspath(sys.argv[0])


def is_admin():
    try:
        # Для Windows
        if os.name == 'nt':
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        # Для Linux/macOS
        else:
            return os.geteuid() == 0
    except AttributeError:
        # Если os.geteuid() недоступен (например, на Windows)
        return False