import csv
import os

# Define the path to the CSV file and the directory containing the video files
csv_path = "./_log.csv"
video_dir = "./"

# Define the path to the CSV file that will contain the old and new file names
output_csv_path = "./renamed_files.csv"

# Open the output CSV file and write the header row
with open(output_csv_path, "w", newline="") as output_csv:
    writer = csv.writer(output_csv)
    writer.writerow(["Old Name", "New Name"])

    # Open the CSV file and read its contents
    with open(csv_path, "r") as csvfile:
        reader = csv.reader(csvfile, delimiter=";")
        # For each row in the CSV file
        for row in reader:
            # Get the content name and the starting video number
            content = row[0]
            start_num = int(row[1])
            # If there is an end video number, rename all the videos in the sequence
            if len(row) > 2:
                end_num = int(row[2])
                # For each video in the sequence
                for i in range(start_num, end_num+1):
                    # Generate the old and new file names
                    old_name = "PICT{:04d}.avi".format(i)
                    new_name = "{}_{:04d}.avi".format(content, i)
                    # Rename the file and write the old and new names to the output CSV file
                    os.rename(os.path.join(video_dir, old_name), os.path.join(video_dir, new_name))
                    writer.writerow([old_name, new_name])
            # If there is only one video for the content, rename it
            else:
                old_name = "PICT{:04d}.avi".format(start_num)
                new_name = "{}_{:04d}.avi".format(content, start_num)
                os.rename(os.path.join(video_dir, old_name), os.path.join(video_dir, new_name))
                writer.writerow([old_name, new_name])
