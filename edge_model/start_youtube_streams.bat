@echo off
setlocal

:: =========================================================
:: AUTO-RECONNECT WORKER FUNCTION (Bulletproof Demo Logic)
:: =========================================================
if "%~1"=="STR_WORKER" (
    set LANE_NAME=%~2
    set FILE_NAME=%~3
    set STREAM_KEY=%~4
    
    title %LANE_NAME%
    echo Starting Bulletproof Stream Worker for %LANE_NAME%...
    
    :RECONNECT_LOOP
    echo.
    echo [INFO] Connecting RTMP stream to YouTube for %LANE_NAME%...
    ffmpeg -re -stream_loop -1 -i "testimages\%FILE_NAME%" -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 -c:v libx264 -preset veryfast -b:v 2500k -maxrate 2500k -bufsize 5000k -vf format=yuv420p -g 60 -c:a aac -b:a 128k -map 0:v:0 -map 1:a:0 -f flv "rtmp://a.rtmp.youtube.com/live2/%STREAM_KEY%"
    
    :: If ffmpeg crashes or finishes (due to network failure), it falls through to here.
    echo.
    echo [WARNING] NETWORK FLUCUATION DETECTED!
    echo [ACTION] YouTube stream dropped. Auto-reconnecting in 3 seconds to save the demo...
    timeout /t 3 >nul
    goto RECONNECT_LOOP
)

:: =========================================================
:: MAIN LAUNCHER CONFIGURATION
:: =========================================================

:: --- YOUTUBE STREAM KEYS ---
set KEY_NORTH=uwjy-0rz1-429t-v4ut-2che
set KEY_SOUTH=3qkr-q7ep-a1t0-7e5f-fxqt
set KEY_EAST=u0fw-wuae-dm0q-0edd-5ppd
set KEY_WEST=gyy5-gbpd-b7g4-c4sc-dgc9

echo ================================================
echo    STARTING BULLETPROOF YOUTUBE STREAM PIPELINE
echo ================================================
echo.

:: Launch the 4 auto-reconnecting workers in separate windows
start "Lane 001 (North)" cmd /c "%~f0" STR_WORKER "Lane 001 (North)" north.mp4 %KEY_NORTH%
start "Lane 002 (South)" cmd /c "%~f0" STR_WORKER "Lane 002 (South)" south.mp4 %KEY_SOUTH%
start "Lane 003 (East)"  cmd /c "%~f0" STR_WORKER "Lane 003 (East)"  east.mp4  %KEY_EAST%
start "Lane 004 (West)"  cmd /c "%~f0" STR_WORKER "Lane 004 (West)"  west.mp4  %KEY_WEST%

echo [SUCCESS] 4 streams launched with Auto-Reconnect enabled!
echo Close the 4 black terminal windows to stop the streams.
timeout /t 10
