import cv2
import csv
from ultralytics import YOLO

video_path = r"videos\VIRAT_S_010000_00_000000_000165.mp4"
events_file = r"data\events.csv"

# Load ROI
with open("data\\roi.txt", "r") as file:
    x, y, w, h = map(int, file.read().split(","))

print("Restricted Area:")
print("X:", x)
print("Y:", y)
print("Width:", w)
print("Height:", h)

model = YOLO("yolo11n.pt")

cap = cv2.VideoCapture(video_path)

fps = cap.get(cv2.CAP_PROP_FPS)

frame_number = 0
events = set()
event_records = []

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

            inside_roi = (
                x <= center_x <= x + w
                and
                y <= center_y <= y + h
            )

            object_id = int(object_id)

            if inside_roi and object_id not in events:

                events.add(object_id)

                timestamp = frame_number / fps

                print()
                print("EVENT DETECTED!")
                print("Event: Restricted Area Entry")
                print("Object ID:", object_id)
                print("Frame:", frame_number)
                print("Timestamp:", round(timestamp, 2), "seconds")

                event_records.append([
                    "Restricted Area Entry",
                    object_id,
                    frame_number,
                    round(timestamp, 2)
                ])

cap.release()

# Save events to CSV
with open(events_file, "w", newline="") as file:

    writer = csv.writer(file)

    writer.writerow([
        "Event Type",
        "Object ID",
        "Frame Number",
        "Timestamp (seconds)"
    ])

    writer.writerows(event_records)

print()
print("Event detection completed!")
print("Total events:", len(event_records))
print("Event log saved to:", events_file)