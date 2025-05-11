from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
import sys

class ErrorWindow:
    def __init__(self):
        self.app = QApplication(sys.argv) if QApplication.instance() is None else QApplication.instance()

    def show_error(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Ошибка")
        msg.setStandardButtons(QMessageBox.Ok)
        # Устанавливаем окно поверх всех и на весь экран
        msg.setWindowFlags(Qt.WindowStaysOnTopHint)
        # Настраиваем стиль: большой шрифт, центрированный текст, красный фон
        msg.setStyleSheet("QLabel { font-size: 20pt; text-align: center; } QMessageBox { background-color: #ffcccc; }")
        msg.showFullScreen()
        msg.exec_()