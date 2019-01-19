// Test

bool out =false;

void setup() {
    Serial.begin(115200);
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, out);
    Serial.write(192);
    Serial.write(105);
}
void loop() {
    if (Serial.available() > 0) {
        Serial.print("I received: ");
        char b = Serial.read();
        Serial.println(b);
        if (b==105) {
          out = !out;
          digitalWrite(LED_BUILTIN, out);
        }
    }
}
