import cv2
import csv
import os

video_path = r"videos\VIRAT_S_010000_00_000000_000165.mp4"
events_file = r"data\events.csv"
output_folder = r"outputs\events"

os.makedirs(output_folder, exist_ok=True)

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

with open(events_file, "r") as file:
    reader = csv.DictReader(file)
    events = list(reader)

for number, event in enumerate(events, start=1):

    event_frame = int(event["Frame Number"])

    start_frame = max(0, event_frame - int(5 * fps))
    end_frame = min(total_frames - 1, event_frame + int(5 * fps))

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    filename = f"event_{number:02d}.mp4"
    output_path = os.path.join(output_folder, filename)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(
        output_path,
        fourcc,
        fps,
        (width, height)
    )

    current_frame = start_frame

    while current_frame <= end_frame:

        ret, frame = cap.read()

        if not ret:
            break

        out.write(frame)
        current_frame += 1

    out.release()

    print(
        "Created:",
        filename,
        "| Event:",
        event["Event Type"],
        "| Timestamp:",
        event["Timestamp (seconds)"],
        "seconds"
    )

cap.release()

print()
print("Event video segments created successfully!")
print("Location:", output_folder)