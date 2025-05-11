from ultralytics import YOLO
import cv2

class Detector:
    def __init__(self, model_path):
        try:
            self.model = YOLO(model_path)
            print(f"Модель загружена. Классы: {self.model.names}")
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")
            raise

    def detect_phone(self, frame, conf=0.5):
        try:
            results = self.model(frame, conf=conf)  # Используем переданный conf
            phones = []
            confidences = []
            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls)
                    if class_id == 0:  # Класс телефона
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf_value = box.conf.item()
                        print(f"Обнаружен объект: класс={class_id}, уверенность={conf_value:.2f}, координаты=({x1}, {y1}, {x2}, {y2})")
                        phones.append((x1, y1, x2, y2))
                        confidences.append(conf_value)
            if phones:
                return True, phones[0], confidences
            print("Телефон не обнаружен в кадре")
            return False, None, []
        except Exception as e:
            print(f"Ошибка при детекции: {e}")
            return False, None, []