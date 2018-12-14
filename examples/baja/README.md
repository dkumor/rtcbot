Robot claw:
The claw is:
myservo.attach(6,1000,2000);

raspi to atmega connectors:
red goes to 3v3
grey to 17
yellow to raspi tx (top)
orange to raspi rx

Distance Sensor
Input to sensor:
VCC is green wire, gnd is red wire

Output into micro
echo is green
trig is yellow

atmega

A0 is voltage sensor
A1 is temp sensor

A3 CS
A4 CS from motor controller
A5 Z accel
A6 Y accel
A7 X accel

3 SLP
2 PWM
4 DIR

5 upper servo
6 leftmost servo

7 FLT CS

9 rightmost servo
10 middle right
11 middle left

8 echo
13 trigger

the switch
12
22
23

STEERING
1000,2000 - attach timing
range:
50-142, middle: 96
