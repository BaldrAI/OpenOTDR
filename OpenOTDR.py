#!/usr/bin/env python3

import sys
import os
import json
from collections import deque
from threading import Lock
from PyQt5 import QtWidgets
from PyQt5 import QtPrintSupport
from PyQt5 import QtGui
from PyQt5 import QtCore
import numpy as np
from scipy.ndimage import zoom
from scipy.signal import find_peaks
from pyOTDR import sorparse
from matplotlib.figure import Figure
from matplotlib import cm
from matplotlib import colors
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import mainwindow


'''An Open Source OTDR reporting tool'''


def round_sig(value, significant_figures):
    '''Rounds a value to a number of significant figures.
    However the value is less than 1 then simply round it to 1 D.P.'''
    if value < 1:
        return round(value, 1)
    return round(value, -int(np.floor(np.sign(value) * np.log10(abs(value)))) + significant_figures)


def _low_pass_filter_trace(a_raw_trace, window_len):
    '''A simple LowPass Hanning filter'''
    samples = np.r_[a_raw_trace[0][window_len-1:0:-1],
                    a_raw_trace[0],
                    a_raw_trace[0][-2:-window_len-1:-1]]
    window = np.hanning(window_len)
    a_smoothed_levels = np.convolve(window/window.sum(), samples, mode='valid')
    trim = min(len(a_smoothed_levels), len(a_raw_trace[1]))
    a_trace = np.array([a_smoothed_levels[:trim], a_raw_trace[1][:trim]])
    return a_trace


def prepare_data(d_data, window_len):
    '''Transforms the trace data to unify sample width and signal quality'''
    a_raw_trace = d_data["trace"]
    # Smoothing
    a_smooth_trace = _low_pass_filter_trace(a_raw_trace, window_len)
    # Scale to ensure resolution per distance unit is equal.
    a_trace = zoom(a_smooth_trace, zoom=(1.0, d_data["meta"]["FxdParams"]["resolution"]), order=1)
    # Offsetting to make all launch levels the same
    n_offset = -a_trace[0][325]
    a_trace[0] = a_trace[0] + n_offset
    return {"meta": d_data["meta"], "trace": a_trace}


def differentiate_data(d_data):
    '''Calculates the 1st order differential of the data'''
    a_raw_trace = d_data["trace"]
    a_diff_trace = np.diff(a_raw_trace[0])
    a_clean_trace = []
    for sample_index in range(len(a_raw_trace[0])):
        if sample_index < len(a_diff_trace)-1:
            a_clean_trace.append(a_diff_trace[sample_index])
        else:
            a_clean_trace.append(0)
    return [a_clean_trace, a_raw_trace]


def find_edges(a_differential_trace):
    '''Finds windows that contain features'''
    a_abs_trace = [abs(sample) for sample in a_differential_trace[0]]
    a_peaks = find_peaks(a_abs_trace, 0.00125, width=5, distance=150)
    return [a_peaks[0],
            [a_differential_trace[1][0][peak] for peak in a_peaks[0]],
            [a_differential_trace[1][1][peak] for peak in a_peaks[0]]]


def wavelength_to_rgb(s_wavelength):
    '''Convert the wavelength to a spectral 'false' colour'''
    wavelength = int(s_wavelength[:-3])
    norm = colors.Normalize(vmin=1250, vmax=1650, clip=True)
    mapper = cm.ScalarMappable(norm=norm, cmap=cm.jet_r)
    red, green, blue, _ = mapper.to_rgba(wavelength)
    return "#{:02X}{:02X}{:02X}".format(int(red*255), int(green*255), int(blue*255))


class CustomNavigationToolbar(NavigationToolbar):
    '''Removing a couple of irrelavent tools from the toolbar'''
    toolitems = (('Home', 'Reset original view', 'home', 'home'),
                 ('Back', 'Back to previous view', 'back', 'back'),
                 ('Forward', 'Forward to next view', 'forward', 'forward'),
                 (None, None, None, None),
                 ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
                 ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'))


class NaturalSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    '''Filter as a human would, not alphanumeric'''
    @staticmethod
    def _numeric_key(key):
        '''The numeric key'''
        if key:
            return float(key)
        return float('-inf')

    def lessThan(self, left, right):
        '''The < operator for Qt5'''
        left_data = self.sourceModel().data(left)
        right_data = self.sourceModel().data(right)
        return self._numeric_key(left_data) < self._numeric_key(right_data)


class MainWindow(QtWidgets.QMainWindow):
    '''The main window handler class'''
    def __init__(self):
        super(MainWindow, self).__init__()
        self.user_interface = mainwindow.Ui_MainWindow()
        self.user_interface.setupUi(self)
        self.project_model = QtGui.QStandardItemModel()
        self.user_interface.treeView.setModel(self.project_model)
        self.events_model = QtGui.QStandardItemModel()
        self.events_proxy_model = NaturalSortFilterProxyModel()
        self.events_proxy_model.setSourceModel(self.events_model)
        self.events_proxy_model.sort(1, QtCore.Qt.AscendingOrder)
        self.user_interface.eventTableView.setModel(self.events_proxy_model)
        self.user_interface.openProject.clicked.connect(self.open_project)
        self.user_interface.saveProject.clicked.connect(self.save_project)
        self.user_interface.printReport.clicked.connect(self.print_pdf)
        self.user_interface.printReport.setDisabled(True)
        self.user_interface.addTrace.clicked.connect(self.add_trace)
        self.user_interface.removeTrace.clicked.connect(self.remove_trace)
        self.user_interface.recalculateEvents.clicked.connect(self.recalculate_events)
        self.window_len = 0
        self.canvas = None
        self.toolbar = None
        self.raw_features = []
        self.raw_traces = []
        self.files = {}
        self.meta = {}
        self.busy = Lock()
        self._draw()

    def __preprocess_data(self, d_meta, l_raw_trace):
        '''Convert the raw data into a numpy array'''
        sample_spacing = float(d_meta["FxdParams"]["sample spacing"][:-5])
        self.window_len = int(0.5/sample_spacing)
        q_trace = deque(l_raw_trace)
        l_distance = list()
        l_level = list()
        raw_row = q_trace.popleft()
        while q_trace:
            raw_distance, raw_level = raw_row.replace("\n", "").split("\t")
            f_distance = float(raw_distance)
            f_level = float(raw_level)
            l_distance.append(f_distance)
            l_level.append(f_level)
            raw_row = q_trace.popleft()
        a_trace = np.array([l_level, l_distance])
        return a_trace

    def _load_file(self, url, _project=False):
        '''Load the raw SOR file from provided url into the internal data format'''
        if not _project:
            _, d_meta, l_raw_trace = sorparse(url)
            d_meta["url"] = url
        else:
            d_meta = _project["meta"]
            l_raw_trace = _project["raw_trace"]
        self.files[url] = {"meta": d_meta, "raw_trace": l_raw_trace}
        a_trace = self.__preprocess_data(d_meta, l_raw_trace)
        d_data= prepare_data({"meta":d_meta, "trace":a_trace}, self.window_len)
        filename = os.path.basename(url)
        item = QtGui.QStandardItem(filename)
        item.data = d_data
        self.project_model.appendRow(item)

    def _draw(self):
        '''(re)draw the plot with the latest data'''
        fig = Figure()
        plt = fig.add_subplot(1, 1, 1)
        if self.raw_traces:
            for d_final_data in self.raw_traces:
                wavelength = d_final_data["meta"]["GenParams"]["wavelength"]
                plt.plot(d_final_data["trace"][1],
                         d_final_data["trace"][0],
                         label=wavelength,
                         color=wavelength_to_rgb(wavelength))
        if self.canvas:
            self.user_interface.graphLayout.removeWidget(self.canvas)
            self.canvas.close()
        if self.toolbar:
            self.user_interface.graphLayout.removeWidget(self.toolbar)
            self.toolbar.close()
        fig.legend()
        self.canvas = FigureCanvas(fig)
        self.toolbar = CustomNavigationToolbar(self.canvas, self, coordinates=True)
        self.user_interface.graphLayout.addWidget(self.canvas)
        self.user_interface.graphLayout.addWidget(self.toolbar)

    def open_project(self):
        '''Load a project from a file'''
        if self.busy.locked():
            return
        with self.busy:
            options = QtWidgets.QFileDialog.Options()
            options |= QtWidgets.QFileDialog.DontUseNativeDialog
            uri, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open project", "", "OpenOTDR Project Files(*.opro);;All Files (*)", options=options)
            if uri:
                with open(uri, "r") as file:
                    content = json.load(file)
                self.meta = content["meta"]
                for uri, data in content["files"].items():
                    self._load_file(uri, _project=data)
                for index in range(self.project_model.rowCount()):
                    raw_data = self.project_model.item(index).data
                    self.raw_traces.append(raw_data)
                self._draw()
        self.recalculate_events()

    def save_project(self):
        '''Save a project to a file'''
        if self.busy.locked():
            return
        with self.busy:
            options = QtWidgets.QFileDialog.Options()
            options |= QtWidgets.QFileDialog.DontUseNativeDialog
            uri, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save project", "", "OpenOTDR Project Files(*.opro);;All Files (*)", options=options)
            if uri:
                _, extension = os.path.splitext(uri)
                if not extension:
                    uri += ".opro"
                content = {"meta": self.meta, "files": self.files}
                with open(uri, "w") as file:
                    json.dump(content, file)

    def print_pdf(self):
        '''Print the report to pdf'''
        if self.busy.locked():
            return
        with self.busy:
            printer = QtPrintSupport.QPrinter()
            dialog = QtPrintSupport.QPrintDialog(printer, self)
            dialog.setModal(True)
            dialog.setWindowTitle("Print Document")
            dialog.options = (QtPrintSupport.QAbstractPrintDialog.PrintToFile
                              | QtPrintSupport.QAbstractPrintDialog.PrintShowPageSize
                              | QtPrintSupport.QAbstractPrintDialog.PrintPageRange)
            if dialog.exec_():
                print("printing")
                # TODO Printing

    def add_trace(self):
        '''Load a new trace'''
        if self.busy.locked():
            return
        with self.busy:
            options = QtWidgets.QFileDialog.Options()
            options |= QtWidgets.QFileDialog.DontUseNativeDialog
            files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Add traces", "", "OTDR Trace Files(*.sor);;All Files (*)", options=options)
            if not files:
                return
            for filename in files:
                self._load_file(filename)
            for index in range(self.project_model.rowCount()):
                raw_data = self.project_model.item(index).data
                self.raw_traces.append(raw_data)

    def remove_trace(self):
        '''Remove a trace'''
        if self.busy.locked():
            return
        with self.busy:
            if not self.user_interface.treeView.selectedIndexes():
                return
            indexes = self.user_interface.treeView.selectedIndexes()
            for index in indexes:
                self.project_model.removeRow(index.row())
                del self.raw_traces[index.row()]
            self._draw()
    
    @staticmethod
    def _filter_events(raw_features):
        '''Filter the detected features of each trace to make a single set with no duplicates or ghosts'''
        d_events = {}
        for trace_features in raw_features:
            for index, feature in enumerate(trace_features[2]):
                feature_position = round_sig(feature, 1)
                if feature_position not in d_events and feature_position-0.1 not in d_events and feature_position+0.1 not in d_events:
                    d_events[feature_position] = {
                        "indexes": []
                        }
                if feature_position in d_events:
                    d_events[feature_position]["indexes"].append(trace_features[0][index])
                elif feature_position-0.1 in d_events:
                    d_events[feature_position-0.1]["indexes"].append(trace_features[0][index])
                elif feature_position+0.1 in d_events:
                    d_events[feature_position+0.1]["indexes"].append(trace_features[0][index])
        return d_events

    def __calculate_loss_and_dispersion(self, raw_traces, meta_data):
        '''Calculate the loss and dispersion of an event'''
        start_values = []
        end_values = []
        for trace in raw_traces:
            for i in meta_data["indexes"]:
                start_index = max(0, i-self.window_len)
                start_values.append(trace["trace"][0][start_index])
                end_index = min(len(trace["trace"][0])-1, i+self.window_len)
                end_values.append(trace["trace"][0][end_index])
                self.canvas.figure.get_axes()[0].axvspan(trace["trace"][1][start_index], trace["trace"][1][end_index], color='yellow', alpha=0.5)
        average_start = sum(start_values)/len(start_values)
        average_end = sum(end_values)/len(end_values)
        loss = average_start - average_end
        difference_start = max(start_values) - min(start_values)
        difference_end = max(end_values) - min(end_values)
        dispersion_factor = round(max(difference_end/difference_start, difference_start/difference_end))
        return loss, dispersion_factor

    def _update_events_table(self, d_events, raw_traces):
        '''Update the events table in the UI'''
        self.events_model.clear()
        self.events_model.setHorizontalHeaderLabels(['Event',
                                                     'Distance (km)',
                                                     'Loss (dB)',
                                                     'Dispersion factor'])
        for position, meta_data in d_events.items():
            current_row = self.events_model.rowCount()
            self.events_model.insertRow(current_row)
            event_position = QtGui.QStandardItem()
            event_position.setText(str(position))
            event_position.setEditable(False)
            self.events_model.setItem(current_row, 1, event_position)
            loss, dispersion_factor = self.__calculate_loss_and_dispersion(raw_traces, meta_data)
            event_loss = QtGui.QStandardItem()
            event_loss.setText(str(loss))
            event_loss.setEditable(False)
            self.events_model.setItem(current_row, 2, event_loss)
            event_dispersion = QtGui.QStandardItem()
            event_dispersion.setText(str(dispersion_factor))
            event_dispersion.setEditable(False)
            self.events_model.setItem(current_row, 3, event_dispersion)
            event_type = QtGui.QStandardItem()
            event_type.setEditable(True)
            self.events_model.setItem(current_row, 0, event_type)
        self.events_model.sort(1)

    def recalculate_events(self):
        '''Recalculate the events'''
        if self.busy.locked():
            return
        with self.busy:
            l_traces = []
            l_feature_points = []
            for index in range(self.project_model.rowCount()):
                raw_data = self.project_model.item(index).data
                d_data = prepare_data(raw_data, self.window_len)
                l_traces.append(d_data)
                l_feature_points.append(find_edges(differentiate_data(d_data)))
            raw_features = l_feature_points
            raw_traces = l_traces
            if not raw_features:
                return
            d_events = self._filter_events(raw_features)
            self._update_events_table(d_events, raw_traces)


APP = QtWidgets.QApplication(sys.argv)

MAIN_WINDOW = MainWindow()
MAIN_WINDOW.setWindowTitle("OpenOTDR")
MAIN_WINDOW.show()

sys.exit(APP.exec_())
