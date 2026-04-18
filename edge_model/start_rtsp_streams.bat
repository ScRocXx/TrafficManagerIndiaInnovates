@echo off
title Northern Blades - RTSP Streamer

:: Cloud server IP (Change this to your friend's cloud server IP before running)
set CLOUD_IP=REPLACE_WITH_CLOUD_IP

echo.
echo ==============================================================
echo   NORTHERN BLADES - EDGE NODE RTSP STREAMER
echo ==============================================================
echo.
echo Target Cloud Server: %CLOUD_IP%
echo.

if "%CLOUD_IP%"=="REPLACE_WITH_CLOUD_IP" (
    echo [ERROR] Please edit this file and change CLOUD_IP to the actual Cloud Server IP.
    pause
    exit /b
)

:: Stream Lane 001 (North)
start "Lane 001 (North)" cmd /c "ffmpeg -re -stream_loop -1 -i testimages\north.mp4 -c copy -f rtsp rtsp://%CLOUD_IP%:8554/cam_001"

:: Stream Lane 002 (South)
start "Lane 002 (South)" cmd /c "ffmpeg -re -stream_loop -1 -i testimages\south.mp4 -c copy -f rtsp rtsp://%CLOUD_IP%:8554/cam_002"

:: Stream Lane 003 (East)
start "Lane 003 (East)" cmd /c "ffmpeg -re -stream_loop -1 -i testimages\east.mp4 -c copy -f rtsp rtsp://%CLOUD_IP%:8554/cam_003"

:: Stream Lane 004 (West)
start "Lane 004 (West)" cmd /c "ffmpeg -re -stream_loop -1 -i testimages\west.mp4 -c copy -f rtsp rtsp://%CLOUD_IP%:8554/cam_004"

echo Streams started! Check the newly opened windows for FFmpeg logs.
pause
