Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

python3 -m venv venv
.\venv\Scripts\Activate.ps1
python3 -m pip install --upgrade pip
pip install -r requirements.txt
pyinstaller --onefile --windowed --add-binary "lib\ffmpeg.exe;." --name "Multimedia Downloader" --icon=images\icon.ico main.py