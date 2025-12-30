@echo off
REM Deploy ClubVoice EXE to remote server and back up existing EXE.
REM Usage: run this from the project root (where dist\ClubVoiceStreamer.exe exists)

SETLOCAL ENABLEDELAYEDEXPANSION

SET DIST=%~dp0dist\ClubVoiceStreamer.exe
SET REMOTE=\\b560\code\ClubVoice
SET BAKROOT=\\b560\code\ClubVoice_bakup

echo Deploy script running from: %~dp0

if not exist "%DIST%" (
  echo ERROR: Built EXE not found: %DIST%
  exit /b 1
)

if not exist "%REMOTE%" (
  echo Creating remote folder %REMOTE%
  md "%REMOTE%" || (echo Failed to create remote folder & exit /b 1)
)

if not exist "%BAKROOT%" (
  echo Creating backup folder %BAKROOT%
  md "%BAKROOT%" || (echo Failed to create backup folder & exit /b 1)
)

for /f %%t in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMddHHmmss')"') do set TIMESTAMP=%%t

if exist "%REMOTE%\ClubVoiceStreamer.exe" (
  echo Backing up existing EXE...
  rem Use delayed expansion for variables modified inside this block
  set "BAKNAME=ClubVoiceStreamer_!TIMESTAMP!.exe"
  set "BAKPATH=!BAKROOT!\!BAKNAME!"
  rem ensure unique backup name if it somehow already exists
  set /A SUFFIX=0
  :ensure_unique
  if exist "!BAKPATH!" (
    set /A SUFFIX+=1
    set "BAKNAME=ClubVoiceStreamer_!TIMESTAMP!_!SUFFIX!.exe"
    set "BAKPATH=!BAKROOT!\!BAKNAME!"
    goto ensure_unique
  )
  echo [DEBUG] Backing up to: !BAKPATH!
  move /Y "%REMOTE%\ClubVoiceStreamer.exe" "!BAKPATH!" >nul 2>&1
  if ERRORLEVEL 1 (
    echo WARNING: Failed to move existing remote EXE. Trying copy then delete...
    copy /Y "%REMOTE%\ClubVoiceStreamer.exe" "!BAKPATH!" || (echo Failed to copy existing EXE to backup & exit /b 1)
    del /F /Q "%REMOTE%\ClubVoiceStreamer.exe" || echo WARN: could not delete remote EXE after backup
  ) else (
    echo Backed up existing EXE to !BAKPATH!
  )
) else (
  echo No existing remote EXE to back up.
)

echo Copying new EXE to remote...
copy /Y "%DIST%" "%REMOTE%\" >nul 2>&1
if ERRORLEVEL 1 (
  echo ERROR: Failed to copy %DIST% to %REMOTE%\
  exit /b 1
)
echo Deployment successful: %REMOTE%\ClubVoiceStreamer.exe

echo Done.
pause
ENDLOCAL
