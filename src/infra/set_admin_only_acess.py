import os
import platform
import stat
# import win32security
# import ntsecuritycon as con
import logging

logging.basicConfig(level=logging.CRITICAL+1, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)


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
            # admin_sid = win32security.CreateWellKnownSid(win32security.WinLocalSystemSid)
            admin_sid = win32security.CreateWellKnownSid(win32security.WinBuiltinAdministratorsSid)

            # Получаем объект безопасности для папки
            sd = win32security.GetFileSecurity(folder_path, win32security.DACL_SECURITY_INFORMATION)

            # Создаём новый DACL (список контроля доступа)
            dacl = win32security.ACL()

            # Добавляем правило: только администраторы имеют полный доступ
            dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_ALL_ACCESS, admin_sid)

            # Устанавливаем новый DACL для папки
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(folder_path, win32security.DACL_SECURITY_INFORMATION, sd)
            logger.debug(f"Права доступа для {folder_path} на Windows успешно установлены (только для администраторов).")

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
            logger.debug(f"Права доступа для {folder_path} на {system} успешно установлены (только для root).")

        except PermissionError:
            raise PermissionError("Запустите скрипт с правами суперпользователя (sudo) для Linux/macOS")
        except Exception as e:
            raise Exception(f"Ошибка при установке прав на {system}: {e}")

    else:
        raise NotImplementedError(f"Операционная система {system} не поддерживается")
    
    
# def set_admin_only_access(file_or_folder_path):
#     if not os.path.exists(file_or_folder_path):
#         raise FileNotFoundError(f"Объект {file_or_folder_path} не существует")

#     system = platform.system()

#     if system == "Windows":
#         try:
#             # Получаем SID группы администраторов
#             admin_sid = win32security.CreateWellKnownSid(win32security.WinBuiltinAdministratorsSid)
#             # Получаем SID SYSTEM
#             system_sid = win32security.CreateWellKnownSid(win32security.WinLocalSystemSid)

#             # Получаем объект безопасности
#             sd = win32security.GetFileSecurity(file_or_folder_path, win32security.DACL_SECURITY_INFORMATION)
            
#             # Создаём новый DACL
#             dacl = win32security.ACL()

#             # Добавляем права для группы администраторов
#             dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_ALL_ACCESS, admin_sid)
#             # Добавляем права для SYSTEM
#             dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_ALL_ACCESS, system_sid)

#             # Устанавливаем новый DACL
#             sd.SetSecurityDescriptorDacl(1, dacl, 0)
#             win32security.SetFileSecurity(file_or_folder_path, win32security.DACL_SECURITY_INFORMATION, sd)
#             print(f"Права доступа для {file_or_folder_path} на Windows успешно установлены (только администраторы и SYSTEM).")

#         except ImportError:
#             raise ImportError("Для Windows требуется установить библиотеку pywin32: 'pip install pywin32'")
#         except Exception as e:
#             raise Exception(f"Ошибка при установке прав на Windows: {e}")
#     elif system == "Linux" or system == "Darwin":  # Darwin — это macOS
#         try:
#             # Устанавливаем владельцем root
#             os.chown(file_or_folder_path, 0, 0)  # 0, 0 — это UID и GID для root

#             # Устанавливаем права доступа: только владелец (root) имеет доступ
#             os.chmod(file_or_folder_path, stat.S_IRWXU)  # 700 — только владелец может читать/писать/выполнять
#             print(f"Права доступа для {file_or_folder_path} на {system} успешно установлены (только для root).")

#         except PermissionError:
#             raise PermissionError("Запустите скрипт с правами суперпользователя (sudo) для Linux/macOS")
#         except Exception as e:
#             raise Exception(f"Ошибка при установке прав на {system}: {e}")

#     else:
#         raise NotImplementedError(f"Операционная система {system} не поддерживается")

# Пример использования
# if __name__ == "__main__":
#     folder_path = r"C:\path\to\your\folder" if platform.system() == "Windows" else "/path/to/your/folder"
#     try:
#         set_admin_only_access(folder_path)
#     except Exception as e:
#         print(f"Ошибка: {e}")