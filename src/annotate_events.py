import cv2
import csv
import os

input_folder = r"outputs\events"
output_folder = r"outputs\events_annotated"

os.makedirs(output_folder, exist_ok=True)

with open("data\\events.csv", "r") as file:
    reader = csv.DictReader(file)
    events = list(reader)

for number, event in enumerate(events, start=1):

    input_path = os.path.join(
        input_folder,
        f"event_{number:02d}.mp4"
    )

    output_path = os.path.join(
        output_folder,
        f"event_{number:02d}_annotated.mp4"
    )

    cap = cv2.VideoCapture(input_path)

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    out = cv2.VideoWriter(
        output_path,
        fourcc,
        fps,
        (width, height)
    )

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        cv2.putText(
            frame,
            "EVENT: Restricted Area Entry",
            (30, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

        cv2.putText(
            frame,
            f"OBJECT ID: {event['Object ID']}",
            (30, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"EVENT TIME: {event['Timestamp (seconds)']} seconds",
            (30, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        out.write(frame)

    cap.release()
    out.release()

    print("Annotated:", f"event_{number:02d}_annotated.mp4")

print()
print("All event videos annotated successfully!")
print("Output folder:", output_folder)