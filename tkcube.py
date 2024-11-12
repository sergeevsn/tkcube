import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading

from utils import *

PROJECT_TITLE = 'TK CUBE version 0.1'
DEFAULT_CMAP = 'gray'
START_GEOMETRY = '800x800'
DEFAULT_HEADER_BYTES = [181, 185, 189, 193]

class ScanSegyThread(threading.Thread):
    def __init__(self, filename, start_bytes, progress_callback, finished_callback):
        super().__init__()
        self.filename = filename
        self.start_bytes = start_bytes
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback

    def run(self):
        cdp_x, cdp_y, inlines, xlines, samples, dt, smin, smax = scan_segy(self.filename, self.start_bytes, self.progress_callback)
        self.finished_callback(cdp_x, cdp_y, inlines, xlines, samples, dt, smin, smax)

class GetCubeThread(threading.Thread):
    def __init__(self, filename, start_bytes, u_inl, u_xln, samples, smin, smax, progress_callback, finished_callback):
        super().__init__()
        self.filename = filename
        self.start_bytes = start_bytes
        self.uinl = u_inl
        self.uxln = u_xln
        self.samples = samples
        self.smin = smin
        self.smax = smax
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback

    def run(self):
        cube = get_cube(self.filename, self.start_bytes, self.uinl, self.uxln, self.samples, self.smin, self.smax, self.progress_callback)
        self.finished_callback(cube)

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(PROJECT_TITLE)
        self.geometry(START_GEOMETRY)
        self.start_bytes = HeaderStartBytes(*DEFAULT_HEADER_BYTES)
         # Переменная для хранения названия файла
        self.current_file_name = "Choose a file to show..."

        self.create_menu()
        self.create_central_widget()
        self.create_plot_canvas()
        self.create_index_slider()
        self.initialize_data_variables()

       
    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        fileMenu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='File', menu=fileMenu)
        fileMenu.add_command(label='Open', command=self.open_file)
        fileMenu.add_command(label='Exit', command=self.quit)

        mapMenu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Plot', menu=mapMenu)
        mapMenu.add_command(label='X/Y/Z Map', command=self.show_xy_map)
        mapMenu.add_command(label='Inline Section', command=self.show_inline_section)
        mapMenu.add_command(label='Crossline Section', command=self.show_crossline_section)
        mapMenu.add_command(label='Time Slice', command=self.show_time_slice)

        segyMenu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='SEGY', menu=segyMenu)
        segyMenu.add_command(label='Reading headers', command=self.show_headers_dialog)

    def create_central_widget(self):
        self.frame = tk.Frame(self)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Добавляем Label для отображения названия файла
        self.file_label = tk.Label(self.frame, text=self.current_file_name, font=("Arial", 12), bg="lightgray", fg="black")
        self.file_label.pack(side=tk.TOP, pady=3)

    def create_plot_canvas(self):
        self.figure = plt.Figure()
        self.canvas = FigureCanvasTkAgg(self.figure, self.frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_index_slider(self):
        self.index_slider = tk.Scale(self.frame, from_=0, to=100, orient=tk.HORIZONTAL, label="TIME")
        self.index_slider.pack(fill=tk.X)
        self.index_slider.bind("<ButtonRelease-1>", self.update_plot_with_slider)

    def initialize_data_variables(self):
        self.cdp_x = None
        self.cdp_y = None
        self.inline = None
        self.crossline = None
        self.dt = None
        self.cube = None
        self.unique_inlines = None
        self.unique_crosslines = None
        self.samples = None
        self.current_mode = None

    def open_file(self):
        filename = filedialog.askopenfilename(filetypes=[("SEG-Y Files", "*.segy *.sgy"), ("All Files", "*.*")])
        if filename:
            self.current_file_name = filename  # Обновляем название файла
            self.file_label.config(text=self.current_file_name)  # Обновляем текст Label
            self.show_progress_dialog("Scanning SEG-Y headers...", self.scan_segy, filename)

    def show_progress_dialog(self, title, operation, *args):
        self.progress_dialog = tk.Toplevel(self)
        self.progress_dialog.title(title)
        self.progress_dialog.overrideredirect(True)
        self.center_window(self.progress_dialog, 300, 100)

        self.progress_label = tk.Label(self.progress_dialog, text=title)
        self.progress_label.pack(pady=10)

        self.progress_bar = ttk.Progressbar(self.progress_dialog, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.progress_bar.pack(pady=10)

        self.progress_value_label = tk.Label(self.progress_dialog, text="0%")
        self.progress_value_label.pack()

        def progress_callback(value):
            self.progress_bar['value'] = value
            self.progress_value_label.config(text=f"{round(value)}%")
            self.progress_dialog.update_idletasks()

        operation(*args, progress_callback)

    def center_window(self, window, width, height):
        parent_width = self.winfo_width()
        parent_height = self.winfo_height()
        x_position = (parent_width // 2) - (width // 2)
        y_position = (parent_height // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x_position}+{y_position}")

    def scan_segy(self, filename, progress_callback):
        def finished_callback1(cdp_x, cdp_y, inline, crossline, dt, samples, smin, smax):
            self.cdp_x = cdp_x
            self.cdp_y = cdp_y
            self.inline = inline
            self.crossline = crossline
            self.dt = dt
            self.unique_inlines = np.unique(inline)
            self.unique_crosslines = np.unique(crossline)
            self.samples = samples
            self.progress_bar['value'] = 0
            self.progress_dialog.title("Reading samples...")
            self.progress_label.config(text="Reading samples...")
            self.show_xy_map()
            self.get_cube(filename, smin, smax, progress_callback)

        self.scan_thread = ScanSegyThread(filename, self.start_bytes, progress_callback, finished_callback1)
        self.scan_thread.start()

    def get_cube(self, filename, smin, smax, progress_callback):
        def finished_callback2(cube):
            self.cube = cube
            self.progress_dialog.destroy()
            self.show_time_slice()

        self.getcube_thread = GetCubeThread(filename, self.start_bytes, self.unique_inlines, self.unique_crosslines, self.samples, smin, smax, progress_callback, finished_callback2)
        self.getcube_thread.start()

    def show_xy_map(self):
        self.current_mode = 'xy_map'
        if self.cdp_x is None:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.scatter(self.cdp_x, self.cdp_y, c='black', s=1)
        ax.set_xlabel('CDP X')
        ax.set_ylabel('CDP Y')
        ax.set_title('X/Y Map')
        ax.ticklabel_format(useOffset=False, style='plain')
        self.canvas.draw()

    def show_inline_section(self, update=False):
        if self.cube is None:
            return

        self.current_mode = 'inline_section'
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        index = self.index_slider.get() if update else self.unique_inlines[len(self.unique_inlines)//2]
        self.configure_slider(self.unique_inlines, index, "INLINE")

        inl_idx = np.where(self.unique_inlines == index)
        ax.imshow(self.cube[inl_idx].T, aspect='auto', cmap=DEFAULT_CMAP, extent=[min(self.unique_crosslines), max(self.unique_crosslines), max(self.samples)*self.dt, 0])
        ax.set_xlabel('CROSSLINE')
        ax.set_ylabel('Time, ms')
        ax.set_title(f'Inline Section {index}')
        self.canvas.draw()

    def show_crossline_section(self, update=False):
        if self.cube is None:
            return

        self.current_mode = 'crossline_section'
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        index = self.index_slider.get() if update else self.unique_crosslines[len(self.unique_crosslines)//2]
        self.configure_slider(self.unique_crosslines, index, "CROSSLINE")

        xln_idx = np.where(self.unique_crosslines == index)[0]
        ax.imshow(self.cube[:, xln_idx].squeeze().T, aspect='auto', cmap=DEFAULT_CMAP, extent=[min(self.unique_inlines), max(self.unique_inlines), max(self.samples)*self.dt, 0])
        ax.set_xlabel('INLINE')
        ax.set_ylabel('Time, ms')
        ax.set_title(f'Crossline Section {index}')
        self.canvas.draw()

    def show_time_slice(self, update=False):
        if self.cube is None:
            return

        self.current_mode = 'time_slice'
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        index = self.index_slider.get() if update else self.samples[len(self.samples)//2]*self.dt
        self.configure_slider(self.samples*self.dt, index, "TIME")

        smp_idx = np.where(self.samples == index//self.dt)[0]
        ax.imshow(self.cube[:, :, smp_idx], aspect='auto', cmap=DEFAULT_CMAP, extent=[min(self.unique_crosslines), max(self.unique_crosslines), max(self.unique_inlines), min(self.unique_inlines)])
        ax.set_xlabel('CROSSLINE')
        ax.set_ylabel('INLINE')
        ax.set_title(f'Time Slice {index} ms')
        ax.invert_yaxis()
        self.canvas.draw()

    def configure_slider(self, values, index, label):
        self.index_slider.config(from_=min(values), to=max(values), resolution=1, label=label)
        self.index_slider.set(index)        

    def update_plot_with_slider(self, event):
        if self.current_mode == 'inline_section':
            self.show_inline_section(update=True)
        elif self.current_mode == 'crossline_section':
            self.show_crossline_section(update=True)
        elif self.current_mode == 'time_slice':
            self.show_time_slice(update=True)

    def show_headers_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title('Headers Start Bytes')

        labels = ['CDP X', 'CDP Y', 'Inline', 'Crossline']
        default_values = DEFAULT_HEADER_BYTES
        entries = []

        for label, start in zip(labels, default_values):
            tk.Label(dialog, text=f'{label}:').pack()
            start_edit = tk.Entry(dialog)
            start_edit.insert(0, str(start))
            start_edit.pack()
            entries.append(start_edit)

        def on_dialog_close():
            values = [int(entry.get()) for entry in entries]
            self.start_bytes = HeaderStartBytes(*values)
            dialog.destroy()

        button = tk.Button(dialog, text='OK', command=on_dialog_close)
        button.pack()

        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)

if __name__ == '__main__':
    mainWindow = MainWindow()
    mainWindow.mainloop()