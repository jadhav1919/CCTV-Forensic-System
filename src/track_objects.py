import cv2
from ultralytics import YOLO

video_path = r"videos\VIRAT_S_010000_00_000000_000165.mp4"

model = YOLO("yolo11n.pt")

results = model.track(
    source=video_path,
    tracker="bytetrack.yaml",
    device="cpu",
    save=True
)

print("Tracking completed successfully!")