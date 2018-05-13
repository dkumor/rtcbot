/*
    Baja Control Code

    An arduino sketch which controls the motor and servos based on serial input data
*/

#include <Servo.h>

Servo myservo;
int pos;
// Run once at startup
void setup() {

    // Claw servo
    // myservo.attach(6,1000,2000);

    // This seems to be basically the full range of the servo
    myservo.attach(6,640,2070);
    /*
    Serial.begin(115200);
    pinMode(LED_BUILTIN,OUTPUT);
    pinMode(6,OUTPUT);
    pinMode(9,OUTPUT);
    digitalWrite(9,HIGH);

    analogWrite(6,0);
    
    delay(1000);
    */
}

int rd() {
    return analogRead(A2)-508;
}

// Run in a loop
void loop() {
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
*/
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
}