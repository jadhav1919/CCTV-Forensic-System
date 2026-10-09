import cv2
import os

input_folder = r"outputs\events_annotated"
output_path = r"outputs\summaries\Forensic_Annotated_Summary.mp4"

os.makedirs(r"outputs\summaries", exist_ok=True)

video_files = []

for i in range(1, 13):
    filename = f"event_{i:02d}_annotated.mp4"
    path = os.path.join(input_folder, filename)

    if os.path.exists(path):
        video_files.append(path)

if len(video_files) == 0:
    print("Error: No annotated event videos found.")
    exit()

first_video = cv2.VideoCapture(video_files[0])

fps = first_video.get(cv2.CAP_PROP_FPS)
width = int(first_video.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(first_video.get(cv2.CAP_PROP_FRAME_HEIGHT))

first_video.release()

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

out = cv2.VideoWriter(
    output_path,
    fourcc,
    fps,
    (width, height)
)

for video_path in video_files:

    cap = cv2.VideoCapture(video_path)

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        out.write(frame)

    cap.release()

    print("Added:", os.path.basename(video_path))

out.release()

print()
print("Final annotated summary created successfully!")
print("Total event clips:", len(video_files))
print("Output:", output_path)