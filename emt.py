import os

FOLDER = r"C:\Users\rasel\Downloads"

def remove_empty_folders(path):
    for root, dirs, files in os.walk(path, topdown=False):
        if not dirs and not files:
            os.rmdir(root)
            print(f"Deleted empty folder: {root}")

remove_empty_folders(FOLDER)