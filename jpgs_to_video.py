import os
import re
import sys
import json
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor

DEFAULT_FRAME_RATE = 4
DEFAULT_MAX_WORKERS = 1  # 4K encodes are memory heavy; increase only if your machine can handle it
DEFAULT_FFMPEG_THREADS = 4  # Per-process encoder threads
DEFAULT_OUTPUT_RESOLUTION = '1920x1080'
DEFAULT_SEARCH_DEPTH = 2
DEFAULT_FFMPEG_PATH = 'ffmpeg'
DEFAULT_INTERNAL_LIST_NAME = '.ffmpeg_concat_list.txt'
DEFAULT_INTERNAL_SUBTITLE_NAME = '.ffmpeg_frame_labels.srt'
DEFAULT_VIDEO_EXTENSIONS = ('.MP4', '.MOV', '.AVI', '.MTS', '.M2TS', '.MKV')
DEFAULT_VIDEO_ACTION = 'ask'
DEFAULT_FRAMES_PER_VIDEO = 3
DEFAULT_ACTION = 'timelapse'
CONFIG_FILE_PATH = os.path.splitext(os.path.abspath(__file__))[0] + '.json'


def parse_output_resolution(value):
    cleaned = value.strip().lower()
    if cleaned in ('source', 'original', 'none'):
        return 'source'

    parts = cleaned.split('x')
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("Resolution must be like 1920x1080 or 'source'.")

    width, height = parts
    if not width.isdigit() or not height.isdigit():
        raise argparse.ArgumentTypeError("Resolution must be numeric, e.g. 1920x1080.")

    if int(width) <= 0 or int(height) <= 0:
        raise argparse.ArgumentTypeError("Resolution values must be > 0.")

    return f"{int(width)}x{int(height)}"


def parse_video_action(value):
    cleaned = value.strip().lower()
    if cleaned not in ('ask', 'extract', 'skip'):
        raise argparse.ArgumentTypeError("video-action must be one of: ask, extract, skip")
    return cleaned


def parse_action(value):
    cleaned = value.strip().lower()
    allowed = ('timelapse', 'create-jpg', 'create-jpg-and-timelapse')
    if cleaned not in allowed:
        raise argparse.ArgumentTypeError(
            "action must be one of: timelapse, create-jpg, create-jpg-and-timelapse"
        )
    return cleaned


def get_builtin_defaults():
    return {
        'start_dir': os.getcwd(),
        'depth': DEFAULT_SEARCH_DEPTH,
        'frame_rate': DEFAULT_FRAME_RATE,
        'max_workers': DEFAULT_MAX_WORKERS,
        'ffmpeg_threads': DEFAULT_FFMPEG_THREADS,
        'output_resolution': DEFAULT_OUTPUT_RESOLUTION,
        'ffmpeg_path': DEFAULT_FFMPEG_PATH,
        'write_file_list': False,
        'file_list_name': 'jpg_files.txt',
        'dry_run': False,
        'dry_run_details': False,
        'video_action': DEFAULT_VIDEO_ACTION,
        'frames_per_video': DEFAULT_FRAMES_PER_VIDEO,
        'action': DEFAULT_ACTION,
    }


def load_config_defaults(config_path):
    defaults = get_builtin_defaults()
    if not os.path.isfile(config_path):
        return defaults

    try:
        with open(config_path, 'r', encoding='utf-8') as handle:
            config = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Warning: could not read config '{config_path}': {error}")
        return defaults

    if not isinstance(config, dict):
        print(f"Warning: invalid config format in '{config_path}', expected JSON object.")
        return defaults

    if 'start_dir' in config and isinstance(config['start_dir'], str):
        defaults['start_dir'] = config['start_dir']
    if 'depth' in config and isinstance(config['depth'], int) and config['depth'] > 0:
        defaults['depth'] = config['depth']
    if 'frame_rate' in config and isinstance(config['frame_rate'], int) and config['frame_rate'] > 0:
        defaults['frame_rate'] = config['frame_rate']
    if 'max_workers' in config and isinstance(config['max_workers'], int) and config['max_workers'] > 0:
        defaults['max_workers'] = config['max_workers']
    if 'ffmpeg_threads' in config and isinstance(config['ffmpeg_threads'], int) and config['ffmpeg_threads'] > 0:
        defaults['ffmpeg_threads'] = config['ffmpeg_threads']
    if 'output_resolution' in config and isinstance(config['output_resolution'], str):
        try:
            defaults['output_resolution'] = parse_output_resolution(config['output_resolution'])
        except argparse.ArgumentTypeError:
            pass
    if 'ffmpeg_path' in config and isinstance(config['ffmpeg_path'], str):
        defaults['ffmpeg_path'] = config['ffmpeg_path']
    if 'write_file_list' in config and isinstance(config['write_file_list'], bool):
        defaults['write_file_list'] = config['write_file_list']
    if 'file_list_name' in config and isinstance(config['file_list_name'], str):
        defaults['file_list_name'] = config['file_list_name']
    if 'dry_run' in config and isinstance(config['dry_run'], bool):
        defaults['dry_run'] = config['dry_run']
    if 'dry_run_details' in config and isinstance(config['dry_run_details'], bool):
        defaults['dry_run_details'] = config['dry_run_details']
    if 'video_action' in config and isinstance(config['video_action'], str):
        try:
            defaults['video_action'] = parse_video_action(config['video_action'])
        except argparse.ArgumentTypeError:
            pass
    if 'frames_per_video' in config and isinstance(config['frames_per_video'], int) and config['frames_per_video'] > 0:
        defaults['frames_per_video'] = config['frames_per_video']
    if 'action' in config and isinstance(config['action'], str):
        try:
            defaults['action'] = parse_action(config['action'])
        except argparse.ArgumentTypeError:
            pass

    return defaults


def save_config_defaults(config_path, args):
    config = {
        'start_dir': args.start_dir,
        'depth': args.depth,
        'frame_rate': args.frame_rate,
        'max_workers': args.max_workers,
        'ffmpeg_threads': args.ffmpeg_threads,
        'output_resolution': args.output_resolution,
        'ffmpeg_path': args.ffmpeg_path,
        'write_file_list': args.write_file_list,
        'file_list_name': args.file_list_name,
        'dry_run': args.dry_run,
        'dry_run_details': args.dry_run_details,
        'video_action': args.video_action,
        'frames_per_video': args.frames_per_video,
        'action': args.action,
    }
    with open(config_path, 'w', encoding='utf-8') as handle:
        json.dump(config, handle, indent=2)


def write_folder_file_list(root, jpg_files, list_name):
    list_path = os.path.join(root, list_name)
    with open(list_path, 'w', encoding='utf-8') as handle:
        for filename in jpg_files:
            handle.write(f"{filename}\n")


def get_ffprobe_path(ffmpeg_path):
    ffmpeg_name = os.path.basename(ffmpeg_path).lower()
    if ffmpeg_name in ('ffmpeg', 'ffmpeg.exe'):
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        if ffmpeg_dir:
            candidate = os.path.join(ffmpeg_dir, 'ffprobe.exe' if ffmpeg_name.endswith('.exe') else 'ffprobe')
            if os.path.isfile(candidate):
                return candidate
    return 'ffprobe'


def get_video_duration_seconds(video_path, ffprobe_path):
    cmd = [
        ffprobe_path,
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path,
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def extract_frames_from_videos(root, video_files, ffmpeg_path, frames_per_video=3):
    ffprobe_path = get_ffprobe_path(ffmpeg_path)
    extracted_files = []

    for video_file in video_files:
        video_path = os.path.join(root, video_file)
        video_stem = os.path.splitext(video_file)[0]
        safe_stem = re.sub(r'[^A-Za-z0-9._-]+', '_', video_stem).strip('._-') or 'video'
        try:
            duration = get_video_duration_seconds(video_path, ffprobe_path)
        except (subprocess.CalledProcessError, ValueError) as error:
            print(f"ERROR probing {video_file}: {error}")
            continue

        if duration <= 0:
            print(f"Skipping {video_file}: invalid duration")
            continue

        timestamps = [duration * (i + 1) / (frames_per_video + 1) for i in range(frames_per_video)]
        for frame_index, timestamp in enumerate(timestamps):
            output_name = f"{safe_stem}_{frame_index:02d}.JPG"
            if os.path.exists(os.path.join(root, output_name)):
                duplicate_index = 1
                while True:
                    candidate_name = f"{safe_stem}_{frame_index:02d}_{duplicate_index}.JPG"
                    if not os.path.exists(os.path.join(root, candidate_name)):
                        output_name = candidate_name
                        break
                    duplicate_index += 1

            output_path = os.path.join(root, output_name)
            cmd = [
                ffmpeg_path,
                '-y',
                '-ss', f"{timestamp:.3f}",
                '-i', video_path,
                '-frames:v', '1',
                '-q:v', '2',
                output_path,
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                extracted_files.append(output_name)
            except subprocess.CalledProcessError as error:
                stderr = error.stderr.decode(errors='ignore') if error.stderr else str(error)
                print(f"ERROR extracting frame from {video_file}: {stderr}")

    return extracted_files


def build_concat_list_file(root, jpg_files, list_name):
    list_path = os.path.join(root, list_name)
    with open(list_path, 'w', encoding='utf-8') as handle:
        for filename in jpg_files:
            full_path = os.path.join(root, filename).replace('\\', '/')
            escaped = full_path.replace("'", "'\\''")
            handle.write(f"file '{escaped}'\n")
    return list_path


def _format_srt_timestamp(seconds):
    total_milliseconds = int(round(seconds * 1000))
    hours = total_milliseconds // 3_600_000
    remaining = total_milliseconds % 3_600_000
    minutes = remaining // 60_000
    remaining %= 60_000
    secs = remaining // 1000
    milliseconds = remaining % 1000
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def build_subtitle_file(root, jpg_files, subtitle_name, frame_rate):
    subtitle_path = os.path.join(root, subtitle_name)
    with open(subtitle_path, 'w', encoding='utf-8') as handle:
        for idx, filename in enumerate(jpg_files, start=1):
            start_time = (idx - 1) / frame_rate
            end_time = idx / frame_rate
            handle.write(f"{idx}\n")
            handle.write(f"{_format_srt_timestamp(start_time)} --> {_format_srt_timestamp(end_time)}\n")
            handle.write(f"{filename}\n\n")
    return subtitle_path


def escape_filter_path(path):
    escaped = path.replace('\\', '/')
    escaped = escaped.replace(':', '\\:')
    escaped = escaped.replace("'", "\\'")
    return escaped


def process_folder(root, jpg_files, frame_rate, ffmpeg_threads, output_resolution, ffmpeg_path, write_file_list, file_list_name):
    folder_name = os.path.basename(root)
    output_video = os.path.join(root, f"_{folder_name}_timelapse.mp4")
    concat_list_path = build_concat_list_file(root, jpg_files, DEFAULT_INTERNAL_LIST_NAME)
    subtitle_path = build_subtitle_file(root, jpg_files, DEFAULT_INTERNAL_SUBTITLE_NAME, frame_rate)
    subtitle_filter_path = escape_filter_path(subtitle_path)

    print(f"Starting: {folder_name} ({len(jpg_files)} images)")

    if write_file_list:
        write_folder_file_list(root, jpg_files, file_list_name)

    subtitle_filter = (
        f"subtitles='{subtitle_filter_path}':"
        "force_style='Alignment=7,FontName=Arial,FontSize=16,PrimaryColour=&HFFFFFF&,BackColour=&H80000000&,BorderStyle=3,Outline=1,MarginL=20,MarginV=20'"
    )

    video_filters = [subtitle_filter]
    if output_resolution != 'source':
        width, height = output_resolution.split('x')
        video_filters.insert(0, f"scale={width}:{height}:flags=lanczos")

    # FFmpeg command
    # Use concat demuxer for broad compatibility and SRT subtitles for per-frame filename overlays.
    cmd = [
        ffmpeg_path, '-y',
        '-f', 'concat',
        '-safe', '0',
        '-r', str(frame_rate),
        '-i', concat_list_path,
        '-vf', ','.join(video_filters),
        '-c:v', 'libx264',
        '-threads', str(ffmpeg_threads),
        '-pix_fmt', 'yuv420p',
        output_video
    ]

    try:
        # We use check=True to raise an error if FFmpeg fails
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"DONE: {output_video}")
    except subprocess.CalledProcessError as e:
        print(f"ERROR in {folder_name}: {e.stderr.decode()}")
    finally:
        if os.path.exists(concat_list_path):
            os.remove(concat_list_path)
        if os.path.exists(subtitle_path):
            os.remove(subtitle_path)


def discover_tasks(start_dir, max_depth):
    tasks = []
    video_only_folders = []
    start_dir = os.path.abspath(start_dir)

    for root, dirs, files in os.walk(start_dir):
        rel_path = os.path.relpath(root, start_dir)
        current_depth = 0 if rel_path == '.' else rel_path.count(os.sep) + 1

        if current_depth >= max_depth:
            dirs[:] = []

        jpg_files = sorted([
            filename for filename in files
            if filename.upper().endswith(('.JPG', '.JPEG'))
        ])
        video_files = sorted([
            filename for filename in files
            if filename.upper().endswith(DEFAULT_VIDEO_EXTENSIONS)
        ])
        if jpg_files:
            tasks.append((root, jpg_files))
        elif video_files:
            video_only_folders.append((root, video_files))

    return tasks, video_only_folders


def parse_args(defaults):
    parser = argparse.ArgumentParser(
        description="Create timelapse MP4 files from JPG/JPEG sequences in subfolders."
    )
    parser.add_argument(
        '--start-dir',
        default=defaults['start_dir'],
        help='Start directory to scan (default: current working directory).'
    )
    parser.add_argument(
        '--depth',
        type=int,
        default=defaults['depth'],
        help='Maximum directory depth to scan from --start-dir (default: 2).'
    )
    parser.add_argument(
        '--frame-rate',
        type=int,
        default=defaults['frame_rate'],
        help='Output video framerate (default: 4).'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=defaults['max_workers'],
        help='Number of folders to process in parallel (default: 1).'
    )
    parser.add_argument(
        '--ffmpeg-threads',
        type=int,
        default=defaults['ffmpeg_threads'],
        help='FFmpeg encoder threads per folder (default: 4).'
    )
    parser.add_argument(
        '--output-resolution',
        type=parse_output_resolution,
        default=defaults['output_resolution'],
        help="Output resolution, e.g. 1920x1080 (default) or 'source' to keep original size."
    )
    parser.add_argument(
        '--ffmpeg-path',
        default=defaults['ffmpeg_path'],
        help='FFmpeg executable path (default: ffmpeg).'
    )
    parser.add_argument(
        '--write-file-list',
        action='store_true',
        default=defaults['write_file_list'],
        help='Write a list file with JPG names in each processed folder.'
    )
    parser.add_argument(
        '--file-list-name',
        default=defaults['file_list_name'],
        help='Output file list name when --write-file-list is enabled (default: jpg_files.txt).'
    )
    parser.add_argument(
        '--gui',
        action='store_true',
        help='Interactive CLI mode to configure options before running.'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=defaults['dry_run'],
        help='Preview folders and image counts without running FFmpeg.'
    )
    parser.add_argument(
        '--dry-run-details',
        action='store_true',
        default=defaults['dry_run_details'],
        help='Include first/last JPG filename per folder in dry-run output.'
    )
    parser.add_argument(
        '--video-action',
        type=parse_video_action,
        default=defaults['video_action'],
        help="Action for video-only folders after normal processing: ask, extract, or skip (default: ask)."
    )
    parser.add_argument(
        '--auto-extract-from-videos',
        action='store_true',
        help='Shortcut for --video-action extract.'
    )
    parser.add_argument(
        '--frames-per-video',
        type=int,
        default=defaults['frames_per_video'],
        help='How many equally spaced frames to extract from each video (default: 3).'
    )
    parser.add_argument(
        '--action',
        type=parse_action,
        default=defaults['action'],
        help='Workflow action: timelapse, create-jpg, or create-jpg-and-timelapse.'
    )
    parser.add_argument(
        '--save-config',
        action='store_true',
        help='Save current options to the default config JSON for next runs.'
    )
    return parser.parse_args()


def prompt_text(label, current):
    raw_value = input(f"{label} [{current}]: ").strip()
    return raw_value if raw_value else str(current)


def prompt_int(label, current, minimum=1):
    while True:
        raw_value = input(f"{label} [{current}]: ").strip()
        if not raw_value:
            return current
        try:
            parsed = int(raw_value)
            if parsed < minimum:
                print(f"Please enter a value >= {minimum}.")
                continue
            return parsed
        except ValueError:
            print("Please enter a valid integer.")


def prompt_bool(label, current):
    default_text = 'y' if current else 'n'
    while True:
        raw_value = input(f"{label} (y/n) [{default_text}]: ").strip().lower()
        if not raw_value:
            return current
        if raw_value in ('y', 'yes'):
            return True
        if raw_value in ('n', 'no'):
            return False
        print("Please answer y or n.")


def prompt_resolution(label, current):
    while True:
        raw_value = input(f"{label} [{current}]: ").strip()
        if not raw_value:
            return current
        try:
            return parse_output_resolution(raw_value)
        except argparse.ArgumentTypeError as error:
            print(error)


def prompt_choice(label, current, choices):
    options_text = '/'.join(choices)
    while True:
        raw_value = input(f"{label} ({options_text}) [{current}]: ").strip().lower()
        if not raw_value:
            return current
        if raw_value in choices:
            return raw_value
        print(f"Please choose one of: {options_text}")


def prompt_action_menu(current):
    choices = {
        '1': ('timelapse', 'Create timelapse from existing JPG folders'),
        '2': ('create-jpg', 'Create JPG frames from video-only folders'),
        '3': ('create-jpg-and-timelapse', 'Create JPG frames, then timelapse from those frames'),
    }
    current_choice = '1'
    for key, (action_key, _) in choices.items():
        if action_key == current:
            current_choice = key
            break

    while True:
        print("Action menu:")
        for key, (_, text) in choices.items():
            print(f"  {key}) {text}")
        raw_value = input(f"Choose action [{current_choice}]: ").strip()
        if not raw_value:
            return choices[current_choice][0]
        if raw_value in choices:
            return choices[raw_value][0]
        print("Please enter 1, 2, or 3.")


def apply_gui_overrides(args):
    print("\nInteractive mode (--gui)")
    args.action = prompt_action_menu(args.action)
    args.start_dir = prompt_text('Start directory', args.start_dir)
    args.depth = prompt_int('Search depth', args.depth, minimum=1)
    args.frame_rate = prompt_int('Frame rate', args.frame_rate, minimum=1)
    args.max_workers = prompt_int('Max workers', args.max_workers, minimum=1)
    args.ffmpeg_threads = prompt_int('FFmpeg threads', args.ffmpeg_threads, minimum=1)
    args.frames_per_video = prompt_int('Frames per video for extraction', args.frames_per_video, minimum=1)
    args.output_resolution = prompt_resolution('Output resolution (e.g. 1920x1080 or source)', args.output_resolution)
    args.ffmpeg_path = prompt_text('FFmpeg path', args.ffmpeg_path)
    args.write_file_list = prompt_bool('Write file list in each folder', args.write_file_list)
    if args.write_file_list:
        args.file_list_name = prompt_text('File list name', args.file_list_name)
    args.video_action = prompt_choice('Video-only folder behavior after normal run', args.video_action, ('ask', 'extract', 'skip'))
    args.dry_run = prompt_bool('Dry run (preview only, no encoding)', args.dry_run)
    if args.dry_run:
        args.dry_run_details = prompt_bool('Dry run details (show first/last filename)', args.dry_run_details)
    args.save_config = prompt_bool('Save these settings as defaults for next run', getattr(args, 'save_config', False))
    print()


def print_dry_run_report(tasks, show_details=False):
    total_images = sum(len(jpg_files) for _, jpg_files in tasks)
    print(f"Dry run: {len(tasks)} folders, {total_images} images")
    for root, jpg_files in tasks:
        print(f"- {root} ({len(jpg_files)} images)")
        if show_details and jpg_files:
            print(f"  first: {jpg_files[0]}")
            print(f"  last:  {jpg_files[-1]}")


def ask_extract_video_frames(video_only_folders):
    if not video_only_folders:
        return False

    folder_count = len(video_only_folders)
    video_count = sum(len(video_files) for _, video_files in video_only_folders)
    print(
        f"Found {folder_count} folder(s) with videos but no JPG/JPEG images "
        f"({video_count} video file(s))."
    )

    if not sys.stdin.isatty():
        print("Non-interactive mode detected; skipping frame extraction prompt.")
        return False

    while True:
        answer = input(
            "Extract 3 frames per video at equal intervals and create timelapses from them? (y/n) [n]: "
        ).strip().lower()
        if not answer:
            return False
        if answer in ('y', 'yes'):
            return True
        if answer in ('n', 'no'):
            return False
        print("Please answer y or n.")


def run_timelapse_tasks(tasks, args):
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = [
            executor.submit(
                process_folder,
                root,
                jpg_files,
                args.frame_rate,
                args.ffmpeg_threads,
                args.output_resolution,
                args.ffmpeg_path,
                args.write_file_list,
                args.file_list_name,
            )
            for root, jpg_files in tasks
        ]
        for future in futures:
            future.result()


def extract_for_video_only_folders(video_only_folders, args):
    extraction_tasks = []
    total_extracted = 0
    for root, video_files in video_only_folders:
        print(f"Extracting from videos in: {root}")
        extracted_files = extract_frames_from_videos(root, video_files, args.ffmpeg_path, frames_per_video=args.frames_per_video)
        total_extracted += len(extracted_files)
        if extracted_files:
            extraction_tasks.append((root, sorted(extracted_files)))
    return extraction_tasks, total_extracted


def main():
    defaults = load_config_defaults(CONFIG_FILE_PATH)
    args = parse_args(defaults)

    if args.auto_extract_from_videos:
        args.video_action = 'extract'

    if args.gui:
        apply_gui_overrides(args)

    if args.save_config:
        save_config_defaults(CONFIG_FILE_PATH, args)
        print(f"Saved defaults to {CONFIG_FILE_PATH}")

    start_dir = os.path.abspath(args.start_dir)
    if not os.path.isdir(start_dir):
        raise FileNotFoundError(f"Start directory does not exist: {start_dir}")

    tasks, video_only_folders = discover_tasks(start_dir, args.depth)
    if not tasks and not video_only_folders:
        print("No matching JPG/JPEG files or supported video files found in the selected depth.")
        return

    if args.dry_run:
        if tasks:
            print_dry_run_report(tasks, show_details=args.dry_run_details)
        else:
            print("No matching JPG/JPEG files found in the selected depth.")
        if video_only_folders:
            print(f"Video-only folders (no JPG/JPEG): {len(video_only_folders)}")
        return

    if args.action == 'timelapse':
        if tasks:
            run_timelapse_tasks(tasks, args)
        else:
            print("No JPG folders found for timelapse generation.")

        should_extract = False
        if video_only_folders:
            if args.video_action == 'extract':
                should_extract = True
            elif args.video_action == 'ask':
                should_extract = ask_extract_video_frames(video_only_folders)

        if should_extract:
            extraction_tasks, total_extracted = extract_for_video_only_folders(video_only_folders, args)
            if extraction_tasks:
                print(f"Creating timelapses from extracted frames in {len(extraction_tasks)} folder(s)...")
                run_timelapse_tasks(extraction_tasks, args)
            else:
                print(f"No frames were extracted from video-only folders (total extracted: {total_extracted}).")
        return

    if args.action == 'create-jpg':
        if not video_only_folders:
            print("No video-only folders found to extract JPG frames.")
            return
        _, total_extracted = extract_for_video_only_folders(video_only_folders, args)
        print(f"Extraction completed. Total frames extracted: {total_extracted}")
        return

    if args.action == 'create-jpg-and-timelapse':
        if not video_only_folders:
            print("No video-only folders found to extract JPG frames.")
            return
        extraction_tasks, total_extracted = extract_for_video_only_folders(video_only_folders, args)
        if extraction_tasks:
            print(f"Creating timelapses from extracted frames in {len(extraction_tasks)} folder(s)...")
            run_timelapse_tasks(extraction_tasks, args)
        else:
            print(f"No frames were extracted from video-only folders (total extracted: {total_extracted}).")

if __name__ == "__main__":
    main()