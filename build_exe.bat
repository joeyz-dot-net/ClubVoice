@echo off
REM Build a single-file EXE for ClubVoice HLS streamer using PyInstaller
REM Run this from the project root (where player.html, ffmpeg.exe, settings.ini live)

SETLOCAL ENABLEDELAYEDEXPANSION
echo === Building ClubVoice EXE ===

REM Ensure PyInstaller is installed
python -m pip show pyinstaller >nul 2>&1
if ERRORLEVEL 1 (
    echo PyInstaller not found; installing...
    python -m pip install pyinstaller
    if ERRORLEVEL 1 (
        echo Failed to install PyInstaller. Exiting.
        exit /b 1
    )
)

REM Set variables
set SRC=run.py
set OUTNAME=ClubVoiceStreamer
set BASEDIR=%~dp0
set PLAYER=%BASEDIR%player.html
set FFMPEG=%BASEDIR%ffmpeg.exe
set SETTINGS=%BASEDIR%settings.ini
set HLSDIR=%BASEDIR%hls

REM Remove previous build/dist
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist %OUTNAME%.spec del /f /q %OUTNAME%.spec

REM Run pyinstaller
REM Note: on Windows the --add-data separator is a semicolon: SOURCE;DEST
pyinstaller --noconfirm --onefile ^
    --hidden-import hls_streamer ^
    --hidden-import src.hls_streamer ^
    --add-data "%PLAYER%;." ^
    --add-data "%FFMPEG%;." ^
    --add-data "%SETTINGS%;." ^
    --add-data "%HLSDIR%;hls" ^
    --name "%OUTNAME%" ^
    --console "%SRC%"

if ERRORLEVEL 1 (
    echo PyInstaller failed. See output above.
    exit /b 1
)

REM The EXE is produced into the dist\ folder by PyInstaller.
if exist dist\%OUTNAME%.exe (
    echo EXE created: %BASEDIR%dist\%OUTNAME%.exe
) else (
    echo Build succeeded but EXE not found in dist\ folder.
)

echo Done.
ENDLOCAL
pause
