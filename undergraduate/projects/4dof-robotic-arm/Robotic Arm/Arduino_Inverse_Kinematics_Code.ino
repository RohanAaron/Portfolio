/*
  3-DOF Robotic Arm — Inverse Kinematics Pick-and-Place Code
  Extracted from: Appendix, "Arduino Inverse Kinematics Code"

  Controls a 3-DOF robotic arm with 5 servo motors (base, shoulder, elbow,
  wrist, gripper) to perform an automated pick-and-place sequence.
  Triggered by a joystick module's push-button input.
*/

#include <Servo.h>
#include <math.h>

#define L1 31.0
#define L2 27.0
#define JOYSTICK_BUTTON_PIN 2

Servo servoBase, servoShoulder, servoElbow, servoWrist, servoGripper;

void setup() {
  Serial.begin(9600);
  pinMode(JOYSTICK_BUTTON_PIN, INPUT_PULLUP);
  servoBase.attach(3);
  servoShoulder.attach(4);
  servoElbow.attach(5);
  servoWrist.attach(6);
  servoGripper.attach(7);
  servoBase.write(90);
  servoShoulder.write(90);
  servoElbow.write(90);
  servoWrist.write(90);
  servoGripper.write(90);
}

void loop() {
  if (digitalRead(JOYSTICK_BUTTON_PIN) == LOW) {
    delay(200);
    while (digitalRead(JOYSTICK_BUTTON_PIN) == LOW);
    pickAndPlace();
  }
}

void computeAndMoveIK(float x, float y) {
  float dist = sqrt(x * x + y * y);
  if (dist > (L1 + L2)) {
    Serial.println("Target out of reach.");
    return;
  }
  float cosTheta2 = (x * x + y * y - L1 * L1 - L2 * L2) / (2 * L1 * L2);
  float theta2 = acos(cosTheta2);
  float k1 = L1 + L2 * cos(theta2);
  float k2 = L2 * sin(theta2);
  float theta1 = atan2(y, x) - atan2(k2, k1);
  float thetaWrist = -(theta1 + theta2);
  int angle1 = constrain(degrees(theta1), 0, 180);
  int angle2 = constrain(degrees(theta2), 0, 180);
  int angleWrist = constrain(degrees(thetaWrist), 0, 180);
  servoShoulder.write(angle1);
  delay(300);
  servoElbow.write(angle2);
  delay(300);
  servoWrist.write(angleWrist);
  delay(300);
}

void pickAndPlace() {
  servoBase.write(60);
  delay(1000);
  computeAndMoveIK(40.0, 10.0);
  delay(500);
  servoGripper.write(40);
  delay(800);
  computeAndMoveIK(40.0, 20.0);
  delay(800);
  servoBase.write(120);
  delay(1000);
  computeAndMoveIK(40.0, 10.0);
  delay(800);
  servoGripper.write(90);
  delay(800);
  computeAndMoveIK(35.0, 20.0);
  servoBase.write(90);
}
