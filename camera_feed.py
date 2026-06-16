from flask import Flask, Response
from picamera2 import Picamera2
import cv2
import numpy as np
import time

app = Flask(__name__)

# -----------------------------
# Load calibration
# -----------------------------

data = np.load("camera_calib.npz")

camera_matrix = data["camera_matrix"]
dist_coeffs = data["dist_coeffs"]

# -----------------------------
# QR dimensions
# -----------------------------

qr_size = 0.05

object_points = np.array([
    [0, 0, 0],
    [qr_size, 0, 0],
    [qr_size, qr_size, 0],
    [0, qr_size, 0]
], dtype=np.float32)

# -----------------------------
# Camera setup
# -----------------------------

picam2 = Picamera2()

config = picam2.create_preview_configuration(
    main={"size": (1280, 720)}
)

picam2.configure(config)
picam2.start()

time.sleep(2)

# -----------------------------
# Detector setup
# -----------------------------

qr_detector = cv2.QRCodeDetector()

# -----------------------------
# Calculate camera matrix once
# -----------------------------

first_frame = picam2.capture_array()

first_frame = cv2.cvtColor(
    first_frame,
    cv2.COLOR_RGB2BGR
)

h, w = first_frame.shape[:2]

new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
    camera_matrix,
    dist_coeffs,
    (w, h),
    1,
    (w, h)
)

# -----------------------------
# Streaming function
# -----------------------------

def generate_frames():

    while True:

        frame = picam2.capture_array()

        frame = cv2.cvtColor(
            frame,
            cv2.COLOR_RGB2BGR
        )

        frame = cv2.undistort(
            frame,
            camera_matrix,
            dist_coeffs,
            None,
            new_camera_matrix
        )

        retval, decoded_info, points, _ = (
            qr_detector.detectAndDecodeMulti(frame)
        )

        if retval:

            for qr_data, point in zip(
                decoded_info,
                points
            ):

                if qr_data:

                    image_points = np.array(
                        point,
                        dtype=np.float32
                    )

                    success, rvec, tvec = cv2.solvePnP(
                        object_points,
                        image_points,
                        camera_matrix,
                        dist_coeffs
                    )

                    if success:

                        distance = np.linalg.norm(
                            tvec
                        )

                        pts = image_points.astype(
                            int
                        )

                        cv2.polylines(
                            frame,
                            [pts],
                            True,
                            (0, 255, 0),
                            2
                        )

                        center = pts.mean(
                            axis=0
                        ).astype(int)

                        text = (
                            f"{qr_data} | "
                            f"{distance:.2f} m"
                        )

                        cv2.putText(
                            frame,
                            text,
                            (
                                center[0],
                                center[1]
                            ),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 255, 0),
                            2
                        )

        ret, buffer = cv2.imencode(
            '.jpg',
            frame
        )

        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + frame_bytes +
            b'\r\n'
        )

# -----------------------------
# Video endpoint
# -----------------------------

@app.route('/video')
def video():

    return Response(
        generate_frames(),
        mimetype=
        'multipart/x-mixed-replace; boundary=frame'
    )

# -----------------------------
# Simple webpage
# -----------------------------

@app.route('/')
def index():

    return """
    <html>
        <body>
            <h1>QR Distance Scanner</h1>
            <img src="/video">
        </body>
    </html>
    """

# -----------------------------
# Start Flask
# -----------------------------

if __name__ == "__main__":

    app.run(
        host='0.0.0.0',
        port=5000,
        threaded=True
    )
cv2.destroyAllWindows()
