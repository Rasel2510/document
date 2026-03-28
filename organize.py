import os
import shutil

# Folder to organize
SOURCE_FOLDER = r"C:\Users\rasel\Downloads"

# File type categories
FILE_TYPES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif"],
    "Documents": [".pdf", ".docx", ".txt", ".xlsx"],
    "Videos": [".mp4", ".mkv", ".mov"],
    "Music": [".mp3", ".wav"],
    "Archives": [".zip", ".rar"]
}

def organize_files():
    for filename in os.listdir(SOURCE_FOLDER):
        file_path = os.path.join(SOURCE_FOLDER, filename)

        if os.path.isfile(file_path):
            _, ext = os.path.splitext(filename)

            moved = False
            for folder, extensions in FILE_TYPES.items():
                if ext.lower() in extensions:
                    target_folder = os.path.join(SOURCE_FOLDER, folder)

                    if not os.path.exists(target_folder):
                        os.makedirs(target_folder)

                    shutil.move(file_path, os.path.join(target_folder, filename))
                    moved = True
                    break

            if not moved:
                other_folder = os.path.join(SOURCE_FOLDER, "Others")
                if not os.path.exists(other_folder):
                    os.makedirs(other_folder)
                shutil.move(file_path, os.path.join(other_folder, filename))

if __name__ == "__main__":
    organize_files()
    print("Files organized successfully!")