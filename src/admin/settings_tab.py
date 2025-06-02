from typing import List, Tuple, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLabel,
    QPushButton, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QListWidget, QLineEdit, QTextEdit, QScrollArea
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor
from PyQt5.QtCore import Qt, QTimer
import os
import cv2
import numpy as np

from src.core.camera import Camera
from src.core.config import Config
from src.admin.styles import ThemeManager
from src.admin.utils import get_resource_path


class SettingsTab(QWidget):
    """Класс для управления вкладкой настроек в админ-панели."""

    def __init__(self, config: Config, theme_manager: ThemeManager) -> None:
        """
        Инициализация вкладки настроек.

        Args:
            config: Экземпляр класса Config для доступа к настройкам.
            theme_manager: Экземпляр ThemeManager для управления темами.
        """
        super().__init__()
        self.config: Config = config
        self.theme_manager: ThemeManager = theme_manager
        self.cameras: List[Tuple[int, str]] = Camera.list_available_cameras()
        self.current_theme: str = "light"
        self.camera: Optional[Camera] = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_preview)
        self._init_ui()

    def _init_ui(self) -> None:
        """Инициализация пользовательского интерфейса вкладки."""
        theme = self.theme_manager.get_theme()
        self.setStyleSheet(f"QWidget {{ background-color: {theme.surface}; }}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.setAlignment(Qt.AlignCenter)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_widget = QWidget()
        scroll_widget.setObjectName("scrollWidget")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(10)
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        column_widget = QWidget()
        column_widget.setMaximumWidth(1024)
        column_layout = QVBoxLayout(column_widget)
        column_layout.setAlignment(Qt.AlignHCenter)
        scroll_layout.addWidget(column_widget, alignment=Qt.AlignHCenter)

        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {theme.surface};
                border: none;
            }}
            QWidget#scrollWidget {{
                background-color: {theme.surface};
            }}
            QScrollBar:vertical {{
                width: 8px;
                margin: 0px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {theme.outline};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(10)
        form_layout.setHorizontalSpacing(20)

        device_layout = QHBoxLayout()
        device_label = QLabel("Устройство:")
        device_label.setStyleSheet(self.theme_manager.get_label_stylesheet_with_padding())
        self.camera_combo = QComboBox()
        self.camera_combo.setFixedWidth(200)
        self.camera_combo.setStyleSheet(self.theme_manager.get_combobox_stylesheet())
        camera_names = [name for _, name in self.cameras] or ["Нет доступных камер"]
        self.camera_combo.addItems(camera_names)
        self._set_current_camera()
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.camera_combo)
        device_layout.addStretch()
        form_layout.addRow(device_layout)

        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(720, 576)
        self.preview_label.setMaximumSize(720, 576)  # Увеличено до 720x576
        self.preview_label.setSizePolicy(
            self.preview_label.sizePolicy().Expanding,
            self.preview_label.sizePolicy().Expanding
        )
        self.preview_label.setScaledContents(False)
        self.preview_label.setAlignment(Qt.AlignCenter)
        logo_path = get_resource_path("assets/logo.png")
        print(f"DEBUG: Loading logo: {logo_path}, exists={os.path.exists(logo_path)}")
        try:
            pixmap = QPixmap(logo_path).scaled(
                720, 576, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            if pixmap.isNull():
                raise ValueError("Не удалось загрузить изображение")
            self.preview_label.setPixmap(pixmap)
        except Exception as e:
            print(f"ERROR: Failed to load logo: {e}")
            self.preview_label.setText("Логотип отсутствует")
        form_layout.addRow(self.preview_label)

        self.check_button = QPushButton("Проверить соединение")
        self.check_button.setStyleSheet(self.theme_manager.get_button_stylesheet())
        self.check_button.clicked.connect(self.toggle_preview)
        form_layout.addRow(self.check_button)

        self.fps_spin = QSpinBox()
        self.fps_spin.setFixedWidth(200)
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(self.config.get("fps"))
        self.fps_spin.setStyleSheet(self.theme_manager.get_input_stylesheet())
        fps_label = QLabel("Частота кадров (FPS):")
        fps_label.setStyleSheet(self.theme_manager.get_label_stylesheet())
        form_layout.addRow(fps_label, self.fps_spin)

        self.retention_combo = QComboBox()
        self.retention_combo.setFixedWidth(200)
        self.retention_combo.setStyleSheet(self.theme_manager.get_combobox_stylesheet())
        self.retention_combo.addItems(["1 день", "1 неделя", "1 месяц", "1 год", "Не удалять"])
        self.retention_combo.setCurrentText(self.config.get("log_retention"))
        retention_label = QLabel("Время хранения логов:")
        retention_label.setStyleSheet(self.theme_manager.get_label_stylesheet())
        form_layout.addRow(retention_label, self.retention_combo)

        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setFixedWidth(200)
        self.confidence_spin.setRange(0.1, 0.9)
        self.confidence_spin.setSingleStep(0.1)
        self.confidence_spin.setValue(self.config.get("confidence_threshold"))
        self.confidence_spin.setStyleSheet(self.theme_manager.get_input_stylesheet())
        confidence_label = QLabel("Уровень уверенности:")
        confidence_label.setStyleSheet(self.theme_manager.get_label_stylesheet())
        form_layout.addRow(confidence_label, self.confidence_spin)

        self.count_spin = QSpinBox()
        self.count_spin.setFixedWidth(200)
        self.count_spin.setRange(1, 999)
        self.count_spin.setValue(self.config.get("phone_limit"))
        self.count_spin.setStyleSheet(self.theme_manager.get_input_stylesheet())
        count_label = QLabel("Кол-во кадров реакции:")
        count_label.setStyleSheet(self.theme_manager.get_label_stylesheet())
        form_layout.addRow(count_label, self.count_spin)

        lock_group = QGroupBox("Блокировка экрана")
        lock_group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {theme.outline};
                border-radius: {self.theme_manager.constants.corner_radius_large}px;
                padding: {self.theme_manager.constants.padding_small}px;
                background-color: {theme.surface};
                font-family: {self.theme_manager.typography.font_family};
                font-size: {self.theme_manager.typography.label_medium}px;
                color: {theme.on_surface};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: {theme.on_surface};
            }}
        """)
        lock_layout = QVBoxLayout()
        lock_layout.setSpacing(5)
        self.lock_phone_detected = QCheckBox("Детекция телефона")
        self.lock_phone_detected.setChecked(self.config.get("lock_events")["phone_detected"])
        self.lock_phone_detected.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        lock_layout.addWidget(self.lock_phone_detected)
        self.lock_camera_lost = QCheckBox("Потеря связи с камерой")
        self.lock_camera_lost.setChecked(self.config.get("lock_events")["camera_lost"])
        self.lock_camera_lost.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        lock_layout.addWidget(self.lock_camera_lost)
        self.lock_uniform_image = QCheckBox("Однотонное изображение")
        self.lock_uniform_image.setChecked(self.config.get("lock_events")["uniform_image"])
        self.lock_uniform_image.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        lock_layout.addWidget(self.lock_uniform_image)
        self.lock_attempt_to_close = QCheckBox("Попытка закрыть приложение")
        self.lock_attempt_to_close.setChecked(self.config.get("lock_events")["attempt_to_close"])
        self.lock_attempt_to_close.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        lock_layout.addWidget(self.lock_attempt_to_close)
        self.lock_static_img = QCheckBox("Статичное изображение (кадры не меняются 30 секунд)")
        self.lock_static_img.setChecked(self.config.get("lock_events")["static_img"])
        self.lock_static_img.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        lock_layout.addWidget(self.lock_static_img)
        lock_group.setLayout(lock_layout)
        form_layout.addRow(lock_group)

        log_group = QGroupBox("Запись в журнал событий")
        log_group.setStyleSheet(lock_group.styleSheet())
        log_layout = QVBoxLayout()
        log_layout.setSpacing(5)
        self.log_phone_detected = QCheckBox("Детекция телефона")
        self.log_phone_detected.setChecked(self.config.get("log_events")["phone_detected"])
        self.log_phone_detected.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        log_layout.addWidget(self.log_phone_detected)
        self.log_camera_lost = QCheckBox("Потеря связи с камерой")
        self.log_camera_lost.setChecked(self.config.get("log_events")["camera_lost"])
        self.log_camera_lost.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        log_layout.addWidget(self.log_camera_lost)
        self.log_uniform_image = QCheckBox("Однотонное изображение")
        self.log_uniform_image.setChecked(self.config.get("log_events")["uniform_image"])
        self.log_uniform_image.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        log_layout.addWidget(self.log_uniform_image)
        self.log_attempt_to_close = QCheckBox("Попытка закрыть приложение")
        self.log_attempt_to_close.setChecked(self.config.get("log_events")["attempt_to_close"])
        self.log_attempt_to_close.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        log_layout.addWidget(self.log_attempt_to_close)
        self.log_static_img = QCheckBox("Статичное изображение (кадры не меняются 30 секунд)")
        self.log_static_img.setChecked(self.config.get("log_events")["static_img"])
        self.log_static_img.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        log_layout.addWidget(self.log_static_img)
        log_group.setLayout(log_layout)
        form_layout.addRow(log_group)

        other_group = QGroupBox("Дополнительно")
        other_group.setStyleSheet(lock_group.styleSheet())
        other_layout = QVBoxLayout()
        other_layout.setSpacing(5)
        self.make_screen_enabled = QCheckBox("Снимок экрана")
        self.make_screen_enabled.setChecked(self.config.get("other_events")["make_screen_enabled"])
        self.make_screen_enabled.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        other_layout.addWidget(self.make_screen_enabled)
        self.autostart_system = QCheckBox("Автозапуск при старте системы")
        self.autostart_system.setChecked(self.config.get("autostart")["on_system_start"])
        self.autostart_system.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        other_layout.addWidget(self.autostart_system)
        other_group.setLayout(other_layout)
        form_layout.addRow(other_group)

        notifications_group = QGroupBox("Оповещения")
        notifications_group.setStyleSheet(lock_group.styleSheet())
        notifications_layout = QVBoxLayout()
        notifications_layout.setSpacing(5)
        self.notifications_phone_detected = QCheckBox("Детекция телефона")
        self.notifications_phone_detected.setChecked(self.config.get("notifications")["phone_detected"])
        self.notifications_phone_detected.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        notifications_layout.addWidget(self.notifications_phone_detected)
        self.notifications_camera_lost = QCheckBox("Потеря связи с камерой")
        self.notifications_camera_lost.setChecked(self.config.get("notifications")["camera_lost"])
        self.notifications_camera_lost.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        notifications_layout.addWidget(self.notifications_camera_lost)
        self.notifications_uniform_image = QCheckBox("Однотонное изображение")
        self.notifications_uniform_image.setChecked(self.config.get("notifications")["uniform_image"])
        self.notifications_uniform_image.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        notifications_layout.addWidget(self.notifications_uniform_image)
        self.notifications_attempt_to_close = QCheckBox("Попытка закрыть приложение")
        self.notifications_attempt_to_close.setChecked(self.config.get("notifications")["attempt_to_close"])
        self.notifications_attempt_to_close.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        notifications_layout.addWidget(self.notifications_attempt_to_close)
        self.notifications_static_img = QCheckBox("Статичное изображение (кадры не меняются 30 секунд)")
        self.notifications_static_img.setChecked(self.config.get("notifications")["static_img"])
        self.notifications_static_img.setStyleSheet(self.theme_manager.get_checkbox_stylesheet())
        notifications_layout.addWidget(self.notifications_static_img)
        notifications_group.setLayout(notifications_layout)
        form_layout.addRow(notifications_group)

        tg_group = QGroupBox("Telegram оповещения")
        tg_group.setStyleSheet(lock_group.styleSheet())
        tg_layout = QVBoxLayout()
        tg_layout.setSpacing(10)

        telegram_label = QLabel("Список Telegram ID для рассылки:")
        telegram_label.setStyleSheet(self.theme_manager.get_label_stylesheet())
        tg_layout.addWidget(telegram_label)
        self.telegram_id_list = QListWidget()
        self.telegram_id_list.setFixedWidth(350)
        self.telegram_id_list.setMinimumHeight(150)
        self.telegram_id_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {theme.surface};
                border: 1px solid {theme.outline};
                border-radius: {self.theme_manager.constants.corner_radius_small}px;
                color: {theme.on_surface};
                font-family: {self.theme_manager.typography.font_family};
                font-size: {self.theme_manager.typography.label_small}px;
            }}
            QListWidget::item:selected {{
                background-color: {theme.primary_container};
                color: {theme.on_surface};
            }}
        """)
        telegram_ids = self.config.get("telegram_ids")
        self.telegram_id_list.addItems(telegram_ids if telegram_ids else ["Нет добавленных ID"])
        tg_layout.addWidget(self.telegram_id_list)

        self.telegram_id_input = QLineEdit()
        self.telegram_id_input.setPlaceholderText("Введите Telegram ID")
        self.telegram_id_input.setFixedWidth(350)
        self.telegram_id_input.setStyleSheet(self.theme_manager.get_input_stylesheet())
        tg_layout.addWidget(self.telegram_id_input)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        add_button = QPushButton("Добавить")
        add_button.setStyleSheet(self.theme_manager.get_button_stylesheet())
        add_button.clicked.connect(self.add_telegram_id)
        button_layout.addWidget(add_button)
        edit_button = QPushButton("Изменить")
        edit_button.setStyleSheet(self.theme_manager.get_button_stylesheet())
        edit_button.clicked.connect(self.edit_telegram_id)
        button_layout.addWidget(edit_button)
        delete_button = QPushButton("Удалить")
        delete_button.setStyleSheet(self.theme_manager.get_button_stylesheet("error"))
        delete_button.clicked.connect(self.delete_telegram_id)
        button_layout.addWidget(delete_button)
        tg_layout.addLayout(button_layout)

        tg_layout.addSpacing(10)
        instruction_label = QLabel("Инструкция:")
        instruction_label.setStyleSheet(self.theme_manager.get_label_stylesheet())
        tg_layout.addWidget(instruction_label)
        self.instruction_text = QTextEdit()
        self.instruction_text.setReadOnly(True)
        # self.instruction_text.setFixedWidth(350)
        self.instruction_text.setMinimumHeight(200)
        self.instruction_text.setSizePolicy(
            self.instruction_text.sizePolicy().horizontalPolicy(),
            self.instruction_text.sizePolicy().Preferred
        )
        # self.instruction_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.instruction_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.surface};
                border: 1px solid {theme.outline};
                border-radius: {self.theme_manager.constants.corner_radius_small}px;
                padding: {self.theme_manager.constants.padding_small}px;
                font-family: {self.theme_manager.typography.font_family};
                font-size: {self.theme_manager.typography.label_small}px;
                color: {theme.on_surface};
            }}
        """)
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
        tg_layout.addWidget(self.instruction_text)

        tg_group.setLayout(tg_layout)
        form_layout.addRow(tg_group)

        column_layout.addLayout(form_layout)

        save_button = QPushButton("Сохранить")
        save_button.setStyleSheet(self.theme_manager.get_button_stylesheet())
        save_button.clicked.connect(self.save_settings)
        save_button.setMaximumWidth(200)
        column_layout.addWidget(save_button, alignment=Qt.AlignCenter)

        column_layout.addStretch()

    def _scale_pixmap_with_padding(self, pixmap: QPixmap, target_width: int, target_height: int) -> QPixmap:
        """Масштабирует QPixmap с сохранением пропорций, добавляя поля."""
        scaled_pixmap = pixmap.scaled(
            target_width, target_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        scaled_width, scaled_height = scaled_pixmap.width(), scaled_pixmap.height()
        if scaled_width == target_width and scaled_height == target_height:
            return scaled_pixmap
        result = QPixmap(target_width, target_height)
        result.fill(QColor(self.theme_manager.get_theme().surface))
        painter = QPainter(result)
        painter.drawPixmap((target_width - scaled_width) // 2, (target_height - scaled_height) // 2, scaled_pixmap)
        painter.end()
        return result

    def update_preview(self) -> None:
        """Обновление предпросмотра видео с камеры."""
        if not self.camera:
            self.preview_label.setText("Камера не инициализирована")
            return
        frame = self.camera.get_frame()
        if frame is None:
            self.preview_label.setText("Нет сигнала")
            print("DEBUG: No frame received for preview")
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = frame.shape
        qimage = QImage(frame.data, width, height, width * channel, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        target_width = min(self.preview_label.width(), 720)
        target_height = min(self.preview_label.height(), 576)  # Увеличено до 576
        scaled_pixmap = self._scale_pixmap_with_padding(pixmap, target_width, target_height)
        self.preview_label.setPixmap(scaled_pixmap)

    def _set_current_camera(self) -> None:
        """Установка текущей камеры в QComboBox."""
        current_camera = self.config.get("camera_id")
        for i, (cam_id, _) in enumerate(self.cameras):
            if cam_id == current_camera:
                self.camera_combo.setCurrentIndex(i)
                break

    def toggle_preview(self) -> None:
        """Переключение предпросмотра камеры."""
        if self.timer.isActive():
            self.timer.stop()
            if self.camera:
                self.camera.release()
                self.camera = None
            logo_path = get_resource_path('assets/logo.png')
            try:
                pixmap = QPixmap(logo_path).scaled(
                    720, 576, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                if pixmap.isNull():
                    raise ValueError("Не удалось загрузить изображение")
                self.preview_label.setPixmap(pixmap)
            except Exception as e:
                print(f"ERROR: Failed to load logo: {e}")
                self.preview_label.setText("Логотип отсутствует")
            self.check_button.setText("Проверить соединение")
            print("DEBUG: Preview stopped")
        else:
            selected_index = self.camera_combo.currentIndex()
            if not self.cameras or selected_index < 0:
                self.preview_label.setText("Камера недоступна")
                self.check_button.setText("Проверить соединение")
                print("DEBUG: No cameras available for preview")
                return
            camera_id = self.cameras[selected_index][0]
            try:
                self.camera = Camera(camera_id)
                self.timer.start(100)
                self.check_button.setText("Остановить проверку")
                print(f"DEBUG: Preview started for camera ID={camera_id}")
            except Exception as e:
                self.preview_label.setText("Ошибка камеры")
                self.check_button.setText("Проверить соединение")
                print(f"DEBUG: Error starting preview: {e}")

    def add_telegram_id(self) -> None:
        """Добавление нового Telegram ID в список."""
        telegram_id = self.telegram_id_input.text().strip()
        if not telegram_id:
            return
        if self.telegram_id_list.item(0) and self.telegram_id_list.item(0).text() == "Нет добавленных ID":
            self.telegram_id_list.clear()
        self.telegram_id_list.addItem(telegram_id)
        self.telegram_id_input.clear()

    def edit_telegram_id(self) -> None:
        """Редактирование выбранного Telegram ID."""
        selected_item = self.telegram_id_list.currentItem()
        if selected_item:
            new_id = self.telegram_id_input.text().strip()
            if new_id:
                selected_item.setText(new_id)
                self.telegram_id_input.clear()

    def delete_telegram_id(self) -> None:
        """Удаление выбранного Telegram ID."""
        selected_row = self.telegram_id_list.currentRow()
        if selected_row >= 0:
            self.telegram_id_list.takeItem(selected_row)
            if self.telegram_id_list.count() == 0:
                self.telegram_id_list.addItem("Нет добавленных ID")

    def toggle_theme(self) -> None:
        """Переключение темы интерфейса."""
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.theme_manager.set_theme(self.current_theme)
        self._init_ui()

    def save_settings(self) -> None:
        """Сохранение всех настроек."""
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
            },
            "lock_events": {
                "phone_detected": self.lock_phone_detected.isChecked(),
                "camera_lost": self.lock_camera_lost.isChecked(),
                "uniform_image": self.lock_uniform_image.isChecked(),
                "attempt_to_close": self.lock_attempt_to_close.isChecked(),
                "static_img": self.lock_static_img.isChecked(),
            },
            "log_events": {
                "phone_detected": self.log_phone_detected.isChecked(),
                "camera_lost": self.log_camera_lost.isChecked(),
                "uniform_image": self.log_uniform_image.isChecked(),
                "attempt_to_close": self.log_attempt_to_close.isChecked(),
                "static_img": self.log_static_img.isChecked(),
            },
            "other_events": {
                "make_screen_enabled": self.make_screen_enabled.isChecked(),
            },
            "notifications": {
                "phone_detected": self.notifications_phone_detected.isChecked(),
                "camera_lost": self.notifications_camera_lost.isChecked(),
                "uniform_image": self.notifications_uniform_image.isChecked(),
                "attempt_to_close": self.notifications_attempt_to_close.isChecked(),
                "static_img": self.notifications_static_img.isChecked(),
            },
            "telegram_ids": [self.telegram_id_list.item(i).text()
                             for i in range(self.telegram_id_list.count())
                             if self.telegram_id_list.item(i).text() != "Нет добавленных ID"]
        })
        self.config.save_config(config)
        print(f"DEBUG: Settings saved: {config}")