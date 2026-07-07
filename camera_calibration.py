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
