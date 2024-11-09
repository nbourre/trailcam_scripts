import os
import csv
import re
from datetime import datetime, timedelta
import exiftool

# Path to ExifTool
EXIFTOOL_PATH = r'E:\outils\exiftool\exiftool(-k).exe'

def exiftool_execute(filename, tags=None, set_tags=None):
    """
    Helper to execute ExifTool operations.
    :param filename: Path to the file.
    :param tags: Tags to retrieve (list or single string).
    :param set_tags: Tags to set (dictionary).
    :return: Retrieved tags if `tags` is provided.
    """
    with exiftool.ExifToolHelper(executable=EXIFTOOL_PATH) as et:
        if tags:
            return et.get_tags(filename, tags)
        if set_tags:
            et.set_tags(filename, set_tags)

def get_date_tag(filename, tag):
    """Retrieve a specific date tag from a file."""
    tags = exiftool_execute(filename, tags=tag)
    return tags[0].get(tag)

def set_date_tag(filename, tag, date):
    """Set a specific date tag in a file."""
    date_str = date.strftime('%Y:%m:%d %H:%M:%S%z')
    exiftool_execute(filename, set_tags={tag: date_str})

def update_date_with_offset(filename, tag, offset_days):
    """Update a file's date by an offset in days."""
    original_date_str = get_date_tag(filename, tag)
    if original_date_str:
        original_date = datetime.strptime(original_date_str, '%Y:%m:%d %H:%M:%S%z')
        new_date = original_date + timedelta(days=offset_days)
        set_date_tag(filename, tag, new_date)
        os.utime(filename, (new_date.timestamp(), new_date.timestamp()))

def change_video_dates(filename, date):
    """
    Set multiple date tags in a video file to the same specified date.
    """
    date_str = date.strftime('%Y:%m:%d %H:%M:%S%z')
    tags = {
        'File:FileModifyDate': date_str,
        'File:FileCreateDate': date_str,
        'QuickTime:ModifyDate': date_str,
        'QuickTime:CreateDate': date_str,
        'QuickTime:MediaModifyDate': date_str,
        'QuickTime:MediaCreateDate': date_str
    }
    exiftool_execute(filename, set_tags=tags)
    os.utime(filename, (date.timestamp(), date.timestamp()))

def batch_update_dates(csv_path, offset_days):
    """
    Batch update dates for videos using CSV data.
    """
    with open(csv_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header
        for row in reader:
            original_date_str = get_date_tag(row[0], 'File:FileModifyDate')
            if original_date_str:
                original_date = datetime.strptime(original_date_str, '%Y:%m:%d %H:%M:%S%z')
                new_date = original_date + timedelta(days=offset_days)
                set_date_tag(row[2], 'File:FileCreateDate', new_date)
                print(f"Updated {row[2]}")

def redate_video_by_filename(filepath, filename_date_pattern):
    """
    Update a video file's metadata to match the date in its filename.
    """
    match = re.search(filename_date_pattern, os.path.basename(filepath))
    if match:
        date_str = f"{match.group(1)}-{match.group(2)} {match.group(3)}"
        file_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        change_video_dates(filepath, file_date)

def main():
    # Define folder paths and parameters
    folder_path = r'D:\path\to\videos'
    offset_days = (datetime.now() - datetime(2024, 5, 9)).days
    
    # Update files in a folder with an offset
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.mp4', '.mov', '.avi')):
            update_date_with_offset(os.path.join(folder_path, filename), 'File:FileModifyDate', offset_days)

if __name__ == "__main__":
    main()
