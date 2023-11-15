import os
import shutil
import argparse
from datetime import datetime

DEF_TARGET = 'E:\\'
DEF_SOURCE = 'G:\\dev'
EXCLUDE_DIRS = ['System Volume Information']
TIME_TOLERANCE = 2.0

def parse_arguments():
    parser = argparse.ArgumentParser(description='Synchronize files between two directories.')
    parser.add_argument('--source', '-s', default=DEF_SOURCE, help='The source directory for the files.')
    parser.add_argument('--target', '-t', default=DEF_TARGET, help='The target directory for the files.')
    return parser.parse_args()

def should_delete_file(target_file, source_dir, target_dir):
    # Compute the relative path from the target directory
    relative_path = os.path.relpath(target_file, target_dir)
    # Use the relative path to get the corresponding source file path
    source_file_path = os.path.join(source_dir, relative_path)
    file_exists = os.path.exists(source_file_path)
    return not file_exists

def should_overwrite_file(target_file, source_file):
    target_mtime = os.path.getmtime(target_file)
    source_mtime = os.path.getmtime(source_file)
    
    # Calculate the absolute difference in modification times
    time_difference = abs(target_mtime - source_mtime)
    
    # If the difference is less than or equal to the tolerance, we consider the files the same
    if time_difference <= TIME_TOLERANCE:
        return 'same'
    else:
        # Return 'true' if the target file is newer, otherwise 'false'
        return 'true' if target_mtime > source_mtime else 'false'

def group_files_by_directory(files_list):
    directories = {}
    for file in files_list:
        directory = os.path.dirname(file)
        if directory in directories:
            directories[directory].append(file)
        else:
            directories[directory] = [file]
    return directories

def sync_directories(source, target):
    script_name = os.path.basename(__file__)

    delete_candidates = []
    overwrite_candidates = []
    copy_candidates = []
    error_paths = []  # To collect paths where an error occurred

    # Walk through the target directory
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in files:
            if name == script_name:
                continue

            target_file = os.path.join(root, name)
            relative_path = os.path.relpath(target_file, target)
            source_file = os.path.join(source, relative_path)

            # Check for deletion
            if should_delete_file(target_file, source, target):
                delete_candidates.append(target_file)
            # Check for overwrite
            elif os.path.exists(source_file) and should_overwrite_file(target_file, source_file) == 'true':
                overwrite_candidates.append(target_file)
    
    # Walk from bottom to top to handle subdirectories first
    for root, dirs, _ in os.walk(target, topdown=False):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in dirs:
            target_dir_path = os.path.join(root, name)
            relative_path = os.path.relpath(target_dir_path, target)
            source_dir_path = os.path.join(source, relative_path)

            if not os.path.exists(source_dir_path):
                delete_candidates.append(target_dir_path)

    # Walk through the source directory to find files to copy
    for root, dirs, files in os.walk(source):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in files:
            if name == script_name:
                continue

            source_file = os.path.join(root, name)
            target_file = source_file.replace(source, target, 1)

            if not os.path.exists(target_file) or os.path.getmtime(source_file) > os.path.getmtime(target_file):
                copy_candidates.append((source_file, target_file))

    # Group files by directory
    delete_directories = group_files_by_directory(delete_candidates)
    overwrite_directories = group_files_by_directory(overwrite_candidates)

    # Summarize deletions
    deletion_summary = []
    for directory, files in delete_directories.items():
        if len(files) > 20:
            deletion_summary.append(f"Delete 20+ files in directory: {directory}")
        else:
            for file in files:
                deletion_summary.append(f"Delete file: {file}")

    # Summarize overwrites
    overwrite_summary = []
    for directory, files in overwrite_directories.items():
        if len(files) > 20:
            overwrite_summary.append(f"Overwrite 20+ files in directory: {directory}")
        else:
            for file in files:
                overwrite_summary.append(f"Overwrite file: {file}")

    if len(deletion_summary) > 0 or len(overwrite_summary) > 0:
        # Display summary of deletions and overwrites
        for summary in deletion_summary + overwrite_summary:
            print(summary)

        if input("Proceed with these changes? (y/n): ").strip().lower() == 'y':
            # Perform deletions
            for path in delete_candidates:
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                        print(f"Deleted directory: {path}")
                    else:
                        os.remove(path)
                        print(f"Deleted {path}")
                except Exception as e:
                    error_paths.append(f"Error deleting {path}: {e}")

            # Perform overwrites
            for target_file in overwrite_candidates:
                try:
                    relative_path = os.path.relpath(target_file, target)
                    source_file = os.path.join(source, relative_path)
                    shutil.copy2(source_file, target_file, follow_symlinks=False)
                    print(f"Overwritten {target_file}")
                except Exception as e:
                    error_paths.append(f"Error overwriting {target_file}: {e}")

    # Proceed to copy files regardless of the confirmation for deletions/overwrites
    for source_file, target_file in copy_candidates:
        try:
            target_dir = os.path.dirname(target_file)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            shutil.copy2(source_file, target_file, follow_symlinks=False)
            print(f"Copied {source_file} to {target_file}")
        except Exception as e:
            error_paths.append(f"Error copying {source_file}: {e}")

    # After all operations, print out any errors that occurred
    if error_paths:
        print("\nThe script encountered errors with the following paths:")
        for path in error_paths:
            print(path)

if __name__ == "__main__":
    args = parse_arguments()

    # Set the default directories
    source_dir = args.source
    target_dir = args.target

    # You might still want to check if the script is being run from the target directory
    # and swap the source and target if necessary
    if not os.getcwd().startswith(target_dir):
        source_dir, target_dir = target_dir, source_dir

    sync_directories(source_dir, target_dir)
