import os
import sys
import subprocess

def main():
    print("=== Instalador de dependencias para PDF Splitter Avanzado ===\n")

    # 1. Verificar que el archivo requirements.txt existe
    req_file = "requirements.txt"
    if not os.path.exists(req_file):
        print(f"❌ No se encontró '{req_file}' en el directorio actual.")
        sys.exit(1)

    # 2. Detectar el comando de Python adecuado
    python_cmd = sys.executable
    print(f"Usando intérprete de Python: {python_cmd}\n")

    # 3. Instalar dependencias desde requirements.txt
    try:
        subprocess.check_call([python_cmd, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([python_cmd, "-m", "pip", "install", "-r", req_file])
        print("\n✅ Instalación completada con éxito.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error al instalar dependencias: {e}")
        sys.exit(1)

    # 4. Confirmar finalización
    print("\nPuedes ejecutar tu aplicación con:")
    print("   python main.py   (o el nombre de tu script principal)\n")

if __name__ == "__main__":
    main()
