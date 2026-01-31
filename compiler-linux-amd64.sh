sudo apt-get install python3-venv  # Untuk Ubuntu/Debian
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pyinstaller --onefile --windowed --add-binary "lib/ffmpeg:." --name "Multimedia Downloader" --icon=images/icon.ico main.py