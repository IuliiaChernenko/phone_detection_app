from PyQt5.QtCore import Qt
from dataclasses import dataclass

@dataclass
class ThemeColors:
    """Хранит цветовую палитру для темы."""
    surface: str
    on_surface: str
    primary: str
    primary_container: str
    on_primary: str
    outline: str
    error: str
    on_error: str
    disabled: str
    disabled_text: str

@dataclass
class ThemeTypography:
    """Хранит типографику для темы."""
    font_family: str = "Roboto, sans-serif"
    # font_family: str = "Segoe UI, sans-serif"
    label_medium: int = 16
    label_small: int = 14
    font_weight_regular: int = 400
    font_weight_medium: int = 500

@dataclass
class ThemeConstants:
    """Хранит константы дизайна."""
    corner_radius_small: int = 4  # dp, для полей ввода
    corner_radius_large: int = 8  # dp, для кнопок
    padding_small: int = 8  # dp
    padding_large: int = 16  # dp
    button_height: int = 32  # dp
    row_height: int = 56  # dp
    font_family: str = "Roboto, sans-serif"
    font_size_label_medium: int = 16
    font_size_label_small: int = 14
    font_weight_regular: int = 400
    font_weight_medium: int = 500

class ThemeManager:
    """Управляет темами и стилями для приложения."""
    def __init__(self):
        self.themes = {
            "light": ThemeColors(
                surface="#F5F5F5",
                on_surface="#1C1B1F",
                primary="#6750A4",
                primary_container="#E6DDFF",
                on_primary="#FFFFFF",
                outline="#757575",
                error="#B3261E",
                on_error="#FFFFFF",
                disabled="#E0E0E0",
                disabled_text="#757575"
            ),
            "dark": ThemeColors(
                surface="#1C1B1F",
                on_surface="#E6E1E5",
                primary="#D0BCFF",
                primary_container="#4F378B",
                on_primary="#381E72",
                outline="#938F99",
                error="#F2B8B5",
                on_error="#601410",
                disabled="#424242",
                disabled_text="#757575"
            ),
            "teal": ThemeColors(
                surface="#F7FAFA",  # Светлый серо-голубой фон, современный и чистый
                on_surface="#1A3C34",  # Тёмный teal для текста, высокая контрастность
                primary="#26A69A",  # Яркий teal, модный и энергичный
                primary_container="#E0F2F1",  # Светлый teal для фона элементов
                on_primary="#FFFFFF",  # Белый для текста на primary
                outline="#607D8B",  # Нейтральный серо-голубой для границ
                error="#D32F2F",  # Стандартный красный для ошибок
                on_error="#FFFFFF",  # Белый для текста на ошибках
                disabled="#B0BEC5",  # Приглушённый серо-голубой для неактивных
                disabled_text="#78909C"  # Серо-голубой для текста неактивных
            )
        }
        self.typography = ThemeTypography()
        self.current_theme = "teal"
        self.constants = ThemeConstants()

    def get_widget_stylesheet(self) -> str:
        """Возвращает StyleSheet для QWidget (например, LogsTab)."""
        theme = self.get_theme()
        return f"""
            QWidget {{
                background-color: {theme.surface};
                border: 1px solid {theme.outline};
                border-radius: {self.constants.corner_radius_large}px;
            }}
        """

    def set_theme(self, theme_name: str):
        """Переключает текущую тему."""
        if theme_name in self.themes:
            self.current_theme = theme_name

    def get_theme(self) -> ThemeColors:
        """Возвращает текущую цветовую палитру."""
        return self.themes[self.current_theme]

    def get_date_edit_stylesheet(self) -> str:
        """Возвращает StyleSheet для QDateEdit/QTimeEdit."""
        theme = self.get_theme()
        return f"""
            QDateEdit, QTimeEdit {{
                background-color: {theme.surface};
                border: 1px solid {theme.outline};
                border-radius: 4px;
                padding: 8px;
                font-family: {self.typography.font_family};
                font-size: {self.typography.label_medium}px;
                color: {theme.on_surface};
            }}
            QDateEdit:hover, QTimeEdit:hover {{
                background-color: {theme.primary_container};
                border: 1px solid {theme.primary};
            }}
            QDateEdit:focus, QTimeEdit:focus {{
                border: 2px solid {theme.primary};
                padding: 7px 27px 7px 11px;
            }}
            QDateEdit:disabled, QTimeEdit:disabled {{
                background-color: {theme.disabled};
                color: {theme.disabled_text};
                border: 1px solid {theme.disabled_text};
            }}
        """

    def get_combobox_stylesheet(self) -> str:
        """Возвращает StyleSheet для QComboBox."""
        theme = self.get_theme()
        return f"""
            QComboBox {{
                background-color: {theme.surface};
                border: 1px solid {theme.outline};
                border-radius: {self.constants.corner_radius_small}px;
                padding: {self.constants.padding_small}px;
                font-family: {self.typography.font_family};
                font-size: {self.typography.label_medium}px;
                color: {theme.on_surface};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 32px;
            }}
            QComboBox::down-arrow {{
                image: url(:/icons/arrow_drop_down.png);
                width: 24px;
                height: 24px;
            }}
            QComboBox:hover {{
                background-color: {theme.primary_container};
                border: 1px solid {theme.primary};
            }}
            QComboBox:focus {{
                border: 2px solid {theme.primary};
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.surface};
                border: 1px solid {theme.outline};
                border-radius: {self.constants.corner_radius_small}px;
                color: {theme.on_surface};
                font-family: {self.typography.font_family};
                font-size: {self.typography.label_medium}px;
                selection-background-color: {theme.primary_container};
                selection-color: {theme.on_surface};
            }}
            QComboBox QAbstractItemView::item {{
                padding: {self.constants.padding_small}px;
                border-radius: {self.constants.corner_radius_small}px;
                min-height: {self.constants.row_height - 2 * self.constants.padding_small}px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {theme.primary};
                color: {theme.on_primary};
                font-weight: {self.typography.font_weight_medium};
            }}
        """

    def get_table_stylesheet(self) -> str:
        """Возвращает StyleSheet для QTableWidget.

        Returns:
            str: Стилизованный CSS для таблицы.
        """
        theme = self.get_theme()
        return f"""
            QTableWidget {{
                background-color: {theme.surface};
                border: 1px solid {theme.outline};
                border-radius: {self.constants.corner_radius_small}px;
                gridline-color: {theme.outline};
                font-family: {self.typography.font_family};
                font-size: {self.typography.label_small}px;
                alternate-background-color: {theme.primary_container};
            }}
            QTableWidget::item {{
                padding: {self.constants.padding_small}px;
                color: {theme.on_surface};
            }}
            QTableWidget::item:selected {{
                background-color: {theme.primary_container};
                color: {theme.on_surface};
            }}
            QHeaderView::section {{
                background-color: {theme.primary};
                color: {theme.on_primary};
                padding: {self.constants.padding_small}px;
                font-family: {self.typography.font_family};
                font-weight: {self.typography.font_weight_medium};
                font-size: {self.typography.label_small}px;
                border: none;
                border-bottom: 1px solid {theme.outline};
            }}
            QScrollBar:vertical, QScrollBar:horizontal {{
                background: {theme.surface};
                border: none;
                margin: 0px;
                width: 8px;
                height: 8px;
            }}
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
                background: {theme.outline};
                border-radius: 4px;
                min-height: 20px;
                min-width: 20px;
            }}
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
                background: {theme.primary};
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                height: 0px;
                width: 0px;
            }}
            QScrollBar::add-page, QScrollBar::sub-page {{
                background: transparent;
            }}
        """

    def get_button_stylesheet(self, variant: str = "primary") -> str:
        """Возвращает StyleSheet для QPushButton.

        Args:
            variant: Вариант кнопки ('primary' или 'error').

        Returns:
            str: Стилизованный CSS для кнопки.
        """
        theme = self.get_theme()
        if variant == "error":
            bg_color, text_color, hover_color, pressed_color = (
                theme.error, theme.on_error, "#C62828", "#9A1C1C"
            )
        else:
            bg_color, text_color, hover_color, pressed_color = (
                theme.primary, theme.on_primary, "#7E57C2", "#5E35B1"
            )
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                border-radius: {self.constants.corner_radius_small}px;
                padding: 8px 16px;
                font-family: {self.typography.font_family};
                font-weight: {self.typography.font_weight_medium};
                font-size: {self.typography.label_small}px;
                min-height: 32px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
            QPushButton:disabled {{
                background-color: {theme.disabled};
                color: {theme.disabled_text};
            }}
        """

    def get_label_stylesheet(self) -> str:
        """Возвращает StyleSheet для QLabel.

        Returns:
            str: Стилизованный CSS для меток.
        """
        theme = self.get_theme()
        return f"""
            QLabel {{
                color: {theme.on_surface};
                font-family: {self.typography.font_family};
                font-size: {self.typography.label_medium}px;
                font-weight: {self.typography.font_weight_regular};
                padding: 0px;
                background: transparent;
            }}
        """
                
    def get_label_stylesheet_with_padding(self) -> str:
        """Возвращает StyleSheet для QLabel.

        Returns:
            str: Стилизованный CSS для меток.
        """
        theme = self.get_theme()
        return f"""
            QLabel {{
                color: {theme.on_surface};
                font-family: {self.typography.font_family};
                font-size: {self.typography.label_medium}px;
                font-weight: {self.typography.font_weight_regular};
                padding: padding: {self.constants.padding_small}px;
                background: transparent;
            }}
        """

    def get_input_stylesheet(self) -> str:
        """Возвращает StyleSheet для QLineEdit, QSpinBox, QDoubleSpinBox."""
        theme = self.get_theme()
        return f"""
            QLineEdit, QSpinBox, QDoubleSpinBox {{
                background-color: {theme.surface};
                border: 1px solid {theme.outline};
                border-radius: {self.constants.corner_radius_small}px;
                padding: {self.constants.padding_small}px;
                font-family: {self.typography.font_family};
                font-size: {self.typography.label_medium}px;
                color: {theme.on_surface};
            }}
            QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
                background-color: {theme.primary_container};
                border: 1px solid {theme.primary};
            }}
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {theme.primary};
            }}
        """
            # QSpinBox::up-button, QSpinBox::down-button,
            # QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            #     width: 20px;
            #     border: none;
            #     background-color: {theme.surface};
            # }}
            # QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
            #     image: url(:/icons/arrow_up.png);
            #     width: 16px;
            #     height: 16px;
            # }}
            # QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
            #     image: url(:/icons/arrow_down.png);
            #     width: 16px;
            #     height: 16px;
            # }}

    def get_checkbox_stylesheet(self) -> str:
        """Возвращает StyleSheet для QCheckBox."""
        theme = self.get_theme()
        return f"""
            QCheckBox {{
                color: {theme.on_surface};
                font-family: {self.typography.font_family};
                font-size: {self.typography.label_medium}px;
                font-weight: {self.typography.font_weight_regular};
                padding: {self.constants.padding_small}px;
                spacing: 8px; /* Отступ между индикатором и текстом */
            }}
            QCheckBox::indicator {{
                width: 24px; /* Увеличенный размер для современности */
                height: 24px;
                border: 2px solid {theme.outline};
                border-radius: {self.constants.corner_radius_small}px;
                background-color: {theme.surface};
            }}
            QCheckBox::indicator:checked {{
                width: 24px; /* Увеличенный размер для современности */
                height: 24px;
                background-color: qradialgradient(spread:pad, 
                        cx:0.5,
                        cy:0.5,
                        radius:0.5,
                        fx:0.5,
                        fy:0.5,
                        stop:0 rgba(38, 166, 154, 255), 
                        stop:1 rgba(224, 242, 241, 255));
                border: 2px solid {theme.primary};
                border-radius: {self.constants.corner_radius_small}px;
            }}
        """
        # return f"""
        #     QCheckBox::indicator {{
        #         width: 30px;
        #         height: 30px;
        #         background-color: gray;
        #         border-radius: 15px;
        #         border-style: solid;
        #         border-width: 1px;
        #         border-color: white white black black;
        #     }}
        #     QCheckBox::indicator:checked {{
        #         background-color: qradialgradient(spread:pad, 
        #                                 cx:0.5,
        #                                 cy:0.5,
        #                                 radius:0.9,
        #                                 fx:0.5,
        #                                 fy:0.5,
        #                                 stop:0 rgba(0, 255, 0, 255), 
        #                                 stop:1 rgba(0, 64, 0, 255));
        #     }}
        #     QCheckBox:checked, QCheckBox::indicator:checked {{
        #         border-color: black black white white;
        #     }}
        #     QCheckBox:checked {{
        #         background-color: qradialgradient(spread:pad, 
        #                                 cx:0.739, 
        #                                 cy:0.278364, 
        #                                 radius:0.378, 
        #                                 fx:0.997289, 
        #                                 fy:0.00289117, 
        #                                 stop:0 rgba(255, 255, 255, 255), 
        #                                 stop:1 rgba(160, 160, 160, 255));
        #     }}
        # """
        # return f"""
        #     QCheckBox {{
        #         color: {theme.on_surface};
        #         font-family: {self.typography.font_family};
        #         font-size: {self.typography.label_medium}px;
        #         font-weight: {self.typography.font_weight_regular};
        #         padding: {self.constants.padding_small}px;
        #         spacing: 8px; /* Отступ между индикатором и текстом */
        #     }}
        #     QCheckBox::indicator {{
        #         width: 24px; /* Увеличенный размер для современности */
        #         height: 24px;
        #         border: 2px solid {theme.outline};
        #         border-radius: {self.constants.corner_radius_small}px;
        #         background-color: {theme.surface};
        #     }}
        #     QCheckBox::indicator:checked {{
        #         width: 12px; /* Увеличенный размер для современности */
        #         height: 12px;
        #         background-color: {theme.primary_container};
        #         border: 8px solid {theme.primary};
        #         border-radius: {self.constants.corner_radius_small}px;
        #         image: url(:\\assets\\logo.png);
        #     }}
        # """
        # return f"""
        #     QCheckBox {{
        #         color: {theme.on_surface};
        #         font-family: {self.typography.font_family};
        #         font-size: {self.typography.label_medium}px;
        #         font-weight: {self.typography.font_weight_regular};
        #         padding: {self.constants.padding_small}px;
        #         spacing: 8px; /* Отступ между индикатором и текстом */
        #     }}
        #     QCheckBox::indicator {{
        #         width: 24px; /* Увеличенный размер для современности */
        #         height: 24px;
        #         border: 2px solid {theme.outline};
        #         border-radius: {self.constants.corner_radius_small}px;
        #         background-color: {theme.surface};
        #     }}
        #     QCheckBox::indicator:checked {{
        #         background-color: {theme.primary_container};
        #         border: 2px solid {theme.primary};
        #         border-radius: {self.constants.corner_radius_small}px;
        #     }}
        #     QCheckBox::indicator:hover {{
        #         border: 2px solid {theme.primary};
        #     }}
        #     QCheckBox::indicator:checked:hover {{
        #         background-color: {theme.primary}; /* Сохраняем основной цвет */
        #         border: 2px solid {theme.primary};
        #     }}
        #     QCheckBox:hover {{
        #         background-color: {theme.primary_container}; /* Фон контейнера при наведении */
        #         border-radius: {self.constants.corner_radius_small}px;
        #     }}
        # """