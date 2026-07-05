@echo off
title Kitian - Instalar dependencias faltantes
echo Instalando sounddevice, keyboard, python-telegram-bot ...
python -m pip install --quiet sounddevice keyboard python-telegram-bot
echo.
echo Dependencias instaladas.
timeout /t 4