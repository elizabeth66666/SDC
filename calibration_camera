from picamera2 import Picamera2
import cv2
import numpy as np
import time
import RPi.GPIO as GPIO
import os

class CameraSwitcher:

    def __init__(self):

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)

        GPIO.setup(7, GPIO.OUT)
        GPIO.setup(11, GPIO.OUT)
        GPIO.setup(12, GPIO.OUT)

    def select(self, camera):

        if camera == "A":

            os.system("i2cset -y 10 0x70 0x00 0x04")

            GPIO.output(7, False)
            GPIO.output(11, False)
            GPIO.output(12, True)

        elif camera == "B":

            os.system("i2cset -y 10 0x70 0x00 0x05")

            GPIO.output(7, True)
            GPIO.output(11, False)
            GPIO.output(12, True)

        time.sleep(0.5)

switcher = CameraSwitcher()

def calibrate_camera(camera):

  #Chessboard Dimensions
  chessboard_size = (9,6)
  
  #Prepare Object Points
  objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3),
                   np.float32)
  objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)
  objpoints = []
  imgpoints = []
  
  switcher.select(camera)
  
  picam2 = Picamera2()
  config = picam2.create_preview_configuration(
    main={"size": (1280, 720)}
  )
  
  picam2.configure(config)
  picam2.start()
  
  time.sleep(2)
  
  print("Press SPACE to capture calibration images")
  print("Press Q to finish calibration")
  
  img_count = 0
  while True:
    frame = picam2.capture_array()
    
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    
    ret_cb, corners = cv2.findChessboardCorners(
      gray,
      chessboard_size,
      None, 
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
            f"{camera}calibration_{img_count}.jpg",
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

  if len(objpoints) < 15:
    print("Not enough calibration images.")
    return None, None
    
  print("Calculating Calibration")

  ret, camera_matrix, dist_coeffs, rvecs, tvecs = \
          cv2.calibrateCamera(
            objpoints, 
            imgpoints, 
            gray.shape[::-1],
            None, 
            None
          )
  np.savez(
      f"{camera}_calib.npz",
    camera_matrix=camera_matrix,
    dist_coeffs=dist_coeffs
    )
  
  print("Calibration saved to" f"{camera}_calib.npz")
  print("\nCamera Matrix:")
  print(camera_matrix)
  print("\nDistortion Coefficients")
  print(dist_coeffs)
  
  return camera_matrix, dist_coeffs 
    
def main():
  leftMatrix, leftDist = calibrate_camera("A")

  rightMatrix, rightDist = calibrate_camera("B")

  print(rightMatrix)
  print(rightDist)
  print(leftMatrix)
  print(leftDist)
  
if __name__ == "__main__":
    main()
  GPIO.cleanup()
##### Stereo calibration code
square_size = 25.0
from picamera2 import Picamera2
import cv2
import numpy as np
import time
import RPi.GPIO as GPIO
import os

switcher = CameraSwitcher()


def capture_frame(camera):
    switcher.select(camera)

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (1280, 720)}
    )

    picam2.configure(config)
    picam2.start()
    time.sleep(1)

    frame = picam2.capture_array()
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    picam2.stop()

    return frame_bgr


def stereo_calibrate():
    chessboard_size = (9, 6)

    # Change this to your actual chessboard square size.
    # Example: 25.0 means each square is 25 mm.
    square_size = 25.0

    image_size = (1280, 720)

    # Prepare object points.
    objp = np.zeros(
        (chessboard_size[0] * chessboard_size[1], 3),
        np.float32
    )

    objp[:, :2] = (
        np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]]
        .T.reshape(-1, 2)
    )

    objp = objp * square_size

    objpoints = []
    imgpoints_A = []
    imgpoints_B = []

    # Load existing single-camera calibration.
    calib_A = np.load("A_calib.npz")
    calib_B = np.load("B_calib.npz")

    camera_matrix_A = calib_A["camera_matrix"]
    dist_coeffs_A = calib_A["dist_coeffs"]

    camera_matrix_B = calib_B["camera_matrix"]
    dist_coeffs_B = calib_B["dist_coeffs"]

    print("Stereo calibration started.")
    print("Place the chessboard where both cameras can see it.")
    print("Press SPACE to capture a stereo pair.")
    print("Press Q to finish.")

    pair_count = 0

    while True:
        frame_A = capture_frame("A")
        frame_B = capture_frame("B")

        gray_A = cv2.cvtColor(frame_A, cv2.COLOR_BGR2GRAY)
        gray_B = cv2.cvtColor(frame_B, cv2.COLOR_BGR2GRAY)

        ret_A, corners_A = cv2.findChessboardCorners(
            gray_A,
            chessboard_size,
            None
        )

        ret_B, corners_B = cv2.findChessboardCorners(
            gray_B,
            chessboard_size,
            None
        )

        display_A = frame_A.copy()
        display_B = frame_B.copy()

        if ret_A:
            cv2.drawChessboardCorners(
                display_A,
                chessboard_size,
                corners_A,
                ret_A
            )

        if ret_B:
            cv2.drawChessboardCorners(
                display_B,
                chessboard_size,
                corners_B,
                ret_B
            )

        combined = np.hstack((display_A, display_B))
        cv2.imshow("Camera A | Camera B", combined)

        key = cv2.waitKey(0) & 0xFF

        if key == ord(" "):
            if ret_A and ret_B:
                criteria = (
                    cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                    30,
                    0.001
                )

                corners_A_refined = cv2.cornerSubPix(
                    gray_A,
                    corners_A,
                    (11, 11),
                    (-1, -1),
                    criteria
                )

                corners_B_refined = cv2.cornerSubPix(
                    gray_B,
                    corners_B,
                    (11, 11),
                    (-1, -1),
                    criteria
                )

                objpoints.append(objp)
                imgpoints_A.append(corners_A_refined)
                imgpoints_B.append(corners_B_refined)

                cv2.imwrite(f"stereo_A_{pair_count}.jpg", frame_A)
                cv2.imwrite(f"stereo_B_{pair_count}.jpg", frame_B)

                pair_count += 1
                print(f"Captured stereo pair {pair_count}")

            else:
                print("Chessboard not detected in both cameras.")

        elif key == ord("q"):
            break

    cv2.destroyAllWindows()

    if len(objpoints) < 10:
        print("Not enough stereo pairs. Capture at least 10 to 15 good pairs.")
        return

    print("Calculating stereo calibration...")

    flags = cv2.CALIB_FIX_INTRINSIC

    ret, camera_matrix_A, dist_coeffs_A, camera_matrix_B, dist_coeffs_B, R, T, E, F = cv2.stereoCalibrate(
        objpoints,
        imgpoints_A,
        imgpoints_B,
        camera_matrix_A,
        dist_coeffs_A,
        camera_matrix_B,
        dist_coeffs_B,
        image_size,
        criteria=(
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            100,
            1e-5
        ),
        flags=flags
    )

    print("Stereo calibration error:", ret)
    print("Rotation R:")
    print(R)
    print("Translation T:")
    print(T)

    R1, R2, P1, P2, Q, roi1, roi2 = cv2.stereoRectify(
        camera_matrix_A,
        dist_coeffs_A,
        camera_matrix_B,
        dist_coeffs_B,
        image_size,
        R,
        T,
        alpha=0
    )

    np.savez(
        "stereo_calib.npz",
        camera_matrix_A=camera_matrix_A,
        dist_coeffs_A=dist_coeffs_A,
        camera_matrix_B=camera_matrix_B,
        dist_coeffs_B=dist_coeffs_B,
        R=R,
        T=T,
        E=E,
        F=F,
        R1=R1,
        R2=R2,
        P1=P1,
        P2=P2,
        Q=Q
    )

    print("Stereo calibration saved to stereo_calib.npz")


if __name__ == "__main__":
    try:
        stereo_calibrate()
    finally:
        GPIO.cleanup()
