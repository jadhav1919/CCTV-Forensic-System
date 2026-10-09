import cv2
import os
import sys
import csv
from ultralytics import YOLO


# ============================================================
# 1. GET VIDEO PATH
# ============================================================

if len(sys.argv) < 2:
    print("Usage:")
    print('python src\\process_video.py "path_to_video"')
    sys.exit()

video_path = sys.argv[1]

if not os.path.exists(video_path):
    print("Error: Video file not found.")
    sys.exit()


# ============================================================
# 2. OPEN VIDEO
# ============================================================

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: Could not open video.")
    sys.exit()

fps = cap.get(cv2.CAP_PROP_FPS)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

duration = frame_count / fps if fps > 0 else 0

print("Video opened successfully")
print("Filename:", os.path.basename(video_path))
print("Resolution:", width, "x", height)
print("FPS:", round(fps, 2))
print("Total Frames:", frame_count)
print("Duration:", round(duration, 2), "seconds")


# ============================================================
# 3. LOAD RESTRICTED AREA
# ============================================================

roi_file = r"data\roi.txt"

if not os.path.exists(roi_file):
    print("Error: ROI file not found.")
    cap.release()
    sys.exit()

with open(roi_file, "r") as file:
    x, y, w, h = map(int, file.read().split(","))

print()
print("Restricted Area:")
print("X:", x)
print("Y:", y)
print("Width:", w)
print("Height:", h)


# ============================================================
# 4. LOAD YOLO MODEL
# ============================================================

print()
print("Loading YOLO model...")

model = YOLO("yolo11n.pt")

print("YOLO model loaded successfully!")
print("Starting forensic analysis...")


# ============================================================
# 5. CREATE OUTPUT FOLDERS
# ============================================================

snapshot_folder = r"outputs\snapshots"
events_folder = r"outputs\events"

os.makedirs(snapshot_folder, exist_ok=True)
os.makedirs(events_folder, exist_ok=True)


# ============================================================
# 6. EVENT LOG SETTINGS
# ============================================================

events_file = r"data\events.csv"

event_records = []

detected_ids = set()

frame_number = 0
event_number = 0


# ============================================================
# 7. PROCESS VIDEO
# ============================================================

while True:

    ret, frame = cap.read()

    if not ret:
        break

    frame_number += 1

    results = model.track(
        frame,
        tracker="bytetrack.yaml",
        persist=True,
        classes=[0],
        device="cpu",
        verbose=False
    )

    result = results[0]

    if result.boxes.id is not None:

        boxes = result.boxes.xyxy.cpu().numpy()
        ids = result.boxes.id.cpu().numpy()

        for box, object_id in zip(boxes, ids):

            x1, y1, x2, y2 = map(int, box)

            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)

            object_id = int(object_id)

            # Check whether person is inside restricted area

            inside_roi = (
                x <= center_x <= x + w
                and
                y <= center_y <= y + h
            )

            # New event

            if inside_roi and object_id not in detected_ids:

                detected_ids.add(object_id)

                event_number += 1

                timestamp = frame_number / fps

                snapshot_name = f"event_{event_number:02d}.jpg"

                snapshot_path = os.path.join(
                    snapshot_folder,
                    snapshot_name
                )

                # Save event snapshot

                cv2.imwrite(
                    snapshot_path,
                    frame
                )

                print()
                print("EVENT DETECTED!")
                print("Event: Restricted Area Entry")
                print("Object ID:", object_id)
                print("Frame:", frame_number)
                print("Timestamp:", round(timestamp, 2), "seconds")
                print("Snapshot:", snapshot_name)

                event_records.append([
                    "Restricted Area Entry",
                    object_id,
                    frame_number,
                    round(timestamp, 2),
                    snapshot_name
                ])

    if frame_number % 100 == 0:

        print(
            "Processed frames:",
            frame_number
        )


# ============================================================
# 8. RELEASE ORIGINAL VIDEO
# ============================================================

cap.release()


# ============================================================
# 9. SAVE EVENT CSV
# ============================================================

with open(
    events_file,
    "w",
    newline=""
) as file:

    writer = csv.writer(file)

    writer.writerow([
        "Event Type",
        "Object ID",
        "Frame Number",
        "Timestamp (seconds)",
        "Snapshot"
    ])

    writer.writerows(event_records)


# ============================================================
# 10. CREATE EVENT VIDEO CLIPS
# ============================================================

print()
print("Creating event video clips...")


for number, event in enumerate(
    event_records,
    start=1
):

    event_frame = int(event[2])

    # 5 seconds before event

    start_frame = max(
        0,
        event_frame - int(5 * fps)
    )

    # 5 seconds after event

    end_frame = min(
        frame_count - 1,
        event_frame + int(5 * fps)
    )

    # Reopen video

    event_cap = cv2.VideoCapture(
        video_path
    )

    event_cap.set(
        cv2.CAP_PROP_POS_FRAMES,
        start_frame
    )

    output_path = os.path.join(
        events_folder,
        f"event_{number:02d}.mp4"
    )

    fourcc = cv2.VideoWriter_fourcc(
        *"mp4v"
    )

    out = cv2.VideoWriter(
        output_path,
        fourcc,
        fps,
        (width, height)
    )

    current_frame = start_frame

    while current_frame <= end_frame:

        ret, frame = event_cap.read()

        if not ret:
            break

        out.write(frame)

        current_frame += 1

    event_cap.release()
    out.release()

    print(
        "Created:",
        f"event_{number:02d}.mp4"
    )


# ============================================================
# 11. FINAL RESULTS
# ============================================================

print()
print("========================================")
print("FORENSIC ANALYSIS COMPLETED")
print("========================================")

print(
    "Total frames processed:",
    frame_number
)

print(
    "Total events detected:",
    len(event_records)
)

print(
    "Snapshots saved to:",
    snapshot_folder
)

print(
    "Event clips saved to:",
    events_folder
)

print(
    "Event log saved to:",
    events_file
)

print("========================================")