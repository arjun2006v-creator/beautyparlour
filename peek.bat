@echo off
set PY="f:\web projects\beauty parlour\.venv\Scripts\python.exe"
set OUT="f:\web projects\beauty parlour\peek_out.txt"
del /q "f:\web projects\beauty parlour\peek_out.txt" 2>nul
%PY% "f:\web projects\beauty parlour\peek.py" >> %OUT% 2>&1
echo DONE>> %OUT%