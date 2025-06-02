import onnxruntime as ort
import cv2
import numpy as np
import logging

logging.basicConfig(level=logging.CRITICAL+1, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)


class Detector:
    def __init__(self, model_path):
        try:
            self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
            self.input_name = self.session.get_inputs()[0].name
            logger.debug(f"Сессия ONNX Runtime создана: {self.session.get_providers()}")
        except Exception as e:
            logger.debug(f"Ошибка при создании сессии ONNX: {e}")
            raise

    def detect_phone(self, image, conf=0.5):
        try:
            input_data = self.preprocess_image(image)
            outputs = self.session.run(None, {self.input_name: input_data})[0]
            detections = self.postprocess_output(outputs, conf_thres=conf)
            
            phones = []
            confidences = []
            for x1, y1, x2, y2, conf_value, class_id in detections:
                class_id = int(class_id)
                if class_id == 0 and float(conf_value) >= conf:
                    x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                    logger.debug(f"Обнаружен объект: класс={class_id}, уверенность={conf_value:.2f}, координаты=({x1}, {y1}, {x2}, {y2})")
                    phones.append((x1, y1, x2, y2))
                    confidences.append(float(conf_value))
                    break
            if phones:
                return True, phones[0], confidences
            logger.debug("Телефон не обнаружен в кадре")
            return False, None, []
        except Exception as e:
            logger.debug(f"Ошибка при детекции: {e}")
            return False, None, []
        
    @staticmethod
    def prepreprocess(frame: np.ndarray) -> np.ndarray:
        # 1. rgb to bgr
        img = frame
        # img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Проверка и удаление 4-го канала, если он есть
        if img.shape[-1] == 4:
            img = img[:, :, :3]
        
        # Определение размеров для ресайза
        h, w = img.shape[:2]
        if h > w:
            new_h = 640
            new_w = int(w * 640 / h)
        else:
            new_w = 640
            new_h = int(h * 640 / w)
        
        # Ресайз с сохранением пропорций
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Добавление серых полей (RGB: 114, 114, 114)
        border_v = (640 - new_h) // 2
        border_h = (640 - new_w) // 2
        img = cv2.copyMakeBorder(
            img,
            top=border_v,
            bottom=640 - new_h - border_v,
            left=border_h,
            right=640 - new_w - border_h,
            borderType=cv2.BORDER_CONSTANT,
            value=(114, 114, 114)
        )
        return img
    
    @staticmethod
    def preprocess_image(img: np.ndarray) -> np.ndarray:
        # Расширение до BHWC (добавление размерности batch)
        img = img[np.newaxis, ...]  # (1, h, w, c)
        
        # Транспонирование BHWC -> BCHW
        img = img.transpose((0, 3, 1, 2))  # (n, c, h, w)
        
        # Обеспечение непрерывности массива и нормализация
        img = np.ascontiguousarray(img, dtype=np.float32)
        img = img / 255.0
        
        return img
    
    @staticmethod
    def postprocess_output(
        outputs: np.ndarray, 
        conf_thres: float = 0.25,
        iou_thres: float = 0.45
    ) -> np.ndarray:
        """
        Постобработка выходов модели YOLO для одного класса (индекс 0).

        Args:
            outputs: Выход модели [batch, num_boxes, 4 + num_classes].
            conf_thres: Порог уверенности.
            iou_thres: Порог IoU для NMS.

        Returns:
            Список детекций: [(x1, y1, x2, y2, confidence, class_id), ...].
        """
        boxes = outputs[0]  # [num_boxes, 5] (x, y, w, h, conf)
        detections = []

        for i in range(boxes.shape[-1]):
            box = boxes[:, i]
            x, y, w, h, conf = box[:5]
            if conf > 1:
                logger.debug("what!? conf more than 1?")
            if conf < conf_thres:
                continue

            x1 = x - w / 2
            y1 = y - h / 2
            x2 = x + w / 2
            y2 = y + h / 2
            class_id = 0  # Один класс с индексом 0

            detections.append((x1, y1, x2, y2, conf, class_id))

        if detections:
            boxes = np.array([[x1, y1, x2, y2] for x1, y1, x2, y2, _, _ in detections])
            scores = np.array([conf for _, _, _, _, conf, _ in detections])
            indices = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), conf_thres, iou_thres)
            detections = [detections[i] for i in indices.flatten()]

        logger.debug(f"Найдено {len(detections)} объектов")
        return detections
