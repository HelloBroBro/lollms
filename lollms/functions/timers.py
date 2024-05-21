# Lollms function call definition file
# Here you need to import any necessary imports depending on the function requested by the user
# example import math

# Partial is useful if we need to preset some parameters
from functools import partial

# It is advised to import typing elements
# from typing import List

# Import PackageManager if there are potential libraries that need to be installed 
from lollms.utilities import PackageManager

# ascii_colors offers advanced console coloring and bug tracing
from ascii_colors import trace_exception

# Here is an example of how we install a non installed library using PackageManager
if not PackageManager.check_package_installed("PyQt5"):
    PackageManager.install_package("PyQt5")

# now we can import the library
import threading
import time
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
import winsound

# here is the core of the function to be built
def set_timer_with_alert(duration: int, message: str) -> str:
    def timer_callback():
        time.sleep(duration)
        winsound.Beep(1000, 1000)  # Make noise when time is up

        app = QApplication(sys.argv)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Timer Alert")
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.buttonClicked.connect(app.quit)
        msg_box.exec_()
        
    try:
        # Start the timer in a new thread to make it non-blocking
        timer_thread = threading.Thread(target=timer_callback)
        timer_thread.start()
        
        # Return a success message
        return f"Timer set for {duration} seconds with message '{message}'."
    except Exception as e:
        return trace_exception(e)

# Here is the metadata function that should have the name in format function_name_function
def set_timer_with_alert_function(processor, client):
    return {
        "function_name": "set_timer_with_alert", # The function name in string
        "function": set_timer_with_alert, # The function to be called
        "function_description": "Sets a non-blocking timer that shows a PyQt window with a message and makes noise after a specified duration.", # Description of the function
        "function_parameters": [{"name": "duration", "type": "int"}, {"name": "message", "type": "str"}] # The set of parameters
    }
