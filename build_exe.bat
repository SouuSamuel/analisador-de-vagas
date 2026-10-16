@echo off
call venv\Scripts\activate
pip install pyinstaller

rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

pyinstaller --noconfirm --clean --windowed --name AnalisadorVagas ^
  --paths . ^
  --hidden-import analisador ^
  --hidden-import componentes ^
  --hidden-import config ^
  --hidden-import caminhos ^
  --hidden-import curriculos ^
  --hidden-import extrator_curriculo ^
  --hidden-import extrator_vaga ^
  --hidden-import tela_curriculos ^
  --hidden-import tela_config ^
  --collect-all customtkinter ^
  --collect-all pdfplumber ^
  --collect-all pdfminer ^
  --collect-all pypdfium2 ^
  --collect-all docx ^
  main.py

echo.
echo Pronto! O programa esta em: dist\AnalisadorVagas\AnalisadorVagas.exe
pause