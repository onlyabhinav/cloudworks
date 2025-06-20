@echo off
set TIME_OUT=4

powershell -NoProfile -ExecutionPolicy Bypass -File "gitau.ps1"

timeout /t %TIME_OUT%
