import sys
import os
import re
import pyqtgraph as pg
import numpy as np
import time
import signal
import threading
import traceback
import ntpath
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QWidget,
    QComboBox,
    QStackedWidget,
    QRadioButton,
)

try:
    import OpenGL
    pg.setConfigOption('useOpenGL', True)
    #pg.setConfigOption('enableExperimental', True)
except Exception as e:
    print(f"Enabling OpenGL failed with {e}. Will result in slow rendering. Try installing PyOpenGL.")

#path_to_lib = os.path.join(os.path.dirname(__file__), 'libs')
#sys.path.append(os.path.realpath(path_to_lib))
#import libs

import libs.image_loader as image_loader
import libs.utils as utils
from libs.utils import Color

CONF_FILENAME = 'conf.npy'

class UI(QMainWindow):
    sig_plot = pyqtSignal(str, str, object)
    win = None

    def __init__(self):
        super().__init__()
        self.init_gui_vars()
        self.setup_main_window()
        self.restore_last_settings()

    def init_gui_vars(self):
        self.gui_vars = {
            'current_mode': Color.MONO,
        }
        #self.threaded_plot = utils.PLOT_QTHREAD(parent=self)
        #self.threaded_plot.sig_plot.connect(self.thread_receive)
        #self.sig_plot.connect(self.threaded_plot.receive)
        #self.threaded_plot.start()

    @pyqtSlot()
    def gui_control(self):
        button_text = self.sender().text()
        cmd = self.button_mapping[button_text]
        if cmd == "load":
            self.load_file()
        else:
            print("Received unknown command {} ({})".format(button_text, cmd))
            return

    @pyqtSlot()
    def load_file(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Image file",
            "",
            "Fits (*.fits);; DSLR Raw (*.cr2)",
            options=options,
        )

        if not filename:
            return
        else:
            try:
                self.img = image_loader.IMAGE(filename)
                self.img.load()
                self.gui_vars['mono'] = True
                self.display_image()
            except Exception:
                self.error_message('Failed to open Image')
                traceback.print_exc()

    def display_image(self):
        if self.get_color_mode() == Color.MONO:
            self.im_frame.setImage(self.img.data_mono, levels=self.img.clip_mono)
            self.histo_m.show()
            self.histo_m.setData(self.img.histogram_edges, self.img.histogram_mono)
            self.histo_r.hide()
            self.histo_g.hide()
            self.histo_b.hide()
        else:
            self.img.debayer()
            self.im_frame.setImage(self.img.data_cfa, levels=self.img.clip_cfa)
            self.histo_m.hide()
            self.histo_r.show()
            self.histo_g.show()
            self.histo_b.show()
            self.histo_r.setData(self.img.histogram_edges, self.img.histogram_r)
            self.histo_g.setData(self.img.histogram_edges, self.img.histogram_g)
            self.histo_b.setData(self.img.histogram_edges, self.img.histogram_b)

    def color_mode_clicked(self):
        radioButton = self.sender()
        if radioButton.isChecked():
            self.gui_vars['current_mode'] = radioButton.mode
            if hasattr(self, 'img'):
                self.display_image()

    def get_color_mode(self):
        for cm in self.color_modes:
            if cm.isChecked():
                return cm.mode


    def thread_receive(self, message_type, message, data=None):
        try:
            if message_type == "dummy":
                pass
            else:
                print("Unknown message type {}: {}".format(message_type, data))
        except Exception:
            traceback.print_exc()

    def setup_main_window(self):
        self.canvas_widget = QFrame(self)
        self.canvas_widget.setStyleSheet("QFrame::handle{background: lightgrey}")
        self.setCentralWidget(self.canvas_widget)
        self.canvas_layout = QtWidgets.QGridLayout(self.canvas_widget)

        pg.setConfigOption("background", "#f0f0f0")
        pg.setConfigOption("foreground", "k")
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('imageAxisOrder', 'row-major')

        self.graph_widget = QFrame()
        self.graph_widget.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.graph_box = QtWidgets.QGridLayout()
        self.graph_widget.setLayout(self.graph_box)

        self.canvas_layout.addWidget(self.graph_widget, 0, 0)

        self.buttons = {
            "load": QPushButton("Load"),
        }

        self.button_mapping = {}
        for b in self.buttons:
            self.button_mapping[self.buttons[b].text()] = b
            button = self.buttons[b]
            button.clicked.connect(self.gui_control)

        self.text = {
        }

        self.color_mode_widget = QFrame()
        color_mode_box = QtWidgets.QGridLayout()
        self.color_mode_widget.setLayout(color_mode_box)
        self.color_mode_widget.setMinimumHeight(25)
        items = [['Mono', Color.MONO], ['CFA', Color.CFA]]
        self.color_modes = []
        for idx, item in enumerate(items):
            radiobutton = QRadioButton(item[0])
            radiobutton.mode = item[1]
            radiobutton.setMinimumHeight(15)
            radiobutton.toggled.connect(self.color_mode_clicked)
            if item[1] == Color.MONO:
                radiobutton.setChecked(True)
            color_mode_box.addWidget(radiobutton, 0, idx)
            self.color_modes.append(radiobutton)

        self.control_widget = QFrame()
        self.control_widget.setFrameStyle(QFrame.Panel | QFrame.Raised)
        control_box = QtWidgets.QGridLayout()
        control_box.setAlignment(QtCore.Qt.AlignLeft)
        self.control_widget.setLayout(control_box)
        control_box.addWidget(self.buttons["load"], 0, 0)
        control_box.addWidget(self.color_mode_widget, 0, 1)

        self.canvas_layout.addWidget(self.control_widget, 2, 0, 1, 1)

        #self.scroll_area = QtWidgets.QScrollArea()
        #self.scroll_area.setFrameShape(QFrame.NoFrame)
        #self.scroll_area.setMinimumWidth(350)
        #self.scroll_area.setMaximumWidth(600)
        #self.scroll_area.setWidgetResizable(True)
        #self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        #self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        #self.scroll_area.horizontalScrollBar().setEnabled(False)

        #self.scroll_area_widget = QStackedWidget(self.scroll_area)
        #self.scroll_area.setWidget(self.scroll_area_widget)
        #self.sublayout = QtWidgets.QGridLayout()
        #self.sublayout.setContentsMargins(2, 2, 2, 2)
        #self.sublayout.setSpacing(1)
        #self.sublayout_widget = QWidget(self.scroll_area_widget)
        #self.sublayout_widget.setLayout(self.sublayout)
        #self.scroll_area_widget.addWidget(self.sublayout_widget)
        #self.scroll_area_widget.setCurrentWidget(self.sublayout_widget)
        #self.canvas_layout.addWidget(self.scroll_area, 0, 2, 2, 1)

        self.resize(800, 800)
        self.show()
        QApplication.processEvents()
        self.setup_plotting_window()

    @pyqtSlot()
    def dummy(self):
        pass

    @pyqtSlot()
    def setup_plotting_window(self):
        if self.win is not None:
            self.graph_box.removeWidget(self.win)
            self.win.setParent(None)
            self.win.deleteLater()
            self.win = None

        self.im_frame = pg.ImageView()
        self.graph_box.addWidget(self.im_frame, 0, 0)

        self.win = pg.GraphicsLayoutWidget()
        self.win.setMaximumHeight(100)
        self.histo_plot_win = self.win.addPlot(row=0, col=0)
        self.histo_plot_win.showGrid(x=True, y=True)
        pen = pg.mkPen('#000000', width=2)
        self.histo_m = self.histo_plot_win.plot(pen=pen)
        pen = pg.mkPen('#ff0000', width=2)
        self.histo_r = self.histo_plot_win.plot(pen=pen)
        pen = pg.mkPen('#00ff00', width=2)
        self.histo_g = self.histo_plot_win.plot(pen=pen)
        pen = pg.mkPen('#0000ff', width=2)
        self.histo_b = self.histo_plot_win.plot(pen=pen)
        self.win.addItem(self.histo_plot_win)
        self.graph_box.addWidget(self.win, 1, 0)

    def close(self):
        print("Closing down!")
        signals = []

        for sig in signals:
            try:
                sig.emit("stop", "", None)
            except Exception:
                traceback.print_exc()
        time.sleep(0.2)
        app.closeAllWindows()

    def error_message(self, text, info_text=None):
        if not text:
            return
        message_box = MessageBox(self.canvas_widget)
        message_box.setIcon(QtWidgets.QMessageBox.Warning)
        message_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        message_box.setWindowTitle("Alert")
        message_box.setText(text.replace("\n", "<br>"))
        if info_text:
            message_box.setInformativeText(info_text.replace("\n", "<br>"))
        if any(sys.exc_info()):
            detailed_text = traceback.format_exc()
            message_box.setDetailedText(detailed_text)

        message_box.exec_()

    def restore_last_settings(self):
        if not os.path.isfile(CONF_FILENAME):
            return
        try:
            conf = np.load(CONF_FILENAME, allow_pickle=True).item()
        except Exception:
            traceback.print_exc()
        else:
            for key in conf:
                self.gui_vars[key] = conf[key]

    def closeEvent(self, event=None):
        try:
            np.save(CONF_FILENAME, self.gui_vars, allow_pickle=True)
        except Exception:
            traceback.print_exc()
        self.close()


class MessageBox(QtWidgets.QMessageBox):
    def resizeEvent(self, event):
        result = super().resizeEvent(event)
        self.setFixedWidth(500)
        return result


def sigint_handler(gui):
    event = threading.Event()
    thread = threading.Thread(target=watchdog, args=(event,))
    thread.start()
    gui.closeEvent()
    event.set()
    thread.join()


def watchdog(event):
    flag = event.wait(1)
    if not flag:
        print("\nforcing exit...")
        os._exit(1)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = UI()

    signal.signal(signal.SIGINT, lambda *_: sigint_handler(ex))

    # Makes sure the signal is caught
    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(200)

    sys.exit(app.exec())
