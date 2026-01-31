sudo apt-get install python3-venv libtiff5 libxcb-cursor0
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pyinstaller --onefile --windowed --add-binary "lib/ffmpeg:." --name "Multimedia Downloader" main.py