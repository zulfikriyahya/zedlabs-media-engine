# 🎬 ZEDLABS YouTube Downloader Pro v4.0 - Web Edition

Versi web dari YouTube Downloader dengan antarmuka modern dan fitur lengkap!

## 📋 Fitur Utama

### ✨ Original CLI Features (masih berfungsi)

- ✅ Download video YouTube (MP4)
- ✅ Extract audio only (MP3)
- ✅ Support playlist download
- ✅ Proxy support dengan auto-testing
- ✅ Multi-threaded proxy testing
- ✅ Progress bar yang cantik dengan animasi
- ✅ Auto-fallback ke proxy backup jika gagal

### 🌐 New Web Features

- ✅ Modern responsive web interface
- ✅ Real-time progress tracking via API
- ✅ Interactive proxy testing dengan visual feedback
- ✅ Drag & drop proxy CSV upload
- ✅ Beautiful gradient UI dengan animasi
- ✅ API health monitoring
- ✅ Download statistics (speed, ETA, size)

## 🚀 Quick Start

### 1️⃣ Instalasi Dependencies

```bash
pip install -r requirements.txt
```

Atau install manual:

```bash
pip install yt-dlp colorama pandas requests certifi flask flask-cors
```

### 2️⃣ Jalankan Backend API

```bash
python main.py
```

Server akan berjalan di `http://localhost:5000`

### 3️⃣ Buka Web Interface

Buka file `youtube_downloader_complete.html` di browser favorit Anda.

Atau bisa juga hosting lokal:

```bash
# Gunakan Python built-in server
python -m http.server 8000
# Lalu buka http://localhost:8000/youtube_downloader_complete.html
```

## 📁 Struktur Project

```
├── main.py                          # Flask backend API
├── youtube_downloader_complete.html # Web interface (full featured)
├── youtube_downloader_web.html     # Web interface (standalone demo)
├── requirements.txt                # Python dependencies
├── proxy.csv                       # (Optional) Proxy list
└── hasil/                          # Default download folder
```

## 🎯 Cara Menggunakan

### Via Web Interface:

1. **Masukkan URL YouTube**
   - Paste URL video atau playlist YouTube

2. **Pilih Mode Download**
   - Video (MP4) - untuk video lengkap
   - Audio (MP3) - hanya audio

3. **Set Output Folder**
   - Default: `hasil`
   - Bisa diganti sesuai keinginan

4. **Proxy (Optional)**
   - ☑️ Centang "Use Proxy"
   - Upload file CSV dengan format:
     ```csv
     ip_address
     192.168.1.1:8080
     10.0.0.1:3128
     socks5://proxy.example.com:1080
     ```
   - Sistem akan auto-test semua proxy
   - Menampilkan proxy tercepat dengan latency

5. **Klik Start Download**
   - Progress bar real-time
   - Speed monitoring
   - ETA estimation

### Via CLI (Original):

```bash
python [original_script_name].py
```

Follow the prompts untuk konfigurasi.

## 🔧 API Endpoints

### Health Check

```
GET /api/health
Response: {
  "success": true,
  "message": "ZEDLABS YouTube Downloader API is running",
  "version": "4.0"
}
```

### Test Proxies

```
POST /api/test-proxies
Body: {
  "csv_content": "ip_address\n192.168.1.1:8080\n..."
}
Response: {
  "success": true,
  "total": 50,
  "working": 15,
  "proxies": [
    {
      "proxy": "http://192.168.1.1:8080",
      "latency": 234.5,
      "status": "OK"
    }
  ]
}
```

### Start Download

```
POST /api/download
Body: {
  "url": "https://youtube.com/watch?v=...",
  "mode": "video",  // or "audio"
  "folder": "hasil",
  "proxy": "http://192.168.1.1:8080"  // optional
}
Response: {
  "success": true,
  "download_id": "1234567890",
  "message": "Download started"
}
```

### Get Progress

```
GET /api/progress/{download_id}
Response: {
  "success": true,
  "status": "downloading",
  "percent": 45.2,
  "speed": "2.5 MB/s",
  "eta": "00:30",
  "downloaded": "50 MB",
  "total": "110 MB"
}
```

## 📝 Format Proxy CSV

Buat file `proxy.csv` dengan format:

```csv
ip_address
192.168.1.1:8080
10.0.0.1:3128
proxy.example.com:8888
socks5://socks-proxy.com:1080
http://username:password@proxy.com:8080
```

**Notes:**

- Baris pertama adalah header (akan di-skip)
- Format: `ip:port` atau `protocol://ip:port`
- Support: http, https, socks5
- Support authentication: `http://user:pass@ip:port`

## 🎨 Technology Stack

### Backend

- **Flask** - Web framework
- **yt-dlp** - YouTube downloader engine
- **pandas** - CSV processing
- **requests** - HTTP client
- **colorama** - Terminal colors (CLI)

### Frontend

- **HTML5** - Markup
- **CSS3** - Styling dengan gradients & animations
- **JavaScript** - Interactivity & API calls
- **Fetch API** - REST API communication

## ⚙️ Configuration

Edit di `main.py`:

```python
# Port server
app.run(debug=True, host='0.0.0.0', port=5000)

# Timeout proxy testing
TIMEOUT = 8

# Max threads untuk proxy testing
MAX_THREADS = 10
```

## 🔍 Troubleshooting

### API Offline

**Problem:** Web interface menunjukkan "API Offline"

**Solution:**

1. Pastikan `main.py` sudah dijalankan
2. Check console untuk error messages
3. Pastikan port 5000 tidak dipakai aplikasi lain
4. Try restart: `Ctrl+C` lalu `python main.py` lagi

### Download Gagal

**Problem:** Download error atau stuck

**Solution:**

1. Cek koneksi internet
2. Verify URL YouTube valid
3. Jika pakai proxy, test proxy dulu
4. Check apakah FFmpeg terinstall (untuk audio extraction)

### Proxy Tidak Bekerja

**Problem:** Semua proxy failed saat testing

**Solution:**

1. Verify format CSV benar
2. Test proxy manual di browser/curl
3. Increase timeout di `main.py`
4. Gunakan proxy dari provider terpercaya

### FFmpeg Error

**Problem:** Audio extraction gagal

**Solution:**

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download dari https://ffmpeg.org/download.html
```

## 📊 Performance Tips

1. **Proxy Testing:**
   - Limit proxy list ke 50-100 untuk testing cepat
   - Gunakan MAX_THREADS=10 untuk balance speed/resource

2. **Download Speed:**
   - Pilih proxy dengan latency <500ms
   - Disable proxy jika koneksi langsung lebih cepat

3. **Multi-Download:**
   - API support multiple concurrent downloads
   - Each download tracked by unique ID

## 🔐 Security Notes

- ⚠️ Jangan share proxy credentials di public repo
- ⚠️ API tidak ada authentication (localhost only)
- ⚠️ Untuk production, add CORS restrictions
- ⚠️ Add rate limiting untuk prevent abuse

## 📜 License

Created by **Yahya Zulfikri**

## 🤝 Contributing

Feel free to:

- Report bugs
- Suggest features
- Submit pull requests
- Improve documentation

## 📞 Support

Jika ada masalah atau pertanyaan:

1. Check troubleshooting section
2. Review API documentation
3. Check browser console untuk errors
4. Verify backend logs

## 🎉 Changelog

### v4.0 - Web Edition

- ✅ Added Flask REST API
- ✅ Beautiful web interface
- ✅ Real-time progress tracking
- ✅ Interactive proxy testing
- ✅ Download statistics
- ✅ API health monitoring

### v3.0 - CLI Enhanced

- ✅ Multi-threaded proxy testing
- ✅ Animated terminal UI
- ✅ Progress bars
- ✅ Auto-fallback proxies

---

**Made with ❤️ by Yahya Zulfikri**

_Happy Downloading! 🎬_
