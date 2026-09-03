@echo off
set PY="f:\web projects\beauty parlour\.venv\Scripts\python.exe"
set OUT="f:\web projects\beauty parlour\peek_out.txt"
del /q "f:\web projects\beauty parlour\peek_out.txt" 2>nul
echo === PATCH ===>> %OUT%
%PY% "f:\web projects\beauty parlour\patch_book.py" >> %OUT% 2>&1
echo === COMPILE ===>> %OUT%
%PY% -m py_compile "f:\web projects\beauty parlour\app.py" >> %OUT% 2>&1
if errorlevel 1 (echo COMPILE_FAILED>> %OUT%) else (echo COMPILE_OK>> %OUT%)