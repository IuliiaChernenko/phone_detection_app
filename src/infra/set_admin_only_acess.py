import os
import platform
import stat

def set_admin_only_access(folder_path):
    # Проверяем, существует ли папка
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Папка {folder_path} не существует")

    system = platform.system()

    if system == "Windows":
        try:
            import win32security
            import ntsecuritycon as con

            # Получаем SID группы администраторов
            admin_sid = win32security.CreateWellKnownSid(win32security.WinLocalSystemSid)

            # Получаем объект безопасности для папки
            sd = win32security.GetFileSecurity(folder_path, win32security.DACL_SECURITY_INFORMATION)

            # Создаём новый DACL (список контроля доступа)
            dacl = win32security.ACL()

            # Добавляем правило: только администраторы имеют полный доступ
            dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_ALL_ACCESS, admin_sid)

            # Устанавливаем новый DACL для папки
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(folder_path, win32security.DACL_SECURITY_INFORMATION, sd)
            print(f"Права доступа для {folder_path} на Windows успешно установлены (только для администраторов).")

        except ImportError:
            raise ImportError("Для Windows требуется установить библиотеку pywin32: 'pip install pywin32'")
        except Exception as e:
            raise Exception(f"Ошибка при установке прав на Windows: {e}")

    elif system == "Linux" or system == "Darwin":  # Darwin — это macOS
        try:
            # Устанавливаем владельцем root
            os.chown(folder_path, 0, 0)  # 0, 0 — это UID и GID для root

            # Устанавливаем права доступа: только владелец (root) имеет доступ
            os.chmod(folder_path, stat.S_IRWXU)  # 700 — только владелец может читать/писать/выполнять
            print(f"Права доступа для {folder_path} на {system} успешно установлены (только для root).")

        except PermissionError:
            raise PermissionError("Запустите скрипт с правами суперпользователя (sudo) для Linux/macOS")
        except Exception as e:
            raise Exception(f"Ошибка при установке прав на {system}: {e}")

    else:
        raise NotImplementedError(f"Операционная система {system} не поддерживается")

# Пример использования
# if __name__ == "__main__":
#     folder_path = r"C:\path\to\your\folder" if platform.system() == "Windows" else "/path/to/your/folder"
#     try:
#         set_admin_only_access(folder_path)
#     except Exception as e:
#         print(f"Ошибка: {e}")