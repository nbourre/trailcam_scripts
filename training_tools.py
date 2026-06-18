import os
import subprocess
import json
from pathlib import Path

CONFIG_FILE = "config.json"
SUMMARY_TEXT_FILE = "dataset_summary.txt"
SUMMARY_JSON_FILE = "dataset_summary.json"
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv']


def load_config():
    if not Path(CONFIG_FILE).exists():
        print("⚠️ Config file not found. Please configure the video folder.")
        return {}

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    print("✅ Configuration saved.")


def config_menu():
    folder = input("📁 Enter the path to the video folder: ").strip()
    if not Path(folder).exists():
        print("❌ Folder does not exist. Try again.")
        return
    config = {"video_folder": folder}
    save_config(config)


def extract_frames_from_folder(
    video_folder: str,
    output_folder: str = "frames",
    frame_interval_sec: float = 2.0
):
    """
    Extract 1 frame every `frame_interval_sec` seconds from all videos in `video_folder`.
    """
    if not Path(video_folder).exists():
        print(f"❌ Video folder '{video_folder}' does not exist.")
        return
        
    video_files = [v for v in Path(video_folder).glob("*") if v.suffix.lower() in VIDEO_EXTENSIONS]
    if not video_files:
        print(f"❌ No supported video files found in '{video_folder}'.")
        return

    os.makedirs(output_folder, exist_ok=True)
    frame_rate = 1 / frame_interval_sec

    for video_path in video_files:
        try:
            _extract_single_video(video_path, Path(output_folder) / video_path.stem, frame_rate)
        except Exception as e:
            print(f"❌ Failed to process {video_path.name}: {e}")


def _extract_single_video(video_path: Path, output_dir: Path, frame_rate: float):
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = str(output_dir / "frame_%04d.jpg")

    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vf", f"fps={frame_rate}",
        "-q:v", "2",
        output_pattern
    ]

    print(f"🔄 Extracting frames from {video_path.name}...")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error extracting frames from {video_path.name}: {e}")
    print(f"✅ Done: {output_dir}")

def dataset_summary():
    config = load_config()
    if not config.get("video_folder"):
        print("❌ No folder configured. Please use the configuration menu first.")
        return

    video_folder = Path(config["video_folder"])
    output_folder = Path("frames")
    summary = {
        "total_videos": 0,
        "total_frames": 0,
        "frames_per_video": {},
        "total_size_mb": 0
    }

    # Count videos
    videos = list(video_folder.glob("*"))
    video_files = [v for v in videos if v.suffix.lower() in VIDEO_EXTENSIONS]
    summary["total_videos"] = len(video_files)

    # Count frames and calculate total size
    for video_file in video_files:
        video_name = video_file.stem
        frame_folder = output_folder / video_name

        if frame_folder.exists():
            frames = list(frame_folder.glob("*.jpg"))
            summary["frames_per_video"][video_name] = len(frames)
            summary["total_frames"] += len(frames)

    # Calculate total size
    if output_folder.exists():
        summary["total_size_mb"] = sum(f.stat().st_size for f in output_folder.glob("**/*.jpg")) / (1024 * 1024)

    # Print summary
    print_summary(summary)

    # Save summary to files
    save_summary_to_files(summary)


def print_summary(summary):
    print("\n==== Dataset Summary ====")
    print(f"📂 Total Videos: {summary['total_videos']}")
    print(f"🖼️ Total Frames: {summary['total_frames']}")
    print(f"💾 Total Size: {summary['total_size_mb']:.2f} MB")
    print("\nFrames per Video:")
    for video_name, frame_count in summary["frames_per_video"].items():
        print(f"  - {video_name}: {frame_count} frames")


def save_summary_to_files(summary):
    # Save to text file
    with open(SUMMARY_TEXT_FILE, "w", encoding="utf-8") as txt_file:
        txt_file.write("==== Dataset Summary ====\n")
        txt_file.write(f"Total Videos: {summary['total_videos']}\n")
        txt_file.write(f"Total Frames: {summary['total_frames']}\n")
        txt_file.write(f"Total Size: {summary['total_size_mb']:.2f} MB\n")
        txt_file.write("\nFrames per Video:\n")
        for video_name, frame_count in summary["frames_per_video"].items():
            txt_file.write(f"  - {video_name}: {frame_count} frames\n")
    print(f"✅ Summary saved to {SUMMARY_TEXT_FILE}")

    # Save to JSON file
    with open(SUMMARY_JSON_FILE, "w", encoding="utf-8") as json_file:
        json.dump(summary, json_file, indent=4)
    print(f"✅ Summary saved to {SUMMARY_JSON_FILE}")


def main_menu():
    while True:
        print("\n==== Trail Cam Video Tools ====")
        print("1. Extract frames from all videos")
        print("2. Configure video folder")
        print("3. Generate Dataset Summary")
        print("0. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            config = load_config()
            if not config.get("video_folder"):
                print("❌ No folder configured. Please use option 2 first.")
                continue
            extract_frames_from_folder(config["video_folder"])
        elif choice == "2":
            config_menu()
        elif choice == "3":
            dataset_summary()
        elif choice == "0":
            print("👋 Goodbye!")
            break
        else:
            print("❓ Invalid choice. Try again.")

if __name__ == "__main__":
    main_menu()