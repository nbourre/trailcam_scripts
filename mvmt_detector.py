import cv2
import csv
import os
import numpy as np

# Scan a video for motion and return True if motion is detected
def movement_scan(filename, threshold, display_output=False):
    print ("Scanning file: " + filename)
    cap = cv2.VideoCapture(filename)
    mog = cv2.createBackgroundSubtractorMOG2()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_width = frame.shape[1]
        frame_height = frame.shape[0]
        frame_area = (frame_width * frame_height) / 2.0

        fgmask = mog.apply(frame)
        contours, _ = cv2.findContours(fgmask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            contour_area = cv2.contourArea(contour)
            #print(contour_area)
            if contour_area < frame_area and contour_area > threshold:
                if display_output:
                    # Draw a bounding box around the moving object
                    x, y, w, h = cv2.boundingRect(contour)
                    frame = cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

                    # Show the frame with the moving object
                    cv2.imshow('Motion Detection', frame)

                    # Wait for a key press and quit if 'q' is pressed
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                cap.release()
                cv2.destroyAllWindows()
                return True
            else:
                continue

    cap.release()
    cv2.destroyAllWindows()
    return False

# Scan a folder for motion in videos and write the results to a CSV file
def scan_folder(folder_path, extensions='.mp4,.AVI', display_output=False, threshold=1000):
    extensions = tuple(extensions.split(','))

    with open('results.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Filename", "Movement Detected"])
        for filename in os.listdir(folder_path):
            if filename.endswith(extensions): 
                filepath = os.path.join(folder_path, filename)
                movement_detected = movement_scan(filepath, threshold, display_output) # example threshold
                writer.writerow([filepath, movement_detected])

# Play videos with motion read from a CSV file
# The CSV file should have two columns: filename and motion_detected
# The user can press 'q' to quit or 'n' to skip to the next video
# The last played video is saved to a text file
def play_videos_with_motion(folder_path='', motion_file='motion_videos.csv', last_played_file='last_played.txt'):
    try:
        with open(last_played_file, 'r') as file:
            last_played = file.readline().strip()
    except FileNotFoundError:
        last_played = ''

    start_playing = (last_played == '')

    with open(motion_file, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header
        for row in reader:
            filename, motion_detected = row

            if filename == last_played:
                start_playing = True
                continue

            if not start_playing:
                continue

            if motion_detected.lower() == 'true':
                cap = cv2.VideoCapture(os.path.join(folder_path, filename))

                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    cv2.imshow('Motion Video', frame)

                    key = cv2.waitKey(1)
                    if key & 0xFF == ord('q'):
                        with open(last_played_file, 'w') as file:
                            file.write(filename)
                        cap.release()
                        cv2.destroyAllWindows()
                        return
                    elif key & 0xFF == ord('n'):
                        # Skip to next video
                        break

                cap.release()

    cv2.destroyAllWindows()

def main():
    folder_name = "D:\\temp\\100DSCIM"
    scan_folder(folder_name)
    play_videos_with_motion('', 'results.csv')

if __name__ == "__main__":
    main()