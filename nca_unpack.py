import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import subprocess
import threading

# --- CORE HACTOOL LOGIC ---

def run_hactool_logic(hactool_path, keys_path, nca_path, output_dir, log_callback):
    try:
        hactool_path = os.path.normpath(hactool_path)
        keys_path = os.path.normpath(keys_path)
        nca_path = os.path.normpath(nca_path)
        output_dir = os.path.normpath(output_dir)

        nca_basename = os.path.basename(nca_path)
        romfs_output_dirname = os.path.splitext(nca_basename)[0] + "_romfs"
        romfs_output_path = os.path.join(output_dir, romfs_output_dirname)
        romfs_output_path = os.path.normpath(romfs_output_path)

        command = [
            hactool_path,
            "-k", keys_path,
            "--romfsdir", romfs_output_path,
            nca_path
        ]
        
        log_callback(f"Target directory for RomFS: {romfs_output_path}\n")
        formatted_command = ' '.join(f'"{c}"' for c in command)
        log_callback(f"Running command:\n{formatted_command}\n")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        stdout, stderr = process.communicate()

        if stdout:
            log_callback("--- HACTOOL OUTPUT ---")
            log_callback(stdout.strip())
            log_callback("----------------------")
        
        if stderr:
            log_callback("\n--- HACTOOL ERRORS ---")
            log_callback(stderr.strip())
            log_callback("----------------------")
        
        if process.returncode != 0:
            if "key" in stderr.lower():
                log_callback("\nHint: This error might be caused by an invalid or incomplete keys file (prod.keys).")
            elif "Is NCA file a gamecard image?" in stderr or "PFS0 magic is invalid" in stderr:
                 log_callback("\nHint: This NCA file likely does not contain a RomFS section (e.g., it could be an update or metadata). Try the largest NCA file from the game.")
            raise RuntimeError(f"Hactool exited with an error (code: {process.returncode}). Check the logs.")
        
        log_callback("\nOperation finished!")
        if os.path.exists(romfs_output_path) and os.listdir(romfs_output_path):
             messagebox.showinfo("Success", f"Finished extracting RomFS to:\n{romfs_output_path}")
        else:
             log_callback("\nINFO: Hactool finished successfully, but the RomFS directory was not created. This NCA file probably did not contain a RomFS partition.")
             messagebox.showinfo("Finished", "Hactool completed, but no RomFS section was found to extract.")

    except FileNotFoundError:
        error_msg = f"Error: 'hactool.exe' not found!\nMake sure it is in the same folder as this script."
        log_callback(error_msg)
        messagebox.showerror("Critical Error", error_msg)
    except Exception as e:
        error_msg = f"\nAn error occurred: {e}"
        log_callback(error_msg)
        messagebox.showerror("Error", error_msg)

# --- GRAPHICAL USER INTERFACE ---

class HactoolGuiApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Hactool GUI Wrapper")
        self.geometry("800x650")

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.hactool_path = os.path.join(script_dir, "hactool.exe")
        
        self.keys_path = ctk.StringVar(value=os.path.join(script_dir, "prod.keys"))
        self.nca_path = ctk.StringVar()
        self.output_dir = ctk.StringVar(value=os.getcwd())
        
        self.create_widgets()
        self.check_initial_files()

    def create_widgets(self):
        # Frame 1: Keys File
        self.create_path_selection_frame(0, "1. Keys File", self.keys_path, self.select_keys_file)
        
        # Frame 2: NCA File
        self.create_path_selection_frame(1, "2. NCA File to Unpack", self.nca_path, self.select_nca_file)

        # Frame 3: Output Directory
        self.create_path_selection_frame(2, "3. Base Output Directory", self.output_dir, self.select_output_dir)

        # Action Button
        self.unpack_button = ctk.CTkButton(self, text="UNPACK ROMFS FROM NCA FILE", font=ctk.CTkFont(size=14, weight="bold"), command=self.start_unpacking_thread)
        self.unpack_button.grid(row=3, column=0, padx=10, pady=20, ipady=10, sticky="ew")

        # Log Frame
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(log_frame, text="Operation Log (hactool output)").grid(row=0, column=0, padx=10, pady=(5,0), sticky="w")
        
        self.log_output = ctk.CTkTextbox(log_frame, state='disabled', wrap='word', font=("Consolas", 11))
        self.log_output.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    def create_path_selection_frame(self, row, title, variable, command):
        frame = ctk.CTkFrame(self)
        frame.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text=title).grid(row=0, column=0, columnspan=2, padx=10, pady=(5,0), sticky="w")
        
        entry = ctk.CTkEntry(frame, textvariable=variable, state='disabled')
        entry.grid(row=1, column=0, padx=(10,5), pady=10, sticky="ew")
        
        button = ctk.CTkButton(frame, text="Browse...", command=command)
        button.grid(row=1, column=1, padx=(0,10), pady=10)

    def log(self, message):
        def append_log():
            self.log_output.configure(state='normal')
            self.log_output.insert(ctk.END, message + "\n")
            self.log_output.see(ctk.END)
            self.log_output.configure(state='disabled')
        self.after(0, append_log)

    def select_keys_file(self):
        path = filedialog.askopenfilename(title="Select keys file", filetypes=[("Keys Files", "*.keys"), ("All files", "*.*")])
        if path:
            self.keys_path.set(path)

    def select_nca_file(self):
        path = filedialog.askopenfilename(title="Select NCA file", filetypes=[("NCA Files", "*.nca"), ("All files", "*.*")])
        if path:
            self.nca_path.set(path)

    def select_output_dir(self):
        path = filedialog.askdirectory(title="Select output directory")
        if path:
            self.output_dir.set(path)

    def check_initial_files(self):
        if not os.path.exists(self.hactool_path):
             messagebox.showwarning("File Not Found", "hactool.exe was not found. Please make sure it is in the same folder as this script.")
        if not os.path.exists(self.keys_path.get()):
            self.log("INFO: Default 'prod.keys' file not found. Please select it manually.")

    def start_unpacking_thread(self):
        keys = self.keys_path.get()
        nca = self.nca_path.get()
        out_dir = self.output_dir.get()

        if not all([keys, nca, out_dir]):
            messagebox.showwarning("Missing Information", "Please fill all three fields to continue.")
            return

        self.log_output.configure(state='normal')
        self.log_output.delete('1.0', ctk.END)
        self.log_output.configure(state='disabled')
        
        self.unpack_button.configure(state='disabled', text="WORKING...")
        
        thread = threading.Thread(
            target=run_hactool_logic, 
            args=(self.hactool_path, keys, nca, out_dir, self.log), 
            daemon=True
        )
        thread.start()
        
        self.after(100, self.check_thread, thread)

    def check_thread(self, thread):
        if thread.is_alive():
            self.after(100, self.check_thread, thread)
        else:
            self.unpack_button.configure(state='normal', text="UNPACK ROMFS FROM NCA FILE")

if __name__ == "__main__":
    app = HactoolGuiApp()
    app.mainloop()
