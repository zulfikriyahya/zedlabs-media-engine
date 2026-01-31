import sys
import os
import platform
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QTextEdit, QRadioButton, QButtonGroup, QFileDialog,
                            QProgressBar, QGroupBox, QCheckBox, QTableWidget,
                            QTableWidgetItem, QHeaderView, QFrame, QGridLayout,
                            QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QTextCursor
import yt_dlp
import pandas as pd
import requests
import concurrent.futures
import time

def get_ffmpeg_path():
    filename = 'lib/ffmpeg.exe' if platform.system() == 'Windows' else 'lib/ffmpeg'
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


CHECK_URL = "https://www.google.com"
TIMEOUT = 8
MAX_THREADS = 10


class ProxyTestThread(QThread):
    progress = pyqtSignal(int, int)
    result = pyqtSignal(list)
    log = pyqtSignal(str)
    
    def __init__(self, proxies):
        super().__init__()
        self.proxies = proxies
        
    def check_proxy(self, proxy):
        proxies_dict = {"http": proxy, "https": proxy}
        try:
            start = time.time()
            response = requests.get(CHECK_URL, proxies=proxies_dict, timeout=TIMEOUT,
                                    headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code == 200:
                latency = (time.time() - start) * 1000
                return {'proxy': proxy, 'latency': latency, 'status': 'OK'}
        except:
            pass
        return {'proxy': proxy, 'latency': 9999, 'status': 'FAIL'}
    
    def run(self):
        self.log.emit(f"[NET_SCAN] Probing {len(self.proxies)} nodes...")
        valid_proxies = []
        checked = 0
        total = len(self.proxies)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = {executor.submit(self.check_proxy, proxy): proxy for proxy in self.proxies}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                checked += 1
                self.progress.emit(checked, total)
                if result['status'] == 'OK':
                    valid_proxies.append(result)
        
        valid_proxies.sort(key=lambda x: x['latency'])
        self.log.emit(f"[NET_OK] {len(valid_proxies)}/{total} nodes online")
        self.result.emit(valid_proxies)

class DownloadThread(QThread):
    progress = pyqtSignal(str)
    progress_percent = pyqtSignal(int)  
    finished = pyqtSignal(bool, str)
    
    def __init__(self, url, folder, only_audio, quality_preset, proxies=None, is_playlist=False):
        super().__init__()
        self.url = url
        self.folder = folder
        self.only_audio = only_audio
        self.quality_preset = quality_preset
        self.proxies = proxies if proxies else []
        self.is_playlist = is_playlist
        self._is_cancelled = False
        
    def cancel(self):
        """Method untuk membatalkan download"""
        self._is_cancelled = True
        self.progress.emit("[CANCEL] Aborting download...")
        
    def progress_hook(self, d):
        if self._is_cancelled:
            raise Exception("Download cancelled by user")
            
        if d['status'] == 'downloading':
            try:
                
                percent_str = d.get('_percent_str', '0%').strip()
                percent_val = float(percent_str.replace('%', ''))
                self.progress_percent.emit(int(percent_val))
                
                p = percent_str
                s = d.get('_speed_str', 'N/A').strip()
                e = d.get('_eta_str', 'N/A').strip()
                self.progress.emit(f">> DL: {p} | SPD: {s} | ETA: {e}")
            except: 
                pass
        elif d['status'] == 'finished':
            self.progress_percent.emit(100)
            self.progress.emit(">> PROCESSING FILE...")
    
    def download_with_proxy(self, proxy_index=0):
        if self._is_cancelled:
            return False
            
        try:
            os.makedirs(self.folder, exist_ok=True)
            current_proxy = self.proxies[proxy_index]['proxy'] if self.proxies and proxy_index < len(self.proxies) else None
            
            if current_proxy: self.progress.emit(f">> PROXY: {current_proxy}")
            
            ffmpeg_path = get_ffmpeg_path() 

            opts = {
                'outtmpl': os.path.join(self.folder, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'quiet': True, 'no_warnings': True, 'retries': 5,
                'noplaylist': not self.is_playlist,
                'ffmpeg_location': ffmpeg_path
            }
            if current_proxy: opts['proxy'] = current_proxy
            
            # KONFIGURASI BERDASARKAN QUALITY PRESET
            if self.only_audio:
                # Audio presets
                if self.quality_preset == "MAXIMUM":
                    opts.update({
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3'
                        }]
                    })
                    self.progress.emit("[QUALITY] Audio: Best Available (No Limit)")
                    
                elif self.quality_preset == "BALANCED":
                    opts.update({
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '320'
                        }]
                    })
                    self.progress.emit("[QUALITY] Audio: 320kbps MP3 (High Quality)")
                    
                elif self.quality_preset == "ECONOMY":
                    opts.update({
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192'
                        }]
                    })
                    self.progress.emit("[QUALITY] Audio: 192kbps MP3 (Standard)")
                    
            else:
                # Video presets
                if self.quality_preset == "MAXIMUM":
                    opts.update({
                        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                        'merge_output_format': 'mp4'
                    })
                    self.progress.emit("[QUALITY] Video: Best Available (No Limit)")
                    
                elif self.quality_preset == "BALANCED":
                    opts.update({
                        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best',
                        'merge_output_format': 'mp4'
                    })
                    self.progress.emit("[QUALITY] Video: 1080p Max (Full HD)")
                    
                elif self.quality_preset == "ECONOMY":
                    opts.update({
                        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best',
                        'merge_output_format': 'mp4'
                    })
                    self.progress.emit("[QUALITY] Video: 720p Max (HD)")
            
            if self.is_playlist:
                opts['outtmpl'] = os.path.join(self.folder, '%(playlist_title)s/%(title)s.%(ext)s')
                opts['ignoreerrors'] = True
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url])
            return True
        except Exception as e:
            if self._is_cancelled:
                return False
            self.progress.emit(f"[ERR] {str(e)[:60]}")
            return False
    
    def run(self):
        attempts = 3 if not self.proxies else min(len(self.proxies), 5)
        for i in range(attempts):
            if self._is_cancelled:
                self.finished.emit(False, "[CANCELLED] OPERATION CANCELLED BY USER")
                return
                
            if self.download_with_proxy(i):
                self.finished.emit(True, "[COMPLETE] OPERATION SUCCESSFUL")
                return
            if i < attempts - 1:
                self.progress.emit(f"[RETRY] Switching node {i+2}/{attempts}...")
                time.sleep(1)
        self.finished.emit(False, "[FAILED] OPERATION ABORTED")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZEDLABS.ID :: MEDIA DOWNLOADER ENGINE")
        
        # Dapatkan ukuran layar
        screen = QApplication.primaryScreen().geometry()
        
        # Set minimum size agar tidak terlalu kecil
        self.setMinimumSize(900, 700)
        
        # Fullscreen mode dengan margin kecil (opsional)
        margin = 0  # Set ke 0 untuk fullscreen penuh, atau 50 untuk ada margin
        self.setGeometry(
            screen.x() + margin,
            screen.y() + margin,
            screen.width() - (margin * 2),
            screen.height() - (margin * 2)
        )
        
        # Atau gunakan showMaximized() untuk mode maximize window
        # self.showMaximized()
        
        self.proxies = []
        self.valid_proxies = []
        self.dt = None  
        
        self.init_ui()
        self.apply_theme()
        
    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #050505; color: #00FF00; font-family: 'Consolas', monospace; font-size: 9pt; }
            /* GROUPS */
            QGroupBox {
                border: 1px solid #333;
                background-color: #080808;
                margin-top: 20px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: #00FF00;
                color: #000;
                font-weight: 900;
                text-transform: uppercase;
            }
            /* INPUTS */
            QLineEdit {
                background-color: #0F0F0F;
                border: 1px solid #333;
                color: #FFF;
                padding: 6px;
                font-family: 'Consolas';
            }
            QLineEdit:focus { border: 1px solid #00FF00; background-color: #111; }
            /* COMBOBOX */
            QComboBox {
                background-color: #0F0F0F;
                border: 1px solid #333;
                color: #FFF;
                padding: 6px;
                font-family: 'Consolas';
                font-weight: bold;
            }
            QComboBox:hover { border: 1px solid #00FF00; }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { 
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #00FF00;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #0F0F0F;
                border: 1px solid #00FF00;
                selection-background-color: #003300;
                color: #FFF;
            }
            /* BUTTONS */
            QPushButton {
                background-color: #000;
                color: #00FF00;
                border: 1px solid #00FF00;
                padding: 8px;
                font-weight: bold;
                text-transform: uppercase;
            }
            QPushButton:hover { background-color: #00FF00; color: #000; }
            QPushButton:pressed { background-color: #008800; }
            QPushButton:disabled { border-color: #444; color: #444; }
            /* TABLE */
            QTableWidget {
                background-color: #080808;
                border: 1px solid #333;
                gridline-color: #222;
                color: #DDD;
                font-size: 8pt;
            }
            QHeaderView::section {
                background-color: #111;
                color: #00FF00;
                border: none;
                padding: 4px;
                font-weight: bold;
            }
            QTableWidget::item:selected { background-color: #003300; color: #FFF; }
            /* LOGS */
            QTextEdit {
                background-color: #000;
                border: 1px solid #333;
                color: #00FF00;
                font-size: 8pt;
                padding: 5px;
            }
            /* PROGRESS */
            QProgressBar {
                border: 1px solid #333;
                background-color: #000;
                text-align: center;
                height: 15px;
                color: #FFF;
            }
            QProgressBar::chunk { background-color: #00FF00; }
            /* CONTROLS */
            QCheckBox, QRadioButton { spacing: 8px; font-weight: bold; }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 14px; height: 14px;
                border: 1px solid #00FF00;
                background: #000;
            }
            QCheckBox::indicator:checked, QRadioButton::indicator:checked { background: #00FF00; }
        """)
        
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        root_layout = QVBoxLayout(main_widget)
        root_layout.setSpacing(15)
        root_layout.setContentsMargins(20, 20, 20, 20)
        
        ascii_banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║   ███████╗███████╗██████╗ ██╗      █████╗ ██████╗ ███████╗     ██╗██████╗    ║
║   ╚══███╔╝██╔════╝██╔══██╗██║     ██╔══██╗██╔══██╗██╔════╝     ██║██╔══██╗   ║
║     ███╔╝ █████╗  ██║  ██║██║     ███████║██████╔╝███████╗     ██║██║  ██║   ║
║    ███╔╝  ██╔══╝  ██║  ██║██║     ██╔══██║██╔══██╗╚════██║     ██║██║  ██║   ║
║   ███████╗███████╗██████╔╝███████╗██║  ██║██████╔╝███████║ ██╗ ██║██████╔╝   ║
║   ╚══════╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝ ╚═╝ ╚═╝╚═════╝    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║   >> SYSTEM : MEDIA DOWNLOADER ENGINE | VER : 2.0.0 | DEV : YAHYA ZULFIKRI   ║
║                                                                              ║
║          UNIVERSAL VIDEO & AUDIO EXTRACTION ENGINE + QUALITY CONTROL         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        lbl_header = QLabel(ascii_banner)
        lbl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_header.setStyleSheet("font-family: 'Consolas', monospace; font-size: 7pt; color: #00FF00; margin-bottom: 5px;")
        root_layout.addWidget(lbl_header)
        
        body_layout = QHBoxLayout()
        body_layout.setSpacing(20)
        
        # LEFT COLUMN
        left_col = QVBoxLayout()
        
        # TARGET CONFIGURATION
        grp_target = QGroupBox("TARGET CONFIGURATION")
        grp_target.setMinimumHeight(135)  # Set tinggi konsisten
        l_target = QVBoxLayout()
        l_target.setSpacing(10)
        
        self.url_edit = QLineEdit()
        self.url_edit.setMinimumHeight(28)
        self.url_edit.setPlaceholderText("Paste URL Here...")
        self.url_edit.textChanged.connect(self.detect_playlist)
        l_target.addWidget(QLabel(">> TARGET URL:"))
        l_target.addWidget(self.url_edit)
        
        h_folder = QHBoxLayout()
        self.folder_edit = QLineEdit("")
        self.folder_edit.setMinimumHeight(28)
        self.folder_edit.setPlaceholderText("Select Output Path...")
        btn_browse = QPushButton("➭➭➭")
        btn_browse.setFixedWidth(40)
        btn_browse.setFixedHeight(28)
        btn_browse.clicked.connect(self.browse_folder)
        h_folder.addWidget(self.folder_edit)
        h_folder.addWidget(btn_browse)
        l_target.addWidget(QLabel(">> OUTPUT DIRECTORY:"))
        l_target.addLayout(h_folder)
        
        grp_target.setLayout(l_target)
        left_col.addWidget(grp_target)
        
        # OPERATION MODE
        grp_mode = QGroupBox("OPERATION MODE")
        grp_mode.setMinimumHeight(105)  # Set tinggi konsisten
        l_mode = QVBoxLayout()
        l_mode.setSpacing(10)
        
        h_radios = QHBoxLayout()
        self.mode_group = QButtonGroup()
        self.r_vid = QRadioButton("VIDEO (MP4)")
        self.r_aud = QRadioButton("AUDIO (MP3)")
        self.r_vid.setChecked(True)
        self.mode_group.addButton(self.r_vid)
        self.mode_group.addButton(self.r_aud)
        h_radios.addWidget(self.r_vid)
        h_radios.addWidget(self.r_aud)
        l_mode.addLayout(h_radios)
        
        self.chk_playlist = QCheckBox("FORCE BATCH / PLAYLIST MODE")
        self.chk_playlist.setStyleSheet("color: #FFFF00;")
        l_mode.addWidget(self.chk_playlist)
        
        grp_mode.setLayout(l_mode)
        left_col.addWidget(grp_mode)
        
        # QUALITY PRESET - NEW SECTION
        grp_quality = QGroupBox("QUALITY PRESET")
        grp_quality.setMinimumHeight(140)  # Set tinggi konsisten
        l_quality = QVBoxLayout()
        l_quality.setSpacing(8)
        
        l_quality.addWidget(QLabel(">> SELECT QUALITY LEVEL:"))
        
        self.quality_combo = QComboBox()
        self.quality_combo.setMinimumHeight(28)  # Tinggi combobox sama dengan input lain
        self.quality_combo.addItem("MAXIMUM - Best Available (No Limit)")
        self.quality_combo.addItem("BALANCED - 1080p / 320kbps (Recommended)")
        self.quality_combo.addItem("ECONOMY - 720p / 192kbps (Save Space)")
        self.quality_combo.setCurrentIndex(1)  # Default: BALANCED
        self.quality_combo.currentIndexChanged.connect(self.on_quality_changed)
        l_quality.addWidget(self.quality_combo)
        
        # Info label
        self.quality_info = QLabel()
        self.quality_info.setWordWrap(True)
        self.quality_info.setMinimumHeight(45)  # Tinggi info box
        self.quality_info.setStyleSheet("color: #888; font-size: 7pt; padding: 5px;")
        self.update_quality_info()
        l_quality.addWidget(self.quality_info)
        
        grp_quality.setLayout(l_quality)
        left_col.addWidget(grp_quality)
        
        # NETWORK ROUTING
        grp_proxy = QGroupBox("NETWORK ROUTING")
        grp_proxy.setMinimumHeight(160)  # Set tinggi konsisten
        l_proxy = QVBoxLayout()
        l_proxy.setSpacing(10)
        
        h_pfile = QHBoxLayout()
        self.proxy_edit = QLineEdit("")
        self.proxy_edit.setMinimumHeight(28)
        self.proxy_edit.setPlaceholderText("Select Proxy File...")
        btn_p_browse = QPushButton("➭➭➭")
        btn_p_browse.setFixedWidth(40)
        btn_p_browse.setFixedHeight(28)
        btn_p_browse.clicked.connect(self.browse_proxy_file)
        h_pfile.addWidget(self.proxy_edit)
        h_pfile.addWidget(btn_p_browse)
        l_proxy.addWidget(QLabel(">> PROXY LIST (CSV):"))
        l_proxy.addLayout(h_pfile)
        
        self.btn_scan = QPushButton("SCAN NODES")
        self.btn_scan.setMinimumHeight(28)
        self.btn_scan.clicked.connect(self.load_proxies)
        l_proxy.addWidget(self.btn_scan)
        
        self.chk_use_proxy = QCheckBox("ENABLE AUTO-ROTATION")
        l_proxy.addWidget(self.chk_use_proxy)
        
        grp_proxy.setLayout(l_proxy)
        left_col.addWidget(grp_proxy)
        
        left_col.addStretch() 
        
        # RIGHT COLUMN
        right_col = QVBoxLayout()
        
        # NODE STATUS MONITOR
        grp_monitor = QGroupBox("NODE STATUS MONITOR")
        l_monitor = QVBoxLayout()
        
        self.proxy_bar = QProgressBar()
        self.proxy_bar.setVisible(False)
        l_monitor.addWidget(self.proxy_bar)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "NODE ADDRESS", "LATENCY"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(180)  # Minimum height agar tidak terlalu kecil
        l_monitor.addWidget(self.table)
        
        grp_monitor.setLayout(l_monitor)
        right_col.addWidget(grp_monitor)
        
        # SYSTEM KERNEL LOG
        grp_log = QGroupBox("SYSTEM KERNEL LOG")
        l_log = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)  # Minimum height agar log tetap terlihat
        l_log.addWidget(self.log_text)
        grp_log.setLayout(l_log)
        right_col.addWidget(grp_log)
        
        body_layout.addLayout(left_col, 3)  # Proporsi 3
        body_layout.addLayout(right_col, 7)  # Proporsi 7 untuk area yang lebih luas 
        
        root_layout.addLayout(body_layout)
        
        # DOWNLOAD PROGRESS
        grp_dl_progress = QGroupBox("DOWNLOAD PROGRESS")
        l_dl_progress = QVBoxLayout()
        
        self.download_bar = QProgressBar()
        self.download_bar.setFormat("%p% - Ready")
        self.download_bar.setValue(0)
        self.download_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #00FF00;
                background-color: #000;
                text-align: center;
                height: 25px;
                color: #00FF00;
                font-weight: bold;
            }
            QProgressBar::chunk { background-color: #00FF00; }
        """)
        l_dl_progress.addWidget(self.download_bar)
        
        grp_dl_progress.setLayout(l_dl_progress)
        root_layout.addWidget(grp_dl_progress)

        # FOOTER
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)
        
        self.btn_run = QPushButton(">> INITIALIZE DOWNLOAD SEQUENCE <<")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setStyleSheet("""
            QPushButton { font-size: 14pt; background-color: #001100; border: 2px solid #00FF00; letter-spacing: 3px; }
            QPushButton:hover { background-color: #00FF00; color: #000; }
        """)
        self.btn_run.clicked.connect(self.start_download)
        
        self.btn_cancel = QPushButton("✖ ABORT")
        self.btn_cancel.setFixedHeight(50)
        self.btn_cancel.setFixedWidth(120)
        self.btn_cancel.setVisible(False)  
        self.btn_cancel.setStyleSheet("""
            QPushButton { 
                font-size: 12pt; 
                background-color: #110000; 
                border: 2px solid #FF0000; 
                color: #FF0000;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #FF0000; color: #000; }
            QPushButton:disabled { border-color: #440000; color: #440000; }
        """)
        self.btn_cancel.clicked.connect(self.cancel_download)
        
        footer_layout.addWidget(self.btn_run, 5)
        footer_layout.addWidget(self.btn_cancel, 1)
        
        footer_wrapper = QVBoxLayout()
        footer_wrapper.addLayout(footer_layout)
        
        lbl_info = QLabel("ZEDLABS.ID SECURITY SYSTEMS | ALL RIGHTS RESERVED")
        lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_info.setStyleSheet("color: #444; font-size: 7pt; margin-top: 5px;")
        footer_wrapper.addWidget(lbl_info)
        
        root_layout.addLayout(footer_wrapper)

        self.log("SYSTEM INITIALIZED...")
        self.log("READY FOR INPUT.")

    def showEvent(self, event):
        """Override showEvent untuk maximize window saat pertama kali ditampilkan"""
        super().showEvent(event)
        if not hasattr(self, '_first_show_done'):
            self.showMaximized()
            self._first_show_done = True

    def on_quality_changed(self):
        """Update info ketika quality preset berubah"""
        self.update_quality_info()
        preset = self.get_quality_preset()
        self.log(f"[QUALITY] Preset changed to: {preset}")

    def update_quality_info(self):
        """Update label info sesuai quality preset"""
        index = self.quality_combo.currentIndex()
        
        if index == 0:  # MAXIMUM
            info = "Video: Up to 4K/8K | Audio: Best available bitrate\nFile Size: VERY LARGE | Speed: SLOWEST"
        elif index == 1:  # BALANCED
            info = "Video: Max 1080p (Full HD) | Audio: 320kbps MP3\nFile Size: MEDIUM | Speed: FAST (Recommended)"
        else:  # ECONOMY
            info = "Video: Max 720p (HD) | Audio: 192kbps MP3\nFile Size: SMALL | Speed: VERY FAST"
        
        self.quality_info.setText(info)

    def get_quality_preset(self):
        """Mendapatkan quality preset yang dipilih"""
        index = self.quality_combo.currentIndex()
        presets = ["MAXIMUM", "BALANCED", "ECONOMY"]
        return presets[index]

    def detect_playlist(self):
        if any(x in self.url_edit.text().lower() for x in ["playlist", "list="]):
            if not self.chk_playlist.isChecked():
                self.chk_playlist.setChecked(True)
                self.log("[SYS] Playlist detected. Mode updated.")

    def browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Output Dir")
        if d: self.folder_edit.setText(d)

    def browse_proxy_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Proxy CSV", "", "*.csv")
        if f: self.proxy_edit.setText(f)

    def log(self, msg):
        t = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{t}] {msg}")
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    def load_proxies(self):
        try:
            path = self.proxy_edit.text()
            self.log(f"[SYS] Loading {path}...")
            df = pd.read_csv(path)
            raw = df.iloc[:,0].dropna().astype(str).str.strip().tolist() if 'ip_address' not in df else df['ip_address'].dropna().astype(str).tolist()
            proxies = [f"http://{p}" if not p.startswith(('http','socks')) else p for p in raw]
            
            self.proxy_bar.setVisible(True)
            self.proxy_bar.setMaximum(len(proxies))
            self.btn_scan.setEnabled(False)
            
            self.pt = ProxyTestThread(list(set(proxies)))
            self.pt.progress.connect(lambda c, t: self.proxy_bar.setValue(c))
            self.pt.result.connect(self.on_scan_done)
            self.pt.log.connect(self.log)
            self.pt.start()
        except Exception as e:
            self.log(f"[ERR] {e}")

    def on_scan_done(self, valid):
        self.valid_proxies = valid
        self.proxy_bar.setVisible(False)
        self.btn_scan.setEnabled(True)
        
        self.table.setRowCount(0)
        for row, p in enumerate(valid):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(f"{row+1:02d}"))
            self.table.setItem(row, 1, QTableWidgetItem(p['proxy']))
            lat = QTableWidgetItem(f"{p['latency']:.0f} ms")
            lat.setForeground(QColor("#00FF00" if p['latency']<500 else "#FFFF00"))
            self.table.setItem(row, 2, lat)
            
        if valid: 
            self.chk_use_proxy.setChecked(True)
            self.log(f"[SYS] Routing table updated with {len(valid)} nodes.")

    def update_download_progress(self, percent):
        """Update progress bar download"""
        self.download_bar.setValue(percent)
        self.download_bar.setFormat(f"%p% - Downloading...")

    def start_download(self):
        url = self.url_edit.text().strip()
        if not url: 
            return self.log("[ERR] Target URL required.")
        
        self.download_bar.setValue(0)
        self.download_bar.setFormat("0% - Initializing...")
        
        proxies = self.valid_proxies if self.chk_use_proxy.isChecked() else []
        quality_preset = self.get_quality_preset()
        
        self.btn_run.setEnabled(False)
        self.btn_run.setText(">> EXECUTING... <<")
        self.btn_run.setStyleSheet("background-color: #330000; border-color: #550000; color: #AA0000;")
        
        self.btn_cancel.setVisible(True)
        
        self.dt = DownloadThread(
            url, 
            self.folder_edit.text(), 
            self.r_aud.isChecked(), 
            quality_preset,
            proxies, 
            self.chk_playlist.isChecked()
        )
        self.dt.progress.connect(self.log)
        self.dt.progress_percent.connect(self.update_download_progress)  
        self.dt.finished.connect(self.on_dl_finished)
        self.dt.start()

    def cancel_download(self):
        """Method untuk membatalkan download"""
        if self.dt and self.dt.isRunning():
            self.log("[USER] Cancellation requested...")
            self.dt.cancel()
            self.btn_cancel.setVisible(False)  
            self.download_bar.setFormat("Cancelling...")

    def on_dl_finished(self, success, msg):
        self.log(msg)
        self.btn_run.setEnabled(True)
        self.btn_run.setText(">> INITIALIZE DOWNLOAD SEQUENCE <<")
        self.btn_run.setStyleSheet("""
            QPushButton { font-size: 14pt; background-color: #001100; border: 2px solid #00FF00; letter-spacing: 3px; }
            QPushButton:hover { background-color: #00FF00; color: #000; }
        """)
        
        self.btn_cancel.setVisible(False)
        
        if success:
            self.download_bar.setValue(100)
            self.download_bar.setFormat("100% - Completed")
        else:
            self.download_bar.setFormat("Failed / Cancelled")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())