from lollms.utilities import PackageManager, find_first_available_file_index, discussion_path_to_url
from lollms.client_session import Client
if not PackageManager.check_package_installed("pyautogui"):
    PackageManager.install_package("pyautogui")
if not PackageManager.check_package_installed("PyQt5"):
    PackageManager.install_package("PyQt5")

import cv2
import time
from PyQt5 import QtWidgets, QtGui, QtCore
import sys

class CameraWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.cap = cv2.VideoCapture(0)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(50)

    def initUI(self):
        self.setWindowTitle('Camera')
        
        self.image_label = QtWidgets.QLabel(self)
        self.image_label.resize(640, 480)
        
        self.captured_image_label = QtWidgets.QLabel(self)
        self.captured_image_label.resize(640, 480)

        self.take_shot_button = QtWidgets.QPushButton('Take Shot', self)
        self.take_shot_button.clicked.connect(self.take_shot)

        self.ok_button = QtWidgets.QPushButton('OK', self)
        self.ok_button.clicked.connect(self.ok)
        
        self.hbox_layout = QtWidgets.QHBoxLayout()
        self.hbox_layout.addWidget(self.image_label)
        self.hbox_layout.addWidget(self.captured_image_label)

        self.vbox_layout = QtWidgets.QVBoxLayout()
        self.vbox_layout.addLayout(self.hbox_layout)
        self.vbox_layout.addWidget(self.take_shot_button)
        self.vbox_layout.addWidget(self.ok_button)
        self.setLayout(self.vbox_layout)

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            self.frame = frame
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = image.shape
            step = channel * width
            qImg = QtGui.QImage(image.data, width, height, step, QtGui.QImage.Format_RGB888)
            self.image_label.setPixmap(QtGui.QPixmap.fromImage(qImg))

    def take_shot(self):
        if hasattr(self, 'frame'):
            self.captured_frame = self.frame
            image = cv2.cvtColor(self.captured_frame, cv2.COLOR_BGR2RGB)
            height, width, channel = image.shape
            step = channel * width
            qImg = QtGui.QImage(image.data, width, height, step, QtGui.QImage.Format_RGB888)
            self.captured_image_label.setPixmap(QtGui.QPixmap.fromImage(qImg))

    def ok(self):
        if hasattr(self, 'captured_frame'):
            self.close()

    def closeEvent(self, event):
        self.cap.release()
        event.accept()

def take_photo(client, use_ui=False):
    if use_ui:
        def run_app():
            app = QtWidgets.QApplication(sys.argv)
            win = CameraWindow()
            win.show()
            app.exec_()
            return win

        win = run_app()

        if hasattr(win, 'captured_frame'):
            frame = win.captured_frame
        else:
            return "Failed to capture image."
    else:
        # Attempt to access the webcam
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            return "\nWebcam is not connected."
        
        # Capture a single frame
        n = time.time()
        ret, frame = cap.read()
        while(time.time()-n<2):
            ret, frame = cap.read()

        if not ret:
            return "Failed to capture image."
        
        cap.release()

    view_image = client.discussion.discussion_folder/"view_images"
    image = client.discussion.discussion_folder/"images"
    index = find_first_available_file_index(view_image,"screen_shot_",".png")
    fn_view = view_image/f"screen_shot_{index}.png"
    cv2.imwrite(str(fn_view), frame)
    fn = image/f"screen_shot_{index}.png"
    cv2.imwrite(str(fn), frame)
    client.discussion.image_files.append(fn)
    return f'<img src="{discussion_path_to_url(fn_view)}" width="80%"></img>'
