import argparse
import glob
import math
import os

import cv2
import numpy as np

def main() -> None:
    """Capture camera feed and detect QR codes."""
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    # Set camera properties for better performance
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv2.CAP_PROP_FPS, 30)

    # Create QR code detector
    qr_detector = cv2.QRCodeDetector()

    # Known marker size (meters) and assumed horizontal FOV (degrees)
    # If you have camera calibration, replace this logic with solvePnP for better accuracy.
    marker_size_m = 0.05  # default: 5 cm QR code
    assumed_fov_deg = 60.0  # typical webcam horizontal FOV; change if known

    # Create a named window for better display control
    cv2.namedWindow('QR Code Scanner', cv2.WINDOW_NORMAL)

    print("Press 'q' to quit. Point camera at QR code to scan.")
    detected_qr_codes = set()

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("Error: Failed to capture frame.")
                break

            # Detect and decode QR code(s)
            retval, decoded_info, points, straight_qr = qr_detector.detectAndDecodeMulti(frame)

            def _handle_detection(data, point_arr):
                if not data or point_arr is None:
                    return

                # Normalize point shape and convert to float
                pts = np.array(point_arr, dtype=float).reshape(-1, 2)

                # Draw the QR code bounding box
                cv2.polylines(frame, [pts.astype(int)], True, (0, 255, 0), 2)

                # Compute center pixel of QR code
                center = pts.mean(axis=0)

                # Estimate pixel width of the QR (average of two opposite edges)
                w1 = np.linalg.norm(pts[0] - pts[1])
                w2 = np.linalg.norm(pts[2] - pts[3])
                pixel_width = (w1 + w2) / 2.0

                # Approximate focal length in pixels from assumed horizontal FOV
                frame_width = frame.shape[1]
                f_px = (frame_width / 2.0) / math.tan(math.radians(assumed_fov_deg) / 2.0)

                # Depth (Z) estimation using similar triangles: Z = f * real_width / pixel_width
                Z = (f_px * marker_size_m) / pixel_width if pixel_width > 0 else 0.0

                # Principal point assumed at image center
                cx = frame_width / 2.0
                cy = frame.shape[0] / 2.0

                # Convert image pixel coordinates to camera coordinates (meters)
                X = (center[0] - cx) * Z / f_px
                Y = (center[1] - cy) * Z / f_px

                # Display QR code data and estimated coordinates on frame
                label = f"{data}"
                coord_text = f"X={X:.3f}m Y={Y:.3f}m Z={Z:.3f}m"
                cv2.putText(frame, label, (int(center[0] - 50), int(center[1] - 20)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(frame, coord_text, (int(center[0] - 50), int(center[1] + 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # Print to console and add to detected set
                if data not in detected_qr_codes:
                    print(f"QR Code detected: {data} -> X={X:.3f}m Y={Y:.3f}m Z={Z:.3f}m")
                    detected_qr_codes.add(data)

            if retval and points is not None:
                for point, data in zip(points, decoded_info):
                    _handle_detection(data, point)
            else:
                # Fallback to single detection (some OpenCV builds don't support multi)
                data, point, _ = qr_detector.detectAndDecode(frame)
                _handle_detection(data, point)

            # Display the frame
            cv2.imshow('QR Code Scanner', frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q')):
                break

    except KeyboardInterrupt:
        print("\nQR code scanner stopped by user.")
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

import cv2
import numpy as np
import glob

# Chessboard dimensions
chessboard_size = (9,6)

# Prepare object points (3D real-world points)
objp = np.zeros((chessboard_size[0]*chessboard_size[1],3), np.float32)
objp[:,:2] = np.mgrid[0:chessboard_size[0],0:chessboard_size[1]].T.reshape(-1,2)

objpoints = []
imgpoints = []

cap = cv2.VideoCapture(0)

print("Press SPACE to capture calibration image")
print("Press Q to finish calibration")

img_count = 0

while True:
    ret, frame = cap.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    ret_cb, corners = cv2.findChessboardCorners(gray, chessboard_size, None)

    if ret_cb:
        cv2.drawChessboardCorners(frame, chessboard_size, corners, ret_cb)

    cv2.imshow("Calibration", frame)

    key = cv2.waitKey(1)

    if key == ord(' '):  # capture frame
        if ret_cb:
            objpoints.append(objp)
            imgpoints.append(corners)

            cv2.imwrite(f"calibration_{img_count}.jpg", frame)
            img_count += 1

            print("Captured calibration image", img_count)
        else:
            print("Chessboard not detected")

    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

print("Calculating calibration...")

ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
    objpoints, imgpoints, gray.shape[::-1], None, None
)

np.savez("camera_calib.npz",
         camera_matrix=camera_matrix,
         dist_coeffs=dist_coeffs)

print("Calibration saved to camera_calib.npz")

import cv2
import numpy as np
import glob

# Chessboard size (number of inner corners)
chessboard_size = (9,6)

# Prepare object points
objp = np.zeros((np.prod(chessboard_size),3), np.float32)
objp[:,:2] = np.indices(chessboard_size).T.reshape(-1,2)

objpoints = []  # 3D points
imgpoints = []  # 2D points

# Load calibration images
images = glob.glob('calibration_images/*.jpg')

for fname in images:
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ret, corners = cv2.findChessboardCorners(gray, chessboard_size, None)

    if ret:
        objpoints.append(objp)
        imgpoints.append(corners)

        cv2.drawChessboardCorners(img, chessboard_size, corners, ret)
        cv2.imshow('Corners', img)
        cv2.waitKey(500)

cv2.destroyAllWindows()

# Calibrate camera
ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
    objpoints,
    imgpoints,
    gray.shape[::-1],
    None,
    None
)

print("Camera matrix:")
print(mtx)

print("\nDistortion coefficients:")
print(dist)