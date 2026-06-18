import cv2
import csv
import os
import numpy as np
from ultralytics import YOLO

DEFAULT_RESULTS_CSV = "results.csv"
DEFAULT_ANIMAL_CSV = "animal_results.csv"
DEFAULT_ROI_FILE = "roi.txt"

ANIMAL_LABELS = {'cat', 'dog', 'bird', 'crow', 'squirrel', 'turkey', 'bear', 'deer', 'rabbit', 'fox', 'wolf', 'elk', 'moose', 'coyote', 'bobcat', 'raccoon', 'opossum', 'skunk'}

def get_video_files(folder, extensions=('.mp4', '.avi', '.mov')):
    results = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(extensions)]
    return results


# Scan a video for motion and return True if motion is detected
def movement_scan(filename, threshold, display_output=False):
    print("Scanning file: " + filename)
    cap = cv2.VideoCapture(filename)
    mog = cv2.createBackgroundSubtractorMOG2()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Apply histogram equalization to increase contrast
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame = cv2.equalizeHist(frame)

        # Apply ROI mask
        try:
            with open(DEFAULT_ROI_FILE, "r") as f:
                x, y, w, h = map(int, f.read().strip().split(','))
            frame = frame[y:y+h, x:x+w]
        except FileNotFoundError:
            pass  # Process full frame if no ROI file

        
        if display_output:
            cv2.imshow('Motion Detection', frame)
            cv2.waitKey(1)

        frame_width = frame.shape[1]
        frame_height = frame.shape[0]
        frame_area = (frame_width * frame_height) / 2.0
        
        fgmask = mog.apply(frame)
        contours, _ = cv2.findContours(fgmask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            contour_area = cv2.contourArea(contour)
            if contour_area < frame_area and contour_area > threshold:
                if display_output:
                    # Draw a bounding box around the moving object
                    x, y, w, h = cv2.boundingRect(contour)
                    frame = cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

                    # Show the frame with the moving object
                    cv2.imshow('Motion Detection', frame)

                    # Wait for a key press and quit if 'q' is pressed
                    if cv2.waitKey(1) &  0xFF == ord('q'):
                        break
                cap.release()
                cv2.destroyAllWindows()
                return True
        
    cap.release()
    cv2.destroyAllWindows()
    return False

# Load the YOLOv8 nano model (fastest)
yolo_model = YOLO("yolov8n.pt")  # First run will auto-download the model
yolo_model.to('cuda')  # Use GPU if available

def test_gpu():
    import torch
    from ultralytics import YOLO

    print("Checking PyTorc and YOLO GPU availability...")
    print(f"PyTorch CUDA available: {torch.cuda.is_available()}")

    try:
        model = YOLO("yolov8n.pt")
        model.to("cuda")
        print("✅ YOLO model successfully moved to GPU.")
    except Exception as e:
        print("❌ Failed to move YOLO to GPU.")
        print(f"Error: {e}")

# Detect animals in one video and return True if any are found
def detect_animals_yolo(filename, display_output=False, conf_threshold=0.25):
    print(f"Scanning file for animals: {filename}")
    cap = cv2.VideoCapture(filename)

    if not cap.isOpened():
        print("Failed to open video.")
        return False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Resize for faster processing (50%)
        frame_small = cv2.resize(frame, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

        # Run YOLO inference on the frame
        results = yolo_model.predict(source=frame_small, conf=conf_threshold, verbose=False)

        # Filter results to only animal classes
        for r in results:
            for c in r.boxes.cls:
                label = yolo_model.names[int(c)]
                if label in ANIMAL_LABELS:
                    if display_output:
                        cv2.imshow("Animal Detection", frame_small)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    cap.release()
                    cv2.destroyAllWindows()
                    return True

    cap.release()
    cv2.destroyAllWindows()
    return False

def scan_folder_for_animals(results_csv=DEFAULT_RESULTS_CSV, output_csv='animal_results.csv', display_output=False):
    if not os.path.exists(results_csv):
        print(f"File not found: {results_csv}")
        return

    with open(results_csv, 'r', newline='') as infile, open(output_csv, 'w', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        header = next(reader)
        if len(header) < 2:
            print("Invalid header in results.csv")
            return

        writer.writerow(["Filename", "Movement Detected", "Animal Detected"])

        for row in reader:
            if len(row) < 2:
                continue
            filepath, movement_detected = row[0], row[1]
            if movement_detected.lower() == 'true':
                animal_detected = detect_animals_yolo(filepath, display_output)
            else:
                animal_detected = False
            writer.writerow([filepath, movement_detected, animal_detected])

# Scan a folder for motion in videos and write the results to a CSV file
def scan_folder(folder_path, extensions='.mp4', display_output=False, threshold=1000):
    extensions = tuple(extensions.split(','))

    with open(DEFAULT_RESULTS_CSV, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Filename", "Movement Detected"])
        for filepath in get_video_files(folder_path, extensions):
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
        print ("No last played file found")
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
                video_path = os.path.join(folder_path, filename)
                print("Playing video:", video_path)
                cap = cv2.VideoCapture(video_path)

                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    frame_small = cv2.resize(frame, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

                    # Display filename in the upper right corner
                    cv2.putText(frame_small, filename, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.imshow('Motion Video', frame_small)

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
                    elif key & 0xFF == ord('p'):
                        # Pause
                        cv2.waitKey(0)

                cap.release()

    cv2.destroyAllWindows()

def set_roi(folder_path, roi_file=DEFAULT_ROI_FILE):
    import cv2
    import os

    # Get first video in folder
    for fname in os.listdir(folder_path):
        if fname.lower().endswith(('.mp4', '.avi', '.mov')):
            video_path = os.path.join(folder_path, fname)
            break
    else:
        print("No video found in folder.")
        return

    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("Failed to read video.")
        return

    h, w = frame.shape[:2]
    roi = [0, 0, w, h]  # x, y, width, height

    print("Controls:")
    print("WASD - move ROI")
    print("IJKL - resize ROI")
    print("R - reset")
    print("Q - save and quit")

    while True:
        display_frame = frame.copy()
        x, y, rw, rh = roi
        cv2.rectangle(display_frame, (x, y), (x+rw, y+rh), (0, 255, 0), 2)
        cv2.putText(display_frame, "Use WASD to move, IJKL to resize, Q to save", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.imshow("Set ROI", display_frame)

        key = cv2.waitKey(0) & 0xFF
        if key == ord('w'): roi[1] = max(0, roi[1] - 10)
        elif key == ord('s'): roi[1] = min(h - roi[3], roi[1] + 10)
        elif key == ord('a'): roi[0] = max(0, roi[0] - 10)
        elif key == ord('d'): roi[0] = min(w - roi[2], roi[0] + 10)
        elif key == ord('i'): roi[3] = min(h - roi[1], roi[3] + 10)
        elif key == ord('k'): roi[3] = max(20, roi[3] - 10)
        elif key == ord('j'): roi[2] = max(20, roi[2] - 10)
        elif key == ord('l'): roi[2] = min(w - roi[0], roi[2] + 10)
        elif key == ord('r'): roi = [0, 0, w, h]
        elif key == ord('q'):
            with open(roi_file, 'w') as f:
                f.write(','.join(map(str, roi)))
            print(f"ROI saved to {roi_file}: {roi}")
            break

    cv2.destroyAllWindows()


def main():
    folder_name = "D:\\temp\\trail_cam\\DCIM_250621_250714\\100MEDIA"

    while True:
        print("\nMenu:")
        print("1. Set Region of Interest")
        print("2. Scan folder for motion videos")
        print("3. Scan folder for animal detection")
        print("4. Play videos with motion")
        print("5. Test GPU")
        print("6. Quit")

        choice = input("Enter your choice (1/2/3/4): ").strip()

        if choice == '1':
            set_roi(folder_name)
        elif choice == '2':
            scan_folder(folder_name, display_output=False)
        elif choice == '4':
            print ("Press 'q' to quit or 'n' to skip to the next video")
            print ("Press 'p' to pause the video")
            print ("The last played video is saved to a text file")
            play_videos_with_motion('', DEFAULT_RESULTS_CSV)
        elif choice == '3':
            scan_folder_for_animals(DEFAULT_RESULTS_CSV, DEFAULT_ANIMAL_CSV, display_output=True)
        elif choice == '5':
            test_gpu()
        elif choice == '6':
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Please enter 1, 2, 3 or 4.")

if __name__ == "__main__":
    main()