import csv
import os

# Define the path to the CSV file containing the old and new file names

def revert_names(csv_path):
    # Open the CSV file and read its contents
    with open(csv_path, "r") as csvfile:
        reader = csv.reader(csvfile)
        # Skip the header row
        next(reader)
        # For each row in the CSV file
        for row in reader:
            # Get the old and new file names
            old_name = row[0]
            new_name = row[1]
            # Rename the file back to its old name
            os.rename(new_name, old_name)

def main():
    csv_path = "./renamed_files.csv"
    revert_names(csv_path)

if __name__ == "__main__":
    main()