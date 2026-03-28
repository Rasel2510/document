import os
import hashlib
from pathlib import Path

# --- Step 1: Set folder to scan ---
folder_path = Path("C:/")  # Change this to your folder

# --- Step 2: Function to get file hash ---
def file_hash(file_path):
    hasher = hashlib.md5()  # You can also use sha256
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

# --- Step 3: Find duplicates ---
hashes = {}
duplicates = []

for file in folder_path.rglob("*"):  # rglob scans subfolders too
    if file.is_file():
        h = file_hash(file)
        if h in hashes:
            duplicates.append((file, hashes[h]))
        else:
            hashes[h] = file

# --- Step 4: Print duplicates ---
if duplicates:
    print("Duplicate files found:")
    for dup, original in duplicates:
        print(f"{dup} is a duplicate of {original}")
else:
    print("No duplicate files found.")