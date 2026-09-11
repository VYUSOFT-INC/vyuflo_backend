@echo off
cd /d E:\project\vyuflo_backend
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
"E:\project\vyuflo_backend\venv\Scripts\python.exe" -m uvicorn main:app --reload --port 8002 --host 0.0.0.0 1> E:\project\vyuflo_backend\uvicorn8002.out.log 2> E:\project\vyuflo_backend\uvicorn8002.err.log
