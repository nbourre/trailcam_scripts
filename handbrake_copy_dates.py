"""_summary_
    Script to copy the creation and modification dates from the original video files to the converted ones.
    This was necessary because Handbrake does not preserve the original dates when converting videos.
Returns:
    _type_: _description_
"""

import exiftool
import os
from datetime import datetime
import re

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
