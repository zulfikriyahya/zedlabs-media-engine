from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import pandas as pd
import requests
import concurrent.futures
from threading import Thread
import time
import json

app = Flask(__name__)
CORS(app)

# Global variables untuk tracking progress
download_progress = {}
proxy_test_results = {}

class DownloadProgress:
    def __init__(self, download_id):
        self.download_id = download_id
        self.status = 'initializing'
        self.percent = 0
        self.speed = 'N/A'
        self.eta = 'N/A'
        self.downloaded = 'N/A'
        self.total = 'N/A'
        self.error = None

def progress_hook(d, download_id):
    """Progress hook untuk tracking download"""
    if download_id not in download_progress:
        download_progress[download_id] = DownloadProgress(download_id)
    
    progress = download_progress[download_id]
    
    if d['status'] == 'downloading':
        try:
            percent_str = d.get('_percent_str', '0%').strip()
            progress.percent = float(percent_str.replace('%', ''))
            progress.speed = d.get('_speed_str', 'N/A').strip()
            progress.eta = d.get('_eta_str', 'N/A').strip()
            progress.downloaded = d.get('_downloaded_bytes_str', 'N/A').strip()
            progress.total = d.get('_total_bytes_str', 'N/A').strip()
            progress.status = 'downloading'
        except:
            pass
    elif d['status'] == 'finished':
        progress.status = 'finished'
        progress.percent = 100

def check_proxy(proxy):
    """Check single proxy"""
    proxies_dict = {"http": proxy, "https": proxy}
    try:
        start = time.time()
        response = requests.get(
            "https://www.google.com", 
            proxies=proxies_dict, 
            timeout=8,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        if response.status_code == 200:
            latency = (time.time() - start) * 1000
            return {'proxy': proxy, 'latency': latency, 'status': 'OK'}
    except:
        pass
    return {'proxy': proxy, 'latency': 9999, 'status': 'FAIL'}

@app.route('/api/test-proxies', methods=['POST'])
def test_proxies():
    """Test proxies dari CSV content"""
    try:
        data = request.json
        csv_content = data.get('csv_content', '')
        
        # Parse CSV
        lines = csv_content.split('\n')
        proxies = []
        
        for line in lines[1:]:  # Skip header
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split(',')
                if parts[0]:
                    proxy = parts[0].strip()
                    if not proxy.startswith(('http://', 'https://', 'socks5://')):
                        proxy = 'http://' + proxy
                    proxies.append(proxy)
        
        proxies = list(set(proxies))[:50]  # Limit to 50 proxies
        
        if not proxies:
            return jsonify({'success': False, 'message': 'No valid proxies found'})
        
        # Test proxies concurrently
        valid_proxies = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_proxy, proxy): proxy for proxy in proxies}
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result['status'] == 'OK':
                    valid_proxies.append(result)
        
        # Sort by latency
        valid_proxies.sort(key=lambda x: x['latency'])
        
        return jsonify({
            'success': True,
            'total': len(proxies),
            'working': len(valid_proxies),
            'proxies': valid_proxies[:20]  # Return top 20
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/download', methods=['POST'])
def download():
    """Start download process"""
    try:
        data = request.json
        url = data.get('url')
        mode = data.get('mode', 'video')
        folder = data.get('folder', 'hasil')
        proxy = data.get('proxy')
        
        if not url:
            return jsonify({'success': False, 'message': 'URL is required'})
        
        # Generate download ID
        download_id = str(int(time.time() * 1000))
        
        # Start download in background thread
        thread = Thread(target=perform_download, args=(download_id, url, mode, folder, proxy))
        thread.start()
        
        return jsonify({
            'success': True,
            'download_id': download_id,
            'message': 'Download started'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def perform_download(download_id, url, mode, folder, proxy):
    """Perform actual download"""
    try:
        os.makedirs(folder, exist_ok=True)
        
        opts = {
            'outtmpl': os.path.join(folder, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: progress_hook(d, download_id)],
            'quiet': True,
            'no_warnings': True,
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 30,
        }
        
        if proxy:
            opts['proxy'] = proxy
        
        if mode == 'audio':
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }],
            })
        else:
            opts.update({
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
            })
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        
        if download_id in download_progress:
            download_progress[download_id].status = 'completed'
            download_progress[download_id].percent = 100
            
    except Exception as e:
        if download_id in download_progress:
            download_progress[download_id].status = 'error'
            download_progress[download_id].error = str(e)

@app.route('/api/progress/<download_id>', methods=['GET'])
def get_progress(download_id):
    """Get download progress"""
    if download_id not in download_progress:
        return jsonify({'success': False, 'message': 'Download not found'})
    
    progress = download_progress[download_id]
    
    return jsonify({
        'success': True,
        'status': progress.status,
        'percent': progress.percent,
        'speed': progress.speed,
        'eta': progress.eta,
        'downloaded': progress.downloaded,
        'total': progress.total,
        'error': progress.error
    })

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'ZEDLABS YouTube Downloader API is running',
        'version': '4.0'
    })

if __name__ == '__main__':
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          ZEDLABS YouTube Downloader API v4.0             ║")
    print("║                  Author: Yahya Zulfikri                  ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║  API Server running on http://localhost:5500             ║")
    print("║  Open youtube_downloader_web.html in browser             ║")
    print("╚══════════════════════════════════════════════════════════╝")
    app.run(debug=True, host='0.0.0.0', port=5500)