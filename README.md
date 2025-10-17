# Pokemon-Legends-Z-A-Tools
in progress.....

1. NSP Files



# **NSP Files**

## 1. PFS0 Header

| Offset (Hex) | Size (bytes) | Description | Example (Hex) | Value (Little Endian) |
| :--- | :--- | :--- | :--- | :--- |
| `0x00` | 4 | **Magic Number** (identifier) | `50 46 53 30` | `"PFS0"` |
| `0x04` | 4 | **Number of files** in the container | `06 00 00 00` | `6` |
| `0x08` | 4 | **Size of the String Table** | `FC 00 00 00` | `252` bytes |
| `0x0C` | 4 | Reserved | `00 00 00 00` | `0` |

---

## 2. File Entry Table

**Single Entry Structure (24 bytes):**
*   **8 bytes (u64):** Data offset, relative to the start of the Data Section.
*   **8 bytes (u64):** File size in bytes.
*   **4 bytes (u32):** Name offset within the String Table.
*   **4 bytes (u32):** Reserved (always zero).

#### Entry Analysis:

**Entry 1** (offset `0x10` - `0x27`)
*   **Data Offset:** `0x0`
*   **Size:** `0x6A3`
*   **Name Offset:** `0x0`

**Entry 2** (offset `0x28` - `0x3F`)
*   **Data Offset:** `0x6A3`
*   **Size:** `0x101C180`
*   **Name Offset:** `0x2A`

**Entry 3** (offset `0x40` - `0x57`)
*   **Data Offset:** `0x101C86A3`
*   **Size:** `0x10CA`
*   **Name Offset:** `0x4F`

**Entry 4** (offset `0x58` - `0x6F`)
*   **Data Offset:** `0x101D250A3`
*   **Size:** `0x4E4`
*   **Name Offset:** `0x74`

**Entry 5** (offset `0x70` - `0x87`)
*   **Data Offset:** `0x101D734A3`
*   **Size:** `0x1C0`
*   **Name Offset:** `0x99`

**Entry 6** (offset `0x88` - `0x9F`)
*   **Data Offset:** `0x101D8F4A3`
*   **Size:** `0xE`
*   **Name Offset:** `0xBE`

---

## 3. String Table (File Name Table)

This section is a continuous block of data containing the names of all files, separated by a `NULL` (`0x00`) character. It starts right after the File Entry Table.

*   **Start of File Entry Table:** `0x10`
*   **Size of File Entry Table:** `6 files * 24 bytes/file = 144 bytes (0x90)`
*   **End of File Entry Table:** `0x10 + 0x90 = 0xA0`
*   **Start of String Table:** `0xA0`
*   **Size (from header):** `252 bytes (0xFC)`

#### Identified Filenames:

The name offsets are relative to the start of this table (`0xA0`).

1.  **Offset `0x0`:** `8f826c26180ad48f0fc04b690d0211ec.cnmt.xml`
2.  **Offset `0x2A`:** `461e1e40fb6a016a4e6cb76e7d5b482d.nca`
3.  **Offset `0x4F`:** `63ee77442e522d1ad684b6f1384bff45.nca`
4.  **Offset `0x74`:** `3b7396dfe703c48a093b1f76a39cf379.nca`
5.  **Offset `0x99`:** `15364f1775aa8e8a7aeb804368951c5f.nca`
6.  **Offset `0xBE`:** `8f826c26180ad48f0fc04b690d0211ec.cnmt.nca`

---

## 4. Data Section

The final section contains the actual file content. Its starting address can be calculated by adding the size of the String Table to its start address.

*   **Start of String Table:** `0xA0`
*   **Size of String Table:** `0xFC`
*   **Start of Data Section:** `0xA0 + 0xFC = 0x19C`

Now we can locate the data for the first file in the container.

*   **File 1:** `*.cnmt.xml`
*   **Data Offset (from Entry 1):** `0x0`
*   **Size (from Entry 1):** `0x6A3`
*   **Location within the PFS0 file:**
    *   **Start:** `0x19C + 0x0 = 0x19C`
    *   **End:** `0x19C + 0x6A3 = 0x83F`
