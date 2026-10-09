import cv2
import csv
import os

video_path = r"videos\VIRAT_S_010000_00_000000_000165.mp4"
events_file = r"data\events.csv"
output_folder = r"outputs\snapshots"

os.makedirs(output_folder, exist_ok=True)

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

with open(events_file, "r") as file:
    reader = csv.DictReader(file)
    events = list(reader)

for number, event in enumerate(events, start=1):

    frame_number = int(event["Frame Number"])

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number - 1)

    ret, frame = cap.read()

    if not ret:
        print("Could not read frame:", frame_number)
        continue

    filename = f"event_{number:02d}.jpg"
    output_path = os.path.join(output_folder, filename)

    cv2.imwrite(output_path, frame)

    print(
        "Saved:",
        filename,
        "| Event:",
        event["Event Type"],
        "| Timestamp:",
        event["Timestamp (seconds)"],
        "seconds"
    )

cap.release()

print()
print("Event snapshots created successfully!")
print("Location:", output_folder)