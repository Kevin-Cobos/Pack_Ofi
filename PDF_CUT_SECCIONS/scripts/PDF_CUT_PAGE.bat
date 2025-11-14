@echo off
REM Cambia el directorio a la ubicación del script Python
cd "C:\Users\PC\Documents\PROJECTES\Proyecto Cono\_Scripts\PDF_cut_pag"

REM Ejecuta el script Python usando pythonw.exe para evitar que aparezca la ventana de la consola.
REM Si pythonw.exe no funciona, puedes probar con "python.exe" en su lugar, pero aparecerá una ventana de consola.
start "" pythonw.exe PDF_CUT_PAGE.py

REM Cierra esta ventana de comando (el archivo .bat) inmediatamente después de lanzar la aplicación Python.
exit