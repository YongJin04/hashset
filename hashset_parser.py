import pytsk3
import os
import hashlib

# Reads a list of MD5 hash values from a file and returns them as a set of uppercased strings
def read_hashset(hashset_path):
    with open(hashset_path, 'r') as file:
        hashset = set(line.strip().upper() for line in file.readlines())
    return hashset

# Calculates the MD5 hash of a file's data using a buffer of 4096 bytes at a time until the entire file is processed
def calculate_md5(file_object, size):
    md5 = hashlib.md5()
    offset = 0
    while offset < size:
        data = file_object.read_random(offset, 4096)
        if not data:
            break
        md5.update(data)
        offset += len(data)
    return md5.hexdigest().upper()

# Extracts a file's data and saves it to the output directory under a filename that combines the MD5 hash and the original file extension
def extract_and_save_file(file_object, size, md5_hash, file_extension, output_dir):
    output_filename = f"{md5_hash}{file_extension}"
    output_path = os.path.join(output_dir, output_filename)
    with open(output_path, 'wb') as out_file:
        offset = 0
        while offset < size:
            data = file_object.read_random(offset, 4096)
            if not data:
                break
            out_file.write(data)
            offset += len(data)
    return output_path

# Recursively scans directories and files in a filesystem, checking files against a set of MD5 hashes and extracting matches
def print_files_with_matching_md5(fs, parent_path, directory, visited, hashset, output_dir, indent="", extracted_files=0):
    for entry in directory:
        if hasattr(entry, 'info') and hasattr(entry.info, 'name') and hasattr(entry.info.name, 'name') and entry.info.name.name not in [".", ".."]:
            file_name = entry.info.name.name.decode('utf-8')
            file_path = os.path.normpath(os.path.join(parent_path, file_name))

            if file_path in visited:
                continue

            visited.add(file_path)

            if entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_REG:
                file_object = fs.open_meta(inode=entry.info.meta.addr)
                file_size = entry.info.meta.size
                md5_hash = calculate_md5(file_object, file_size)
                if md5_hash in hashset:
                    file_extension = os.path.splitext(file_name)[1]
                    saved_file_path = extract_and_save_file(file_object, file_size, md5_hash, file_extension, output_dir)
                    extracted_files += 1
            elif entry.info.meta.type is pytsk3.TSK_FS_META_TYPE_DIR:
                try:
                    sub_directory = fs.open_dir(path=file_path)
                    extracted_files = print_files_with_matching_md5(fs, file_path, sub_directory, visited, hashset, output_dir, indent + "  ", extracted_files)
                except IOError:
                    print(f"Could not open directory: {file_path}")
    return extracted_files

# Initializes the process by opening the image file and hashset, then scans the filesystem for files with hashes that match those in the hashset
def main(image_path, hashset_path):
    img = pytsk3.Img_Info(image_path)
    fs = pytsk3.FS_Info(img, offset=65536)
    root_dir = fs.open_dir(path="/")
    hashset = read_hashset(hashset_path)
    visited = set()
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    extracted_files_count = print_files_with_matching_md5(fs, "/", root_dir, visited, hashset, output_dir)
    print(f"Input hash lines: {len(hashset) - 1}, Extracted files: {extracted_files_count - 1}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        image_path = sys.argv[1]
        hashset_path = sys.argv[2]
        main(image_path, hashset_path)
    else:
        print("Usage: python parser.py [image path] [hashset path]")
