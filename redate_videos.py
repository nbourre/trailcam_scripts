import exiftool
import os
import csv
from datetime import datetime, timedelta

def get_video_tag(filename, tag):
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        tags = et.get_tags(filename, tag)
        #all_tags = et.get_tags(filename, None)
        return tags[0][tag]

def get_video_all_tags(filename):
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        all_tags = et.get_tags(filename, None)
        return all_tags

def set_video_tag(filename, tag, value):
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        et.set_tags(filename, {tag: value})

def set_video_tags(filename, tags):
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        et.set_tags(filename, tags)

def change_video_dates(filename, date):
    date_str = date.strftime('%Y:%m:%d %H:%M:%S%z')
    set_video_tags(filename, {'File:FileModifyDate': date_str, 'File:FileCreateDate': date_str, 
                              'QuickTime:ModifyDate':date_str, 'QuickTime:CreateDate' : date_str, 
                              'QuickTime:MediaModifyDate':date_str, 'QuickTime:MediaCreateDate':date_str})

    # Update the modification time of the video file to the current time
    
    date_tz = date.replace(tzinfo=None)	# Remove the timezone
    date_int = int(date_tz.timestamp())
    os.utime(filename, (date_int, date_int))

def change_video_creation_date_by_date(filename, date):
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        et.set_tags(filename, {'File:FileCreateDate': date})
        #et.execute("-DateTimeOriginal={}".format(date), filename)
    os.utime(filename, date)

def change_video_creation_date_by_offset(filename, offset):
    with exiftool.ExifToolHelper(executable=r'E:\outils\exiftool\exiftool(-k).exe') as et:
        # Get the original creation date of the video file
        #metadata = et.get_metadata(filename)
        tags = et.get_tags(filename, 'File:FileCreateDate')
        #creation_date_str = metadata['MediaCreateDate']
        creation_date_str = tags[0]['File:FileCreateDate']
        creation_date_format = '%Y:%m:%d %H:%M:%S%z'
        
        #creation_date = datetime.strptime(creation_date_str, '%Y:%m:%d %H:%M:%S')
        creation_date = datetime.strptime(creation_date_str, creation_date_format)
        
        # Calculate the new creation date based on the offset
        new_creation_date = creation_date + timedelta(days=offset)
        new_creation_date_str = new_creation_date.strftime('%Y:%m:%d %H:%M:%S%z')
        
        # Update the MediaCreateDate metadata of the video file to the new date
        # et.execute(f'-CreateDate="{new_creation_date_str}"', filename)

        new_date = {'File:FileCreateDate': new_creation_date_str}
        et.set_tags(filename, new_date)
        
        # Update the modification time of the video file to the current time
        os.utime(filename, new_creation_date)

def change_videos_creation_date_in_folder(folder_path, offset):
    for filename in os.listdir(folder_path):
        if filename.endswith('.mp4') or filename.endswith('.mov') or filename.endswith('.avi'):
            full_path = os.path.join(folder_path, filename)
            if (isinstance(offset, datetime)):
                change_video_creation_date_by_date(full_path, offset)
            else:
                change_video_creation_date_by_offset(full_path, offset)

# From revert_names.py
def get_old_date(csv_row):
    # Get the old and new file names
    old_name = csv_row[0]

    # Old names are in the original folder
    old_name = os.path.join(r'D:\temp\DCIM\100DSCIM\original', old_name)
    
    if not os.path.exists(old_name):
        return None
    
    # Get the creation date of the old file
    old_date = get_video_tag(old_name, 'File:FileModifyDate')
    return old_date

def set_new_date(csv_row, new_date):
    # Get the old and new file names
    new_name = csv_row[2]

    # New names are in the todo folder
    new_name = os.path.join(r'D:\photos\2022\camera_chasse', new_name)

    # Check if the file exists
    if not os.path.exists(new_name):
        return None
    
    # Get the creation date of the old file
    change_video_dates(new_name, new_date)

def batch_date_change():
    csv_path = "./renamed_files_new.csv"
    with open(csv_path, "r") as csvfile:
        reader = csv.reader(csvfile)
        # Skip the header row
        next(reader)
        # For each row in the CSV file
        for row in reader:
            old_date_str = get_old_date(row)

            if (old_date_str is None):
                continue

            old_date_format = '%Y:%m:%d %H:%M:%S%z'
            old_date = datetime.strptime(old_date_str, old_date_format)

            # Calculate offset date
            offset_date = old_date + timedelta(days=4206.32)
            #offset_date_str = offset_date.strftime('%Y:%m:%d %H:%M:%S%z')

            #print(old_date_str + ' -> ' + offset_date_str)
            try:
                set_new_date(row, offset_date)
                # Move the backup file to the done folder
                backup_fn = row[2] + '_original'
                backup_name = os.path.join(r'D:\photos\2022\camera_chasse', backup_fn)
                done_name = os.path.join(r'D:\temp\DCIM\100DSCIM\done', backup_fn)
                os.rename(backup_name, done_name)
            except:
                print('Error with file ' + row[2])

            


def main():
    batch_date_change()
    # folder = r'D:\temp\DCIM\100DSCIM\converted'
    # offset = datetime.now()
    # change_videos_creation_date_in_folder(folder, offset)

if __name__ == "__main__":
    main()