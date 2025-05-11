import psutil
import win32gui
import win32process
import win32con

def get_active_apps():
    apps = []
    try:
        def enum_windows_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    process = psutil.Process(pid)
                    process_name = process.name()
                    window_title = win32gui.GetWindowText(hwnd)
                    is_foreground = (hwnd == win32gui.GetForegroundWindow())
                    if is_foreground:  # Only include foreground apps
                        results.append({
                            "process": process_name,
                            "title": window_title,
                            "foreground": is_foreground
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        win32gui.EnumWindows(enum_windows_callback, apps)
        print(f"DEBUG: Active apps (foreground only): {apps}")
        return apps
    except Exception as e:
        print(f"DEBUG: Error getting active apps: {e}")
        return []