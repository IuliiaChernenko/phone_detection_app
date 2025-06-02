from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt
import sys


message = """
Приложение запущено без прав администратора!
Пожалуйста, обратитесь к администратору, либо запустите приложение используя его права.
"""

def critical_error(logger):
    msg = QMessageBox()
    msg.setWindowFlags(Qt.WindowStaysOnTopHint)
    msg.setWindowTitle("Критическая ошибка")
    msg.setText(message)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()
    logger.debug(f"Showed alert: {message}")
    sys.exit()
