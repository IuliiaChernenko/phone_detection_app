import os
import sys

def print_directory_structure(start_path, indent="", exclude_dirs=None):
    """
    Рекурсивно выводит структуру директории, исключая указанные папки.
    """
    if exclude_dirs is None:
        exclude_dirs = []

    try:
        # Получаем список элементов в директории
        items = sorted(os.listdir(start_path))
    except PermissionError:
        print(f"{indent}[Permission Denied] {start_path}")
        return

    for item in items:
        item_path = os.path.join(start_path, item)
        # Пропускаем исключенные директории
        if item in exclude_dirs and os.path.isdir(item_path):
            continue
        if os.path.isdir(item_path):
            print(f"{indent}[DIR] {item}")
            print_directory_structure(item_path, indent + "  ", exclude_dirs)
        else:
            print(f"{indent}[FILE] {item}")

def main():
    # Корневая папка проекта
    project_root = os.path.abspath(os.path.dirname(__file__))
    print(f"Project Root: {project_root}")
    print("Directory Structure:")
    print("===================")
    
    # Исключаем виртуальное окружение и другие большие папки
    exclude_dirs = ['.venv', '__pycache__', 'build', 'dist']
    print_directory_structure(project_root, exclude_dirs=exclude_dirs)
    print("===================")

if __name__ == "__main__":
    main()