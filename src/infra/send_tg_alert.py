import requests
from datetime import datetime
from io import BytesIO
import cv2
import logging

logging.basicConfig(level=logging.CRITICAL+1, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = "8024143683:AAEIdfSrzRQW9qfUA0-BaDNAUnwuFf3VQHc"
ALL_CHAT_IDS = [-1002539322922]     # получатели CRITICAL и RECOVERY
ADMIN_CHAT_IDS = [-1002539322922]              # получатели WARNING

# notification_async.py
from concurrent.futures import ThreadPoolExecutor, Future
import traceback
import logging

# Глобальный пул для фоновых задач (уведомлений)
_NOTIFICATION_POOL = ThreadPoolExecutor(max_workers=2)  # 2 потока достаточно

def notify_async(*args, **kwargs) -> Future:
    """
    Отправляет уведомление в фоне через ThreadPoolExecutor.
    Возвращает Future, с которым можно работать (например, проверять ошибки).
    """
    def safe_notify():
        try:
            send_notification(*args, **kwargs)
        except Exception:
            logging.error("Ошибка при отправке уведомления:\n%s", traceback.format_exc())

    return _NOTIFICATION_POOL.submit(safe_notify)


def escape_markdown(text: str) -> str:
    # escape_chars = r'\_*[]()~`>#+-=|{}.!'
    escape_chars = r'\_*[]()~`>#+=|{}.!'
    return ''.join(f'\\{c}' if c in escape_chars else c for c in text)


def send_notification(recipients, status, message_text, username, pc_name: str, images, timestamp, data_dict):
    status_tags = {'CRITICAL': '🛑', 'WARNING': '⚠️', 'RECOVERY': '✅'}
    tag = status_tags.get(status, 'ℹ️')

    if isinstance(timestamp, datetime):
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    else:
        timestamp_str = str(timestamp)

    # Формируем текст уведомления
    data_lines = "\n".join(f"{k}: {v}" for k, v in data_dict.items())
    text = (
        f"{tag} *{status}*\n"
        f"*Имя устройства*: {escape_markdown(pc_name)}\n"
        f"*Пользователь:* {escape_markdown(username)}\n"
        f"*Описание:* {escape_markdown(message_text)}\n"
        f"*Время:* {escape_markdown(timestamp_str)}\n"
        f"*Данные:*\n{escape_markdown(data_lines)}"
    )

    # # Определяем получателей
    # if status == 'CRITICAL':
    #     recipients = ALL_CHAT_IDS
    # elif status == 'WARNING':
    #     recipients = ADMIN_CHAT_IDS
    # elif status == 'RECOVERY':
    #     recipients = ALL_CHAT_IDS
    # else:
    #     recipients = ADMIN_CHAT_IDS

    # Отправляем текстовое сообщение
    for chat_id in recipients:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
        )
        if not response.ok:
            logger.warning(f"[Ошибка] Текст в {chat_id}: {response.text}")

    # Отправляем изображения
    for img in images:
        success, encoded_image = cv2.imencode('.jpg', img)
        if not success:
            logger.warning("[Ошибка] Не удалось закодировать изображение")
            continue
        img_bytes = BytesIO(encoded_image.tobytes())

        for chat_id in recipients:
            img_bytes.seek(0)
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={'chat_id': chat_id},
                files={'photo': ('image.jpg', img_bytes, 'image/jpeg')}
            )
            if not response.ok:
                logger.warning(f"[Ошибка] Картинка в {chat_id}: {response.text}")
        img_bytes.close()


if __name__ == "__main__":
    img = cv2.imread(r"D:\start_point\projects\phone_detection_app\logs\2025-04-30_20-13-38_phone_detected_screen.jpg")[:,:,::-1]
    
    send_notification(
        "CRITICAL",
        "test critical alert",
        "custom username",
        "custom pc name",
        [img, img],
        "это дата события",
        {"info": "дополнительная инфа, если потребуется"})
