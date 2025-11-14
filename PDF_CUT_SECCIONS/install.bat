@echo off
REM ===============================================================
REM Instalador de Dependencias para PDF Splitter Avanzado
REM ===============================================================
title Instalador - PDF Splitter Avanzado
color 0A
echo ===========================================
echo     Instalador de Dependencias Python
echo ===========================================
echo.

REM --- Ir al directorio donde está este .bat ---
cd /d "%~dp0"

REM --- Verificar Python en PATH ---
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ❌ Python no está instalado o no está en PATH.
    echo    Instala Python 3.8+ desde https://www.python.org/downloads/ y marca "Add to PATH".
    echo Intentando con el lanzador 'py'...
    py --version >nul 2>&1
    IF ERRORLEVEL 1 (
        pause
        exit /b
    )
)

REM --- Rutas relativas ---
set "SCRIPTS_DIR=.\scripts"
set "INSTALL_PY=%SCRIPTS_DIR%\install.py"

REM --- Comprobar existencia de install.py ---
IF NOT EXIST "%INSTALL_PY%" (
    echo ❌ No se encontro "%INSTALL_PY%".
    echo    Asegurate de que exista la carpeta "scripts" y el archivo "install.py".
    pause
    exit /b
)

echo Ejecutando desde:
echo   %CD%
echo Usando instalador:
echo   %INSTALL_PY%
echo.

REM --- Ejecutar install.py (intenta python y luego py) ---
echo Instalando dependencias desde requirements.txt...
python "%INSTALL_PY%" 2>nul || py "%INSTALL_PY%"
IF ERRORLEVEL 1 (
    echo ❌ La instalación reporto un error.
    pause
    exit /b
)

echo.
echo ✅ Instalación completada. Puedes lanzar la app con:
echo    PDF_CUT_SECCIONS.bat
echo.
pause
