import json
import os
import sys
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        self.default_config = {
            "camera_id": 0,
            "fps": 10,
            "log_retention": "1 месяц",
            "confidence_threshold": 0.8,
            "notifications_enabled": False,
            "phone_limit": 1,
            "lock_events": {
                "camera_lost": True,
                "uniform_image": True,
                "phone_detected": True,
                "attempt_to_close": False,
                "static_img": True
            },
            "log_events": {
                "phone_detected": True,
                "camera_lost": True,
                "uniform_image": True,
                "attempt_to_close": True,
                "static_img": True
            },
            "other_events": {
                "make_screen_enabled": True
            },
            "notifications": {
                "phone_detected": True,
                "camera_lost": True,
                "uniform_image": True,
                "attempt_to_close": True,
                "static_img": True
            },
            "autostart": {
                "on_system_start": False,
                "on_program_start": {"enabled": False, "program_path": ""},
                "on_file_open": {"enabled": False, "file_path": ""}
            },
            "telegram_ids": []
        }
        self.config_path = self._get_config_path()
        self.config = self.load_config()
        logger.debug(f"Initialized Config with config_path: {self.config_path}")
        logger.debug(f"Loaded config: {self.config}")

    def _get_base_path(self):
        """Возвращает базовый путь: sys._MEIPASS для .exe или корень проекта."""
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    def _get_writeable_path(self):
        """Возвращает путь для записи (рядом с .exe или корень проекта)."""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return self._get_base_path()

    def _get_config_path(self):
        """Возвращает путь для чтения config.json."""
        base_path = self._get_base_path()
        return os.path.join(base_path, 'config.json')

    def load_config(self):
        """Загружает config.json."""
        try:
            # Сначала проверяем writeable путь (для модифицированного config.json)
            writeable_path = os.path.join(self._get_writeable_path(), 'config.json')
            if os.path.exists(writeable_path):
                with open(writeable_path, 'r') as f:
                    config = json.load(f)
                logger.debug(f"Loaded config from writeable path: {writeable_path}")
            else:
                # Если нет в writeable, берем из base_path (встроенный в .exe)
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.debug(f"Loaded config from base path: {self.config_path}")

            # Обновляем недостающие ключи из default_config
            for key, value in self.default_config.items():
                if key not in config:
                    config[key] = value
            logger.debug(f"Loaded and updated config: {config}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file not found at {self.config_path}, using defaults")
            self.save_config(self.default_config.copy())  # Создаем новый config.json
            return self.default_config.copy()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.default_config.copy()

    def save_config(self, config):
        """Сохраняет config.json в writeable директорию."""
        try:
            writeable_path = os.path.join(self._get_writeable_path(), 'config.json')
            with open(writeable_path, 'w') as f:
                json.dump(config, f, indent=4)
            self.config = config
            self.config_path = writeable_path  # Обновляем путь для последующих операций
            logger.debug(f"Saved config to: {writeable_path}")
            logger.debug(f"Saved config content: {config}")
        except Exception as e:
            logger.error(f"Error saving config to {writeable_path}: {e}")

    def get(self, key):
        """Получает значение по ключу, возвращает значение из default_config, если отсутствует."""
        return self.config.get(key, self.default_config.get(key))


# import json
# import os

# class Config:
#     def __init__(self):
#         self.config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config.json'))
#         self.default_config = {
#             "camera_id": 0,
#             "fps": 10,
#             "log_retention": "1 месяц",
#             "confidence_threshold": 0.8,
#             "notifications_enabled": False,
#             "lock_events": {
#                 "camera_lost": True,
#                 "uniform_image": True,
#                 "phone_detected": True,
#                 "attempt_to_close": False
#             },
#             "log_events": {
#                 "phone_detected": True,
#                 "camera_lost": True,
#                 "uniform_image": True,
#                 "attempt_to_close": True
#             },
#             "autostart": {
#                 "on_system_start": False,
#                 "on_program_start": {"enabled": False, "program_path": ""},
#                 "on_file_open": {"enabled": False, "file_path": ""}
#             },
#             "telegram_ids": []
#         }
#         self.config = self.load_config()
#         print(self.config)

#     def load_config(self):
#         try:
#             if os.path.exists(self.config_path):
#                 with open(self.config_path, 'r') as f:
#                     config = json.load(f)
#                 for key, value in self.default_config.items():
#                     if key not in config:
#                         config[key] = value
#                 print(f"DEBUG: Loaded config: {config}")
#                 return config
#             print(f"DEBUG: Config file not found, using defaults: {self.default_config}")
#             return self.default_config.copy()
#         except Exception as e:
#             print(f"DEBUG: Error loading config: {e}")
#             return self.default_config.copy()

#     def save_config(self, config):
#         try:
#             with open(self.config_path, 'w') as f:
#                 json.dump(config, f, indent=4)
#             self.config = config
#             print(f"DEBUG: Saved config: {config}")
#         except Exception as e:
#             print(f"DEBUG: Error saving config: {e}")

#     def get(self, key):
#         return self.config.get(key, self.default_config.get(key))