sudo apt-get install python3-venv libtiff6 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 -y
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pyinstaller --onefile --windowed --add-binary "lib/ffmpeg:." --name "Multimedia Downloader" main.py