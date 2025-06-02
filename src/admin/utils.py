import os
import sys


def get_base_path():
    """Возвращает базовый путь: sys._MEIPASS для .exe или корень проекта."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def get_resource_path(relative_path):
    """Возвращает абсолютный путь к ресурсу."""
    return os.path.join(get_base_path(), relative_path)


def get_image_path(relative_path):
    """
    Возвращает абсолютный путь к ресурсу, учитывая запуск из .py или .exe.
    Для .exe использует директорию исполняемого файла, а не sys._MEIPASS.
    """
    if getattr(sys, 'frozen', False):  # Запуск из .exe (PyInstaller)
        # Получаем директорию, где находится .exe
        base_path = os.path.dirname(sys.executable)
    else:  # Запуск из .py
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return os.path.join(base_path, relative_path)
