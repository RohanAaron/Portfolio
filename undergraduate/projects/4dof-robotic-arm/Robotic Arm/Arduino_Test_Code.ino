/*
  3-DOF Robotic Arm — Test/Calibration Code
  Extracted from: Appendix, "Arduino Test Code"

  A simpler, fixed-sequence servo movement test used to validate servo
  wiring, range of motion, and smooth interpolation before running the
  full inverse-kinematics pick-and-place program.
*/

#include <Servo.h>

Servo servoBase;
Servo servolink1;
Servo servowrist;
Servo servogrip;

void smoothMove(Servo &servo, int fromAngle, int toAngle, int stepDelay) {
  int step = (fromAngle < toAngle) ? 1 : -1;
  for (int angle = fromAngle; angle != toAngle; angle += step) {
    servo.write(angle);
    delay(stepDelay);
  }
  servo.write(toAngle);
}

void setup() {
  servoBase.attach(3);
  servolink1.attach(4);
  servowrist.attach(5);
  servogrip.attach(6);

  servoBase.write(120);
  servolink1.write(90);
  servowrist.write(90);
  servogrip.write(90);
  delay(1000);

  smoothMove(servolink1, 90, 180, 20);
  delay(1000);

  smoothMove(servoBase, 120, 90, 20);
  delay(1000);

  smoothMove(servowrist, 90, 0, 20);
  delay(1000);

  smoothMove(servogrip, 90, 135, 20);
  delay(1000);

  smoothMove(servolink1, 180, 90, 20);
  delay(1000);

  smoothMove(servogrip, 135, 35, 20);
  delay(1000);

  smoothMove(servolink1, 90, 180, 20);
  delay(1000);

  smoothMove(servoBase, 90, 20, 20);
  delay(1000);

  smoothMove(servolink1, 180, 90, 20);
  delay(1000);

  smoothMove(servogrip, 35, 135, 20);
  delay(1000);
}

void loop() {}
