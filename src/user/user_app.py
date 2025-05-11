import os
import sys
import cv2
import numpy as np
import logging
from PyQt5.QtCore import QThread, pyqtSignal, QCoreApplication
from PyQt5.QtWidgets import QApplication, QMessageBox
import time

import platform
import getpass
from src.core.camera import Camera
from src.core.detector import Detector
from src.core.lock_screen import lock_screen, is_screen_locked, wait_for_unlock
from src.core.logger import Logger
from src.core.config import Config
from src.core.error_window import ErrorWindow
from src.core.system_info import get_active_apps
from src.infra.take_screenshot import take_screenshot
from src.infra.send_tg_alert import send_notification, notify_async
from src.infra.minimize_all import minimize_all_windows
from src.infra.set_admin_only_acess import set_admin_only_access
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from skimage.metrics import structural_similarity as ssim
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger("UserApp")

import time
import threading

import threading
import time
import cv2
import signal
# import queue
from typing import Optional


def get_resource_path(relative_path):
    """Возвращает абсолютный путь к ресурсу."""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', relative_path))


class CameraStream:
    """
    Потокобезопасный видеозахват с одной камеры с поддержкой паузы, прогрева и graceful shutdown.
    Используется для передачи кадров в систему анализа (например, запуск нейросети).
    """

    def __init__(
        self,
        source: int | str = 0,
        warmup_seconds: int = 2,
        max_fps: int = 2,
    ) -> None:
        """
        :param source: ID камеры или URL потока
        :param warmup_seconds: Время ожидания после запуска камеры (прогрев)
        :param queue_size: Максимальное количество кадров в буфере
        """
        self.source = source
        self.warmup_seconds = warmup_seconds
        self.max_fps = max_fps
        
        self._cap: Optional[cv2.VideoCapture] = None
        self._latest_frame: Optional["cv2.typing.MatLike"] = None
        self._new_frame_ready = threading.Event()
        self._last_frame_time = 0.0

        self._paused = threading.Event()
        self._stopped = threading.Event()
        self._ready = threading.Event()
        self._camera_lost = threading.Event()
        self._error_event = threading.Event()

        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._lock = threading.Lock()
        
    def start(self) -> None:
        """Запускает поток чтения кадров"""
        self._cap = cv2.VideoCapture(self.source)
        if not self._cap.isOpened():
            self._camera_lost.set()
            self._error_event.set()
            return  # не поднимаем исключение, просто считаем, что камеры нет

        self._paused.clear()
        self._stopped.clear()
        self._ready.clear()
        self._camera_lost.clear()
        self._error_event.clear()

        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()
        
    def restart(self) -> None:
        """Перезапускает камеру после сбоя соединения"""
        self.stop()
        # time.sleep(1)

        self._cap = None
        self._latest_frame = None
        self._new_frame_ready.clear()
        self._last_frame_time = 0.0

        self._paused.clear()
        self._stopped.clear()
        self._ready.clear()
        self._camera_lost.clear()
        self._error_event.clear()

        self._cap = cv2.VideoCapture(self.source)
        if not self._cap.isOpened():
            self._camera_lost.set()
            self._error_event.set()
            return

        # time.sleep(1.5)
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()
        # time.sleep(1)
        
    def is_camera_lost(self) -> bool:
        return self._camera_lost.is_set()

    def _reader_loop(self) -> None:
        """Внутренний цикл чтения кадров"""
        failure_count = 0
        max_failures = 10  # например, 10 подряд ошибок
        first_frame_read = False

        while not self._stopped.is_set():
            if self._paused.is_set():
                time.sleep(0.05)
                continue

            ret, frame = self._cap.read()
            if not ret:
                failure_count += 1
                if failure_count >= max_failures:
                    self._camera_lost.set()
                    self._error_event.set()
                    break
                time.sleep(0.1)
                continue

            if not first_frame_read:
                # Успешное первое чтение — теперь выполняем прогрев
                first_frame_read = True
                time.sleep(self.warmup_seconds)
                self._ready.set()

            failure_count = 0  # сбрасываем, если чтение успешно

            with self._lock:
                self._latest_frame = frame
                self._new_frame_ready.set()

    def get_frame(self, timeout: float = 1.0) -> Optional["cv2.typing.MatLike"]:
        """
        Возвращает кадр из очереди, если доступен.
        :param timeout: Максимальное время ожидания
        :return: Кадр или None
        """
        if not self._ready.is_set():
            return None

        is_new = self._new_frame_ready.wait(timeout=timeout)
        if not is_new:
            return None

        now = time.monotonic()
        delay = 1.0 / self.max_fps
        if now - self._last_frame_time < delay:
            return None  # Пропускаем кадр — слишком рано

        with self._lock:
            frame = self._latest_frame.copy() if self._latest_frame is not None else None
            self._new_frame_ready.clear()
            self._last_frame_time = now
            return frame

    def pause(self) -> None:
        """Приостанавливает чтение кадров (например, при блокировке экрана)"""
        self._paused.set()

    def resume(self) -> None:
        """Возобновляет чтение кадров"""
        self._paused.clear()

    def stop(self) -> None:
        """Останавливает поток и освобождает ресурсы"""
        self._stopped.set()
        self._thread.join(timeout=2)
        if self._cap is not None:
            self._cap.release()

    def is_ready(self) -> bool:
        """Готов ли поток к обработке (прогрев завершен)"""
        return self._ready.is_set()


class ApplicationController:
    """
    Управляет видеозахватом, обработкой YOLOv12n и блокировкой экрана.
    """
    def __init__(self, model_path: str) -> None:
        self.app = QApplication(sys.argv)
        self.error_window = ErrorWindow()
        self.config = Config()
        self.phone_limit = self.config.get("phone_limit")
        try:
            self.window_name = "Stream"
            self.fps = self.config.get("fps")
            self.camera_id = self.config.get("camera_id")
            self.confidence_threshold = self.config.get("confidence_threshold")
            self.min_step_time = 0.5 / self.fps
            self.detector = Detector(model_path=model_path)
            self.camera = CameraStream(
                source=self.camera_id,
                warmup_seconds=2,
                max_fps=self.fps,
            )
            self.logger = Logger()  # Без явного пути, Logger сам управляет
            # set_admin_only_access("logs")
            self._loop_thread = threading.Thread(target=self._main_loop, daemon=True)
            self._stop_event = threading.Event()
            signal.signal(signal.SIGTERM, self.handle_termination)
            signal.signal(signal.SIGINT, self.handle_termination)
            logger.debug(f"Initialized UserApp: camera_id={self.config.get('camera_id')}, fps={self.fps}, confidence={self.confidence_threshold}")
        except Exception as e:
            logger.critical(f"Error initializing camera: {e}")
            if self.config.get("lock_events")["camera_lost"]:
                lock_screen()
            sys.exit(1)

    # def __init__(self, model_path: str) -> None:
    #     self.app = QApplication(sys.argv)  # For QMessageBox
    #     self.error_window = ErrorWindow()
    #     self.config = Config()
        
    #     try:
    #         self.window_name = "Stream"
    #         self.fps = self.config.get("fps")
    #         self.camera_id = self.config.get("camera_id")
    #         self.confidence_threshold = self.config.get("confidence_threshold")
    #         self.min_step_time = 0.5 / self.fps
            
    #         self.detector = Detector(model_path=model_path)
    #         self.camera = CameraStream(
    #             source=self.camera_id,
    #             warmup_seconds=2,
    #             max_fps=self.fps,
    #         )
    #         self.logger = Logger(get_resource_path("logs/detection_log.db"))
    #         # set_admin_only_access("logs")
    #         self._loop_thread = threading.Thread(target=self._main_loop, daemon=True)
    #         self._stop_event = threading.Event()
            
            
    #         signal.signal(signal.SIGTERM, self.handle_termination)
    #         signal.signal(signal.SIGINT, self.handle_termination)
    #         logger.debug(f"Initialized UserApp: camera_id={self.config.get('camera_id')}, fps={self.fps}, confidence={self.confidence_threshold}")
    #     except Exception as e:
    #         logger.critical(f"Error initializing camera: {e}")
    #         if self.config.get("lock_events")["camera_lost"]:
    #             lock_screen()
    #         sys.exit(1)
            
    def show_alert(self, message):
        if not self.config.get("notifications_enabled"):
            return
        msg = QMessageBox()
        msg.setWindowFlags(Qt.WindowStaysOnTopHint)
        msg.setWindowTitle("Оповещение")
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        logger.debug(f"Showed alert: {message}")
        
    def handle_termination(self, signum, frame):
        logger.debug("Detected attempt to terminate process")
        active_apps = get_active_apps()
        logger.debug(f"Active apps on termination: {active_apps}")
        frame = self.camera.get_frame(timeout=1.0) if self.camera._cap.isOpened() else None
        if self.config.get("log_events")["attempt_to_close"]:
            self.logger.log_event("Попытка закрыть приложение", frame, active_apps=active_apps)
        if self.config.get("lock_events")["attempt_to_close"]:
            lock_screen()
        logger.debug("Terminating")
        self.camera.stop()
        cv2.destroyAllWindows()
        sys.exit(0)
        
    def prepare_logging(
        self,
        event: str,
        frame: np.ndarray,
        notification_status: str,
        notifications_enabled: bool,
        log_enable: bool,
        lock_enable: bool,
        bbox=None, confs=None,
        notification_data: dict = {},
    ) -> None:
        logger.debug(event)
        active_apps = get_active_apps()
        logger.debug(f"Active apps: {active_apps}")
        
        username = str(getpass.getuser())
        pc_name = str(platform.node())
        screen = take_screenshot()
        timestamp = str(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        
        logger.debug("before log enable")
        if frame is not None and bbox is not None and event == "Обнаружен мобильный телефон":
            x1, y1, x2, y2 = bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, "Phone", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        if log_enable:
            logger.debug("log_enable - true")
            self.logger.log_event(event, frame, screen, username, logger, timestamp, confs, active_apps=active_apps)
        else:
            logger.debug("log_enable - false")
        
        if lock_enable:
            try:
                minimize_all_windows()
            except Exception as e:
                logger.warning(e)
            lock_screen()
            print(f"Время выполнения: {time.perf_counter() - self.start_time:.6f} секунд")
            range_v = 20
            sleep_v = 0.2
            for _ in range(20):
                if is_screen_locked():
                    break
                time.sleep(0.2)
            else:
                print(f"[App] Предупреждение: экран не заблокировался в течение {range_v * sleep_v} секунд")
            
        
        # self.show_alert(event)
        if notifications_enabled:
            notify_async(
                list(map(int, self.config.get("telegram_ids"))),
                str(notification_status),
                str(event),
                str(username),
                str(pc_name),
                [screen,] if frame is None else [frame, screen],
                str(timestamp),
                notification_data,
            )
            
    def start(self) -> None:
        print("[App] Запуск камеры и логики анализа...")
        self.camera.start()

        if self.camera.is_camera_lost():
            logger.warning("[App] Камера недоступна при запуске")
            self.prepare_logging(
                "Камера не подключена при запуске",
                frame=None,
                notification_status="CRITICAL",
                notifications_enabled=self.config.get("notifications_enabled"),
                log_enable=self.config.get("log_events")["camera_lost"],
                lock_enable=self.config.get("lock_events")["camera_lost"],
            )

        self._loop_thread.start()

    def stop(self) -> None:
        print("[App] Остановка приложения...")
        self._stop_event.set()
        self.camera.stop()
        
    def sleep_remain(self, step_start) -> None:
        elapsed = time.perf_counter() - step_start
        remaining = self.min_step_time - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _main_loop(self) -> None:
        """Главный цикл: обработка кадров и реакция на блокировку экрана"""
        status_continued = {
            "uniform_image": False,
            "static_img": False,
            "camera_lost": False,
        }
        phone_count: int = 0  # считаем число подряд идущих кадров телефонов, чтобы вызвать события на это
        # phone_limit: int = 2  # порог по которому вызываем события
        last_frame = None
        last_unique_frame_time = time.time()
        while not self._stop_event.is_set():
            # print(1)
            step_start = time.perf_counter()
            if is_screen_locked():
                print("is_screen_locked", is_screen_locked())
                print("[App] Обнаружена блокировка экрана. Ставим на паузу.")
                self.camera.pause()
                wait_for_unlock()
                print("[App] Разблокировано. Продолжаем работу.")
                self.camera.resume()
                # if status_continued["camera_lost"]:
                #     try:
                #         self.camera.restart()
                #         logger.info("Camera restarted succenssfully")
                #     except Exception as e:
                #         logger.warning("Camera restart failed: {e}")
                #         time.sleep(1)
                #         continue
                # else:
                #     self.camera.resume()
                #     print("resume end")
            
            if self.camera.is_camera_lost():
                if not status_continued["camera_lost"]:
                    logger.warning("Camera connection lost")
                    self.prepare_logging(
                        "Потеря связи с камерой",
                        frame,
                        "CRITICAL",
                        self.config.get("notifications")["camera_lost"],
                        self.config.get("log_events")["camera_lost"],
                        self.config.get("lock_events")["camera_lost"],
                    )
                    status_continued["camera_lost"] = True
                self.sleep_remain(step_start)
                break
            # elif status_continued["camera_lost"]:
            #     logger.info("Camera connection lost - cancel.")
            #     try:
            #         self.camera.restart()
            #         logger.info("Camera restarted succenssfully")
            #     except Exception as e:
            #         logger.warning("Camera restart failed: {e}")
            #         time.sleep(1)
            #         continue
            #     frame = self.camera.get_frame(timeout=1.0)
            #     self.prepare_logging(
            #         "Востановление после \"Потеря связи с камерой\"",
            #         frame,
            #         "RECOVERY",
            #         self.config.get("notifications_enabled"),
            #         self.config.get("log_events")["camera_lost"],
            #         False,
            #     )
            #     status_continued["camera_lost"] = False
            #     self.sleep_remain(step_start)
            #     continue

            frame = self.camera.get_frame(timeout=1.0)
            self.start_time = time.perf_counter()
            if frame is None:
                self.sleep_remain(step_start)
                continue
                
            if is_uniform(frame):
                if not status_continued["uniform_image"]:
                    logger.debug("Uniform image detected")
                    self.prepare_logging(
                        "Однотонное изображение",
                        frame,
                        "CRITICAL",
                        self.config.get("notifications")["uniform_image"],
                        self.config.get("log_events")["uniform_image"],
                        self.config.get("lock_events")["uniform_image"],
                    )
                    status_continued["uniform_image"] = True
                    self.sleep_remain(step_start)
                    continue
            elif status_continued["uniform_image"]:
                if status_continued["uniform_image"]:
                    logger.debug("Uniform image detected - cancel.")
                    self.prepare_logging(
                        "После однотонного изображения",
                        frame,
                        "RECOVERY",
                        self.config.get("notifications")["uniform_image"],
                        self.config.get("log_events")["uniform_image"],
                        False,
                    )
                    status_continued["uniform_image"] = False
            
            now = time.time()
            if last_frame is not None and is_similar_frame(frame, last_frame):
                if not status_continued["static_img"]:
                    if now - last_unique_frame_time > 30:
                        logger.debug("Frame frozen for >30s, triggering lock")
                        self.prepare_logging(
                            "Зависшее изображение",
                            frame,
                            "CRITICAL",
                            self.config.get("notifications")["static_img"],
                            self.config.get("log_events")["static_img"],
                            self.config.get("lock_events")["static_img"],
                        )
                        status_continued["static_img"] = True
                        self.sleep_remain(step_start)
                        continue
            else:
                last_unique_frame_time = now
                last_frame = frame.copy()
                if status_continued["static_img"]:
                    logger.debug("Frame frozen for >30s, triggering lock - cancel.")
                    self.prepare_logging(
                        "После однотонного изображения",
                        frame,
                        "RECOVERY",
                        self.config.get("notifications")["static_img"],
                        self.config.get("log_events")["static_img"],
                        False,
                    )
                    status_continued["static_img"] = False

            # Обработка YOLO
            found, bbox, confs = self.detector.detect_phone(frame, conf=self.confidence_threshold)
            if found:
                phone_count += 1
                if phone_count >= self.phone_limit:
                    logger.debug(f"[App] Телефон обнаружен: {bbox}, conf: {confs[0]:.2f}")
                    self.prepare_logging(
                        "Обнаружен мобильный телефон",
                        frame,
                        "CRITICAL",
                        self.config.get("notifications")["phone_detected"],
                        self.config.get("log_events")["phone_detected"],
                        self.config.get("lock_events")["phone_detected"],
                        bbox,
                        confs,
                    )
                    self.sleep_remain(step_start)
                    continue
            else:
                phone_count = 0
                
            self.sleep_remain(step_start)


if __name__ == "__main__":
    try:
        app = ApplicationController(model_path="../../models/model.pt")
        app.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.stop()


# import cv2
# import signal
# import sys
# import time
# import getpass
# import numpy as np
# from src.core.camera import Camera
# from src.core.detector import Detector
# from src.core.lock_screen import lock_screen, is_screen_locked, wait_for_unlock
# from src.core.logger import Logger
# from src.core.config import Config
# from src.core.error_window import ErrorWindow
# from src.core.system_info import get_active_apps
# from src.infra.take_screenshot import take_screenshot
# from src.infra.send_tg_alert import send_notification
# from PyQt5.QtWidgets import QApplication, QMessageBox
# from PyQt5.QtCore import Qt
# from skimage.metrics import structural_similarity as ssim
# from datetime import datetime

# class UserApp:
#     def __init__(self):
#         self.app = QApplication(sys.argv)  # For QMessageBox
#         self.config = Config()
#         self.first_run = True
#         try:
#             self.camera = Camera(device_id=self.config.get("camera_id"))
#             self.detector = Detector("models/model.pt")
#             self.logger = Logger("logs/detection_log.db")
#             self.fps = self.config.get("fps")
#             self.confidence_threshold = self.config.get("confidence_threshold")
#             self.error_window = ErrorWindow()
#             self.window_name = "Stream"
#             signal.signal(signal.SIGTERM, self.handle_termination)
#             signal.signal(signal.SIGINT, self.handle_termination)
#             print(f"DEBUG: Initialized UserApp: camera_id={self.config.get('camera_id')}, fps={self.fps}, confidence={self.confidence_threshold}")
#         except Exception as e:
#             print(f"DEBUG: Error initializing camera: {e}")
#             self.show_alert("Камера не найдена")
#             if self.config.get("lock_events")["camera_lost"] and not self.first_run:
#                 lock_screen()
#             sys.exit(1)

#     def show_alert(self, message):
#         if True or not self.config.get("notifications_enabled"):
#             return
#         msg = QMessageBox()
#         msg.setWindowFlags(Qt.WindowStaysOnTopHint)
#         msg.setWindowTitle("Оповещение")
#         msg.setText(message)
#         msg.setStandardButtons(QMessageBox.Ok)
#         msg.exec_()
#         print(f"DEBUG: Showed alert: {message}")

#     def handle_termination(self, signum, frame):
#         print("DEBUG: Detected attempt to terminate process")
#         active_apps = get_active_apps()
#         print(f"DEBUG: Active apps on termination: {active_apps}")
#         frame = self.camera.get_frame() if self.camera.cap.isOpened() else None
#         if self.config.get("log_events")["attempt_to_close"]:
#             self.logger.log_event("Попытка закрыть приложение", frame, active_apps=active_apps)
#         if self.config.get("lock_events")["attempt_to_close"]:
#             lock_screen()
#         print("DEBUG: Terminating")
#         self.camera.release()
#         cv2.destroyAllWindows()
#         sys.exit(0)

#     def run(self):
#         status_continued = {
#             "uniform_image": False,
#             "static_img": False,
#         }
#         last_frame = None
#         last_unique_frame_time = time.time()
#         cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
#         while True:
#             if is_screen_locked():
#                 print("DEBUG: Screen locked, pausing analysis")
#                 wait_for_unlock()
#                 cv2.destroyWindow(self.window_name)
#                 cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
#                 print("DEBUG: OpenCV window recreated after unlock")
#                 continue
#             # screen = take_screenshot()

#             print("DEBUG: Capturing new frame")
#             frame = self.camera.get_frame()
#             now = time.time()
#             if last_frame is not None and is_similar_frame(frame, last_frame):
#                 if not status_continued["static_img"]:
#                     if now - last_unique_frame_time > 30:
#                         print("DEBUG: Frame frozen for >30s, triggering lock")
#                         active_apps = get_active_apps()
#                         self.show_alert("Изображение не меняется 30 секунд (камера зависла?)")
#                         if self.config.get("log_events")["static_img"]:
#                             self.logger.log_event("Зависшее изображение", frame, take_screenshot, active_apps=active_apps)
#                         if self.config.get("lock_events")["static_img"]:
#                             lock_screen()
#                         status_continued["static_img"] = True
#                         continue
#             else:
#                 last_unique_frame_time = now
#                 last_frame = frame.copy()
#                 if status_continued["static_img"]:
#                     self.show_alert("Изображение изменилось после зависания")
#                     if self.config.get("log_events")["static_img"]:
#                         self.logger.log_event("Изображение отвисло", frame, take_screenshot, active_apps=active_apps)
#                     status_continued["static_img"] = False
            
#             if frame is None:
#                 print("DEBUG: Camera connection lost")
#                 active_apps = get_active_apps()
#                 print(f"DEBUG: Active apps on camera loss: {active_apps}")
#                 self.show_alert("Потеря связи с камерой")
#                 if self.config.get("log_events")["camera_lost"]:
#                     self.logger.log_event("Потеря связи с камерой", frame, take_screenshot, active_apps=active_apps)
#                 if self.config.get("lock_events")["camera_lost"] and not self.first_run:
#                     lock_screen()
#                 continue

#             if self.camera.is_uniform(frame):
#                 if not status_continued["uniform_image"]:
#                     print("DEBUG: Uniform image detected")
#                     active_apps = get_active_apps()
#                     print(f"DEBUG: Active apps on uniform image: {active_apps}")
#                     self.show_alert("Обнаружено однотонное изображение (камера закрыта)")
#                     if self.config.get("log_events")["uniform_image"]:
#                         self.logger.log_event("Однотонное изображение", frame, take_screenshot, active_apps=active_apps)
#                     if self.config.get("lock_events")["uniform_image"] and not self.first_run:
#                         lock_screen()
#                     status_continued["uniform_image"] = True
#                     continue
#             elif status_continued["uniform_image"]:
#                 self.show_alert("Однотонность пропала")
#                 if status_continued["uniform_image"]:
#                     self.show_alert("Однотонность прошла (камера открыта)")
#                     if self.config.get("log_events")["uniform_image"]:
#                         self.logger.log_event("После однотонного изображения", frame, take_screenshot, active_apps=active_apps)
#                     status_continued["uniform_image"] = False

#             print("DEBUG: Performing phone detection")
#             phone_detected, box, confidences = self.detector.detect_phone(frame, conf=self.confidence_threshold)
#             if phone_detected:
#                 print("DEBUG: Phone detected")
#                 active_apps = get_active_apps()
#                 print(f"DEBUG: Confidences: {confidences}, Active apps: {active_apps}")
#                 self.show_alert("Обнаружен мобильный телефон")
#                 if self.config.get("notifications_enabled"):
#                     print("-" * 50)
#                     send_notification(
#                         "CRITICAL",
#                         "Обнаружен мобильный телефон",
#                         getpass.getuser(),
#                         [frame, take_screenshot()],
#                         datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
#                         {},
#                     )
#                 if self.config.get("log_events")["phone_detected"]:
#                     self.logger.log_event("Обнаружен мобильный телефон", frame, take_screenshot, box=box, confidence=confidences, active_apps=active_apps)
#                 if self.config.get("lock_events")["phone_detected"]:
#                     lock_screen()
#                 continue

#             print("DEBUG: Displaying frame")
#             cv2.imshow(self.window_name, frame)
#             print("DEBUG: Waiting for key press")
#             key = cv2.waitKey(int(1000 / self.fps))
#             if key & 0xFF == ord("q"):
#                 print("DEBUG: 'q' key pressed, logging attempt to close")
#                 active_apps = get_active_apps()
#                 print(f"DEBUG: Active apps on 'q' press: {active_apps}")
#                 if self.config.get("log_events")["attempt_to_close"]:
#                     self.logger.log_event("Попытка закрыть приложение", frame, take_screenshot, active_apps=active_apps)
#                 if self.config.get("lock_events")["attempt_to_close"]:
#                     lock_screen()
#                 print("DEBUG: 'q' key pressed, terminating")
#                 break
#             print(f"DEBUG: Key code: {key}")

#         print("DEBUG: Terminating, releasing resources")
#         self.first_run = False
#         self.camera.release()
#         cv2.destroyAllWindows()

def is_uniform(frame):
    try:
        if frame is None:
            return False
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        variance = cv2.meanStdDev(gray)[1][0][0]
        is_uniform = variance < 10
        logger.debug(f"Проверка однотонности: variance={variance}, is_uniform={is_uniform}")
        return is_uniform
    except Exception as e:
        logger.warning(f"Ошибка проверки однотонности: {e}")
        return False

        
def is_similar_frame(frame1: np.ndarray, frame2: np.ndarray, 
                     ssim_threshold: float = 0.95,
                     mean_diff_threshold: float = 5.0) -> bool:
    """
    Сравнивает два кадра и определяет, похожи ли они.

    :param frame1: Первый кадр (BGR NumPy массив)
    :param frame2: Второй кадр (BGR NumPy массив)
    :param ssim_threshold: Минимальное значение SSIM, при котором кадры считаются одинаковыми (от 0 до 1)
    :param mean_diff_threshold: Максимальное среднее отклонение по пикселям (0–255), при котором кадры считаются одинаковыми
    :return: True, если кадры считаются похожими
    """
    if frame1.shape != frame2.shape:
        return False

    # Переводим в оттенки серого и сглаживаем
    gray1 = cv2.GaussianBlur(cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    gray2 = cv2.GaussianBlur(cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY), (5, 5), 0)

    # Считаем SSIM
    similarity, _ = ssim(gray1, gray2, full=True)
    print(f"DEBUG: SSIM similarity = {similarity:.4f}")

    # Альтернативный способ: среднее абсолютное отклонение
    mean_diff = np.mean(cv2.absdiff(gray1, gray2))
    print(f"DEBUG: Mean gray-level difference = {mean_diff:.2f}")

    # Оба условия должны выполняться, чтобы считать кадры "похожими"
    return similarity >= ssim_threshold and mean_diff <= mean_diff_threshold
