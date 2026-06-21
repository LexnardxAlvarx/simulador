@echo off
echo Instalando dependencias...
pip install -r requirements.txt
echo.
echo Ejecutando Simulador...
streamlit run src\app.py
pause