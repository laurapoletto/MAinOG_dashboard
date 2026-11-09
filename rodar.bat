@echo off
REM Duplo clique: instala as dependencias (1a vez) e abre o dashboard
python -m pip install -r requirements.txt
python -m streamlit run app.py
pause
