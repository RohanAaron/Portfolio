import sys
sys.path.append('.')
import cv2
import numpy as np

from controller import Supervisor, Camera, Display, Motor, Keyboard

print("=" * 50)
print("ASSIGNMENT 4 - WEBOTS SUPERVISOR CONTROLLER")
print("=" * 50)

TIME_STEP = 64
robot = Supervisor()
keyboard = Keyboard()
keyboard.enable(TIME_STEP)

# Kinematics Parameters (from A3)
R_WHEEL = 0.123
L = 0.2225
W = 0.2045
R_sum = L + W


def calculate_wheel_velocities(vx, vy, omega):
    H = np.array([
        [1, -1, -R_sum],
        [1,  1,  R_sum],
        [1, -1,  R_sum],
        [1,  1, -R_sum]
    ]) / R_WHEEL
    V_body = np.array([vx, vy, omega])
    return np.dot(H, V_body)


print("\n[1] Initializing camera...")
camera = robot.getDevice('rgb_camera')
camera.enable(TIME_STEP)
width = camera.getWidth()
height = camera.getHeight()
print(f" Camera ready: {width}x{height}")

print("\n[2] Initializing display...")
display = robot.getDevice('display')
print(f" Display ready: {width}x{height}")

print("\n[3] Initializing motors...")
motor_names = [
    'front_right_wheel_joint',
    'front_left_wheel_joint',
    'back_left_wheel_joint',
    'back_right_wheel_joint'
]
motors = []
for name in motor_names:
    motor = robot.getDevice(name)
    motor.setPosition(float('inf'))
    motor.setVelocity(0.0)
    motors.append(motor)
    print(f" Motor '{name}' ready")

print("\n[4] Initializing ArUco detection...")
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
parameters = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
print(" ArUco detector ready")

print("\n" + "=" * 50)
print("ALL SYSTEMS READY")
print("Controls: W/S = forward/back, A/D = turn, P = save image + poses, ESC = quit")
print("=" * 50 + "\n")

# Movement Parameters (tune as needed)
V_FORWARD = 0.5    # forward linear speed
W_TURN = 0.5       # angular speed

MOTOR_IDX = {'FR': 0, 'FL': 1, 'BL': 2, 'BR': 3}

# Precompute "stop" wheel velocities
V_WHEELS_STOP = calculate_wheel_velocities(0.0, 0.0, 0.0)

# Logging
from controller import Supervisor, Camera, Display, Motor, Keyboard
import numpy as np
import cv2

# ... initialization (as already done) ...

image_index = 0
NUM_MARKERS = 10  # or however many MARKER0..MARKER9 you have

while robot.step(TIME_STEP) != -1:
    key = keyboard.getKey()

    vx, vy, omega = 0.0, 0.0, 0.0

    if key == ord('W'):
        vx = V_FORWARD
    elif key == ord('S'):
        vx = -V_FORWARD
    elif key == ord('A'):
        omega = W_TURN
    elif key == ord('D'):
        omega = -W_TURN
    elif key == 27:  # ESC
        print("ESC pressed, quitting.")
        break

    current_wheel_velocities = calculate_wheel_velocities(vx, vy, omega)
    for i, motor in enumerate(motors):
        motor.setVelocity(current_wheel_velocities[i])

    # ---------- P key: save image + marker poses ----------
    if key == ord('P'):
        img_filename = f"webots_img_{image_index:04d}.png"
        camera.saveImage(img_filename, 100)
        print(f"[P] Saved image: {img_filename}")

        pose_log_filename = "marker_poses_log.txt"
        with open(pose_log_filename, "a") as f:
            for mid in range(NUM_MARKERS):
                def_name = f"MARKER{mid}"
                node = robot.getFromDef(def_name)
                if node is None:
                    continue

                translation = node.getPosition()        # [x, y, z]
                orientation = node.getOrientation()     # 3x3 row-major, 9 numbers

                # Build one CSV line:
                # img_idx, marker_id, tx,ty,tz, r00..r22
                line_parts = [str(image_index), str(mid)]
                line_parts += [f"{t:.8f}" for t in translation]
                line_parts += [f"{r:.8f}" for r in orientation]
                line = ",".join(line_parts)

                f.write(line + "\n")

        print(f"[P] Logged marker poses for image index {image_index}")
        image_index += 1

    # ----- your existing image-processing / display code here -----


    # Image processing for visualization and marker detection
    try:
        image = camera.getImage()
        if image is None:
            continue

        imgarray = np.frombuffer(image, dtype=np.uint8).copy().reshape((height, width, 4))
        img_bgr = cv2.cvtColor(imgarray, cv2.COLOR_BGRA2BGR)

        # Example overlay: red circle at center
        center_x, center_y = width // 2, height // 2
        cv2.circle(img_bgr, (center_x, center_y), 50, (0, 0, 255), -1)

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = detector.detectMarkers(gray)

        if ids is not None and len(ids) > 0:
            cv2.aruco.drawDetectedMarkers(img_bgr, corners, ids)
            marker_detections.append(ids.flatten().tolist())

        # Show image on Webots display
        img_bgra = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2BGRA)
        ir = display.imageNew(img_bgra.tobytes(), Display.BGRA, width, height)
        display.imagePaste(ir, 0, 0, False)
        display.imageDelete(ir)

    except Exception as e:
        print(f"ERROR during image processing: {e}")
        continue

print("\nSimulation ended.")
