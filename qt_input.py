import sys
from PyQt5.QtWidgets import QApplication, QLineEdit
from PyQt5.QtCore import Qt

def qt_input(app, title, placeholder=None, tool_window=False):
    code = None    
    code_le = QLineEdit()

    def return_pressed_handler():
        nonlocal code
        code = code_le.text()
        code_le.close()

    code_le.setWindowTitle(title)
    if placeholder is not None:
        code_le.setPlaceholderText(placeholder) 
    if tool_window:    
        code_le.setWindowFlags(code_le.windowFlags() | Qt.Tool | Qt.WindowStaysOnTopHint)    
    code_le.returnPressed.connect(return_pressed_handler)
    code_le.show()
    code_le.setAttribute(Qt.WA_QuitOnClose)
    code_le.setFocusPolicy(Qt.StrongFocus)
    code_le.setFocus()
    code_le.raise_()
    code_le.activateWindow()
    app.exec_()

    return code


if __name__ == "__main__":
	app = QApplication(sys.argv)
	print(qt_input(app, 'test1'))
	print(qt_input(app, 'test2', placeholder='azaza'))