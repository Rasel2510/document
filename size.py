import os

FOLDER = r"C:\Users\rasel\Downloads"

files = []

for filename in os.listdir(FOLDER):
    path = os.path.join(FOLDER, filename)

    if os.path.isfile(path):
        size = os.path.getsize(path)
        files.append((filename, size))

files.sort(key=lambda x: x[1], reverse=True)

for file, size in files[:10]:
    print(f"{file} - {size / (1024*1024):.2f} MB")