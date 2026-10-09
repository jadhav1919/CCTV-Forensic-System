import cv2
from ultralytics import YOLO

# Input CCTV video
video_path = r"videos\VIRAT_S_010000_00_000000_000165.mp4"

# Output detection video
output_path = r"outputs\detection_video.mp4"

# Load YOLO model
model = YOLO("yolo11n.pt")

# Open video
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

# Video information
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print("Video opened successfully")
print("FPS:", fps)
print("Resolution:", width, "x", height)

# Create output video
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter(
    output_path,
    fourcc,
    fps,
    (width, height)
)

frame_count = 0

while True:

    ret, frame = cap.read()

    if not ret:
        break

    # YOLO detection
    results = model(frame, device="cpu", verbose=False)

    # Draw detections
    annotated_frame = results[0].plot()

    # Save frame to output video
    out.write(annotated_frame)

    frame_count += 1

    if frame_count % 100 == 0:
        print("Processed frames:", frame_count)

# Release resources
cap.release()
out.release()

print()
print("Detection completed!")
print("Total frames processed:", frame_count)
print("Output:", output_path)