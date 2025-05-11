import os
import sys
import platform
from pathlib import Path

APP_NAME = "phone_detection_app"

def get_project_main_path() -> Path:
    """
    Возвращает путь к main.py, предполагая, что он находится
    в корне проекта на 2 уровня выше текущего файла.
    """
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[2]  # два уровня вверх
    main_path = project_root / "main.py"

    if not main_path.exists():
        raise FileNotFoundError(f"main.py не найден по пути: {main_path}")

    return main_path

def enable_autostart(app_name: str, script_path: str):
    """
    Добавляет скрипт Python в автозагрузку, если он ещё не добавлен.

    :param app_name: Имя приложения (уникальное, используется как имя ярлыка/файла)
    :param script_path: Полный путь к .py-скрипту
    """
    system = platform.system()

    if not os.path.isfile(script_path):
        raise ValueError(f"Файл не найден: {script_path}")

    python_exe = sys.executable
    command = f'"{python_exe}" "{script_path}"'

    if system == "Windows":
        import win32com.client

        startup_dir = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        shortcut_path = os.path.join(startup_dir, f"{app_name}.lnk")

        if os.path.exists(shortcut_path):
            print(f"[i] Уже в автозагрузке (Windows): {shortcut_path}")
            return

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = python_exe
        shortcut.Arguments = f'"{script_path}"'
        shortcut.WorkingDirectory = os.path.dirname(script_path)
        shortcut.save()
        print(f"[✓] Добавлено в автозагрузку (Windows): {shortcut_path}")

    elif system == "Linux":
        autostart_dir = Path.home() / ".config" / "autostart"
        desktop_file = autostart_dir / f"{app_name}.desktop"

        if desktop_file.exists():
            print(f"[i] Уже в автозагрузке (Linux): {desktop_file}")
            return

        autostart_dir.mkdir(parents=True, exist_ok=True)
        content = f"""[Desktop Entry]
Type=Application
Exec={command}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name={app_name}
"""
        desktop_file.write_text(content)
        print(f"[✓] Добавлено в автозагрузку (Linux): {desktop_file}")

    elif system == "Darwin":
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{app_name}.plist"

        if plist_path.exists():
            print(f"[i] Уже в автозагрузке (macOS): {plist_path}")
            return

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{app_name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_exe}</string>
        <string>{script_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_text(plist_content)
        os.system(f"launchctl load {plist_path}")
        print(f"[✓] Добавлено в автозагрузку (macOS): {plist_path}")

    else:
        raise NotImplementedError(f"Автозапуск не поддержан для ОС: {system}")
    
    
def disable_autostart(app_name: str):
    """
    Удаляет автозапуск скрипта Python по имени приложения.

    :param app_name: Имя приложения (используется как имя ярлыка/файла/plist)
    """
    system = platform.system()

    if system == "Windows":
        startup_dir = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        shortcut_path = os.path.join(startup_dir, f"{app_name}.lnk")
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
            print(f"[✓] Удалено из автозагрузки (Windows): {shortcut_path}")
        else:
            print(f"[i] Автозапуск не найден (Windows)")

    elif system == "Linux":
        desktop_file = Path.home() / ".config" / "autostart" / f"{app_name}.desktop"
        if desktop_file.exists():
            desktop_file.unlink()
            print(f"[✓] Удалено из автозагрузки (Linux): {desktop_file}")
        else:
            print(f"[i] Автозапуск не найден (Linux)")

    elif system == "Darwin":
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{app_name}.plist"
        if plist_path.exists():
            os.system(f"launchctl unload {plist_path}")
            plist_path.unlink()
            print(f"[✓] Удалено из автозагрузки (macOS): {plist_path}")
        else:
            print(f"[i] Автозапуск не найден (macOS)")

    else:
        raise NotImplementedError(f"ОС не поддерживается: {system}")


if __name__ == "__main__":
    # enable_autostart(APP_NAME, get_project_main_path())
    disable_autostart(APP_NAME)
