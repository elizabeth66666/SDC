import cv2
import numpy as np

# Load calibration data
data = np.load("camera_calib.npz")

camera_matrix = data["camera_matrix"]
dist_coeffs = data["dist_coeffs"]

# Real QR code size in meters (change if needed)
qr_size = 0.05   # 5 cm

# 3D coordinates of QR corners in real world
object_points = np.array([
    [0, 0, 0],
    [qr_size, 0, 0],
    [qr_size, qr_size, 0],
    [0, qr_size, 0]
], dtype=np.float32)

cap = cv2.VideoCapture(0)
qr_detector = cv2.QRCodeDetector()

print("Press Q to quit")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w = frame.shape[:2]

    # Undistort frame
    new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
        camera_matrix, dist_coeffs, (w, h), 1, (w, h)
    )

    frame = cv2.undistort(frame, camera_matrix, dist_coeffs, None, new_camera_matrix)

    # Detect QR codes
    retval, decoded_info, points, _ = qr_detector.detectAndDecodeMulti(frame)

    if retval:
        for data, point in zip(decoded_info, points):

            if data:
                image_points = np.array(point, dtype=np.float32)

                # Solve pose
                success, rvec, tvec = cv2.solvePnP(
                    object_points,
                    image_points,
                    camera_matrix,
                    dist_coeffs
                )

                if success:
                    distance = np.linalg.norm(tvec)

                    pts = image_points.astype(int)

                    # Draw box
                    cv2.polylines(frame, [pts], True, (0,255,0), 2)

                    center = pts.mean(axis=0).astype(int)

                    text = f"{data} | Dist: {distance:.2f} m"

                    cv2.putText(
                        frame,
                        text,
                        (center[0], center[1]),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0,255,0),
                        2
                    )

                    print(f"{data} -> Distance: {distance:.2f} m")

    cv2.imshow("QR Scanner", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()