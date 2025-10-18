import os
import struct
import sys
import traceback
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

# --- FNV-1a HASHING IMPLEMENTATION ---
def fnv1a_64_hash(data: bytes) -> int:
    """Computes the 64-bit FNV-1a hash of the given data."""
    PRIME = 0x100000001b3
    BASIS = 0xcbf29ce484222645
    h = BASIS
    for byte in data:
        h ^= byte
        h = (h * PRIME) & 0xFFFFFFFFFFFFFFFF
    return h

# --- SAFE READ FUNCTIONS ---
def read_u32(f):
    data = f.read(4)
    return struct.unpack('<I', data)[0] if len(data) == 4 else 0

def read_u64(f):
    data = f.read(8)
    return struct.unpack('<Q', data)[0] if len(data) == 8 else 0

def read_string(f):
    length = read_u32(f)
    return f.read(length).decode('utf-8', 'ignore')

def read_vec_u64(f_handle, count):
    return [read_u64(f_handle) for _ in range(count)]

# --- PARSER CLASSES ---
class NameIndex:
    """Parses a .trpfd file to extract package names and their hashes."""
    def __init__(self, fname):
        self.pack_infos = []
        with open(fname, 'rb') as f:
            f.seek(0x1C)
            base = 0x1C + read_u32(f)
            f.seek(base)
            count = read_u32(f)
            rel_offsets = [read_u32(f) for _ in range(count)]
            offsets = [base + 4 + (i * 4) + rel_off for i, rel_off in enumerate(rel_offsets)]
            for off in offsets:
                f.seek(off)
                name = read_string(f)
                hash_val = fnv1a_64_hash(name.encode('utf-8'))
                self.pack_infos.append({'name': name, 'hash': hash_val})

class DataArchiveMap:
    """Parses a .trpfs file to map package hashes to their file offsets."""
    def __init__(self, fname):
        with open(fname, 'rb') as f:
            if f.read(8) != b"ONEPACK\0":
                raise IOError("Invalid .trpfs signature")
            offsets_start = read_u64(f)
            f.seek(offsets_start + 28)
            pack_count = read_u32(f)
            pack_offsets = read_vec_u64(f, pack_count)
            f.seek(f.tell() + 4)
            pack_hash_count = read_u32(f)
            pack_hashes = read_vec_u64(f, pack_hash_count)
            self.pack_hash_to_offset = {h: offset for h, offset in zip(pack_hashes, pack_offsets)}

# --- GUI APPLICATION ---
class BrutalSlicerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TRPFS Unpacker")
        self.geometry("700x400")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.grid_columnconfigure(1, weight=1)

        # --- WIDGETS ---
        # TRPFD File Path
        self.trpfd_label = ctk.CTkLabel(self, text="TRPFD File:")
        self.trpfd_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.trpfd_path = ctk.CTkEntry(self, placeholder_text="Path to data.trpfd")
        self.trpfd_path.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")
        self.trpfd_button = ctk.CTkButton(self, text="Browse", width=100, command=self.browse_trpfd)
        self.trpfd_button.grid(row=0, column=2, padx=20, pady=(20, 10))

        # TRPFS File Path
        self.trpfs_label = ctk.CTkLabel(self, text="TRPFS File:")
        self.trpfs_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.trpfs_path = ctk.CTkEntry(self, placeholder_text="Path to data.trpfs")
        self.trpfs_path.grid(row=1, column=1, padx=20, pady=10, sticky="ew")
        self.trpfs_button = ctk.CTkButton(self, text="Browse", width=100, command=self.browse_trpfs)
        self.trpfs_button.grid(row=1, column=2, padx=20, pady=10)

        # Output Directory
        self.output_label = ctk.CTkLabel(self, text="Output Dir:")
        self.output_label.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.output_dir = ctk.CTkEntry(self, placeholder_text="Directory to extract files to")
        self.output_dir.grid(row=2, column=1, padx=20, pady=10, sticky="ew")
        self.output_button = ctk.CTkButton(self, text="Browse", width=100, command=self.browse_output)
        self.output_button.grid(row=2, column=2, padx=20, pady=10)

        # Start Button
        self.start_button = ctk.CTkButton(self, text="Start Extraction", command=self.start_extraction_thread)
        self.start_button.grid(row=3, column=0, columnspan=3, padx=20, pady=20)

        # Status Label
        self.status_label = ctk.CTkLabel(self, text="Ready. Please select files and an output directory.")
        self.status_label.grid(row=4, column=0, columnspan=3, padx=20, pady=10, sticky="w")

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=5, column=0, columnspan=3, padx=20, pady=20, sticky="ew")

    def browse_trpfd(self):
        path = filedialog.askopenfilename(title="Select data.trpfd", filetypes=[("TRPFD files", "*.trpfd"), ("All files", "*.*")])
        if path:
            self.trpfd_path.delete(0, "end")
            self.trpfd_path.insert(0, path)

    def browse_trpfs(self):
        path = filedialog.askopenfilename(title="Select data.trpfs", filetypes=[("TRPFS files", "*.trpfs"), ("All files", "*.*")])
        if path:
            self.trpfs_path.delete(0, "end")
            self.trpfs_path.insert(0, path)

    def browse_output(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_dir.delete(0, "end")
            self.output_dir.insert(0, path)

    def update_status(self, message):
        self.status_label.configure(text=message)
        self.update_idletasks()

    def update_progress(self, value):
        self.progress_bar.set(value)
        self.update_idletasks()

    def start_extraction_thread(self):
        # Run the extraction in a separate thread to keep the GUI responsive
        threading.Thread(target=self.run_extraction, daemon=True).start()
    
    def run_extraction(self):
        """The core extraction logic, adapted from the console script."""
        trpfd_path = self.trpfd_path.get()
        trpfs_path = self.trpfs_path.get()
        output_path_base = self.output_dir.get()

        # --- INPUT VALIDATION ---
        if not all([trpfd_path, trpfs_path, output_path_base]):
            messagebox.showerror("Error", "All paths must be specified.")
            return
        if not os.path.isfile(trpfd_path):
            messagebox.showerror("Error", f"TRPFD file not found:\n{trpfd_path}")
            return
        if not os.path.isfile(trpfs_path):
            messagebox.showerror("Error", f"TRPFS file not found:\n{trpfs_path}")
            return

        self.start_button.configure(state="disabled", text="Extracting...")
        self.update_progress(0)

        try:
            # --- Step 1: Parse metadata files ---
            self.update_status("[Step 1/3] Parsing metadata files...")
            name_index = NameIndex(trpfd_path)
            data_map = DataArchiveMap(trpfs_path)
            os.makedirs(output_path_base, exist_ok=True)
            self.update_status(f"  > Found {len(name_index.pack_infos)} package names in .trpfd")
            
            # --- Step 2: Create and sort the package map ---
            self.update_status("[Step 2/3] Mapping and sorting packages...")
            pack_map = []
            for info in name_index.pack_infos:
                offset = data_map.pack_hash_to_offset.get(info['hash'])
                if offset is not None:
                    pack_map.append({'name': info['name'], 'offset': offset})
            
            # Sorting by offset is KEY to calculating the size of each pack
            pack_map.sort(key=lambda p: p['offset'])
            total_packs = len(pack_map)
            self.update_status(f"  > Successfully mapped and sorted {total_packs} packages.")

            # --- Step 3: Begin full raw extraction ---
            self.update_status(f"[Step 3/3] Starting full raw extraction of {total_packs} packages...")

            with open(trpfs_path, 'rb') as f_trpfs:
                for i in range(total_packs):
                    current_pack = pack_map[i]
                    start_offset = current_pack['offset']
                    
                    # Determine the end of the block
                    if i + 1 < total_packs:
                        next_pack = pack_map[i+1]
                        end_offset = next_pack['offset']
                    else:
                        # The last pack goes to the end of the file
                        end_offset = os.path.getsize(trpfs_path)
                    
                    slice_size = end_offset - start_offset
                    pack_name = current_pack['name']
                    
                    progress_val = (i + 1) / total_packs
                    self.update_progress(progress_val)
                    self.update_status(f"Extracting {i+1}/{total_packs}: {pack_name} ({slice_size/1024:.1f} KB)")

                    f_trpfs.seek(start_offset)
                    pack_data = f_trpfs.read(slice_size)
                    
                    output_file_path = os.path.join(output_path_base, pack_name.replace('/', os.sep))
                    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                    with open(output_file_path, 'wb') as out_f:
                        out_f.write(pack_data)

            self.update_status("Extraction completed successfully!")
            messagebox.showinfo("Success", "Full raw extraction has finished successfully.")

        except Exception as e:
            error_message = f"A critical error occurred:\n\n{traceback.format_exc()}"
            self.update_status(f"Error: {e}")
            messagebox.showerror("Critical Error", error_message)

        finally:
            self.start_button.configure(state="normal", text="Start Extraction")
            self.update_progress(0)


if __name__ == "__main__":
    app = BrutalSlicerApp()
    app.mainloop()
