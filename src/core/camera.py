import cv2
import time
import win32com.client
import logging

logging.basicConfig(level=logging.CRITICAL+1, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

class Camera:
    def __init__(self, device_id=0):
        self.device_id = device_id
        try:
            self.cap = cv2.VideoCapture(device_id, cv2.CAP_ANY)
            if not self.cap.isOpened():
                raise Exception(f"Не удалось открыть камеру с ID {device_id}")
            logger.debug(f"DEBUG: Камера {device_id} открыта")
        except Exception as e:
            logger.debug(f"DEBUG: Ошибка инициализации камеры {device_id}: {e}")
            raise

    def get_frame(self):
        try:
            ret, frame = self.cap.read()
            if not ret:
                logger.debug(f"DEBUG: Не удалось получить кадр с камеры {self.device_id}")
                return None
            return frame
        except Exception as e:
            logger.debug(f"DEBUG: Ошибка получения кадра: {e}")
            return None

    def is_uniform(self, frame):
        try:
            if frame is None:
                return False
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            variance = cv2.meanStdDev(gray)[1][0][0]
            is_uniform = variance < 10
            logger.debug(f"DEBUG: Проверка однотонности: variance={variance}, is_uniform={is_uniform}")
            return is_uniform
        except Exception as e:
            logger.debug(f"DEBUG: Ошибка проверки однотонности: {e}")
            return False

    def release(self):
        try:
            if hasattr(self, 'cap') and self.cap is not None:
                self.cap.release()
                logger.debug(f"DEBUG: Камера {self.device_id} освобождена")
        except Exception as e:
            logger.debug(f"DEBUG: Ошибка освобождения камеры: {e}")

    @staticmethod
    def list_available_cameras():
        cv2.setLogLevel(0)  # Suppress OpenCV warnings
        cameras = []
        max_index = 3  # Ограничим проверку 3 индексами
        for i in range(max_index):
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_ANY)
                time.sleep(0.05)  # Короткий таймаут
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        wmi = win32com.client.GetObject("winmgmts:")
                        devices = wmi.ExecQuery(f"SELECT * FROM Win32_PnPEntity WHERE PNPClass = 'Camera'")
                        device_name = f"Камера {i}"
                        for device in devices:
                            if device.DeviceID:
                                device_name = device.Name or f"Камера {i}"
                                break
                        cameras.append((i, device_name))
                        logger.debug(f"DEBUG: Найдена камера: ID={i}, Name={device_name}")
                    cap.release()
                else:
                    logger.debug(f"DEBUG: Камера с ID {i} не открыта")
            except Exception as e:
                logger.debug(f"DEBUG: Ошибка проверки камеры {i}: {e}")
        return cameras