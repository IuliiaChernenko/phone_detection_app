import sqlite3
import cv2
import os
import json
import sys
from datetime import datetime, timedelta
import queue
import threading
import logging

logger = logging.getLogger("Logger")

class Logger:
    def __init__(self, db_path="logs/detection_log.db"):
        # Настройка путей
        self.db_path = db_path
        self.abs_db_path = self._get_db_path()
        os.makedirs(os.path.dirname(self.abs_db_path), exist_ok=True)
        logger.debug(f"Initializing logger with db_path={db_path}, absolute={self.abs_db_path}")

        # Словарь для преобразования событий в slug
        self.event_slugs = {
            "Обнаружен мобильный телефон": "phone_detected",
            "Однотонное изображение": "uniform_image",
            "После однотонного изображения": "after_uniform_image",
            "Потеря связи с камерой": "camera_lost",
            "Востановление после \"Потеря связи с камерой\"": "recovery_camera_lost",
            "Попытка закрыть приложение": "attempt_to_close",
            "Зависшее изображение": "static_img",
            "Изображение отвисло": "after_static_img",
        }

        try:
            if not os.path.exists(self.abs_db_path):
                logger.debug(f"Database {self.abs_db_path} does not exist, will be created")
            self.conn = sqlite3.connect(self.abs_db_path)
            self.cursor = self.conn.cursor()
            self._create_or_migrate_table()
            logger.debug(f"Connected to database {self.abs_db_path}")
        except sqlite3.OperationalError as e:
            logger.error(f"Error connecting to database {self.abs_db_path}: {e}")
            raise

        # Инициализация очереди и потока
        self.queue = queue.Queue(maxsize=100)  # Очередь с ограниченным размером
        self._stop_event = threading.Event()  # Событие для остановки потока
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

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

    def _get_db_path(self):
        """Возвращает абсолютный путь к базе данных в writeable директории."""
        writeable_path = self._get_writeable_path()
        return os.path.join(writeable_path, self.db_path)

    def _get_log_file_path(self, relative_path):
        """Возвращает абсолютный путь для файлов логов (изображений)."""
        return os.path.join(self._get_writeable_path(), relative_path)

    def _create_or_migrate_table(self):
        """Создание или миграция таблицы в базе данных."""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    event TEXT,
                    frame_path TEXT,
                    screen_path TEXT,
                    confidence TEXT,
                    active_apps TEXT,
                    username TEXT
                )
            """)
            self.cursor.execute("PRAGMA table_info(logs)")
            columns = [col[1] for col in self.cursor.fetchall()]
            logger.debug(f"Columns in logs table: {columns}")
            if "confidence" not in columns:
                self.cursor.execute("ALTER TABLE logs ADD COLUMN confidence TEXT")
                logger.debug("Added confidence column")
            if "active_apps" not in columns:
                self.cursor.execute("ALTER TABLE logs ADD COLUMN active_apps TEXT")
                logger.debug("Added active_apps column")
            if "username" not in columns:
                self.cursor.execute("ALTER TABLE logs ADD COLUMN username TEXT")
                logger.debug("Added username column")
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error creating/migrating table: {e}")
            raise

    def _worker_loop(self):
        """Цикл обработки задач логирования в отдельном потоке."""
        conn = sqlite3.connect(self.abs_db_path)
        cursor = conn.cursor()

        while not self._stop_event.is_set():
            try:
                task = self.queue.get(timeout=1.0)
                timestamp, event, frame_path, screen_path, username, confidence, active_apps = task

                confidence_json = json.dumps(confidence) if confidence is not None else None
                active_apps_json = json.dumps(active_apps) if active_apps is not None else None

                logger.debug(f"Logging event: event={event}, frame_path={frame_path}, screen_path={screen_path}, confidence={confidence_json}, active_apps={active_apps_json}, username={username}")

                try:
                    cursor.execute(
                        "INSERT INTO logs (timestamp, event, frame_path, screen_path, confidence, active_apps, username) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (timestamp.replace("_", " "), event, frame_path, screen_path, confidence_json, active_apps_json, username)
                    )
                    conn.commit()
                    logger.debug(f"Event successfully logged to database: id={cursor.lastrowid}, username={username}")
                except sqlite3.Error as e:
                    logger.warning(f"Error writing to database: {e}")

                self.queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")

        cursor.close()
        conn.close()
        logger.debug("Logger worker thread stopped")

    def log_event(self, event, frame, screen, username, logger_instance, timestamp: str, confidence=None, active_apps=None):
        """
        Логирование события: сохраняет изображения на диск и передает задачу в очередь.
        """
        logger.debug(f"Logging event={event}")

        # Подготовка slug для события
        event_slug = self.event_slugs.get(event, event.lower().replace(" ", "_"))

        # Подготовка путей для изображений (всегда в writeable директории)
        frame_path = f"logs/{timestamp}_{event_slug}.jpg"
        abs_frame_path = self._get_log_file_path(frame_path)
        screen_path = f"logs/{timestamp}_{event_slug}_screen.jpg"
        abs_screen_path = self._get_log_file_path(screen_path)
        os.makedirs(os.path.dirname(abs_frame_path), exist_ok=True)

        # Сохранение изображений
        if frame is not None:
            try:
                cv2.imwrite(abs_frame_path, frame)
                logger.debug(f"Saved frame: {abs_frame_path}")
            except Exception as e:
                logger.debug(f"Error saving frame {abs_frame_path}: {e}")
                frame_path = None
        else:
            logger.debug(f"Frame is None, skipping save for {abs_frame_path}")
            frame_path = None

        if screen is not None:
            try:
                cv2.imwrite(abs_screen_path, screen)
                logger.debug(f"Saved screen: {abs_screen_path}")
            except Exception as e:
                logger.debug(f"Error saving screen {abs_screen_path}: {e}")
                screen_path = None
        else:
            logger.debug(f"Screen is None, skipping save for {abs_screen_path}")
            screen_path = None

        # Помещаем задачу в очередь
        try:
            self.queue.put(
                (timestamp, event, frame_path, screen_path, username, confidence, active_apps),
                timeout=2.0
            )
        except queue.Full:
            logger.warning("Logging queue is full, dropping event")
            if frame_path and os.path.exists(abs_frame_path):
                try:
                    os.remove(abs_frame_path)
                    logger.debug(f"Deleted unsaved frame: {abs_frame_path}")
                except OSError as e:
                    logger.debug(f"Error deleting frame {abs_frame_path}: {e}")
            if screen_path and os.path.exists(abs_screen_path):
                try:
                    os.remove(abs_screen_path)
                    logger.debug(f"Deleted unsaved screen: {abs_screen_path}")
                except OSError as e:
                    logger.debug(f"Error deleting screen {abs_screen_path}: {e}")

    def get_logs(self):
        """Получение всех логов из базы данных."""
        conn = sqlite3.connect(self.abs_db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC")
            logs = cursor.fetchall()
            logger.debug(f"Loaded {len(logs)} logs from database")
            for log in logs:
                logger.debug(f"Log: id={log[0]}, timestamp={log[1]}, event={log[2]}, frame_path={log[3]}, screen_path={log[4]}, confidence={log[5]}, active_apps={log[6]}, username={log[7]}")
            return logs
        except sqlite3.Error as e:
            logger.error(f"Error reading logs from database: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def clean_old_logs(self, retention_period):
        """Очистка старых логов и связанных файлов."""
        if retention_period == "Не удалять":
            return
        periods = {
            "1 день": timedelta(days=1),
            "1 неделя": timedelta(weeks=1),
            "1 месяц": timedelta(days=30),
            "1 год": timedelta(days=365)
        }
        if retention_period not in periods:
            return
        cutoff = datetime.now() - periods[retention_period]
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(self.abs_db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT frame_path, screen_path FROM logs WHERE timestamp < ?", (cutoff_str,))
            paths = cursor.fetchall()
            for frame_path, screen_path in paths:
                for path in (frame_path, screen_path):
                    if path:
                        abs_path = self._get_log_file_path(path)
                        try:
                            if os.path.exists(abs_path):
                                os.remove(abs_path)
                                logger.debug(f"Deleted old file: {abs_path}")
                        except OSError as e:
                            logger.debug(f"Error deleting file {abs_path}: {e}")
            cursor.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff_str,))
            conn.commit()
            logger.debug(f"Deleted logs older than {cutoff_str}")
        except sqlite3.Error as e:
            logger.error(f"Error cleaning old logs: {e}")
        finally:
            cursor.close()
            conn.close()

    def close(self):
        """Остановка потока обработки и освобождение ресурсов."""
        logger.debug("Stopping Logger")
        self._stop_event.set()
        self._worker_thread.join(timeout=2.0)
        self.conn.close()
        logger.debug("Logger stopped")

    def __del__(self):
        """Гарантированное закрытие при удалении объекта."""
        self.close()


# import sqlite3
# import cv2
# import os
# import json
# from datetime import datetime, timedelta
# import queue
# import threading
# import logging

# logger = logging.getLogger("UserApp")

# class Logger:
#     def __init__(self, db_path):
#         # Используем путь относительно корня проекта
#         base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
#         self.abs_db_path = os.path.join(base_dir, db_path)
#         os.makedirs(os.path.dirname(self.abs_db_path), exist_ok=True)
#         logger.debug(f"Initializing logger with db_path={db_path}, absolute={self.abs_db_path}")

#         # Словарь для преобразования событий в slug
#         self.event_slugs = {
#             "Обнаружен мобильный телефон": "phone_detected",
#             "Однотонное изображение": "uniform_image",
#             "После однотонного изображения": "after_uniform_image",
#             "Потеря связи с камерой": "camera_lost",
#             "Востановление после \"Потеря связи с камерой\"": "recovery_camera_lost",
#             "Попытка закрыть приложение": "attempt_to_close",
#             "Зависшее изображение": "static_img",
#             "Изображение отвисло": "after_static_img",
#         }
#         try:
#             if not os.path.exists(self.abs_db_path):
#                 print(f"DEBUG: Database {self.abs_db_path} does not exist, will be created")
#             self.conn = sqlite3.connect(self.abs_db_path)
#             self.cursor = self.conn.cursor()
#             self.create_or_migrate_table()
#             print(f"DEBUG: Connected to database {self.abs_db_path}")
#         except sqlite3.OperationalError as e:
#             print(f"DEBUG: Error connecting to database {self.abs_db_path}: {e}")
#             raise

#         # Инициализация очереди и потока
#         self.queue = queue.Queue(maxsize=100)  # Очередь с ограниченным размером
#         self._stop_event = threading.Event()  # Событие для остановки потока
#         self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)

#         # Создаем таблицу при инициализации
#         self._create_or_migrate_table()

#         # Запускаем поток обработки логов
#         self._worker_thread.start()
        
#     def create_or_migrate_table(self):
#         try:
#             self.cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS logs (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     timestamp TEXT,
#                     event TEXT,
#                     frame_path TEXT,
#                     screen_path TEXT,
#                     confidence TEXT,
#                     active_apps TEXT,
#                     username TEXT
#                 )
#             """)
#             self.cursor.execute("PRAGMA table_info(logs)")
#             columns = [col[1] for col in self.cursor.fetchall()]
#             print(f"DEBUG: Columns in logs table: {columns}")
#             if "confidence" not in columns:
#                 self.cursor.execute("ALTER TABLE logs ADD COLUMN confidence TEXT")
#                 print("DEBUG: Added confidence column")
#             if "active_apps" not in columns:
#                 self.cursor.execute("ALTER TABLE logs ADD COLUMN active_apps TEXT")
#                 print("DEBUG: Added active_apps column")
#             if "username" not in columns:
#                 self.cursor.execute("ALTER TABLE logs ADD COLUMN username TEXT")
#                 print("DEBUG: Added username column")
#             self.conn.commit()
#         except sqlite3.Error as e:
#             print(f"DEBUG: Error creating/migrating table: {e}")
#             raise

#     def _create_or_migrate_table(self):
#         """Создание или миграция таблицы в базе данных."""
#         try:
#             conn = sqlite3.connect(self.abs_db_path)
#             cursor = conn.cursor()
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS logs (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     timestamp TEXT,
#                     event TEXT,
#                     frame_path TEXT,
#                     screen_path TEXT,
#                     confidence TEXT,
#                     active_apps TEXT,
#                     username TEXT
#                 )
#             """)
#             cursor.execute("PRAGMA table_info(logs)")
#             columns = [col[1] for col in cursor.fetchall()]
#             logger.debug(f"Columns in logs table: {columns}")
#             if "confidence" not in columns:
#                 cursor.execute("ALTER TABLE logs ADD COLUMN confidence TEXT")
#                 logger.debug("Added confidence column")
#             if "active_apps" not in columns:
#                 cursor.execute("ALTER TABLE logs ADD COLUMN active_apps TEXT")
#                 logger.debug("Added active_apps column")
#             if "username" not in columns:
#                 cursor.execute("ALTER TABLE logs ADD COLUMN username TEXT")
#                 logger.debug("Added username column")
#             conn.commit()
#         except sqlite3.Error as e:
#             logger.error(f"Error creating/migrating table: {e}")
#             raise
#         finally:
#             cursor.close()
#             conn.close()

#     def _worker_loop(self):
#         """Цикл обработки задач логирования в отдельном потоке."""
#         # Создаем одно подключение к базе данных в этом потоке
#         conn = sqlite3.connect(self.abs_db_path)
#         cursor = conn.cursor()

#         while not self._stop_event.is_set():
#             try:
#                 # Ждем задачу из очереди с таймаутом
#                 task = self.queue.get(timeout=1.0)
#                 timestamp, event, frame_path, screen_path, username, confidence, active_apps = task

#                 # Подготовка данных для базы данных
#                 confidence_json = json.dumps(confidence) if confidence is not None else None
#                 active_apps_json = json.dumps(active_apps) if active_apps is not None else None

#                 logger.debug(f"Logging event: event={event}, frame_path={frame_path}, screen_path={screen_path}, confidence={confidence_json}, active_apps={active_apps_json}, username={username}")

#                 # Запись в базу данных
#                 try:
#                     cursor.execute(
#                         "INSERT INTO logs (timestamp, event, frame_path, screen_path, confidence, active_apps, username) VALUES (?, ?, ?, ?, ?, ?, ?)",
#                         (timestamp.replace("_", " "), event, frame_path, screen_path, confidence_json, active_apps_json, username)
#                     )
#                     conn.commit()
#                     logger.debug(f"Event successfully logged to database: id={cursor.lastrowid}, username={username}")
#                 except sqlite3.Error as e:
#                     logger.warning(f"Error writing to database: {e}")

#                 # Отмечаем задачу как выполненную
#                 self.queue.task_done()

#             except queue.Empty:
#                 continue
#             except Exception as e:
#                 logger.error(f"Error in worker loop: {e}")

#         # Закрываем подключение при остановке
#         cursor.close()
#         conn.close()
#         logger.debug("Logger worker thread stopped")

#     def log_event(self, event, frame, screen, username, logger, timestamp: str, confidence=None, active_apps=None):
#         """
#         Логирование события: сохраняет изображения на диск и передает задачу в очередь.
#         """
#         logger.debug(f"logger start with event={event}")

#         # Подготовка slug для события
#         event_slug = self.event_slugs.get(event, event.lower().replace(" ", "_"))

#         # Подготовка путей для изображений
#         frame_path = f"logs/{timestamp}_{event_slug}.jpg"  # Relative path
#         abs_frame_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', frame_path))
#         screen_path = f"logs/{timestamp}_{event_slug}_screen.jpg"  # Relative path
#         abs_screen_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', screen_path))
#         os.makedirs(os.path.dirname(abs_frame_path), exist_ok=True)

#         # Сохранение изображений
#         if frame is not None:
#             try:
#                 cv2.imwrite(abs_frame_path, frame)
#                 logger.debug(f"Saved frame: {abs_frame_path}")
#             except Exception as e:
#                 logger.debug(f"Error saving frame {abs_frame_path}: {e}")
#                 frame_path = None
#         else:
#             logger.debug(f"Frame is None, skipping save for {abs_frame_path}")
#             frame_path = None

#         if screen is not None:
#             try:
#                 cv2.imwrite(abs_screen_path, screen)
#                 logger.debug(f"Saved screen: {abs_screen_path}")
#             except Exception as e:
#                 logger.debug(f"Error saving screen {abs_screen_path}: {e}")
#                 screen_path = None
#         else:
#             logger.debug(f"Screen is None, skipping save for {abs_screen_path}")
#             screen_path = None

#         # Помещаем задачу в очередь
#         try:
#             self.queue.put(
#                 (timestamp, event, frame_path, screen_path, username, confidence, active_apps),
#                 timeout=2.0
#             )
#         except queue.Full:
#             logger.warning("Logging queue is full, dropping event")
#             # Удаляем временные файлы, если они были созданы
#             if frame_path and os.path.exists(abs_frame_path):
#                 try:
#                     os.remove(abs_frame_path)
#                     logger.debug(f"Deleted unsaved frame: {abs_frame_path}")
#                 except OSError as e:
#                     logger.debug(f"Error deleting frame {abs_frame_path}: {e}")
#             if screen_path and os.path.exists(abs_screen_path):
#                 try:
#                     os.remove(abs_screen_path)
#                     logger.debug(f"Deleted unsaved screen: {abs_screen_path}")
#                 except OSError as e:
#                     logger.debug(f"Error deleting screen {abs_screen_path}: {e}")

#     def get_logs(self):
#         """Получение всех логов из базы данных."""
#         # Создаем новое подключение для чтения, так как это может вызываться из другого потока
#         conn = sqlite3.connect(self.abs_db_path)
#         cursor = conn.cursor()
#         try:
#             cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC")
#             logs = cursor.fetchall()
#             logger.debug(f"Loaded {len(logs)} logs from database")
#             for log in logs:
#                 logger.debug(f"Log: id={log[0]}, timestamp={log[1]}, event={log[2]}, frame_path={log[3]}, screen_path={log[4]}, confidence={log[5]}, active_apps={log[6]}, username={log[7]}")
#             return logs
#         except sqlite3.Error as e:
#             logger.error(f"Error reading logs from database: {e}")
#             return []
#         finally:
#             cursor.close()
#             conn.close()

#     def clean_old_logs(self, retention_period):
#         """Очистка старых логов и связанных файлов."""
#         if retention_period == "Не удалять":
#             return
#         periods = {
#             "1 день": timedelta(days=1),
#             "1 неделя": timedelta(weeks=1),
#             "1 месяц": timedelta(days=30),
#             "1 год": timedelta(days=365)
#         }
#         if retention_period not in periods:
#             return
#         cutoff = datetime.now() - periods[retention_period]
#         cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

#         # Создаем новое подключение для очистки
#         conn = sqlite3.connect(self.abs_db_path)
#         cursor = conn.cursor()
#         try:
#             cursor.execute("SELECT frame_path, screen_path FROM logs WHERE timestamp < ?", (cutoff_str,))
#             paths = cursor.fetchall()
#             for frame_path, screen_path in paths:
#                 for path in (frame_path, screen_path):
#                     if path:
#                         abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', path))
#                         try:
#                             if os.path.exists(abs_path):
#                                 os.remove(abs_path)
#                                 logger.debug(f"Deleted old file: {abs_path}")
#                         except OSError as e:
#                             logger.debug(f"Error deleting file {abs_path}: {e}")
#             cursor.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff_str,))
#             conn.commit()
#             logger.debug(f"Deleted logs older than {cutoff_str}")
#         except sqlite3.Error as e:
#             logger.error(f"Error cleaning old logs: {e}")
#         finally:
#             cursor.close()
#             conn.close()

#     def close(self):
#         """Остановка потока обработки и освобождение ресурсов."""
#         logger.debug("Stopping Logger")
#         self._stop_event.set()
#         self._worker_thread.join(timeout=2.0)  # Ждем завершения потока
#         logger.debug("Logger stopped")

#     def __del__(self):
#         """Гарантированное закрытие при удалении объекта."""
#         self.close()
