# PDF_CUT_SECCIONS.py

"""
1. Si es la primera vez que ejecutas este script, asegúrate de ejecutar 'install.bat'
2. Ejecuta este script y selecciona el archivo PDF que deseas dividir o
    ejecuta el script 'PDF_CUT_SECCIONS.bat' para abrir la interfaz gráfica y seleccioanr PDF y secciones a dividir.
3. Introduce los rangos de páginas (en la interfaz gráfica) que deseas extraer en el formato adecuado.
(Nota): Las páginas se numeran en el siguiente formato: (ejemplo) 1-5, 8, 10-end -- solo se guardan las secciones seleccionadas en nuevos archivos PDF.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

# --- Sección 1: Lógica Central de División del PDF (split_pdf_by_pages) ---
def split_pdf_by_pages(input_pdf_path: str, page_ranges: list[tuple[int, int]]) -> bool:
    """
    Divide un archivo PDF en documentos PDF según los rangos de páginas especificados,
    guardándolos en una nueva subcarpeta dentro del directorio del PDF original.

    Args:
        input_pdf_path (str): La ruta completa al archivo PDF de entrada.
        page_ranges (list[tuple[int, int]]): Una lista de tuplas, donde cada tupla
                                             (inicio, fin) representa un rango de páginas
                                             a incluir en un nuevo PDF. Las páginas son 1-basadas.

    Returns:
        bool: True si el proceso de división se completó con éxito, False en caso contrario.
    """
    intro = (
        "1) Si es la primera vez, ejecuta 'install.bat' para instalar dependencias.\n"
        "2) Puedes ejecutar directamente este script y seleccionar el PDF, o usar "
        "'PDF_CUT_SECCIONS.bat' para abrir la interfaz y elegir PDF y secciones.\n"
        "3) Formato de rangos: 1-5, 8, 10-end (solo se guardan las secciones indicadas).\n"
    )
    print(intro)
    print("\n=== PDF Splitter Avanzado ===")

    print(f"\nIniciando el proceso de división para: {input_pdf_path}")


    # 1.1. Validar la existencia y tipo del archivo PDF de entrada
    if not os.path.exists(input_pdf_path) or not os.path.isfile(input_pdf_path):
        messagebox.showerror("Error de Entrada", f"El archivo PDF no existe o no es válido: {input_pdf_path}")
        return False

    # 1.2. Determinar el directorio de salida automáticamente
    input_directory = os.path.dirname(input_pdf_path)
    base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]
    output_directory = os.path.join(input_directory, f"{base_name}_paginas_divididas")

    # 1.3. Preparar el directorio de salida
    try:
        os.makedirs(output_directory, exist_ok=True)
        print(f"Directorio de salida preparado (o ya existente): {output_directory}")
    except OSError as e:
        messagebox.showerror("Error de Directorio", f"No se pudo crear/acceder al directorio de salida '{output_directory}'. Detalle: {e}")
        return False

    # 1.4. Procesamiento del Archivo PDF
    try:
        with open(input_pdf_path, 'rb') as pdf_file:
            reader = PdfReader(pdf_file)
            num_total_pages = len(reader.pages)

            print(f"PDF cargado con éxito. Total de páginas detectadas: {num_total_pages}")
            messagebox.showinfo("Proceso Iniciado", f"PDF cargado. Se detectaron {num_total_pages} páginas. Iniciando la división según los rangos...")

            processed_files_count = 0
            # 1.5. Iterar a través de los rangos de páginas especificados
            for idx, (start_page, end_page) in enumerate(page_ranges):
                # Validar que el rango esté dentro de los límites del PDF
                if start_page < 1 or end_page > num_total_pages or start_page > end_page:
                    messagebox.showwarning("Rango Inválido",
                                           f"El rango de páginas {start_page}-{end_page} es inválido o excede el número total de páginas ({num_total_pages}). Se omitirá este rango.")
                    print(f"  - Rango {start_page}-{end_page} omitido debido a validación.")
                    continue

                writer = PdfWriter()
                # pypdf es 0-indexado, por lo que restamos 1 al inicio y el fin es exclusivo
                for page_num in range(start_page - 1, end_page):
                    writer.add_page(reader.pages[page_num])

                # Construir el nombre del archivo de salida para este rango
                if start_page == end_page:
                    output_filename = f"{base_name}_pagina_{start_page}.pdf"
                else:
                    output_filename = f"{base_name}_paginas_{start_page}-{end_page}.pdf"
                
                full_output_path = os.path.join(output_directory, output_filename)

                with open(full_output_path, 'wb') as output_pdf_file:
                    writer.write(output_pdf_file)
                
                processed_files_count += 1
                print(f"  - Rango {start_page}-{end_page} guardado como: {full_output_path}")

        messagebox.showinfo("Proceso Completado",
                              f"Proceso de división de PDF finalizado con éxito.\n"
                              f"Se crearon {processed_files_count} archivos en:\n{output_directory}")
        print(f"\nProceso de división de PDF completado con éxito para '{input_pdf_path}'.")
        return True

    # 1.6. Manejo de Errores
    except PdfReadError as e:
        messagebox.showerror("Error de Lectura de PDF",
                              f"No se pudo procesar el archivo '{input_pdf_path}'.\n"
                              f"Podría estar corrupto, protegido con contraseña o no ser un PDF válido.\n"
                              f"Detalle: {e}")
        return False
    except Exception as e:
        messagebox.showerror("Error Inesperado",
                              f"Ocurrió un problema durante el procesamiento de '{input_pdf_path}'.\n"
                              f"Detalle: {e}")
        return False

# --- Sección 2: Funciones Auxiliares para el Procesamiento de Rangos ---
def parse_page_ranges(ranges_str: str, total_pages: int) -> list[tuple[int, int]]:
    """
    Parsea una cadena de texto de rangos de páginas (ej. "1-5, 8, 10-end")
    en una lista de tuplas (inicio, fin).

    Args:
        ranges_str (str): La cadena de texto con los rangos.
        total_pages (int): El número total de páginas del PDF para validar 'end'.

    Returns:
        list[tuple[int, int]]: Una lista de tuplas (inicio, fin) de los rangos válidos.
                               Retorna una lista vacía si hay errores de formato.
    """
    parsed_ranges = []
    parts = [p.strip() for p in ranges_str.split(',')]

    for part in parts:
        if not part:
            continue
        
        if '-' in part:
            start_str, end_str = part.split('-', 1)
            try:
                start = int(start_str)
                if end_str.lower() == 'end':
                    end = total_pages
                else:
                    end = int(end_str)
            except ValueError:
                messagebox.showwarning("Formato de Rango Inválido", f"Rango '{part}' tiene un formato numérico incorrecto. Ignorando.")
                continue
        else:
            try:
                start = int(part)
                end = start
            except ValueError:
                messagebox.showwarning("Formato de Rango Inválido", f"Rango '{part}' tiene un formato numérico incorrecto. Ignorando.")
                continue
        
        # Validaciones básicas de lógica del rango
        if start < 1 or start > total_pages:
            messagebox.showwarning("Rango Fuera de Límites", f"Página de inicio '{start}' está fuera de los límites (1-{total_pages}). Ignorando el rango '{part}'.")
            continue
        if end < 1 or end > total_pages:
            messagebox.showwarning("Rango Fuera de Límites", f"Página final '{end}' está fuera de los límites (1-{total_pages}). Ignorando el rango '{part}'.")
            continue
        if start > end:
            messagebox.showwarning("Rango Inválido", f"La página de inicio '{start}' es mayor que la página final '{end}'. Ignorando el rango '{part}'.")
            continue

        parsed_ranges.append((start, end))
    
    # Opcional: Ordenar y fusionar rangos si se desea, pero para esta solicitud
    # simplemente se procesan en el orden dado.
    return parsed_ranges

def get_pdf_page_count(pdf_path: str) -> int:
    """
    Obtiene el número total de páginas de un archivo PDF.
    Retorna 0 si el archivo no es válido o no se puede leer.
    """
    try:
        with open(pdf_path, 'rb') as pdf_file:
            reader = PdfReader(pdf_file)
            return len(reader.pages)
    except (PdfReadError, FileNotFoundError, Exception) as e:
        print(f"Error al obtener el número de páginas de {pdf_path}: {e}")
        return 0

# --- Sección 3: Implementación de la Interfaz Gráfica (GUI) con `tkinter` ---
class PDFSplitterApp:
    def __init__(self, master):
        self.master = master
        master.title("PDF CUT SECCIONS - Divisor de páginas a PDF")
        master.geometry("550x350") # Aumentado para los nuevos campos
        master.resizable(False, False)
        master.attributes('-topmost', True) # Mantener la ventana en primer plano

        self.input_pdf_path = tk.StringVar()
        self.total_pages_var = tk.StringVar(value="N/A")
        self.page_ranges_str_var = tk.StringVar(value="Ej: 1-5, 8, 10-end") # Placeholder para el usuario

        main_frame = tk.Frame(master, padx=15, pady=15)
        main_frame.pack(expand=True, fill='both')

        # 3.1. Selector de Archivo PDF de Entrada
        tk.Label(main_frame, text="1. Selecciona el archivo PDF:", font=("Arial", 10, "bold")).pack(pady=(0, 5), anchor='w')
        input_frame = tk.Frame(main_frame)
        input_frame.pack(fill='x', pady=2)
        self.input_entry = tk.Entry(input_frame, textvariable=self.input_pdf_path, width=50, state='readonly')
        self.input_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        tk.Button(input_frame, text="Explorar...", command=self.select_input_pdf).pack(side='right')

        # 3.2. Mostrar Número Total de Páginas
        tk.Label(main_frame, text="Páginas totales del PDF:", font=("Arial", 10, "bold")).pack(pady=(10, 2), anchor='w')
        tk.Label(main_frame, textvariable=self.total_pages_var, font=("Arial", 12, "bold"), fg="blue").pack(pady=(0, 10), anchor='w')

        # 3.3. Entrada para los Rangos de Páginas
        tk.Label(main_frame, text="2. Introduce los rangos de páginas (ej: 1-5, 8, 10-end):", font=("Arial", 10, "bold")).pack(pady=(0, 5), anchor='w')
        self.ranges_entry = tk.Entry(main_frame, textvariable=self.page_ranges_str_var, width=60)
        self.ranges_entry.pack(pady=(0, 15), fill='x')
        # Limpiar el placeholder al hacer click
        self.ranges_entry.bind("<FocusIn>", self.clear_placeholder)
        self.ranges_entry.bind("<FocusOut>", self.set_placeholder)


        # 3.4. Botón para Iniciar la División
        tk.Button(main_frame, text="¡DIVIDIR PDF AHORA!", command=self.start_splitting,
                  bg="#4CAF50", fg="white", font=("Arial", 14, "bold"),
                  relief=tk.RAISED, bd=3).pack(pady=5)

    def select_input_pdf(self):
        """
        Abre un diálogo para seleccionar un PDF y actualiza la interfaz
        con la ruta y el número total de páginas.
        """
        file_path = filedialog.askopenfilename(
            title="Seleccionar Archivo PDF para Dividir",
            filetypes=[("Archivos PDF", "*.pdf")]
        )
        if file_path:
            self.input_pdf_path.set(file_path)
            # Actualizar el número de páginas al seleccionar el PDF
            total_pages = get_pdf_page_count(file_path)
            if total_pages > 0:
                self.total_pages_var.set(f"{total_pages} páginas")
            else:
                self.total_pages_var.set("Error al leer páginas")
                messagebox.showerror("Error de PDF", "No se pudo leer el número de páginas de este PDF. Podría estar dañado o protegido.")
        else:
            self.input_pdf_path.set("")
            self.total_pages_var.set("N/A")

    def start_splitting(self):
        """
        Función que se llama al pulsar el botón "¡DIVIDIR PDF AHORA!".
        Recoge las rutas y rangos, valida y llama a la lógica principal de división.
        """
        input_pdf = self.input_pdf_path.get()
        ranges_str = self.page_ranges_str_var.get()
        total_pages_text = self.total_pages_var.get()

        if not input_pdf:
            messagebox.showwarning("Advertencia", "Por favor, selecciona primero el **archivo PDF de entrada**.")
            return

        if ranges_str == "Ej: 1-5, 8, 10-end" or not ranges_str.strip():
            messagebox.showwarning("Advertencia", "Por favor, introduce los **rangos de páginas** para la división.")
            return

        if "N/A" in total_pages_text or "Error" in total_pages_text:
            messagebox.showwarning("Advertencia", "No se ha podido determinar el número total de páginas del PDF. Por favor, revisa el archivo.")
            return
        
        try:
            total_pages = int(total_pages_text.split(" ")[0])
        except ValueError:
            messagebox.showwarning("Error Interno", "No se pudo parsear el número total de páginas.")
            return

        # Parsear los rangos de páginas introducidos por el usuario
        parsed_ranges = parse_page_ranges(ranges_str, total_pages)

        if not parsed_ranges:
            messagebox.showerror("Error de Rangos", "No se pudieron interpretar los rangos de páginas. Por favor, verifica el formato.")
            return
        
        # Llamar a la función de lógica central para dividir el PDF
        # La función split_pdf_by_pages ya muestra mensajes de éxito/error a través de messagebox.
        split_pdf_by_pages(input_pdf, parsed_ranges)
        
        # Después de que el proceso de división finaliza, cerrar la aplicación
        self.master.destroy()

    def clear_placeholder(self, event):
        """Limpia el texto del placeholder cuando el Entry recibe foco."""
        if self.page_ranges_str_var.get() == "Ej: 1-5, 8, 10-end":
            self.page_ranges_str_var.set("")
            self.ranges_entry.config(fg='black')

    def set_placeholder(self, event):
        """Restablece el texto del placeholder si el Entry está vacío y pierde foco."""
        if not self.page_ranges_str_var.get():
            self.page_ranges_str_var.set("Ej: 1-5, 8, 10-end")
            self.ranges_entry.config(fg='grey')


# --- Sección 4: Bloque de Ejecución Principal (`if __name__ == "__main__":`) ---
if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSplitterApp(root)
    root.mainloop()