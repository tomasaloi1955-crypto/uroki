@echo off
rem Дневной автопостинг уроков — запускается планировщиком Windows
cd /d "%~dp0"
python autopost_daily.py >> autopost_log.txt 2>&1
