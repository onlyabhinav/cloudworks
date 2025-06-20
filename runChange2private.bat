@echo off
set TIME_OUT=4

powershell -NoProfile -ExecutionPolicy Bypass -File "script/gh2private.ps1"

timeout /t %TIME_OUT%
