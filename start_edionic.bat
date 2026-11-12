@echo off
title Edionic — Free Local-First 9:16 AI Video Editor
cd /d "C:\ai editing"
set PATH=C:\ai editing\tools\ffmpeg\bin;C:\ai editing\tools\python;C:\ai editing\tools\python\Scripts;%PATH%
echo Starting Edionic Backend + Web Editor UI at http://127.0.0.1:8080 ...
start "" "http://127.0.0.1:8080"
"C:\ai editing\tools\python\python.exe" "C:\ai editing\backend\server.py"
pause
