/*
    Baja Control Code

    An arduino sketch which controls the motor and servos based on serial input data
*/

// Run once at startup
void setup() {
    Serial.begin(115200);
    pinMode(LED_BUILTIN,OUTPUT);
}

// Run in a loop
void loop() {
    Serial.println("Hello Wolrd!");
    delay(1000);
    digitalWrite(LED_BUILTIN,LOW);
    delay(1000);
    digitalWrite(LED_BUILTIN,HIGH);
}