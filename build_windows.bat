@echo off
REM ============================================================
REM  Build Script for Scan Input - Vietnamese OCR Tool (Windows)
REM  Run this on a Windows machine with Python 3.11/3.12
REM ============================================================

echo === Step 1: Install Python dependencies ===
pip install -r requirements_windows.txt
if %errorlevel% neq 0 goto :error

echo === Step 2: Download Tesseract OCR ===
if not exist "build_deps\tesseract" (
    mkdir build_deps 2>nul
    echo Downloading Tesseract...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/UB-Mannheim/tesseract/releases/download/v5.5.0.20241111/tesseract-ocr-w64-setup-5.5.0.20241111.exe' -OutFile 'build_deps\tesseract_setup.exe'"
    echo Installing Tesseract silently...
    build_deps\tesseract_setup.exe /S /D="%CD%\build_deps\tesseract"
    echo Downloading Vietnamese language data...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata_best/raw/main/vie.traineddata' -OutFile 'build_deps\tesseract\tessdata\vie.traineddata'"
)

echo === Step 3: Download Poppler ===
if not exist "build_deps\poppler" (
    echo Downloading Poppler...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip' -OutFile 'build_deps\poppler.zip'"
    powershell -Command "Expand-Archive -Path 'build_deps\poppler.zip' -DestinationPath 'build_deps\poppler_tmp'"
    move "build_deps\poppler_tmp\poppler-24.08.0" "build_deps\poppler"
    del "build_deps\poppler.zip"
    rmdir /s /q "build_deps\poppler_tmp"
)

echo === Step 4: Build with PyInstaller ===
set TESSERACT_DIR=%CD%\build_deps\tesseract
set POPPLER_DIR=%CD%\build_deps\poppler\Library\bin
pyinstaller scan_input.spec --distpath dist --workpath build --clean -y
if %errorlevel% neq 0 goto :error

echo === Step 5: Create installer with Inno Setup ===
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
    echo Installer created in dist\
) else (
    echo [WARN] Inno Setup not found. Skipping installer creation.
    echo        Download from: https://jrsoftware.org/isdl.php
    echo        The portable build is in: dist\ScanInput\
)

echo.
echo =============================================
echo   BUILD COMPLETE!
echo   Output: dist\ScanInput\ScanInput.exe
echo =============================================
goto :done

:error
echo BUILD FAILED!
exit /b 1

:done
exit /b 0
