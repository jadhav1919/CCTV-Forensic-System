import cv2

video_path = r"videos\VIRAT_S_010000_00_000000_000165.mp4"

cap = cv2.VideoCapture(video_path)

ret, frame = cap.read()
cap.release()

if not ret:
    print("Error: Could not read video.")
    exit()

print("Select the restricted area using your mouse.")
print("After selecting, press ENTER.")

roi = cv2.selectROI("Select Restricted Area", frame, False, False)

x, y, w, h = roi

cv2.destroyAllWindows()

print()
print("Restricted Area:")
print("X:", x)
print("Y:", y)
print("Width:", w)
print("Height:", h)

with open("data\\roi.txt", "w") as file:
    file.write(f"{x},{y},{w},{h}")

print()
print("ROI saved to data\\roi.txt")