@echo off
echo Baue Servo Tool mit PyInstaller...

pyinstaller --clean --name="ServoTool" --windowed --add-data "ui_tabs;ui_tabs" --add-data "*.json;." --collect-all matplotlib --collect-all PyQt5 main.py

echo Build abgeschlossen!
echo.
echo Hinweis: Wenn die EXE-Datei auf anderen Rechnern nicht startet,
echo stelle sicher, dass die Microsoft Visual C++ Redistributable installiert ist.
echo.
pause