import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QRadioButton, QButtonGroup, QFileDialog,
                             QProgressBar, QGroupBox, QCheckBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QFrame, QGridLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QTextCursor
import yt_dlp
import pandas as pd
import requests
import concurrent.futures
import time

# --- KONFIGURASI CONSTANT ---
CHECK_URL = "https://www.google.com"
TIMEOUT = 8
MAX_THREADS = 10

# --- WORKER THREADS (LOGIKA SAMA) ---
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
    finished = pyqtSignal(bool, str)
    
    def __init__(self, url, folder, only_audio, proxies=None, is_playlist=False):
        super().__init__()
        self.url = url
        self.folder = folder
        self.only_audio = only_audio
        self.proxies = proxies if proxies else []
        self.is_playlist = is_playlist
        
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                p = d.get('_percent_str', '0%').strip()
                s = d.get('_speed_str', 'N/A').strip()
                e = d.get('_eta_str', 'N/A').strip()
                self.progress.emit(f">> DL: {p} | SPD: {s} | ETA: {e}")
            except: pass
        elif d['status'] == 'finished':
            self.progress.emit(">> PROCESSING FILE...")
    
    def download_with_proxy(self, proxy_index=0):
        try:
            os.makedirs(self.folder, exist_ok=True)
            current_proxy = self.proxies[proxy_index]['proxy'] if self.proxies and proxy_index < len(self.proxies) else None
            
            if current_proxy: self.progress.emit(f">> PROXY: {current_proxy}")
            
            opts = {
                'outtmpl': os.path.join(self.folder, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'quiet': True, 'no_warnings': True, 'retries': 5,
                'noplaylist': not self.is_playlist,
            }
            if current_proxy: opts['proxy'] = current_proxy
            
            if self.only_audio:
                opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]})
            else:
                opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'merge_output_format': 'mp4'})
            
            if self.is_playlist:
                opts['outtmpl'] = os.path.join(self.folder, '%(playlist_title)s/%(title)s.%(ext)s')
                opts['ignoreerrors'] = True
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url])
            return True
        except Exception as e:
            self.progress.emit(f"[ERR] {str(e)[:60]}")
            return False
    
    def run(self):
        attempts = 3 if not self.proxies else min(len(self.proxies), 5)
        for i in range(attempts):
            if self.download_with_proxy(i):
                self.finished.emit(True, "[COMPLETE] OPERATION SUCCESSFUL")
                return
            if i < attempts - 1:
                self.progress.emit(f"[RETRY] Switching node {i+2}/{attempts}...")
                time.sleep(1)
        self.finished.emit(False, "[FAILED] OPERATION ABORTED")

# --- MAIN UI ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZEDLABS.ID :: MEDIA DOWNLOADER ENGINE")
        self.setFixedSize(640, 720) # Lebar 640px, Tinggi 720px (Fixed)
        
        self.proxies = []
        self.valid_proxies = []
        
        self.init_ui()
        self.apply_theme()
        
    def apply_theme(self):
        # TEMA: Cyberpunk Terminal / Military Dashboard
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
        # Layout Utama: Vertikal (Header -> Body -> Footer)
        root_layout = QVBoxLayout(main_widget)
        root_layout.setSpacing(15)
        root_layout.setContentsMargins(20, 20, 20, 20)

        # 1. HEADER (ASCII ART)
        ascii_banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║   ███████╗███████╗██████╗ ██╗      █████╗ ██████╗ ███████╗     ██╗██████╗    ║
║   ╚══███╔╝██╔════╝██╔══██╗██║     ██╔══██╗██╔══██╗██╔════╝     ██║██╔══██╗   ║
║     ███╔╝ █████╗  ██║  ██║██║     ███████║██████╔╝███████╗     ██║██║  ██║   ║
║    ███╔╝  ██╔══╝  ██║  ██║██║     ██╔══██║██╔══██╗╚════██║     ██║██║  ██║   ║
║   ███████╗███████╗██████╔╝███████╗██║  ██║██████╔╝███████║ ██╗ ██║██████╔╝   ║
║   ╚══════╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝ ╚═╝ ╚═╝╚═════╝    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║   >> SYSTEM : MEDIA DOWNLOADER ENGINE | VER : 1.0.0 | DEV : YAHYA ZULFIKRI   ║
║                                                                              ║
║                   UNIVERSAL VIDEO & AUDIO EXTRACTION ENGINE                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        lbl_header = QLabel(ascii_banner)
        lbl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_header.setStyleSheet("font-family: 'Consolas', monospace; font-size: 7pt; color: #00FF00; margin-bottom: 5px;")
        root_layout.addWidget(lbl_header)

        # 2. BODY (SPLIT LAYOUT: KIRI vs KANAN)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(20)

        # --- KOLOM KIRI (COMMAND CENTER) ---
        left_col = QVBoxLayout()
        
        # Section: Target & Output
        grp_target = QGroupBox("TARGET CONFIGURATION")
        l_target = QVBoxLayout()
        l_target.setSpacing(10)
        
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Paste URL Here...")
        self.url_edit.textChanged.connect(self.detect_playlist)
        l_target.addWidget(QLabel(">> TARGET URL:"))
        l_target.addWidget(self.url_edit)
        
        h_folder = QHBoxLayout()
        self.folder_edit = QLineEdit("downloads")
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(40)
        btn_browse.clicked.connect(self.browse_folder)
        h_folder.addWidget(self.folder_edit)
        h_folder.addWidget(btn_browse)
        l_target.addWidget(QLabel(">> OUTPUT DIRECTORY:"))
        l_target.addLayout(h_folder)
        grp_target.setLayout(l_target)
        left_col.addWidget(grp_target)

        # Section: Mode
        grp_mode = QGroupBox("OPERATION MODE")
        l_mode = QVBoxLayout()
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

        # Section: Proxy Config
        grp_proxy = QGroupBox("NETWORK ROUTING")
        l_proxy = QVBoxLayout()
        h_pfile = QHBoxLayout()
        self.proxy_edit = QLineEdit("proxy.csv")
        btn_p_browse = QPushButton("...")
        btn_p_browse.setFixedWidth(40)
        btn_p_browse.clicked.connect(self.browse_proxy_file)
        h_pfile.addWidget(self.proxy_edit)
        h_pfile.addWidget(btn_p_browse)
        l_proxy.addWidget(QLabel(">> PROXY LIST (CSV):"))
        l_proxy.addLayout(h_pfile)
        
        self.btn_scan = QPushButton("SCAN NODES")
        self.btn_scan.clicked.connect(self.load_proxies)
        l_proxy.addWidget(self.btn_scan)
        
        self.chk_use_proxy = QCheckBox("ENABLE AUTO-ROTATION")
        l_proxy.addWidget(self.chk_use_proxy)
        
        grp_proxy.setLayout(l_proxy)
        left_col.addWidget(grp_proxy)
        left_col.addStretch() # Push everything up

        # --- KOLOM KANAN (MONITORING) ---
        right_col = QVBoxLayout()
        
        # Section: Proxy Monitor
        grp_monitor = QGroupBox("NODE STATUS MONITOR")
        l_monitor = QVBoxLayout()
        self.proxy_bar = QProgressBar()
        self.proxy_bar.setVisible(False)
        l_monitor.addWidget(self.proxy_bar)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "NODE ADDRESS", "LATENCY"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        l_monitor.addWidget(self.table)
        grp_monitor.setLayout(l_monitor)
        right_col.addWidget(grp_monitor)

        # Section: System Log
        grp_log = QGroupBox("SYSTEM KERNEL LOG")
        l_log = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        l_log.addWidget(self.log_text)
        grp_log.setLayout(l_log)
        right_col.addWidget(grp_log)

        # Add columns to body
        body_layout.addLayout(left_col, 4) # Ratio 4
        body_layout.addLayout(right_col, 6) # Ratio 6
        root_layout.addLayout(body_layout)

        # 3. FOOTER (ACTION BAR)
        footer_layout = QVBoxLayout()
        self.btn_run = QPushButton(">> INITIALIZE DOWNLOAD SEQUENCE <<")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setStyleSheet("""
            QPushButton { font-size: 14pt; background-color: #001100; border: 2px solid #00FF00; letter-spacing: 3px; }
            QPushButton:hover { background-color: #00FF00; color: #000; }
        """)
        self.btn_run.clicked.connect(self.start_download)
        footer_layout.addWidget(self.btn_run)
        
        lbl_info = QLabel("ZEDLABS.ID SECURITY SYSTEMS | ALL RIGHTS RESERVED")
        lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_info.setStyleSheet("color: #444; font-size: 7pt; margin-top: 5px;")
        footer_layout.addWidget(lbl_info)
        
        root_layout.addLayout(footer_layout)

        # Init Log
        self.log("SYSTEM INITIALIZED...")
        self.log("READY FOR INPUT.")

    # --- LOGIC HANDLERS (Sama seperti sebelumnya) ---
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

    def start_download(self):
        url = self.url_edit.text().strip()
        if not url: return self.log("[ERR] Target URL required.")
        
        proxies = self.valid_proxies if self.chk_use_proxy.isChecked() else []
        self.btn_run.setEnabled(False)
        self.btn_run.setText(">> EXECUTING... <<")
        self.btn_run.setStyleSheet("background-color: #330000; border-color: #550000; color: #AA0000;")
        
        self.dt = DownloadThread(url, self.folder_edit.text(), self.r_aud.isChecked(), proxies, self.chk_playlist.isChecked())
        self.dt.progress.connect(self.log)
        self.dt.finished.connect(self.on_dl_finished)
        self.dt.start()

    def on_dl_finished(self, success, msg):
        self.log(msg)
        self.btn_run.setEnabled(True)
        self.btn_run.setText(">> INITIALIZE DOWNLOAD SEQUENCE <<")
        self.btn_run.setStyleSheet("""
            QPushButton { font-size: 14pt; background-color: #001100; border: 2px solid #00FF00; letter-spacing: 3px; }
            QPushButton:hover { background-color: #00FF00; color: #000; }
        """)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())