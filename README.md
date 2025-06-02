# Phone Detection App

Приложение для обнаружения мобильного телефона в кадре камеры с блокировкой экрана.

## Установка

1. Установите Python 3.13.
2. Установите окружение: `uv venv`.
3. Активируйте окружение: `.venv\Scripts\activate` или `source .venv/bin/activate`
4. Установите зависимости: `uv sync`
5. Поместите YOLO модель в `models/model.onnx`.
6. Запустите приложение: `python main.py`.
7. Запустите админ-панель: `python src/admin/admin_panel.py`.

## Требования

- Windows (для MVP)
- Веб-камера

## Инструкция для билда

- Проверьте работоспособность приложения
- Удалите предыдущие сборки `rmdir /S /Q dist`, `rmdir /S /Q build`
- Обфускация main.py: `pyarmor gen main.py`
- Копирование зависимостей:

```
xcopy src dist\src /E /I /Y /EXCLUDE:exclude.txt
xcopy models dist\models /E /I /Y
scopy config dist\config /E /I /Y
xcopy assets dist\assets /E /I /Y
copy config.json dist\config.json
```

- Обновите .spec файлы при необходимости
- Сборка main.py `pyinstaller main.spec`
- Сборка main.py `pyinstaller admin_panel.spec`
