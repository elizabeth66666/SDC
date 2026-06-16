from picamera2 import Picamera2
import cv2
import numpy as np
import time

# Chessboard dimensions
chessboard_size = (7, 7)

# Prepare object points
objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3),
                np.float32)
objp[:, :2] = np.mgrid[
    0:chessboard_size[0],
    0:chessboard_size[1]
].T.reshape(-1, 2)

objpoints = []
imgpoints = []

# Start Pi Camera
picam2 = Picamera2()

config = picam2.create_preview_configuration(
    main={"size": (1280, 720)}
)

picam2.configure(config)
picam2.start()

# Give camera time to settle
time.sleep(2)

print("Press SPACE to capture calibration image")
print("Press Q to finish calibration")

img_count = 0

while True:

    # Capture frame from Pi Camera
    frame = picam2.capture_array()

    # Picamera2 returns RGB
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    ret_cb, corners = cv2.findChessboardCorners(
        gray,
        chessboard_size,
        None
    )

    display = frame_bgr.copy()

    if ret_cb:
        cv2.drawChessboardCorners(
            display,
            chessboard_size,
            corners,
            ret_cb
        )

    cv2.imshow("Calibration", display)

    key = cv2.waitKey(1) & 0xFF

    if key == ord(' '):

        if ret_cb:

            objpoints.append(objp)
            imgpoints.append(corners)

            cv2.imwrite(
                f"calibration_{img_count}.jpg",
                frame_bgr
            )

            img_count += 1

            print(f"Captured calibration image {img_count}")

        else:
            print("Chessboard not detected")

    elif key == ord('q'):
        break

picam2.stop()
cv2.destroyAllWindows()

if len(objpoints) < 5:
    print("Not enough calibration images.")
    exit()

print("Calculating calibration...")

ret, camera_matrix, dist_coeffs, rvecs, tvecs = \
    cv2.calibrateCamera(
        objpoints,
        imgpoints,
        gray.shape[::-1],
        None,
        None
    )

np.savez(
    "camera_calib.npz",
    camera_matrix=camera_matrix,
    dist_coeffs=dist_coeffs
)

print("Calibration saved to camera_calib.npz")

print("\nCamera Matrix:")
print(camera_matrix)

print("\nDistortion Coefficients:")
print(dist_coeffs)

print("RMS:", ret)
