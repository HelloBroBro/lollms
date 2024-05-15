from lollms.utilities import PackageManager, find_first_available_file_index, discussion_path_to_url
from lollms.client_session import Client
if not PackageManager.check_package_installed("pyautogui"):
    PackageManager.install_package("pyautogui")
if not PackageManager.check_package_installed("PyQt5"):
    PackageManager.install_package("PyQt5")

import pyautogui
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt
import sys
class ScreenshotWindow(QtWidgets.QWidget):
    def __init__(self, client, screenshot, fn_view, fn):
        super().__init__()
        self.client = client
        self.screenshot = screenshot
        self.fn_view = fn_view
        self.fn = fn
        
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Screenshot Viewer')
        self.layout = QtWidgets.QVBoxLayout()
        
        self.label = QtWidgets.QLabel(self)
        self.pixmap = QtGui.QPixmap(self.screenshot)
        self.label.setPixmap(self.pixmap)
        self.layout.addWidget(self.label)
        
        self.ok_button = QtWidgets.QPushButton('OK')
        self.ok_button.clicked.connect(self.save_and_close)
        self.layout.addWidget(self.ok_button)
        
        self.setLayout(self.layout)
        
    def save_and_close(self):
        self.screenshot.save(self.fn_view)
        self.screenshot.save(self.fn)
        self.client.discussion.image_files.append(self.fn)
        self.close()


def take_screenshot(self, client: Client, use_ui: bool = False):
    screenshot = pyautogui.screenshot()
    view_image = client.discussion.discussion_folder / "view_images"
    image = client.discussion.discussion_folder / "images"
    index = find_first_available_file_index(view_image, "screen_shot_", ".png")
    fn_view = view_image / f"screen_shot_{index}.png"
    fn = image / f"screen_shot_{index}.png"

    if use_ui:
        app = QtWidgets.QApplication(sys.argv)
        window = ScreenshotWindow(client, screenshot, fn_view, fn)
        window.show()
        app.exec_()
        return f'<img src="{discussion_path_to_url(fn_view)}" width="80%"></img>'
    else:
        screenshot.save(fn_view)
        screenshot.save(fn)
        client.discussion.image_files.append(fn)
        return f'<img src="{discussion_path_to_url(fn_view)}" width="80%"></img>'