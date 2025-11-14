import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

def split_pdf_by_pages(input_pdf_path: str) -> bool:
    """
    Divide un archivo PDF en documentos PDF de una sola página,
    guardándolos en una nueva subcarpeta dentro del directorio del PDF original.

    Args:
        input_pdf_path (str): La ruta completa al archivo PDF de entrada.

    Returns:
        bool: True si el proceso de división se completó con éxito, False en caso contrario.
    """
    print(f"\nStarting the PDF splitting process for: {input_pdf_path}")

    # --- 1.1. Validar la existencia y tipo del archivo PDF de entrada ---
    if not os.path.exists(input_pdf_path) or not os.path.isfile(input_pdf_path):
        messagebox.showerror("Input Error", f"The PDF file does not exist or is not valid: {input_pdf_path}")
        return False

    # 1.2. Determinar el directorio de salida automáticamente
    input_directory = os.path.dirname(input_pdf_path)
    base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]
    output_directory = os.path.join(input_directory, f"{base_name}_paginas_separadas")

    # 1.3. Preparar el directorio de salida
    try:
        os.makedirs(output_directory, exist_ok=True)
        print(f"Output directory prepared (or already exists): {output_directory}")
    except OSError as e:
        messagebox.showerror("Directory Error", f"Could not create/access the output directory '{output_directory}'. Detail: {e}")
        return False

    # --- 1.4. Procesamiento del Archivo PDF ---
    try:
        with open(input_pdf_path, 'rb') as pdf_file:
            reader = PdfReader(pdf_file)
            num_pages = len(reader.pages)

            print(f"PDF loaded successfully. Total pages detected: {num_pages}")
            # Considerar si este messagebox es necesario, ya que el proceso es automático.
            # Podría ser redundante si el proceso es muy rápido. Lo mantendremos por ahora.
            messagebox.showinfo("Process Started", f"PDF loaded. {num_pages} pages detected. Starting to split...")

            # 1.5. Iterar a través de cada página del PDF para guardarla individualmente
            for i in range(num_pages):
                writer = PdfWriter()
                writer.add_page(reader.pages[i])

                output_filename = f"{base_name}_pagina_{i + 1}.pdf"
                full_output_path = os.path.join(output_directory, output_filename)

                with open(full_output_path, 'wb') as output_pdf_file:
                    writer.write(output_pdf_file)

                print(f"  - Page {i + 1} of {num_pages} saved as: {full_output_path}")

        messagebox.showinfo("Process Complete", f"PDF splitting process finished successfully.\n{num_pages} files created in:\n{output_directory}")
        print(f"\nPDF splitting process completed successfully for '{input_pdf_path}'.")
        return True

    # 1.6. Manejo de Errores
    except PdfReadError as e:
        messagebox.showerror("PDF Read Error",
                              f"Could not process the file '{input_pdf_path}'.\n"
                              f"It might be corrupt, password-protected, or not a valid PDF.\n"
                              f"Detail: {e}")
        return False
    except Exception as e:
        messagebox.showerror("Unexpected Error",
                              f"An unexpected issue occurred during processing of '{input_pdf_path}'.\n"
                              f"Detail: {e}")
        return False

# --- Sección 2: Implementación de la Interfaz Gráfica (GUI) con `tkinter` ---
class PDFSplitterApp:
    def __init__(self, master):
        self.master = master
        master.title("Select PDF to Split")
        master.geometry("400x150") # Reduced size for minimal interface
        master.resizable(False, False)
        master.attributes('-topmost', True) # Keep window on top

        tk.Label(master, text="Please select the PDF file to split:", font=("Arial", 10, "bold")).pack(pady=20)

        # The "Browse" button will directly trigger the file selection and then the splitting process
        tk.Button(master, text="Select PDF File", command=self.select_and_split,
                  bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                  relief=tk.RAISED, bd=3).pack(pady=10)

    def select_and_split(self):
        """
        Opens a dialog for the user to select a PDF file.
        If a file is selected, it triggers the splitting process and then closes the application.
        """
        file_path = filedialog.askopenfilename(
            title="Select PDF File to Split",
            filetypes=[("PDF Files", "*.pdf")]
        )
        
        if file_path:
            # If a file is selected, call the splitting function
            split_pdf_by_pages(file_path)
            # After the splitting process (and its messageboxes) completes, destroy the Tkinter window
            self.master.destroy()
        else:
            # If no file is selected (user cancels dialog), just close the window
            self.master.destroy()

# --- Sección 3: Bloque de Ejecución Principal (`if __name__ == "__main__":`) ---
if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSplitterApp(root)
    root.mainloop()