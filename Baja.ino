/*
    Baja Control Code

    An arduino sketch which controls the motor and servos based on serial input data

    current sensor - 0 current has value  505-506. 505 to be safe
*/

#include <Servo.h>

#define SERVO_RIGHTMOST 9
#define SERVO_MIDDLERIGHT 10
#define SERVO_MIDDLELEFT 11
#define SERVO_LEFTMOST 6
#define SERVO_UPPER 5

#define VOLTAGE A0
#define TEMPERATURE A1
#define CURRENT A3
#define CURRENT_MOTOR A4
#define ACCEL_X A7
#define ACCEL_Y A6
#define ACCEL_Z A5

#define PWM 2
#define SLP 3           // 0 means sleep, 1 means active
#define DIR 4           // 0 is backwards, 1 is forwards
#define FLT 7
#define ECHO 8
#define TRIGGER 13
#define SWITCH1 12
#define SWITCH2 22
#define SWITCH3 23

Servo steering;
Servo claw;
Servo armRotation;
Servo armUpDown;
Servo armMain;

void setup() {
    // Start comms with Raspi
    Serial.begin(115200);

    // Set up the motor controller
    pinMode(PWM,OUTPUT);
    pinMode(SLP,OUTPUT);
    pinMode(DIR,OUTPUT);

    // The motor controller starts in sleep mode, and direction is forward.
    digitalWrite(SLP,0);
    digitalWrite(DIR,1);
    analogWrite(PWM,0);

    // Whether there was an overcurrent in the current sensor.
    pinMode(FLT,INPUT);

    // Distance sensor
    pinMode(ECHO,INPUT); // ECHO
    pinMode(TRIGGER, OUTPUT); // TRIGGER
    digitalWrite(TRIGGER,LOW);

    // The Switch with values ABC. These values allow us to read the switch value.
    pinMode(SWITCH1,INPUT_PULLUP);
    pinMode(SWITCH3,INPUT_PULLUP);
    pinMode(SWITCH2,OUTPUT);
    digitalWrite(SWITCH2,0);

    // Servos!
    steering.attach(SERVO_RIGHTMOST,1000,2000);
    claw.attach(SERVO_LEFTMOST,1000,2000);
    armMain.attach(SERVO_MIDDLELEFT,640,2070);
    armUpDown.attach(SERVO_MIDDLERIGHT,640,2070);
    armRotation.attach(SERVO_UPPER,640,2070);

    // Initialize servos to a safe setting
    claw.write(90);
    armMain.write(90);
    armUpDown.write(90);
    armRotation.write(90);
    // Steering is weird in that it has a range of
    // 50-142, with middle at 96. This is due to weirdness
    // in the servo library when changing the timing
    steering.write(96);

    // Wait for serial command, and beep on acquisition
    waitForStartup();
    
}

/*
 Returns the setting of the 3-position switch on the bottom.
 1: A, 2: B, 3: C
*/
int getSwitch() {
    if (digitalRead(SWITCH3)==1) return 1;
    if (digitalRead(SWITCH1)==1) return 2;
    return 3;
}


/*
*/
void waitForStartup() {
    // Wait until serial available
    while (!Serial.available());

    // Beep at first serial command
    digitalWrite(SLP,1);
    analogWrite(PWM,5);
    delay(70);
    analogWrite(PWM,0);
    delay(70);
    analogWrite(PWM,5);
    delay(70);
    analogWrite(PWM,0);
    digitalWrite(SLP,0);
}

// Run in a loop
void loop() {
    
    /*
    int pos;
   for (pos = 0; pos <= 180; pos += 1) { // goes from 0 degrees to 180 degrees
    // in steps of 1 degree
    armRotation.write(pos);              // tell servo to go to position in variable 'pos'
    delay(15);                       // waits 15ms for the servo to reach the position
        if (pos==90) delay(1000);
    }
    delay(1000);
    for (pos = 180; pos >= 0; pos -= 1) { // goes from 180 degrees to 0 degrees
        armRotation.write(pos);              // tell servo to go to position in variable 'pos'
        delay(15);                       // waits 15ms for the servo to reach the position
    }
    //delay(1000);
    */
    /*
    digitalWrite(TRIGGER,HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIGGER,LOW);
    unsigned long duration = pulseIn(ECHO,HIGH,100000);
    float distance = duration/58.2;
    Serial.println(distance);
    delay(200);
    */
    /*
    analogWrite(PWM,20);
    delay(500);
    analogWrite(PWM,0);
    delay(3000);
    */
    
    Serial.println("---------");
    Serial.println(analogRead(VOLTAGE));
    Serial.println(analogRead(TEMPERATURE));
    Serial.println(analogRead(CURRENT));
    Serial.println(analogRead(CURRENT_MOTOR));
    Serial.println(analogRead(ACCEL_X));
    Serial.println(analogRead(ACCEL_Y));
    Serial.println(analogRead(ACCEL_Z));
    Serial.println(digitalRead(FLT));
    Serial.println(getSwitch());
    delay(500);
    
   /*
   int pos;
   for (pos = 50; pos <= 142; pos += 1) { // goes from 0 degrees to 180 degrees
    // in steps of 1 degree
    steering.write(pos);              // tell servo to go to position in variable 'pos'
    delay(15);                       // waits 15ms for the servo to reach the position
        if (pos==96) delay(1000);
    }
    delay(1000);
    for (pos = 142; pos >= 50; pos -= 1) { // goes from 180 degrees to 0 degrees
        steering.write(pos);              // tell servo to go to position in variable 'pos'
        delay(15);                       // waits 15ms for the servo to reach the position
    }
    delay(1000);
    */
    /*
    Serial.println(rd());
    analogWrite(6,30);
    for (int i=0;i < 10;i++) {
        delay(100);
        Serial.println(rd());
    }
    analogWrite(6,0);
    
    for (int i=0;i < 10; i++) {
        Serial.println(rd());
        delay(1000);
    }

    for (pos = 0; pos <= 180; pos += 1) { // goes from 0 degrees to 180 degrees
    // in steps of 1 degree
    myservo.write(pos);              // tell servo to go to position in variable 'pos'
    delay(15);                       // waits 15ms for the servo to reach the position
    if (pos==90) delay(8000);
  }
  delay(1000);
  for (pos = 180; pos >= 0; pos -= 1) { // goes from 180 degrees to 0 degrees
    myservo.write(pos);              // tell servo to go to position in variable 'pos'
    delay(15);                       // waits 15ms for the servo to reach the position
  }
  delay(2000);
  */
}