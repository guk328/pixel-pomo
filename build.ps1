# Builds dist\PixelPomo.exe  —  run from the project folder:  .\build.ps1
& .\venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { exit 1 }
& .\venv\Scripts\python.exe -m PyInstaller `
    --noconfirm --clean `
    --onefile `
    --windowed `
    --name PixelPomo `
    --icon assets\icon.ico `
    --add-data "assets;assets" `
    main.py
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "`nDone -> dist\PixelPomo.exe"
