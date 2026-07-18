@echo off
cd /d "%~dp0"
python autopost_shorts2.py >> shorts2_log.txt 2>&1
