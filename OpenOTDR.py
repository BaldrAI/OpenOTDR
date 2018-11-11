import sys, os, re
from collections import deque
from threading import Lock

from PyQt5 import QtWidgets, QtPrintSupport, QtGui, QtCore
import numpy as np
from scipy.ndimage import zoom
from scipy.signal import find_peaks
from pyOTDR import sorparse
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
import mainwindow

window_len = 0

def _low_return_filter_trace(a_raw_trace, window_len):
    samples = np.r_[a_raw_trace[0][window_len-1:0:-1], a_raw_trace[0], a_raw_trace[0][-2:-window_len-1:-1]]
    window = np.hanning(window_len)
    a_smoothed_levels = np.convolve(window/window.sum(), samples, mode='valid')
    trim = min(len(a_smoothed_levels), len(a_raw_trace[1]))
    a_trace = np.array([a_smoothed_levels[:trim], a_raw_trace[1][:trim]])
    return a_trace

def prepare_data(d_data):
    '''Transforms the trace data to unify sample width and signal quality'''
    a_raw_trace = d_data["trace"]
    # Smoothing
    sample_spacing = float(d_data["meta"]["FxdParams"]["sample spacing"][:-5])
    global window_len
    window_len = int(0.5/sample_spacing)
    a_smooth_trace = _low_return_filter_trace(a_raw_trace, window_len)
    # Horizontal scaling
    a_trace = zoom(a_smooth_trace, zoom=(1.0, d_data["meta"]["FxdParams"]["resolution"]), order=1) # Scale to ensure resolution per distance unit is equal.
    # Offsetting
    n_offset = -a_trace[0][325]
    a_trace[0] = a_trace[0] + n_offset
    return {"meta":d_data["meta"], "trace":a_trace}

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
    return  [a_peaks[0], [a_differential_trace[1][0][peak] for peak in a_peaks[0]], [a_differential_trace[1][1][peak] for peak in a_peaks[0]]]

class CustomNavigationToolbar(NavigationToolbar):
    toolitems = (('Home', 'Reset original view', 'home', 'home'), 
                ('Back', 'Back to previous view', 'back', 'back'), 
                ('Forward', 'Forward to next view', 'forward', 'forward'), 
                (None, None, None, None), 
                ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'), 
                ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'))
    


class NaturalSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    @staticmethod
    def _human_key(key):
        if key:
            return float(key)
        return float('-inf')
    
    def lessThan(self, left, right):
        leftData = self.sourceModel().data(left)
        rightData = self.sourceModel().data(right)
        return self._human_key(leftData) < self._human_key(rightData)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = mainwindow.Ui_MainWindow()
        self.ui.setupUi(self)
        self.project_model = QtGui.QStandardItemModel()
        self.ui.treeView.setModel(self.project_model)
        self.events_model = QtGui.QStandardItemModel()
        self.events_proxy_model = NaturalSortFilterProxyModel()
        self.events_proxy_model.setSourceModel(self.events_model)
        self.events_proxy_model.sort(1, QtCore.Qt.AscendingOrder)
        self.ui.eventTableView.setModel(self.events_proxy_model)
        self.ui.openProject.clicked.connect(self.open_project)
        self.ui.openProject.setDisabled(True)
        self.ui.saveProject.clicked.connect(self.save_project)
        self.ui.saveProject.setDisabled(True)
        self.ui.printReport.clicked.connect(self.print_pdf)
        self.ui.printReport.setDisabled(True)
        self.ui.addTrace.clicked.connect(self.add_trace)
        self.ui.removeTrace.clicked.connect(self.remove_trace)
        self.ui.recalculateEvents.clicked.connect(self.recalculate_events)
        self.canvas = None
        self.raw_features = None
        self.raw_traces = None
        self.busy = Lock()
        self._draw()
        
    def _load_file(self, url):
        '''Load the raw SOR file from provided url into the internal data format'''
        status, d_meta, l_raw_trace = sorparse(url)
        d_meta["url"] = url
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
        filename = os.path.basename(url)
        item = QtGui.QStandardItem(filename)
        item.data = {"meta":d_meta, "trace":a_trace}
        self.project_model.appendRow(item)
        l_traces = []
        l_feature_points = []
        for index in range(self.project_model.rowCount()):
            raw_data = self.project_model.item(index).data
            d_data = prepare_data(raw_data)
            l_traces.append(d_data)
            l_feature_points.append(find_edges(differentiate_data(d_data)))
        self.raw_features = l_feature_points
        self.raw_traces = l_traces
        self._draw()
    
    def _draw(self):
        fig = Figure()
        plt = fig.add_subplot(1,1,1)
        if self.raw_traces:
            for trace_index, d_final_data in enumerate(self.raw_traces):
                plt.plot(d_final_data["trace"][1], d_final_data["trace"][0])
        if self.canvas:
            self.ui.graphLayout.removeWidget(self.canvas)
            self.canvas.close()
            self.ui.graphLayout.removeWidget(self.toolbar)
            self.toolbar.close()
        self.canvas = FigureCanvas(fig)
        self.toolbar = CustomNavigationToolbar(self.canvas, self, coordinates=True)
        self.ui.graphLayout.addWidget(self.canvas)
        self.ui.graphLayout.addWidget(self.toolbar)
    
    def open_project(self):
        if self.busy.locked():
            return
        with self.busy:
            options = QtWidgets.QFileDialog.Options()
            options |= QtWidgets.QFileDialog.DontUseNativeDialog
            fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self,"Open project", "","OpenOTDR Project Files(*.opro);;All Files (*)", options=options)
            if fileName:
                print(fileName)
                # TODO Open project
            
    def save_project(self):
        if self.busy.locked():
            return
        with self.busy:
            options = QtWidgets.QFileDialog.Options()
            options |= QtWidgets.QFileDialog.DontUseNativeDialog
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,"Save project", "","OpenOTDR Project Files(*.opro);;All Files (*)", options=options)
            if fileName:
                print(fileName)
                # TODO Save project
    
    def print_pdf(self):
        if self.busy.locked():
            return
        with self.busy:
            printer = QtPrintSupport.QPrinter()
            dialog = QtPrintSupport.QPrintDialog(printer, self)
            dialog.setModal(True)
            dialog.setWindowTitle("Print Document" )
            dialog.options = (QtPrintSupport.QAbstractPrintDialog.PrintToFile
               | QtPrintSupport.QAbstractPrintDialog.PrintShowPageSize
               | QtPrintSupport.QAbstractPrintDialog.PrintPageRange)
            if dialog.exec_():
                print("printing")
                # TODO Printing
                
    def add_trace(self):
        if self.busy.locked():
            return
        with self.busy:
            options = QtWidgets.QFileDialog.Options()
            options |= QtWidgets.QFileDialog.DontUseNativeDialog
            files, _ = QtWidgets.QFileDialog.getOpenFileNames(self,"Add traces", "","OTDR Trace Files(*.sor);;All Files (*)", options=options)
            if not files:
                return
            for filename in files:
                self._load_file(filename)
                
    def remove_trace(self):
        if self.busy.locked():
            return
        with self.busy:
            if not self.ui.treeView.selectedIndexes():
                return
            indexes = self.ui.treeView.selectedIndexes()
            for index in indexes:
                item = index.model().itemFromIndex(index)
                filename = item.text()
                self.project_model.removeRow(index.row())
            self._draw()
                
    def recalculate_events(self):
        if self.busy.locked():
            return
        with self.busy:
            if not self.raw_features:
                return
            d_events = {}
            for trace_features in self.raw_features:
                for index, feature in enumerate(trace_features[2]):
                    feature_position = int(feature)
                    if feature_position not in d_events:
                        d_events[feature_position] = {
                            "indexes": []
                            }
                    d_events[feature_position]["indexes"].append(trace_features[0][index])
            self.events_model.clear()
            self.events_model.setHorizontalHeaderLabels(['Event', 'Distance (km)', 'Loss (dB)', 'Dispersion factor', 'Description'])
            for position, meta_data in d_events.items():
                current_row = self.events_model.rowCount()
                self.events_model.insertRow(current_row)
                event_position = QtGui.QStandardItem()
                event_position.setText(str(position))
                event_position.setEditable(False)
                self.events_model.setItem(current_row, 1, event_position)
                start_values = []
                for trace in self.raw_traces:
                    for i in meta_data["indexes"]:
                        start_index = max(0,i-window_len)
                        start_values.append(trace["trace"][0][start_index])
                end_values = []
                for trace in self.raw_traces:
                    for i in meta_data["indexes"]:
                        end_index = min(len(trace["trace"][0])-1,i+window_len)
                        end_values.append(trace["trace"][0][end_index])
                average_start = sum(start_values)/len(start_values)
                average_end = sum(end_values)/len(end_values)
                loss = average_start - average_end
                event_loss = QtGui.QStandardItem()
                event_loss.setText(str(loss))
                event_loss.setEditable(False)
                self.events_model.setItem(current_row, 2, event_loss)
                difference_start = max(start_values) - min(start_values)
                difference_end = max(end_values) - min(end_values)
                dispersion_factor = round(max(difference_end/difference_start, difference_start/difference_end))
                event_dispersion = QtGui.QStandardItem()
                event_dispersion.setText(str(dispersion_factor))    
                event_dispersion.setEditable(False)
                self.events_model.setItem(current_row, 3, event_dispersion)
                event_type = QtGui.QStandardItem()
                event_type.setEditable(True)
                self.events_model.setItem(current_row, 0, event_type)
            self.events_model.sort(1)
                
                

            

app = QtWidgets.QApplication(sys.argv)

my_mainWindow = MainWindow()
my_mainWindow.setWindowTitle("OpenOTDR")
my_mainWindow.show()

sys.exit(app.exec_())
