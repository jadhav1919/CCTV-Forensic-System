import csv
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cv2
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

SNAPSHOT_DIR = OUTPUT_DIR / "snapshots"
EVENT_DIR = OUTPUT_DIR / "events"
SUMMARY_DIR = OUTPUT_DIR / "summaries"

CSV_FILE = DATA_DIR / "events.csv"
METADATA_FILE = SUMMARY_DIR / "metadata.json"

MODEL_PATH = BASE_DIR / "yolo11n.pt"

CSV_COLUMNS = [
    "Event Number",
    "Event Type",
    "Object ID",
    "Frame Number",
    "Timestamp (seconds)",
    "Snapshot",
    "Clip",
    "Video",
]

# ---- Speed tuning --------------------------------------------------
TARGET_FPS = 5.0
INFERENCE_SIZE = 480
# --------------------------------------------------------------------


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clear_old_evidence():
    for folder in (SNAPSHOT_DIR, EVENT_DIR, SUMMARY_DIR):
        folder.mkdir(parents=True, exist_ok=True)
        for path in folder.iterdir():
            try:
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            except OSError as error:
                raise RuntimeError(
                    f"Cannot clear evidence file: {path}. "
                    f"Close applications using this file and retry. "
                    f"Details: {error}"
                ) from error
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _find_ffmpeg():
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def create_clip(video_path, output_path, start_time, end_time):
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return False
    duration = max(0.1, end_time - start_time)
    command = [
        ffmpeg, "-y",
        "-ss", f"{start_time:.3f}",
        "-i", str(video_path),
        "-t", f"{duration:.3f}",
        "-an",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
        )
        return result.returncode == 0 and output_path.exists()
    except (subprocess.SubprocessError, OSError):
        return False


def inside_roi(point_x, point_y, roi):
    x, y, width, height = roi
    return x <= point_x <= x + width and y <= point_y <= y + height


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python src\\process_video.py VIDEO_PATH "
            "[ROI_X ROI_Y ROI_WIDTH ROI_HEIGHT]"
        )
        return 1

    video_path = Path(sys.argv[1]).resolve()

    if not video_path.is_file():
        print(f"ERROR: Video file not found: {video_path}")
        return 1

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        print("ERROR: OpenCV could not open this video.")
        return 1

    fps = capture.get(cv2.CAP_PROP_FPS)
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if fps <= 0 or total_frames <= 0:
        capture.release()
        print("ERROR: Invalid video FPS or frame count.")
        return 1

    duration = total_frames / fps
    frame_skip = max(1, int(round(fps / TARGET_FPS)))
    effective_fps = fps / frame_skip
    expected_samples = max(1, int(round(duration * effective_fps)))

    if len(sys.argv) >= 6:
        try:
            roi = tuple(int(value) for value in sys.argv[2:6])
        except ValueError:
            capture.release()
            print("ERROR: ROI values must be integers.")
            return 1
    else:
        roi_file = DATA_DIR / "roi.txt"
        if not roi_file.exists():
            capture.release()
            print("ERROR: Configure a restricted area in the dashboard.")
            return 1
        try:
            roi = tuple(
                int(value.strip())
                for value in roi_file.read_text().strip().split(",")
            )
        except ValueError:
            capture.release()
            print("ERROR: Invalid data/roi.txt format.")
            return 1

    if len(roi) != 4:
        capture.release()
        print("ERROR: ROI must contain x,y,width,height.")
        return 1

    x, y, width, height = roi

    if (
        x < 0 or y < 0 or width <= 0 or height <= 0
        or x + width > frame_width
        or y + height > frame_height
    ):
        capture.release()
        print(
            f"ERROR: ROI {roi} is outside the video dimensions "
            f"{frame_width}x{frame_height}."
        )
        return 1

    if not MODEL_PATH.exists():
        capture.release()
        print(f"ERROR: YOLO model not found: {MODEL_PATH}")
        return 1

    try:
        model = YOLO(str(MODEL_PATH))
    except Exception as error:
        capture.release()
        print(f"ERROR: Could not load YOLO model: {error}")
        return 1

    clear_old_evidence()

    video_hash = sha256_file(video_path)
    started = time.perf_counter()

    print(f"Video: {video_path.name}")
    print(f"Resolution: {frame_width}x{frame_height}")
    print(f"Source FPS: {fps:.2f}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Restricted area: {roi}")
    print(
        f"Analysing at {effective_fps:.2f} FPS "
        f"(skipping every {frame_skip} frames, "
        f"~{expected_samples} samples total)"
    )
    print(f"YOLO inference size: {INFERENCE_SIZE}")
    print("Processing on the available device...")

    events = []
    frame_number = 0
    processed_samples = 0

    pre_seconds = 5
    post_seconds = 5

    COOLDOWN_SECONDS = 5.0
    EXIT_GRACE_SECONDS = 1.5
    REASSOC_DISTANCE = 150
    REASSOC_TIME = 2.0

    person_id_for_track = {}
    recent_tracks = {}
    person_has_entered = {}
    person_outside_since = {}
    person_last_event_ts = {}
    next_person_id = 1

    while True:
        if not capture.grab():
            break
        frame_number += 1

        if (frame_number - 1) % frame_skip != 0:
            continue

        success, frame = capture.retrieve()
        if not success:
            break

        processed_samples += 1
        timestamp = (frame_number - 1) / fps

        results = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],
            conf=0.25,
            imgsz=INFERENCE_SIZE,
            verbose=False,
        )

        detections = []
        result = results[0]

        if result.boxes is not None and result.boxes.id is not None:
            boxes = result.boxes.xyxy.cpu().tolist()
            track_ids = result.boxes.id.int().cpu().tolist()

            for box, track_id in zip(boxes, track_ids):
                track_id = int(track_id)
                x1, y1, x2, y2 = [int(value) for value in box]
                point_x = int((x1 + x2) / 2)
                point_y = int(y2)

                if track_id not in person_id_for_track:
                    matched_person = None
                    best_dist = REASSOC_DISTANCE
                    for old_tid, (old_ts, old_pt) in recent_tracks.items():
                        if old_tid == track_id:
                            continue
                        if timestamp - old_ts > REASSOC_TIME:
                            continue
                        if old_tid not in person_id_for_track:
                            continue
                        dist = (
                            (point_x - old_pt[0]) ** 2
                            + (point_y - old_pt[1]) ** 2
                        ) ** 0.5
                        if dist < best_dist:
                            best_dist = dist
                            matched_person = person_id_for_track[old_tid]
                    if matched_person is None:
                        matched_person = next_person_id
                        next_person_id += 1
                    person_id_for_track[track_id] = matched_person

                person_id = person_id_for_track[track_id]
                recent_tracks[track_id] = (timestamp, (point_x, point_y))

                is_inside = inside_roi(point_x, point_y, roi)

                if is_inside:
                    already_entered = person_has_entered.get(person_id, False)
                    if not already_entered:
                        detections.append(
                            (person_id, track_id, (x1, y1, x2, y2))
                        )
                        person_has_entered[person_id] = True
                        person_last_event_ts[person_id] = timestamp
                        person_outside_since[person_id] = None
                    else:
                        outside_since = person_outside_since.get(person_id)
                        if (
                            outside_since is not None
                            and timestamp - outside_since >= EXIT_GRACE_SECONDS
                        ):
                            last_event = person_last_event_ts.get(
                                person_id, -1e9
                            )
                            if timestamp - last_event >= COOLDOWN_SECONDS:
                                detections.append(
                                    (person_id, track_id, (x1, y1, x2, y2))
                                )
                                person_last_event_ts[person_id] = timestamp
                            person_outside_since[person_id] = None
                else:
                    if person_outside_since.get(person_id) is None:
                        person_outside_since[person_id] = timestamp

        annotated = frame.copy()
        cv2.rectangle(
            annotated, (x, y), (x + width, y + height), (0, 0, 255), 3
        )
        cv2.putText(
            annotated,
            "RESTRICTED AREA",
            (x, max(25, y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
        )

        for person_id, track_id, (x1, y1, x2, y2) in detections:
            event_number = len(events) + 1
            event_id = f"event_{event_number:04d}"

            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                annotated,
                f"Person {person_id} - ENTRY",
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

            snapshot_path = SNAPSHOT_DIR / f"{event_id}.jpg"
            clip_path = EVENT_DIR / f"{event_id}.mp4"

            cv2.imwrite(str(snapshot_path), annotated)

            clip_start = max(0, timestamp - pre_seconds)
            clip_end = min(duration, timestamp + post_seconds)

            events.append({
                "Event Number": event_number,
                "Event Type": "Restricted Area Entry",
                "Object ID": person_id,
                "Frame Number": frame_number,
                "Timestamp (seconds)": round(timestamp, 3),
                "Snapshot": snapshot_path.name,
                "Clip": clip_path.name,
                "Video": video_path.name,
                "_clip_start": clip_start,
                "_clip_end": clip_end,
                "_clip_path": clip_path,
            })

            print(
                f"EVENT {event_number}: Person {person_id} "
                f"(track {track_id}), {timestamp:.2f}s, "
                f"source frame {frame_number}"
            )

        if processed_samples % 100 == 0:
            print(
                f"Progress: {processed_samples}/{expected_samples} samples "
                f"(source frame {frame_number}/{total_frames})"
            )

    capture.release()

    for event in events:
        clip_ok = create_clip(
            video_path,
            event["_clip_path"],
            event["_clip_start"],
            event["_clip_end"],
        )
        event["Clip Available"] = "Yes" if clip_ok else "No"
        if not clip_ok:
            event["Clip"] = ""

    elapsed = time.perf_counter() - started

    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for event in events:
            writer.writerow({
                column: event.get(column, "")
                for column in CSV_COLUMNS
            })

    metadata = {
        "video": video_path.name,
        "video_path": str(video_path),
        "video_sha256": video_hash,
        "resolution": f"{frame_width}x{frame_height}",
        "fps": fps,
        "total_frames": total_frames,
        "duration_seconds": round(duration, 3),
        "target_fps": TARGET_FPS,
        "effective_fps": round(effective_fps, 3),
        "frame_skip": frame_skip,
        "inference_size": INFERENCE_SIZE,
        "processed_samples": processed_samples,
        "roi": {"x": x, "y": y, "width": width, "height": height},
        "event_count": len(events),
        "unique_tracked_ids": len(set(
            event["Object ID"] for event in events
        )),
        "processing_seconds": round(elapsed, 2),
        "events": [
            {key: event[key] for key in CSV_COLUMNS}
            for event in events
        ],
    }

    METADATA_FILE.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    # ---- HTML summary (self-contained) ---------------------------------
    # Snapshots are embedded as base64 data URIs so the HTML file works
    # from any folder — including when the user downloads it and opens it
    # outside the project tree.
    import base64

    summary_path = SUMMARY_DIR / "summary.html"
    rows = []

    for event in events:
        timestamp = event["Timestamp (seconds)"]
        snapshot_name = event["Snapshot"]
        clip_name = event.get("Clip") or ""

        snapshot_file = SNAPSHOT_DIR / snapshot_name
        if snapshot_file.is_file():
            with open(snapshot_file, "rb") as fh:
                encoded = base64.b64encode(fh.read()).decode("ascii")
            image_html = (
                f'<img width="220" '
                f'src="data:image/jpeg;base64,{encoded}">'
            )
        else:
            image_html = "<i>snapshot missing</i>"

        clip_html = (
            f"<code>{clip_name}</code>"
            if clip_name
            else "<i>clip unavailable</i>"
        )

        rows.append(
            "<tr>"
            f'<td>{timestamp:.2f}s</td>'
            f'<td>{event["Event Type"]}</td>'
            f'<td>{event["Object ID"]}</td>'
            f'<td>{image_html}</td>'
            f'<td>{clip_html}</td>'
            "</tr>"
        )

    if not rows:
        rows.append(
            '<tr><td colspan="5">No restricted-area entry events detected.</td></tr>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CCTV Forensic Event Summary</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 30px; color: #202938; }}
h1 {{ color: #142b4a; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ border: 1px solid #d7dde5; padding: 10px; text-align: left; }}
th {{ background: #eef2f7; }}
img {{ height: auto; }}
code {{ background:#F1F5F9; padding:2px 6px; border-radius:4px; font-size:12px; }}
</style>
</head>
<body>
<h1>CCTV Forensic Event Summary</h1>
<p><b>Video:</b> {video_path.name}</p>
<p><b>Duration:</b> {duration:.2f} seconds</p>
<p><b>Analysed at:</b> {effective_fps:.2f} samples/second</p>
<p><b>Events:</b> {len(events)}</p>
<p><b>Unique persons:</b> {len(set(
    event["Object ID"] for event in events
))}</p>
<p><b>Processing time:</b> {elapsed:.2f} seconds</p>
<table>
<thead><tr><th>Timestamp</th><th>Event</th><th>Person ID</th>
<th>Evidence snapshot</th><th>Clip file</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</body>
</html>"""

    summary_path.write_text(html, encoding="utf-8")

    print("\nPROCESSING COMPLETE")
    print(f"Events detected: {len(events)}")
    print(
        "Unique persons: "
        f"{len(set(event['Object ID'] for event in events))}"
    )
    print(f"Processing time: {elapsed:.2f} seconds")
    print(f"Event CSV: {CSV_FILE}")
    print(f"Metadata: {METADATA_FILE}")
    print(f"HTML summary: {summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())