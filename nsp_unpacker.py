import customtkinter as ctk
from tkinter import filedialog, messagebox
import struct
import os

# --- CORE UNPACKING LOGIC ---

def unpack_pfs0_logic(pfs0_data, output_dir):
    logs = []
    
    if len(pfs0_data) < 16:
        logs.append("Error: File is too small to be a valid PFS0 container.")
        return logs

    try:
        magic, file_count, string_table_size, _ = struct.unpack('<IIII', pfs0_data[0:16])
        
        if magic != 0x30534650:
            decoded_magic = pfs0_data[0:4].decode('ascii', 'ignore')
            raise ValueError(f"Invalid PFS0 file. Expected 'PFS0', found: '{decoded_magic}'")
    except (struct.error, ValueError) as e:
        logs.append(f"Error: Could not process PFS0 header. {e}")
        return logs

    logs.append(f"PFS0 header found. File count: {file_count}")

    file_entries = []
    header_size = 16
    file_entry_table_size = file_count * 24
    
    for i in range(file_count):
        entry_offset = header_size + (i * 24)
        data_offset, size, string_offset, _ = struct.unpack('<QQII', pfs0_data[entry_offset:entry_offset+24])
        file_entries.append({'data_offset': data_offset, 'size': size, 'string_offset': string_offset})

    string_table_start = header_size + file_entry_table_size
    string_table = pfs0_data[string_table_start : string_table_start + string_table_size]

    for entry in file_entries:
        end_of_string = string_table.find(b'\x00', entry['string_offset'])
        filename_bytes = string_table[entry['string_offset']:end_of_string]
        entry['filename'] = filename_bytes.decode('utf-8')

    data_section_start = string_table_start + string_table_size
    
    extracted_count = 0
    for entry in file_entries:
        filename = entry['filename']
        start = data_section_start + entry['data_offset']
        end = start + entry['size']

        if end > len(pfs0_data):
            logs.append(f"Skipped: {filename} (data is outside the file bounds - likely a reference).")
            continue

        file_data = pfs0_data[start:end]
        output_path = os.path.join(output_dir, filename)

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(file_data)
            logs.append(f"Extracted: {filename} ({entry['size']} bytes)")
            extracted_count += 1
        except IOError as e:
            logs.append(f"Error writing file {filename}: {e}")
            
    logs.append(f"\nOperation finished. Extracted {extracted_count} of {file_count} files.")
    return logs

# --- GRAPHICAL USER INTERFACE ---

class PFS0UnpackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NSP File Unpacker")
        self.geometry("750x550")
        
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.input_file_path = ctk.StringVar()
        self.output_dir_path = ctk.StringVar(value=os.getcwd())

        # --- UI Widgets ---
        
        # Input File Frame
        input_frame = ctk.CTkFrame(self)
        input_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(input_frame, text="1. Select File to Unpack (.nsp, .cnmt, etc.)").grid(row=0, column=0, columnspan=2, padx=10, pady=(5,0), sticky="w")
        
        self.input_path_entry = ctk.CTkEntry(input_frame, textvariable=self.input_file_path, state='disabled')
        self.input_path_entry.grid(row=1, column=0, padx=(10,5), pady=10, sticky="ew")
        
        self.btn_select_file = ctk.CTkButton(input_frame, text="Browse...", command=self.select_input_file)
        self.btn_select_file.grid(row=1, column=1, padx=(0,10), pady=10)

        # Output Directory Frame
        output_frame = ctk.CTkFrame(self)
        output_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        output_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(output_frame, text="2. Select Output Directory").grid(row=0, column=0, columnspan=2, padx=10, pady=(5,0), sticky="w")
        
        self.output_path_entry = ctk.CTkEntry(output_frame, textvariable=self.output_dir_path, state='disabled')
        self.output_path_entry.grid(row=1, column=0, padx=(10,5), pady=10, sticky="ew")
        
        self.btn_select_dir = ctk.CTkButton(output_frame, text="Browse...", command=self.select_output_dir)
        self.btn_select_dir.grid(row=1, column=1, padx=(0,10), pady=10)

        # Action Button
        self.btn_unpack = ctk.CTkButton(self, text="UNPACK FILE", font=ctk.CTkFont(size=14, weight="bold"), command=self.start_unpacking)
        self.btn_unpack.grid(row=2, column=0, padx=10, pady=20, ipady=10)

        # Log Frame
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=3, column=0, padx=10, pady=(5,10), sticky="nsew")
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(log_frame, text="Operation Log").grid(row=0, column=0, padx=10, pady=(5,0), sticky="w")

        self.log_output = ctk.CTkTextbox(log_frame, state='disabled', wrap='word')
        self.log_output.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    def log(self, message):
        self.log_output.configure(state='normal')
        self.log_output.insert(ctk.END, message + "\n")
        self.log_output.see(ctk.END)
        self.log_output.configure(state='disabled')
        self.update_idletasks()

    def select_input_file(self):
        filepath = filedialog.askopenfilename(
            title="Select a PFS0 file", 
            filetypes=[("Switch Files", "*.nsp *.nca *.cnmt"), ("All files", "*.*")]
        )
        if filepath:
            self.input_file_path.set(filepath)
            self.log(f"Selected file: {filepath}")

    def select_output_dir(self):
        directory = filedialog.askdirectory(title="Select output directory")
        if directory:
            self.output_dir_path.set(directory)
            self.log(f"Selected output directory: {directory}")

    def start_unpacking(self):
        self.log_output.configure(state='normal')
        self.log_output.delete('1.0', ctk.END)
        self.log_output.configure(state='disabled')
        
        input_path = self.input_file_path.get()
        output_dir = self.output_dir_path.get()
        
        if not input_path:
            messagebox.showerror("Error", "No input file selected!")
            return
        if not os.path.isfile(input_path):
            messagebox.showerror("Error", f"Input file does not exist:\n{input_path}")
            return
        if not os.path.isdir(output_dir):
            messagebox.showerror("Error", f"Output directory does not exist:\n{output_dir}")
            return

        self.log(f"Starting to unpack: {os.path.basename(input_path)}...")
        
        try:
            with open(input_path, 'rb') as f:
                pfs0_binary_data = f.read()
            
            result_logs = unpack_pfs0_logic(pfs0_binary_data, output_dir)
            for line in result_logs:
                self.log(line)
            messagebox.showinfo("Success", "Operation completed. Check logs for details.")

        except IOError as e:
            messagebox.showerror("File Read Error", f"Could not read the input file: {e}")
            self.log(f"Critical read error: {e}")
        except Exception as e:
            messagebox.showerror("Critical Error", f"An unexpected error occurred: {e}")
            self.log(f"Critical error: {e}")

if __name__ == "__main__":
    app = PFS0UnpackerApp()
    app.mainloop()
