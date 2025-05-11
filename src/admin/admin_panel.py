import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QVBoxLayout, QWidget, QDialog, QLabel, QPushButton, QHBoxLayout, QComboBox,
    QSpinBox, QDoubleSpinBox, QFormLayout, QCheckBox, QGroupBox, QMessageBox, QDateEdit,
    QFileDialog, QTimeEdit, QLineEdit, QTextEdit, QListWidget, QScrollArea
)
from PyQt5.QtGui import QPixmap, QImage, QIcon, QColor
from PyQt5.QtCore import Qt, QTimer, QDate, QTime
import json
import cv2
from src.core.logger import Logger
from src.core.camera import Camera
from src.core.config import Config
from src.infra.enable_autostart import enable_autostart, APP_NAME, get_project_main_path, disable_autostart
from datetime import datetime, timedelta
import sqlite3
import logging

# from PyQt5.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QTabWidget
# from PyQt5.QtGui import QIcon, QImage, QPixmap
# from PyQt5.QtCore import Qt
# import os
# import cv2
# import json


# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

def get_base_path():
    """Возвращает базовый путь: sys._MEIPASS для .exe или корень проекта."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def get_resource_path(relative_path):
    """Возвращает абсолютный путь к ресурсу."""
    return os.path.join(get_base_path(), relative_path)


def get_image_path(relative_path):
    """
    Возвращает абсолютный путь к ресурсу, учитывая запуск из .py или .exe.
    Для .exe использует директорию исполняемого файла, а не sys._MEIPASS.
    """
    if getattr(sys, 'frozen', False):  # Запуск из .exe (PyInstaller)
        # Получаем директорию, где находится .exe
        base_path = os.path.dirname(sys.executable)
    else:  # Запуск из .py
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return os.path.join(base_path, relative_path)


class FullScreenImageDialog(QDialog):
    def __init__(self, frame_path, screen_path, parent=None):
        super().__init__(parent)
        self.frame_path = frame_path
        self.screen_path = screen_path
        self.current_image = "frame"  # Начальное изображение: "frame" или "screen"
        self.setWindowTitle("Просмотр изображения")
        
        # Устанавливаем размер окна (80% от размера экрана)
        screen_size = QApplication.desktop().availableGeometry().size()
        self.resize(int(screen_size.width() * 0.8), int(screen_size.height() * 0.8))

        # Основной макет
        self.layout = QVBoxLayout()

        # Заголовок (Frame или Screen)
        self.title_label = QLabel("Frame")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: white; font-size: 16px; background-color: #333;")
        self.layout.addWidget(self.title_label)

        # Макет для изображения и кнопок
        content_layout = QHBoxLayout()

        # Навигация слева
        nav_left = QVBoxLayout()
        self.prev_button = QPushButton("<")
        self.prev_button.setFixedSize(40, 40)
        self.prev_button.setStyleSheet("background-color: #555; color: white; border: 1px solid #777;")
        self.prev_button.clicked.connect(self.show_previous_image)
        nav_left.addStretch()
        nav_left.addWidget(self.prev_button)
        nav_left.addStretch()
        content_layout.addLayout(nav_left)

        # Область для изображения с прокруткой
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setStyleSheet("background-color: black; border: none;")
        content_layout.addWidget(self.scroll_area)

        # Навигация справа
        nav_right = QVBoxLayout()
        self.next_button = QPushButton(">")
        self.next_button.setFixedSize(40, 40)
        self.next_button.setStyleSheet("background-color: #555; color: white; border: 1px solid #777;")
        self.next_button.clicked.connect(self.show_next_image)
        nav_right.addStretch()
        nav_right.addWidget(self.next_button)
        nav_right.addStretch()
        content_layout.addLayout(nav_right)

        self.layout.addLayout(content_layout)
        self.setLayout(self.layout)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.setStyleSheet("background-color: #222;")  # Темный фон для окна
        self.update_image()

    def update_image(self):
        # Выбор пути к изображению
        image_path = self.frame_path if self.current_image == "frame" else self.screen_path
        print(f"DEBUG: Loading fullscreen image: {image_path}")
        
        if not os.path.exists(image_path):
            print(f"DEBUG: Image file does not exist: {image_path}")
            self.image_label.setText(f"Не удалось загрузить {self.current_image}")
            return

        image = cv2.imread(image_path)
        if image is not None:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            height, width, channel = image.shape
            qimage = QImage(image.data, width, height, width * channel, QImage.Format_RGB888)
            # Масштабируем до размера области с сохранением пропорций
            pixmap = QPixmap.fromImage(qimage).scaled(
                self.scroll_area.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(pixmap)
            self.image_label.adjustSize()  # Подгоняем размер метки под изображение
        else:
            self.image_label.setText(f"Не удалось загрузить {self.current_image}")

        # Обновляем заголовок
        self.title_label.setText("Frame" if self.current_image == "frame" else "Screen")

        # Кнопки всегда активны
        self.prev_button.setEnabled(True)
        self.next_button.setEnabled(True)

    def show_previous_image(self):
        self.current_image = "frame" if self.current_image == "screen" else "screen"
        self.update_image()

    def show_next_image(self):
        self.current_image = "screen" if self.current_image == "frame" else "frame"
        self.update_image()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Left:
            self.show_previous_image()
        elif event.key() == Qt.Key_Right:
            self.show_next_image()

class ImageDialog(QDialog):
    def __init__(self, logs, current_index, parent=None):
        super().__init__(parent)
        self.logs = logs
        self.current_index = current_index
        self.logger = Logger()  # Для получения путей
        self.setWindowTitle("Просмотр событий")
        self.setMinimumSize(900, 700)
        self.layout = QHBoxLayout()

        # Навигация слева
        nav_left = QVBoxLayout()
        # arrow_left_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'arrow_left.png'))
        arrow_left_path = get_resource_path('assets/arrow_left.png')
        print(f"DEBUG: Loading arrow_left: {arrow_left_path}, exists={os.path.exists(arrow_left_path)}")
        self.prev_button = QPushButton("<" if not os.path.exists(arrow_left_path) else "")
        if os.path.exists(arrow_left_path):
            self.prev_button.setIcon(QIcon(arrow_left_path))
        self.prev_button.setFixedSize(40, 40)
        self.prev_button.clicked.connect(self.show_previous)
        nav_left.addStretch()
        nav_left.addWidget(self.prev_button)
        nav_left.addStretch()
        self.layout.addLayout(nav_left)

        # Макет для содержимого (изображения и текст)
        content_layout = QVBoxLayout()
        
        # Макет для изображений (frame и screen)
        images_layout = QHBoxLayout()
        
        # Метка для frame
        self.frame_label = QLabel()
        self.frame_label.setAlignment(Qt.AlignCenter)
        self.frame_label.setStyleSheet("border: 2px solid black; padding: 5px;")
        self.frame_label.setCursor(Qt.PointingHandCursor)  # Курсор указывает на кликабельность
        self.frame_label.mousePressEvent = lambda x: self.open_fullscreen("frame")  # Обработчик клика
        images_layout.addWidget(self.frame_label)
        
        # Метка для screen
        self.screen_label = QLabel()
        self.screen_label.setAlignment(Qt.AlignCenter)
        self.screen_label.setStyleSheet("border: 2px solid black; padding: 5px;")
        self.screen_label.setCursor(Qt.PointingHandCursor)  # Курсор указывает на кликабельность
        self.screen_label.mousePressEvent = lambda x: self.open_fullscreen("screen")  # Обработчик клика
        images_layout.addWidget(self.screen_label)
        
        content_layout.addLayout(images_layout)
        
        # Метка для текстового описания
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        content_layout.addWidget(self.summary_label)
        self.layout.addLayout(content_layout)

        # Навигация справа
        nav_right = QVBoxLayout()
        arrow_right_path = get_resource_path('assets/arrow_right.png')
        # arrow_right_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'arrow_right.png'))
        print(f"DEBUG: Loading arrow_right: {arrow_right_path}, exists={os.path.exists(arrow_right_path)}")
        self.next_button = QPushButton(">" if not os.path.exists(arrow_right_path) else "")
        if os.path.exists(arrow_right_path):
            self.next_button.setIcon(QIcon(arrow_right_path))
        self.next_button.setFixedSize(40, 40)
        self.next_button.clicked.connect(self.show_next)
        nav_right.addStretch()
        nav_right.addWidget(self.next_button)
        nav_right.addStretch()
        self.layout.addLayout(nav_right)

        self.setLayout(self.layout)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.update_display()

    def update_display(self):
        log = self.logs[self.current_index]
        timestamp, event, frame_path, screen_path, confidence, active_apps, username = log[1], log[2], log[3], log[4], log[5], log[6], log[7]
        # abs_frame_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', frame_path))
        # abs_screen_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', screen_path))
        # abs_frame_path = get_resource_path(frame_path)
        # abs_screen_path = get_resource_path(screen_path)
        abs_frame_path = self.logger._get_log_file_path(frame_path) if frame_path else ""
        abs_screen_path = self.logger._get_log_file_path(screen_path) if screen_path else ""
        print(f"DEBUG: Loading images: frame_path={abs_frame_path}, screen_path={abs_screen_path}")

        # Загрузка и отображение frame
        frame_image = cv2.imread(abs_frame_path)
        if frame_image is not None:
            frame_image = cv2.cvtColor(frame_image, cv2.COLOR_BGR2RGB)
            height, width, channel = frame_image.shape
            qimage = QImage(frame_image.data, width, height, width * channel, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimage).scaled(400, 300, Qt.KeepAspectRatio)  # Уменьшенный размер для размещения двух изображений
            self.frame_label.setPixmap(pixmap)
        else:
            self.frame_label.setText("Не удалось загрузить frame")

        # Загрузка и отображение screen
        screen_image = cv2.imread(abs_screen_path)
        if screen_image is not None:
            screen_image = cv2.cvtColor(screen_image, cv2.COLOR_BGR2RGB)
            height, width, channel = screen_image.shape
            qimage = QImage(screen_image.data, width, height, width * channel, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimage).scaled(400, 300, Qt.KeepAspectRatio)  # Уменьшенный размер
            self.screen_label.setPixmap(pixmap)
        else:
            self.screen_label.setText("Не удалось загрузить screen")

        # Обработка текстового описания
        try:
            confidence = json.loads(confidence) if confidence else None
            active_apps = json.loads(active_apps) if active_apps else None
        except (json.JSONDecodeError, TypeError):
            confidence, active_apps = None, None

        confidence_text = ", ".join([f"{c:.2f}" for c in confidence]) if confidence else "Нет"
        apps_text = ""
        if active_apps:
            for app in active_apps:
                status = " (развернуто)" if app.get("foreground") else ""
                process = app.get("process", "")
                title = app.get("title", "")
                apps_text += f"{process}: {title}{status}\n"
        apps_text = apps_text.strip() or "Нет"

        summary = (
            f"Время: {timestamp}\n"
            f"Событие: {event}\n"
            f"Уверенность: {confidence_text}\n"
            f"Запущенные приложения:\n{apps_text}\n"
            f"Пользователь: {username}"
        )
        self.summary_label.setText(summary)

        # Активация/деактивация кнопок навигации
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.logs) - 1)
        
    def open_fullscreen(self, event: str = "frame"):  # frame or screen
        log = self.logs[self.current_index]
        # frame_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', log[3]))
        # screen_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', log[4]))
        frame_path = self.logger._get_log_file_path(log[3]) if log[3] else ""
        screen_path = self.logger._get_log_file_path(log[4]) if log[4] else ""
        fullscreen_dialog = FullScreenImageDialog(frame_path, screen_path, self)
        fullscreen_dialog.current_image = event  # Открываем event
        fullscreen_dialog.update_image()
        fullscreen_dialog.exec_()

    def show_previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()

    def show_next(self):
        if self.current_index < len(self.logs) - 1:
            self.current_index += 1
            self.update_display()

class AdminPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Админ-панель")
        self.setGeometry(50, 50, 1200, 600)
        self.setMinimumSize(1500, 950)  # Минимальный размер для удобства
        self.config = Config()
        self.cameras = []
        self.camera = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_preview)
        
        self.apply_config_settings()

        # db_path = "logs/detection_log.db"
        # # abs_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', db_path))
        # abs_db_path = get_resource_path(db_path)
        # print(f"DEBUG: Database path: db_path={db_path}, abs_db_path={abs_db_path}")
        # if not os.path.exists(abs_db_path):
        #     print(f"DEBUG: Database {abs_db_path} not found")
        # self.logger = Logger(db_path)
        self.logger = Logger()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.settings_tab = QWidget()
        self.notifications_tab = QWidget()
        # self.autostart_tab = QWidget()
        self.logs_tab = QWidget()
        # self.telegram_tab = QWidget()
        self.tabs.addTab(self.settings_tab, "Настройки")
        self.tabs.addTab(self.notifications_tab, "Оповещения и события")
        # self.tabs.addTab(self.autostart_tab, "Автозапуск")
        self.tabs.addTab(self.logs_tab, "Журнал событий")
        # self.tabs.addTab(self.telegram_tab, "Telegram-бот")

        self.init_settings_tab()
        self.init_notifications_tab()
        # self.init_autostart_tab()
        self.init_logs_tab()
        # self.init_telegram_tab()  # Инициализация новой вкладки
        
    def init_telegram_tab(self):
        layout = QVBoxLayout()
        main_layout = QHBoxLayout()

        # Макет для управления Telegram ID
        id_layout = QVBoxLayout()
        id_layout.addWidget(QLabel("Список Telegram ID для рассылки:"))

        # Список ID
        self.telegram_id_list = QListWidget()
        self.telegram_id_list.setFixedWidth(300)
        telegram_ids = self.config.get("telegram_ids")  # Получаем список ID из конфигурации
        self.telegram_id_list.addItems(telegram_ids if telegram_ids else ["Нет добавленных ID"])
        id_layout.addWidget(self.telegram_id_list)

        # Поле для ввода нового/редактируемого ID
        self.telegram_id_input = QLineEdit()
        self.telegram_id_input.setPlaceholderText("Введите Telegram ID")
        self.telegram_id_input.setFixedWidth(300)
        id_layout.addWidget(self.telegram_id_input)

        # Кнопки управления и сохранения
        button_layout = QHBoxLayout()
        add_button = QPushButton("Добавить ID")
        add_button.clicked.connect(self.add_telegram_id)
        button_layout.addWidget(add_button)

        edit_button = QPushButton("Изменить ID")
        edit_button.clicked.connect(self.edit_telegram_id)
        button_layout.addWidget(edit_button)

        delete_button = QPushButton("Удалить ID")
        delete_button.clicked.connect(self.delete_telegram_id)
        button_layout.addWidget(delete_button)

        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_telegram_settings)
        button_layout.addWidget(save_button)

        id_layout.addLayout(button_layout)
        id_layout.addStretch()  # Выравнивание по вертикали
        main_layout.addLayout(id_layout)

        # Инструкция
        instruction_layout = QVBoxLayout()
        instruction_layout.addWidget(QLabel("Инструкция по настройке Telegram-бота:"))

        self.instruction_text = QTextEdit()
        self.instruction_text.setReadOnly(True)
        self.instruction_text.setFixedWidth(500)
        self.instruction_text.setFixedHeight(300)
        self.instruction_text.setText(
            "Инструкция по настройке Telegram-бота:\n"
            "1. Найдите ваш Telegram ID:\n"
            "   - Откройте Telegram и найдите бота @UserIDBot или @GetMyIDBot.\n"
            "   - Напишите боту /start, и он отправит ваш личный Telegram ID."
            "2. Для личных сообщений:\n"
            "   - Напишите боту сообщение (например, /start), чтобы он мог отправлять вам уведомления.\n"
            "3. Для групп или сообществ:\n"
            "   - Добавьте бота в группу или канал.\n"
            "   - Напишите /start@YourBotName в чате группы, чтобы бот получил ID чата.\n"
            "   - ID группы обычно начинается с '-100' (например, -100123456789).\n"
            "4. Введите полученный ID в поле выше и нажмите 'Добавить ID'.\n"
            "Примечание: Убедитесь, что бот активирован и имеет права отправлять сообщения в группе."
        )
        instruction_layout.addWidget(self.instruction_text)
        instruction_layout.addStretch()  # Выравнивание по вертикали

        main_layout.addLayout(instruction_layout)
        layout.addLayout(main_layout)
        layout.addStretch()

        self.telegram_tab.setLayout(layout)
        
    def add_telegram_id(self):
        new_id = self.telegram_id_input.text().strip()
        if not new_id:
            QMessageBox.warning(self, "Ошибка", "Введите Telegram ID")
            return
        current_ids = self.config.get("telegram_ids")
        if new_id in current_ids:
            QMessageBox.warning(self, "Ошибка", "Этот ID уже добавлен")
            return
        current_ids.append(new_id)
        self.config.config["telegram_ids"] = current_ids
        self.telegram_id_list.clear()
        self.telegram_id_list.addItems(current_ids)
        self.telegram_id_input.clear()
        print(f"DEBUG: Added Telegram ID: {new_id}")

    def edit_telegram_id(self):
        selected_item = self.telegram_id_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Ошибка", "Выберите ID для редактирования")
            return
        new_id = self.telegram_id_input.text().strip()
        if not new_id:
            QMessageBox.warning(self, "Ошибка", "Введите новый Telegram ID")
            return
        current_ids = self.config.get("telegram_ids")
        old_id = selected_item.text()
        if new_id in current_ids:
            QMessageBox.warning(self, "Ошибка", "Этот ID уже добавлен")
            return
        if old_id in current_ids:
            index = current_ids.index(old_id)
            current_ids[index] = new_id
            self.config.config["telegram_ids"] = current_ids
            self.telegram_id_list.clear()
            self.telegram_id_list.addItems(current_ids)
            self.telegram_id_input.clear()
            print(f"DEBUG: Edited Telegram ID: {old_id} -> {new_id}")

    def delete_telegram_id(self):
        selected_item = self.telegram_id_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Ошибка", "Выберите ID для удаления")
            return
        current_ids = self.config.get("telegram_ids")
        id_to_delete = selected_item.text()
        if id_to_delete in current_ids:
            current_ids.remove(id_to_delete)
            self.config.config["telegram_ids"] = current_ids
            self.telegram_id_list.clear()
            self.telegram_id_list.addItems(current_ids if current_ids else ["Нет добавленных ID"])
            print(f"DEBUG: Deleted Telegram ID: {id_to_delete}")

    def save_telegram_settings(self):
        try:
            self.config.save_config(self.config.config)  # Save the entire config
            QMessageBox.information(self, "Успех", "Настройки Telegram сохранены")
            print("DEBUG: Telegram settings saved")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить настройки: {e}")
            print(f"DEBUG: Error saving Telegram settings: {e}")
    
    def apply_config_settings(self) -> None:
        if self.config.get("autostart")["on_system_start"]:
            enable_autostart(APP_NAME, get_project_main_path())
        else:
            disable_autostart(APP_NAME)

    def init_settings_tab(self):
        layout = QVBoxLayout()
        main_layout = QHBoxLayout()

        preview_layout = QVBoxLayout()
        self.camera_combo = QComboBox()
        self.camera_combo.setFixedWidth(200)
        self.cameras = Camera.list_available_cameras()
        camera_names = [name for _, name in self.cameras]
        self.camera_combo.addItems(camera_names if camera_names else ["Нет доступных камер"])
        current_camera = self.config.get("camera_id")
        for i, (cam_id, _) in enumerate(self.cameras):
            if cam_id == current_camera:
                self.camera_combo.setCurrentIndex(i)
                break
        preview_layout.addWidget(QLabel("Устройство:"))
        preview_layout.addWidget(self.camera_combo)

        self.check_button = QPushButton("Проверить соединение")
        self.check_button.clicked.connect(self.toggle_preview)
        preview_layout.addWidget(self.check_button)

        self.preview_label = QLabel()
        self.preview_label.setFixedSize(320, 240)
        # logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'logo.png'))
        logo_path = get_resource_path('assets/logo.png')
        print(f"DEBUG: Loading logo: {logo_path}, exists={os.path.exists(logo_path)}")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(320, 240, Qt.KeepAspectRatio)
            self.preview_label.setPixmap(pixmap)
        else:
            self.preview_label.setText("Логотип отсутствует")
        preview_layout.addWidget(self.preview_label)
        
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_settings)
        save_button.setMaximumWidth(100)
        preview_layout.addWidget(save_button)

        preview_layout.addStretch()
        main_layout.addLayout(preview_layout)

        form_layout = QFormLayout()
        self.fps_spin = QSpinBox()
        self.fps_spin.setFixedWidth(200)
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(self.config.get("fps"))
        form_layout.addRow("Частота кадров (FPS):", self.fps_spin)

        self.retention_combo = QComboBox()
        self.retention_combo.setFixedWidth(200)
        self.retention_combo.addItems(["1 день", "1 неделя", "1 месяц", "1 год", "Не удалять"])
        self.retention_combo.setCurrentText(self.config.get("log_retention"))
        form_layout.addRow("Время хранения логов:", self.retention_combo)

        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setFixedWidth(200)
        self.confidence_spin.setRange(0.1, 0.9)
        self.confidence_spin.setSingleStep(0.1)
        self.confidence_spin.setValue(self.config.get("confidence_threshold"))
        form_layout.addRow("Уровень уверенности:", self.confidence_spin)
        
        # Внутри метода init_settings_tab, после блока с confidence_spin
        self.count_spin = QSpinBox()
        self.count_spin.setFixedWidth(200)
        self.count_spin.setRange(1, 999)  # Установите максимум по необходимости
        self.count_spin.setValue(self.config.get("phone_limit"))  # Значение по умолчанию 1, если не задано в конфиге
        form_layout.addRow("Кол-во кадров реакции:", self.count_spin)
        
        self.autostart_system = QCheckBox("Автозапуск при старте системы")
        self.autostart_system.setChecked(self.config.get("autostart")["on_system_start"])
        # form_layout.addWidget(self.autostart_system)
        form_layout.addRow(self.autostart_system)

        main_layout.addLayout(form_layout)
        layout.addLayout(main_layout)

        # button_layout = QHBoxLayout()
        # button_layout.addStretch()
        # save_button = QPushButton("Сохранить")
        # save_button.clicked.connect(self.save_settings)
        # button_layout.addWidget(save_button)
        # layout.addLayout(button_layout)
        layout.addStretch()

        self.settings_tab.setLayout(layout)

    def init_notifications_tab(self):
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        lock_group = QGroupBox("Блокировка экрана")
        lock_layout = QVBoxLayout()
        self.lock_phone_detected = QCheckBox("Детекция телефона")
        self.lock_phone_detected.setChecked(self.config.get("lock_events")["phone_detected"])
        lock_layout.addWidget(self.lock_phone_detected)
        self.lock_camera_lost = QCheckBox("Потеря связи с камерой")
        self.lock_camera_lost.setChecked(self.config.get("lock_events")["camera_lost"])
        lock_layout.addWidget(self.lock_camera_lost)
        self.lock_uniform_image = QCheckBox("Однотонное изображение")
        self.lock_uniform_image.setChecked(self.config.get("lock_events")["uniform_image"])
        lock_layout.addWidget(self.lock_uniform_image)
        self.lock_attempt_to_close = QCheckBox("Попытка закрыть приложение")
        self.lock_attempt_to_close.setChecked(self.config.get("lock_events")["attempt_to_close"])
        lock_layout.addWidget(self.lock_attempt_to_close)
        self.lock_static_img = QCheckBox("Статичное изображение (кадры не меняется 30 секунд)")
        self.lock_static_img.setChecked(self.config.get("lock_events")["static_img"])
        lock_layout.addWidget(self.lock_static_img)
        lock_group.setLayout(lock_layout)
        form_layout.addRow(lock_group)

        log_group = QGroupBox("Запись в журнал событий")
        log_layout = QVBoxLayout()
        self.log_phone_detected = QCheckBox("Детекция телефона")
        self.log_phone_detected.setChecked(self.config.get("log_events")["phone_detected"])
        log_layout.addWidget(self.log_phone_detected)
        self.log_camera_lost = QCheckBox("Потеря связи с камерой")
        self.log_camera_lost.setChecked(self.config.get("log_events")["camera_lost"])
        log_layout.addWidget(self.log_camera_lost)
        self.log_uniform_image = QCheckBox("Однотонное изображение")
        self.log_uniform_image.setChecked(self.config.get("log_events")["uniform_image"])
        log_layout.addWidget(self.log_uniform_image)
        self.log_attempt_to_close = QCheckBox("Попытка закрыть приложение")
        self.log_attempt_to_close.setChecked(self.config.get("log_events")["attempt_to_close"])
        log_layout.addWidget(self.log_attempt_to_close)
        self.log_static_img = QCheckBox("Статичное изображение (кадры не меняется 30 секунд)")
        self.log_static_img.setChecked(self.config.get("log_events")["static_img"])
        log_layout.addWidget(self.log_static_img)
        log_group.setLayout(log_layout)
        form_layout.addRow(log_group)
        
        other_group = QGroupBox("Дополнительно")
        other_layout = QVBoxLayout()
        self.make_screen_enabled = QCheckBox("Делать ли скриншот")
        self.make_screen_enabled.setChecked(self.config.get("other_events")["make_screen_enabled"])
        other_layout.addWidget(self.make_screen_enabled)
        other_group.setLayout(other_layout)
        form_layout.addRow(other_group)
        layout.addLayout(form_layout)
        
        notifications_group = QGroupBox("Оповещения")
        notifications_layout = QVBoxLayout()
        self.notifications_phone_detected = QCheckBox("Детекция телефона")
        self.notifications_phone_detected.setChecked(self.config.get("notifications")["phone_detected"])
        notifications_layout.addWidget(self.notifications_phone_detected)
        self.notifications_camera_lost = QCheckBox("Потеря связи с камерой")
        self.notifications_camera_lost.setChecked(self.config.get("notifications")["camera_lost"])
        notifications_layout.addWidget(self.notifications_camera_lost)
        self.notifications_uniform_image = QCheckBox("Однотонное изображение")
        self.notifications_uniform_image.setChecked(self.config.get("notifications")["uniform_image"])
        notifications_layout.addWidget(self.notifications_uniform_image)
        self.notifications_attempt_to_close = QCheckBox("Попытка закрыть приложение")
        self.notifications_attempt_to_close.setChecked(self.config.get("notifications")["attempt_to_close"])
        notifications_layout.addWidget(self.notifications_attempt_to_close)
        self.notifications_static_img = QCheckBox("Статичное изображение (кадры не меняется 30 секунд)")
        self.notifications_static_img.setChecked(self.config.get("notifications")["static_img"])
        notifications_layout.addWidget(self.notifications_static_img)
        notifications_group.setLayout(notifications_layout)
        form_layout.addRow(notifications_group)
        
        tg_group = QGroupBox("Tg бот")
        tg_group.setMinimumHeight(250)
        tg_layout = QVBoxLayout()
        
        tg_inner_layout = QHBoxLayout()

        # Left: Telegram ID management
        id_layout = QVBoxLayout()
        id_layout.addWidget(QLabel("Список Telegram ID для рассылки:"))

        self.telegram_id_list = QListWidget()
        self.telegram_id_list.setFixedWidth(300)
        self.telegram_id_list.setMinimumHeight(150)  # Stable height
        telegram_ids = self.config.get("telegram_ids")
        self.telegram_id_list.addItems(telegram_ids if telegram_ids else ["Нет добавленных ID"])
        id_layout.addWidget(self.telegram_id_list)

        self.telegram_id_input = QLineEdit()
        self.telegram_id_input.setPlaceholderText("Введите Telegram ID")
        self.telegram_id_input.setFixedWidth(300)
        id_layout.addWidget(self.telegram_id_input)

        button_layout = QHBoxLayout()
        add_button = QPushButton("Добавить")
        add_button.clicked.connect(self.add_telegram_id)
        button_layout.addWidget(add_button)

        edit_button = QPushButton("Изменить")
        edit_button.clicked.connect(self.edit_telegram_id)
        button_layout.addWidget(edit_button)

        delete_button = QPushButton("Удалить")
        delete_button.clicked.connect(self.delete_telegram_id)
        button_layout.addWidget(delete_button)

        id_layout.addLayout(button_layout)
        id_layout.addStretch()
        tg_inner_layout.addLayout(id_layout)

        # Right: Instruction
        instruction_layout = QVBoxLayout()
        instruction_layout.addWidget(QLabel("Инструкция:"))

        self.instruction_text = QTextEdit()
        self.instruction_text.setReadOnly(True)
        self.instruction_text.setFixedWidth(350)
        self.instruction_text.setFixedHeight(200)
        self.instruction_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.instruction_text.setText(
            "1. Найдите Telegram ID:\n"
            "   - Используйте @UserIDBot или @GetMyIDBot.\n"
            "   - Напишите /start для получения ID.\n"
            "2. Личные сообщения:\n"
            "   - Напишите боту /start.\n"
            "3. Группы/каналы:\n"
            "   - Добавьте бота в группу.\n"
            "   - Напишите /start@YourBotName.\n"
            "   - ID группы начинается с '-100'.\n"
            "4. Введите ID и нажмите 'Добавить'."
        )
        instruction_layout.addWidget(self.instruction_text)
        instruction_layout.addStretch()
        tg_inner_layout.addLayout(instruction_layout)

        tg_layout.addLayout(tg_inner_layout)
        tg_group.setLayout(tg_layout)
        form_layout.addRow(tg_group)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_notifications)
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)
        layout.addStretch()

        self.notifications_tab.setLayout(layout)

    def init_autostart_tab(self):
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        autostart_group = QGroupBox("Автозапуск программы")
        autostart_layout = QVBoxLayout()

        self.autostart_system = QCheckBox("При старте системы")
        self.autostart_system.setChecked(self.config.get("autostart")["on_system_start"])
        autostart_layout.addWidget(self.autostart_system)

        # self.autostart_program = QCheckBox("При открытии программы")
        # self.autostart_program.setChecked(self.config.get("autostart")["on_program_start"]["enabled"])
        # autostart_layout.addWidget(self.autostart_program)
        # self.program_path = QPushButton("Выбрать программу")
        # self.program_path.clicked.connect(self.select_program)
        # self.program_path_label = QLabel(self.config.get("autostart")["on_program_start"]["program_path"] or "Не выбрано")
        # autostart_layout.addWidget(self.program_path)
        # autostart_layout.addWidget(self.program_path_label)

        # self.autostart_file = QCheckBox("При открытии файла")
        # self.autostart_file.setChecked(self.config.get("autostart")["on_file_open"]["enabled"])
        # autostart_layout.addWidget(self.autostart_file)
        # self.file_path = QPushButton("Выбрать файл")
        # self.file_path.clicked.connect(self.select_file)
        # self.file_path_label = QLabel(self.config.get("autostart")["on_file_open"]["file_path"] or "Не выбрано")
        # autostart_layout.addWidget(self.file_path)
        # autostart_layout.addWidget(self.file_path_label)

        autostart_group.setLayout(autostart_layout)
        form_layout.addRow(autostart_group)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_autostart)
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)
        layout.addStretch()

        self.autostart_tab.setLayout(layout)

    def select_program(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать программу", "", "Executables (*.exe)")
        if path:
            self.program_path_label.setText(path)
            print(f"DEBUG: Selected program: {path}")

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать файл", "")
        if path:
            self.file_path_label.setText(path)
            print(f"DEBUG: Selected file: {path}")

    def toggle_preview(self):
        if self.timer.isActive():
            self.timer.stop()
            if self.camera:
                self.camera.release()
                self.camera = None
            # logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'logo.png'))
            logo_path = get_resource_path('assets/logo.png')
            if os.path.exists(logo_path):
                pixmap = QPixmap(logo_path).scaled(320, 240, Qt.KeepAspectRatio)
                self.preview_label.setPixmap(pixmap)
            else:
                self.preview_label.setText("Логотип отсутствует")
            self.check_button.setText("Проверить соединение")  # Меняем текст кнопки
            print("DEBUG: Preview stopped")
        else:
            selected_index = self.camera_combo.currentIndex()
            if not self.cameras or selected_index < 0:
                self.preview_label.setText("Камера недоступна")
                self.check_button.setText("Проверить соединение")  # Сбрасываем текст на случай ошибки
                print("DEBUG: No cameras available for preview")
                return
            camera_id = self.cameras[selected_index][0]
            try:
                self.camera = Camera(camera_id)
                self.timer.start(100)
                self.check_button.setText("Остановить проверку")  # Меняем текст при успешном запуске
                print(f"DEBUG: Preview started for camera ID={camera_id}")
            except Exception as e:
                self.preview_label.setText("Ошибка камеры")
                self.check_button.setText("Проверить соединение")  # Сбрасываем текст при ошибке
                print(f"DEBUG: Error starting preview: {e}")

    def update_preview(self):
        if self.camera:
            frame = self.camera.get_frame()
            if frame is not None:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channel = frame.shape
                qimage = QImage(frame.data, width, height, width * channel, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage).scaled(320, 240, Qt.KeepAspectRatio)
                self.preview_label.setPixmap(pixmap)
            else:
                self.preview_label.setText("Нет сигнала")
                print("DEBUG: No frame received for preview")

    def save_settings(self):
        selected_index = self.camera_combo.currentIndex()
        camera_id = self.cameras[selected_index][0] if self.cameras and selected_index >= 0 else 0
        config = self.config.config.copy()
        config.update({
            "camera_id": camera_id,
            "fps": self.fps_spin.value(),
            "log_retention": self.retention_combo.currentText(),
            "confidence_threshold": self.confidence_spin.value(),
            "phone_limit": self.count_spin.value(),
            "autostart": {
                "on_system_start": self.autostart_system.isChecked(),
            }
        })
        self.config.save_config(config)
        self.logger.clean_old_logs(config["log_retention"])
        print(f"DEBUG: Settings saved: {config}")

    def save_notifications(self):
        try:            
            config = self.config.config.copy()
            config.update({
                "notifications": {
                    "camera_lost": self.notifications_camera_lost.isChecked(),
                    "uniform_image": self.notifications_uniform_image.isChecked(),
                    "phone_detected": self.notifications_phone_detected.isChecked(),
                    "attempt_to_close": self.notifications_attempt_to_close.isChecked(),
                    "static_img": self.notifications_static_img.isChecked()
                },
                "lock_events": {
                    "camera_lost": self.lock_camera_lost.isChecked(),
                    "uniform_image": self.lock_uniform_image.isChecked(),
                    "phone_detected": self.lock_phone_detected.isChecked(),
                    "attempt_to_close": self.lock_attempt_to_close.isChecked(),
                    "static_img": self.lock_static_img.isChecked()
                },
                "other_events": {
                    "make_screen_enabled": self.make_screen_enabled.isChecked()
                },
                "log_events": {
                    "phone_detected": self.log_phone_detected.isChecked(),
                    "camera_lost": self.log_camera_lost.isChecked(),
                    "uniform_image": self.log_uniform_image.isChecked(),
                    "attempt_to_close": self.log_attempt_to_close.isChecked(),
                    "static_img": self.log_static_img.isChecked()
                }
            })
            self.config.save_config(config)
            print(f"DEBUG: Notifications settings saved: {config}")
            QMessageBox.information(self, "Успех", "Настройки Оповещений сохранены")
            print("DEBUG: Telegram settings saved")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить настройки: {e}")
            print(f"DEBUG: Error saving Telegram settings: {e}")

    def save_autostart(self):
        config = self.config.config.copy()
        config.update({
            "autostart": {
                "on_system_start": self.autostart_system.isChecked(),
                # "on_program_start": {
                #     "enabled": self.autostart_program.isChecked(),
                #     "program_path": self.program_path_label.text() if self.program_path_label.text() != "Не выбрано" else ""
                # },
                # "on_file_open": {
                #     "enabled": self.autostart_file.isChecked(),
                #     "file_path": self.file_path_label.text() if self.file_path_label.text() != "Не выбрано" else ""
                # }
            }
        })
        self.config.save_config(config)
        print(f"DEBUG: Autostart settings saved: {config}")
        self.apply_config_settings()

    def on_period_changed(self, text):
        """Скрывать/показывать поля даты и времени в режиме «Выбрать период»."""
        is_custom = (text == "Выбрать период")
        self.dateFromEdit.setVisible(is_custom)
        self.dateToEdit.setVisible(is_custom)
        self.timeFromEdit.setVisible(is_custom)
        self.timeToEdit.setVisible(is_custom)

    def init_logs_tab(self):
        self.logs_layout = QVBoxLayout()

        # Первая строка фильтров
        filter_layout_top = QHBoxLayout()

        self.event_filter = QComboBox()
        self.event_filter.addItems([
            "Все события",
            "Обнаружен мобильный телефон",
            "Однотонное изображение",
            "После однотонного изображения",
            "Потеря связи с камерой",
            "Востановление после \"Потеря связи с камерой\"",
            "Попытка закрыть приложение",
            "Зависшее изображение",
            "Изображение отвисло",
        ])
        self.event_filter.currentTextChanged.connect(self.load_logs)
        filter_layout_top.addWidget(QLabel("Фильтр событий:"))
        filter_layout_top.addWidget(self.event_filter)

        self.user_filter = QComboBox()
        self.user_filter.addItem("Все пользователи")
        self.load_users()
        self.user_filter.currentTextChanged.connect(self.load_logs)
        filter_layout_top.addWidget(QLabel("Пользователь:"))
        filter_layout_top.addWidget(self.user_filter)

        filter_layout_top.addStretch()
        self.logs_layout.addLayout(filter_layout_top)

        # Вторая строка фильтров
        filter_layout_bottom = QHBoxLayout()

        self.date_filter = QComboBox()
        self.date_filter.addItems(["Все время", "Сегодня", "Неделя", "Месяц", "Выбрать период"])
        self.date_filter.setCurrentText("Все время")
        self.date_filter.currentTextChanged.connect(self.on_date_filter_changed)
        filter_layout_bottom.addWidget(QLabel("Период:"))
        filter_layout_bottom.addWidget(self.date_filter)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setSpecialValueText("__.__.____")
        # self.date_from.setDate(QDate.fromString("", "dd.MM.yyyy"))
        self.date_from.setDate(QDate.currentDate())
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setStyleSheet("""
            QDateEdit {
                background-color: #F8F4FF;
                border: 1px solid #79747E;
                border-radius: 4px;
                padding: 8px;
                font-family: Roboto, sans-serif;
                font-size: 16px;
                color: #1C1B1F;
            }
            QDateEdit:hover {
                background-color: #E6DDFF; /* Primary Container */
                border: 1px solid #6750A4; /* Primary */
            }
            QDateEdit:focus {
                border: 2px solid #6750A4; /* Primary, толще при фокусе */
                padding: 7px 27px 7px 11px; /* Компенсация толщины границы */
            }
            QDateEdit:disabled {
                background-color: #F5F5F5;
                color: #79747E;
                border: 1px solid #B0B0B0;
            }
        """)
        self.date_from.setEnabled(False)  # По умолчанию выключено
        filter_layout_bottom.addWidget(QLabel("От:"))
        filter_layout_bottom.addWidget(self.date_from)

        self.time_from = QTimeEdit()  # Добавляем поле для времени "От"
        self.time_from.setDisplayFormat("HH:mm:ss")
        self.time_from.setTime(QTime(0, 0, 0))  # Устанавливаем начальное время 00:00:00
        self.time_from.setMinimumWidth(115)  # Ширина уменьшена с 150px до 130px
        self.time_from.setStyleSheet("""
            QTimeEdit {
                background-color: #F8F4FF; /* Surface */
                border: 1px solid #79747E; /* Outline */
                border-radius: 4px;
                padding: 8px 8px 8px 8px; /* 28px справа для стрелок, 12px слева для текста */
                font-family: Roboto, sans-serif;
                font-size: 16px; /* Label Medium, как у QDateEdit */
                font-weight: 400;
                color: #1C1B1F; /* On Surface */
            }
            QTimeEdit:hover {
                background-color: #E6DDFF; /* Primary Container */
                border: 1px solid #6750A4; /* Primary */
            }
            QTimeEdit:focus {
                border: 2px solid #6750A4; /* Primary, толще при фокусе */
                padding: 7px 27px 7px 11px; /* Компенсация толщины границы */
            }
            QTimeEdit:disabled {
                background-color: #F5F5F5;
                color: #79747E;
                border: 1px solid #B0B0B0;
            }
        """)
        self.time_from.setEnabled(False)  # По умолчанию выключено
        filter_layout_bottom.addWidget(QLabel("Время от:"))
        filter_layout_bottom.addWidget(self.time_from)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setSpecialValueText("__.__.____")
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setStyleSheet(self.date_from.styleSheet())
        self.date_to.setEnabled(False)
        filter_layout_bottom.addWidget(QLabel("До:"))
        filter_layout_bottom.addWidget(self.date_to)

        self.time_to = QTimeEdit()  # Добавляем поле для времени "До"
        self.time_to.setDisplayFormat("HH:mm:ss")
        self.time_to.setTime(QTime(23, 59, 59))  # Устанавливаем конечное время 23:59:59
        self.time_to.setMinimumWidth(115)  # Ширина уменьшена с 150px до 130px
        self.time_to.setStyleSheet(self.time_from.styleSheet())
        self.time_to.setEnabled(False)
        filter_layout_bottom.addWidget(QLabel("Время до:"))
        filter_layout_bottom.addWidget(self.time_to)

        filter_layout_bottom.addStretch()

        refresh_button = QPushButton("Обновить логи")
        refresh_button.clicked.connect(self.load_logs)
        filter_layout_bottom.addWidget(refresh_button)

        clear_button = QPushButton("Очистить логи")
        clear_button.clicked.connect(self.clear_logs)
        filter_layout_bottom.addWidget(clear_button)

        self.logs_layout.addLayout(filter_layout_bottom)

        # Таблица с логами
        self.logs_table = QTableWidget()
        self.logs_table.setStyleSheet("""
            QTableWidget {
                background-color: #F8F4FF; /* Surface */
                border: 1px solid #E0E0E0; /* Outline */
                border-radius: 4px;
                gridline-color: #E0E0E0;
                font-family: Roboto, sans-serif;
                font-size: 14px;
                alternate-background-color: #F1F0FA; /* Тонкий акцент для чередующихся строк */
            }
            QTableWidget::item {
                padding: 8px;
                color: #1C1B1F; /* On Surface */
            }
            QTableWidget::item:selected {
                background-color: #E6DDFF; /* Primary Container */
                color: #1C1B1F;
            }
            QHeaderView::section {
                background-color: #6750A4; /* Primary */
                color: #FFFFFF; /* On Primary */
                padding: 8px;
                font-family: Roboto, sans-serif;
                font-weight: 500;
                font-size: 14px;
                border: none;
                border-bottom: 1px solid #E0E0E0;
            }
        """)

        # Установить высоту строк и заголовков
        self.logs_table.verticalHeader().setDefaultSectionSize(56)  # Соответствует M3 для строк
        self.logs_table.horizontalHeader().setMinimumHeight(56)  # Высота заголовка
        self.event_filter.setStyleSheet("""
            QComboBox {
                background-color: #F8F4FF; /* Surface */
                border: 1px solid #79747E; /* Outline */
                border-radius: 4px;
                padding: 8px;
                font-family: Roboto, sans-serif;
                font-size: 16px;
                color: #1C1B1F; /* On Surface */
            }
            QComboBox::drop-down {
                border: none;
                width: 32px;
            }
            QComboBox::down-arrow {
                image: url(:/icons/arrow_drop_down.png); /* Material Icon */
                width: 24px;
                height: 24px;
            }
            QComboBox:hover {
                background-color: #E6DDFF; /* Primary Container */
            }
            QComboBox QAbstractItemView {
                background-color: #F8F4FF;
                border: 1px solid #79747E;
                border-radius: 4px;
                color: #1C1B1F;
            }
        """)
        self.user_filter.setStyleSheet(self.event_filter.styleSheet())
        self.date_filter.setStyleSheet(self.event_filter.styleSheet())

        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #6750A4; /* Primary */
                color: #FFFFFF; /* On Primary */
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-family: Roboto, sans-serif;
                font-weight: 500;
                font-size: 14px;
                min-height: 40px; /* M3 стандарт для кнопок */
            }
            QPushButton:hover {
                background-color: #7F67BE; /* Primary с Elevation */
            }
            QPushButton:pressed {
                background-color: #5B4696; /* Темнее при нажатии */
            }
        """)

        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #B3261E; /* Error */
                color: #FFFFFF; /* On Error */
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-family: Roboto, sans-serif;
                font-weight: 500;
                font-size: 14px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #C62820; /* Error с Elevation */
            }
            QPushButton:pressed {
                background-color: #9F231B; /* Темнее при нажатии */
            }
        """)
        self.logs_table.setColumnCount(7)
        headers = ["Время", "Событие", "Уверенность", "Запущенные приложения", "Пользователь", "Миниатюра", "Скриншот"]
        self.logs_table.setHorizontalHeaderLabels(headers)
        header = self.logs_table.horizontalHeader()
        self.logs_table.setSortingEnabled(True)
        self.logs_table.setWordWrap(True)
        for i in range(self.logs_table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        self.logs_table.setMinimumWidth(1450)
        self.logs_table.setSelectionMode(QTableWidget.SingleSelection)
        self.logs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.logs_table.cellClicked.connect(self.on_cell_clicked)
        self.logs_layout.addWidget(self.logs_table)

        self.no_logs_label = QLabel("События отсутствуют")
        self.no_logs_label.setAlignment(Qt.AlignCenter)
        self.no_logs_label.setVisible(False)
        self.logs_layout.addWidget(self.no_logs_label)

        self.logs_tab.setLayout(self.logs_layout)
        self.load_logs()

    def load_users(self):
        try:
            self.logger.cursor.execute("SELECT DISTINCT username FROM logs WHERE username IS NOT NULL")
            users = [row[0] for row in self.logger.cursor.fetchall()]
            for user in users:
                self.user_filter.addItem(user)
            print(f"DEBUG: Loaded users: {users}")
        except Exception as e:
            print(f"DEBUG: Error loading users: {e}")

    def on_date_filter_changed(self):
        is_custom_period = (self.date_filter.currentText() == "Выбрать период")
        self.date_from.setEnabled(is_custom_period)
        self.date_to.setEnabled(is_custom_period)
        self.time_from.setEnabled(is_custom_period)
        self.time_to.setEnabled(is_custom_period)
        # if self.date_filter.currentText() == "Выбрать период":
        #     # self.date_from.setVisible(True)
        #     # self.time_from.setVisible(True)  # Показываем поле времени "От"
        #     # self.date_to.setVisible(True)
        #     # self.time_to.setVisible(True)    # Показываем поле времени "До"
        #     self.date_from.setVisible(True)
        #     self.time_from.setVisible(True)  # Показываем поле времени "От"
        #     self.date_to.setVisible(True)
        #     self.time_to.setVisible(True)    # Показываем поле времени "До"
        # else:
        #     self.date_from.setVisible(False)
        #     self.time_from.setVisible(False) # Скрываем поле времени "От"
        #     self.date_to.setVisible(False)
        #     self.time_to.setVisible(False)   # Скрываем поле времени "До"
        self.load_logs()
        # if self.date_filter.currentText() == "Выбрать период":
        #     self.date_from.setVisible(True)
        #     self.date_to.setVisible(True)
        # else:
        #     self.date_from.setVisible(False)
        #     self.date_to.setVisible(False)
        # self.load_logs()

    def clear_logs(self):
        reply = QMessageBox.question(
            self, "Подтверждение", "Вы уверены, что хотите очистить Журнал событий?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.logger.cursor.execute("SELECT frame_path FROM logs")
                frame_paths = [row[0] for row in self.logger.cursor.fetchall()]
                for frame_path in frame_paths:
                    if frame_path:
                        # abs_frame_path = os.path.abspath(
                        #     os.path.join(os.path.dirname(__file__), '..', '..', frame_path))
                        # abs_frame_path = get_resource_path(frame_path)
                        abs_frame_path = get_image_path(frame_path)
                        try:
                            if os.path.exists(abs_frame_path):
                                os.remove(abs_frame_path)
                                print(f"DEBUG: Deleted frame: {abs_frame_path}")
                        except OSError as e:
                            print(f"DEBUG: Error deleting frame {abs_frame_path}: {e}")

                self.logger.cursor.execute("DELETE FROM logs")
                self.logger.conn.commit()
                print("DEBUG: All logs cleared")
                self.load_logs()
                self.load_users()

                QMessageBox.information(self, "Очистка журнала", "Журнал событий успешно очищен.")

            except Exception as e:
                print(f"DEBUG: Error clearing logs: {e}")
                QMessageBox.critical(self, "Ошибка", "Не удалось очистить логи.")
        else:
            QMessageBox.information(self, "Очистка журнала", "Очистка журнала отменена.")

    def load_logs(self):
        print(f"DEBUG: Loading logs... Current directory: {os.getcwd()}")
        self.logs_table.clearContents()
        self.no_logs_label.setVisible(False)
        event_filter = self.event_filter.currentText()
        user_filter = self.user_filter.currentText()
        date_filter = self.date_filter.currentText()
        try:
            self.logger.cursor.execute("PRAGMA table_info(logs)")
            columns = [col[1] for col in self.logger.cursor.fetchall()]
            print(f"DEBUG: Columns in logs table: {columns}")

            conditions = []
            params = []
            if event_filter != "Все события":
                conditions.append("event = ?")
                params.append(event_filter)
            if user_filter != "Все пользователи":
                conditions.append("username = ?")
                params.append(user_filter)
            if date_filter != "Все время":
                if date_filter == "Выбрать период":
                    date_from = self.date_from.date().toString("yyyy-MM-dd")
                    time_from = self.time_from.time().toString("HH-mm-ss")
                    date_to = self.date_to.date().toString("yyyy-MM-dd")
                    time_to = self.time_to.time().toString("HH-mm-ss")
                    datetime_from = f"{date_from} {time_from}"
                    datetime_to = f"{date_to} {time_to}"
                    conditions.append("timestamp BETWEEN ? AND ?")
                    params.extend([datetime_from, datetime_to])
                else:
                    cutoff = datetime.now()
                    if date_filter == "Сегодня":
                        cutoff = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
                    elif date_filter == "Неделя":
                        cutoff -= timedelta(weeks=1)
                    elif date_filter == "Месяц":
                        cutoff -= timedelta(days=30)
                    conditions.append("timestamp >= ?")
                    params.append(cutoff.strftime("%Y-%m-%d %H-%M-%S"))

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            query = f"SELECT * FROM logs {where_clause} ORDER BY timestamp DESC"
            self.logger.cursor.execute(query, params)
            print(f"DEBUG: Executed query: {query} with params={params}")

            logs = self.logger.cursor.fetchall()
            print(f"DEBUG: Loaded {len(logs)} logs for event='{event_filter}', user='{user_filter}', date='{date_filter}'")

            if not logs:
                self.logs_table.setRowCount(0)
                self.no_logs_label.setVisible(True)
                return

            self.logs_table.setRowCount(len(logs))
            for row, log in enumerate(logs):
                timestamp = log[1] if len(log) > 1 else ""
                event = log[2] if len(log) > 2 else ""
                frame_path = log[3] if len(log) > 3 else ""
                screen_path = log[4] if len(log) > 3 else ""
                confidence = log[5] if len(log) > 4 else None
                active_apps = log[6] if len(log) > 5 else None
                username = log[7] if len(log) > 6 else ""

                # abs_frame_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', frame_path)) if frame_path else ""
                # abs_frame_path = get_resource_path(frame_path) if frame_path else ""
                abs_frame_path = get_image_path(frame_path) if frame_path else ""
                if frame_path:
                    print(f"DEBUG: Checking path: frame_path={frame_path}, abs_path={abs_frame_path}, exists={os.path.exists(abs_frame_path)}")
                
                # abs_screen_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', screen_path)) if screen_path else ""
                # abs_screen_path = get_resource_path(screen_path) if screen_path else ""
                abs_screen_path = get_image_path(screen_path) if screen_path else ""
                if screen_path:
                    print(f"DEBUG: Checking path: screen_path={screen_path}, abs_path={abs_screen_path}, exists={os.path.exists(abs_screen_path)}")

                try:
                    confidence = json.loads(confidence) if confidence else None
                    active_apps = json.loads(active_apps) if active_apps else None
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"DEBUG: Error parsing JSON for log id={log[0]}: {e}")
                    confidence, active_apps = None, None

                item = QTableWidgetItem(timestamp)
                item.setTextAlignment(Qt.AlignCenter)
                self.logs_table.setItem(row, 0, item)
                
                event_colors = {
                    "Обнаружен мобильный телефон": "#FFD8E4",  # Pink 200
                    "Однотонное изображение": "#FFE7C9",       # Orange 100
                    "Потеря связи с камерой": "#FFCCBC",       # Deep Orange 100
                    "Попытка закрыть приложение": "#F5B7B1",   # Red 100
                    "Востановление после \"Потеря связи с камерой\"": "#B3E5FC",  # Light Blue 100
                    "Зависшее изображение": "#FFECB3",         # Amber 100
                    "Изображение отвисло": "#C8E6C9"           # Green 100
                }
                item = QTableWidgetItem(event)
                item.setTextAlignment(Qt.AlignCenter)
                if event in event_colors:
                    item.setBackground(QColor(event_colors[event]))
                item.setForeground(QColor("#1C1B1F"))  # On Surface для текста
                self.logs_table.setItem(row, 1, item)

                confidence_text = ", ".join([f"{c:.2f}" for c in confidence]) if confidence else ""
                item = QTableWidgetItem(confidence_text)
                item.setTextAlignment(Qt.AlignCenter)
                self.logs_table.setItem(row, 2, item)

                apps_text = ""
                if active_apps:
                    for app in active_apps:
                        status = " (развернуто)" if app.get("foreground") else ""
                        process = app.get("process", "")
                        title = app.get("title", "")
                        apps_text += f"{process}: {title}{status}\n"
                item = QTableWidgetItem(apps_text.strip())
                item.setTextAlignment(Qt.AlignCenter)
                self.logs_table.setItem(row, 3, item)

                item = QTableWidgetItem(username)
                item.setTextAlignment(Qt.AlignCenter)
                self.logs_table.setItem(row, 4, item)

                if frame_path and os.path.exists(abs_frame_path):
                    image = cv2.imread(abs_frame_path)
                    if image is not None:
                        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                        height, width, channel = image.shape
                        qimage = QImage(image.data, width, height, width * channel, QImage.Format_RGB888)
                        pixmap = QPixmap.fromImage(qimage).scaled(150, 150, Qt.KeepAspectRatio)
                        item = QTableWidgetItem()
                        item.setData(Qt.DecorationRole, pixmap)
                        item.setData(Qt.UserRole, row)
                        self.logs_table.setItem(row, 5, item)
                    else:
                        print(f"DEBUG: Error frame loading image: {abs_frame_path}")
                        item = QTableWidgetItem("Ошибка загрузки")
                        item.setTextAlignment(Qt.AlignCenter)
                        self.logs_table.setItem(row, 5, item)
                else:
                    print(f"DEBUG: Frame missing: {abs_frame_path}")
                    item = QTableWidgetItem("Миниатюра отсутствует")
                    item.setTextAlignment(Qt.AlignCenter)
                    self.logs_table.setItem(row, 5, item)
                    
                if screen_path and os.path.exists(abs_screen_path):
                    image = cv2.imread(abs_screen_path)
                    if image is not None:
                        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                        height, width, channel = image.shape
                        qimage = QImage(image.data, width, height, width * channel, QImage.Format_RGB888)
                        pixmap = QPixmap.fromImage(qimage).scaled(150, 150, Qt.KeepAspectRatio)
                        item = QTableWidgetItem()
                        item.setData(Qt.DecorationRole, pixmap)
                        item.setData(Qt.UserRole, row)
                        self.logs_table.setItem(row, 6, item)
                    else:
                        print(f"DEBUG: Error screen loading image: {abs_screen_path}")
                        item = QTableWidgetItem("Ошибка загрузки")
                        item.setTextAlignment(Qt.AlignCenter)
                        self.logs_table.setItem(row, 6, item)
                else:
                    print(f"DEBUG: Screen missing: {abs_screen_path}")
                    item = QTableWidgetItem("Миниатюра отсутствует")
                    item.setTextAlignment(Qt.AlignCenter)
                    self.logs_table.setItem(row, 6, item)

                self.logs_table.resizeRowToContents(row)

            self.logs_table.resizeColumnsToContents()
            self.logs_table.setFixedWidth(1450)  # зафиксировать ширину виджета таблицы

        except sqlite3.Error as e:
            print(f"DEBUG: Error loading logs from database: {e}")
            self.logs_table.setRowCount(0)
            self.no_logs_label.setVisible(True)

    def on_cell_clicked(self, row, column):
        print(f"DEBUG: Cell clicked: row={row}, column={column}")
        # if column == 5:
        # item = self.logs_table.item(row, column)
        item = self.logs_table.item(row, 5)
        if item and item.data(Qt.UserRole) is not None:
            logs = self.logger.get_logs()
            if logs:
                dialog = ImageDialog(logs, row, self)
                dialog.exec_()

    def closeEvent(self, event):
        if self.camera:
            self.camera.release()
            self.camera = None
        if self.timer.isActive():
            self.timer.stop()
        event.accept()

def run_admin_panel():
    app = QApplication(sys.argv)
    window = AdminPanel()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_admin_panel()