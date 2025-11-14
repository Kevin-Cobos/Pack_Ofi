@echo off
REM ===============================================================
REM Lanzador de Interfaz - PDF Splitter Avanzado
REM ===============================================================
title PDF Splitter Avanzado - Lanzador
color 0B
echo ===========================================
echo      Iniciando PDF Splitter Avanzado
echo ===========================================
echo.

REM --- Ir al directorio donde está este .bat ---
cd /d "%~dp0"

REM --- Ruta del script GUI ---
set "SCRIPT_PATH=.\scripts\PDF_CUT_SECCIONS.py"

IF NOT EXIST "%SCRIPT_PATH%" (
    echo ❌ No se encontro "%SCRIPT_PATH%".
    echo    Comprueba la carpeta "scripts" y el nombre del archivo.
    pause
    exit /b
)

REM --- Probar pythonw / pyw para GUI sin consola; fallback a python / py ---
where pythonw >nul 2>&1
IF %ERRORLEVEL%==0 (
    start "" pythonw "%SCRIPT_PATH%"
    goto :end
)

where pyw >nul 2>&1
IF %ERRORLEVEL%==0 (
    start "" pyw "%SCRIPT_PATH%"
    goto :end
)

where python >nul 2>&1
IF %ERRORLEVEL%==0 (
    echo ⚠️  Ejecutando con python (aparecera consola)...
    start "" python "%SCRIPT_PATH%"
    goto :end
)

where py >nul 2>&1
IF %ERRORLEVEL%==0 (
    echo ⚠️  Ejecutando con py (aparecera consola)...
    start "" py "%SCRIPT_PATH%"
    goto :end
)

echo ❌ No se encontro Python en PATH. Instala Python 3.8+ y vuelve a intentar.
pause
exit /b

:end
echo.
echo ✅ Aplicacion lanzada.
exit /b
