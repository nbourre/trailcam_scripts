import exiftool
import os
import csv
from datetime import datetime, timedelta
import re

def get_video_tag(filename, tag):
    """
    Retrieve the value of a specific tag from a video file using ExifTool.

    :param filename: Path to the video file.
    :param tag: The tag to retrieve.
    :return: The value of the specified tag.
    """
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        tags = et.get_tags(filename, tag)
        return tags[0][tag]

def get_video_all_tags(filename):
    """
    Retrieve all tags from a video file using ExifTool.

    :param filename: Path to the video file.
    :return: A dictionary of all tags and their values.
    """
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        all_tags = et.get_tags(filename, None)
        return all_tags

def set_video_tag(filename, tag, value):
    """
    Set the value of a specific tag in a video file using ExifTool.

    :param filename: Path to the video file.
    :param tag: The tag to set.
    :param value: The value to set for the tag.
    """
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        et.set_tags(filename, {tag: value})

def set_video_tags(filename, tags):
    """
    Set multiple tags in a video file using ExifTool.

    :param filename: Path to the video file.
    :param tags: A dictionary of tags and their values to set.
    """
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        et.set_tags(filename, tags)

def change_video_dates(filename, date):
    """
    Change various date tags in a video file to a specified date using ExifTool.

    :param filename: Path to the video file.
    :param date: The new date to set.
    """
    date_str = date.strftime('%Y:%m:%d %H:%M:%S%z')
    set_video_tags(filename, {'File:FileModifyDate': date_str, 'File:FileCreateDate': date_str, 
                              'QuickTime:ModifyDate': date_str, 'QuickTime:CreateDate': date_str, 
                              'QuickTime:MediaModifyDate': date_str, 'QuickTime:MediaCreateDate': date_str})

    date_tz = date.replace(tzinfo=None)  # Remove the timezone
    date_int = int(date_tz.timestamp())
    os.utime(filename, (date_int, date_int))

def change_video_creation_date_by_date(filename, date):
    """
    Change the creation date of a video file to a specified date using ExifTool.

    :param filename: Path to the video file.
    :param date: The new creation date to set.
    """
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        et.set_tags(filename, {'File:FileCreateDate': date})
    os.utime(filename, date)

def change_video_creation_date_by_offset(filename, offset):
    """
    Change the creation date of a video file by a specified offset using ExifTool.

    :param filename: Path to the video file.
    :param offset: The offset in days to adjust the creation date.
    """
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        tags = et.get_tags(filename, 'File:FileCreateDate')
        creation_date_str = tags[0]['File:FileCreateDate']
        creation_date_format = '%Y:%m:%d %H:%M:%S%z'
        creation_date = datetime.strptime(creation_date_str, creation_date_format)
        new_creation_date = creation_date + timedelta(days=offset)
        new_creation_date_str = new_creation_date.strftime('%Y:%m:%d %H:%M:%S%z')
        new_date = {'File:FileCreateDate': new_creation_date_str}
        et.set_tags(filename, new_date)
        os.utime(filename, new_creation_date)

def change_videos_creation_date_in_folder(folder_path, offset):
    """
    Change the creation date of all video files in a folder by a specified offset using ExifTool.

    :param folder_path: Path to the folder containing video files.
    :param offset: The offset in days to adjust the creation date, or a specific datetime.
    """
    for filename in os.listdir(folder_path):
        if filename.endswith('.mp4') or filename.endswith('.mov') or filename.endswith('.avi'):
            full_path = os.path.join(folder_path, filename)
            if isinstance(offset, datetime):
                change_video_creation_date_by_date(full_path, offset)
            else:
                change_video_creation_date_by_offset(full_path, offset)

# From revert_names.py
def get_old_date(csv_row):
    """
    Retrieve the modification date of the old file based on the CSV row.

    :param csv_row: A row from the CSV file containing old and new file names.
    :return: The modification date of the old file.
    """
    old_name = csv_row[0]
    old_name = os.path.join(r'D:\temp\DCIM\100DSCIM\original', old_name)
    if not os.path.exists(old_name):
        return None
    old_date = get_video_tag(old_name, 'File:FileModifyDate')
    return old_date

def set_new_date(csv_row, new_date):
    """
    Set the creation date of the new file based on the old date.

    :param csv_row: A row from the CSV file containing old and new file names.
    :param new_date: The new date to set.
    """
    new_name = csv_row[2]
    new_name = os.path.join(r'D:\photos\2022\camera_chasse', new_name)
    if not os.path.exists(new_name):
        return None
    change_video_dates(new_name, new_date)

def batch_date_change():
    """
    Batch process to change the dates of multiple video files based on a CSV file.
    """
    csv_path = "./renamed_files_new.csv"
    with open(csv_path, "r") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip the header row
        for row in reader:
            old_date_str = get_old_date(row)
            if old_date_str is None:
                continue
            old_date_format = '%Y:%m:%d %H:%M:%S%z'
            old_date = datetime.strptime(old_date_str, old_date_format)
            offset_date = old_date + timedelta(days=4206.32)
            try:
                set_new_date(row, offset_date)
                backup_fn = row[2] + '_original'
                backup_name = os.path.join(r'D:\photos\2022\camera_chasse', backup_fn)
                done_name = os.path.join(r'D:\temp\DCIM\100DSCIM\done', backup_fn)
                os.rename(backup_name, done_name)
            except:
                print('Error with file ' + row[2])

def extract_datetime_from_filename(filename):
    """
    Extract the datetime from the filename.

    :param filename: The filename to extract the datetime from.
    :return: A datetime object representing the extracted date and time.
    """
    pattern = r'(\d{8}) (\d{6})'
    match = re.search(pattern, filename)
    if match:
        date_str = match.group(1)
        time_str = match.group(2)
        datetime_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
        return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
    else:
        return None
    
def redate_video_file_by_filename(filepath):
    """
    Update the video file's metadata to match the date and time in its filename.

    :param filepath: Path to the video file.
    """
    filename = os.path.basename(filepath)
    file_datetime = extract_datetime_from_filename(filename)
    if file_datetime:
        change_video_dates(filepath, file_datetime)
    else:
        print(f"Filename {filename} does not match the expected pattern.")

def redate_videos_in_folder_by_filename(folder_path):
    """
    Update the metadata of all video files in a folder to match the dates and times in their filenames.

    :param folder_path: Path to the folder containing video files.
    """
    for filename in os.listdir(folder_path):
        if filename.endswith('.mp4') or filename.endswith('.mov') or filename.endswith('.avi'):
            full_path = os.path.join(folder_path, filename)
            redate_video_file_by_filename(full_path)


def get_video_dates(filename):
    """
    Retrieve the creation and modification dates from a video file using ExifTool.

    :param filename: Path to the video file.
    :return: A dictionary with the creation and modification dates.
    """
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        tags = et.get_tags(filename, ['File:FileCreateDate', 'File:FileModifyDate'])
        return {
            'create_date': tags[0].get('File:FileCreateDate'),
            'modify_date': tags[0].get('File:FileModifyDate')
        }

def set_video_dates(filename, dates):
    """
    Set the creation and modification dates in a video file using ExifTool.

    :param filename: Path to the video file.
    :param dates: A dictionary with the new creation and modification dates.
    """
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        et.set_tags(filename, {
            'File:FileCreateDate': dates['create_date'],
            'File:FileModifyDate': dates['modify_date'],
            'QuickTime:CreateDate': dates['create_date'],
            'QuickTime:ModifyDate': dates['modify_date']
        })
    # Adjust the OS-level file times
    date_format = '%Y:%m:%d %H:%M:%S%z'
    create_time = datetime.strptime(dates['create_date'], date_format).timestamp()
    modify_time = datetime.strptime(dates['modify_date'], date_format).timestamp()
    os.utime(filename, (modify_time, create_time))

def match_and_update_dates(original_folder, converted_folder):
    """
    Match converted videos with their original counterparts by handling the replacement of underscores with spaces.
    """
    for converted_filename in os.listdir(converted_folder):
        if converted_filename.lower().endswith(('.mp4', '.mov', '.avi')):
            # Replace spaces with underscores and remove the "-x" suffix
            base_name = re.sub(r'-\d+', '', converted_filename).replace(' ', '_').upper()
            original_filename = base_name

            original_path = os.path.join(original_folder, original_filename)

            if os.path.exists(original_path):
                converted_path = os.path.join(converted_folder, converted_filename)
                dates = get_video_dates(original_path)
                set_video_dates(converted_path, dates)
                print(f"Updated dates for {converted_filename}")
            else:
                print(f"Original file {original_filename} not found for {converted_filename}")


def main():
    """
    Main function to execute the batch date change process.
    """
    # batch_date_change()
    # folder = r'D:\temp\DCIM\100DSCIM\converted'
    # offset = datetime.now()
    # change_videos_creation_date_in_folder(folder, offset)
    
    # folder = r'D:\photos\drone\2023_classique_canoe\video_converted'
    # redate_videos_in_folder_by_filename(folder)
    original_folder = r'D:\photos\drone\2024_europe\100MEDIA'
    converted_folder = original_folder + r'\video_converted'
    
    match_and_update_dates(original_folder, converted_folder)

if __name__ == "__main__":
    main()
