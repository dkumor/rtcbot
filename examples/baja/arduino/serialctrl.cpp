#include <Arduino.h>
#include <HardwareSerial.h>
#include <stdint.h>


typedef __attribute__ ((packed)) struct {
    uint16_t value1;
    uint8_t checksum;
} controlMessage;

typedef __attribute__ ((packed)) struct {
    uint8_t checksum;
    uint16_t value2;
} sensorMessage;

controlMessage cMsg;
sensorMessage sMsg;


#define writeStruct(serial,structObject) (serial.write((char*)&structObject,sizeof(structObject)))

#define readStruct(serial,structObject) readStruct_(serial,(char*)&structObject,sizeof(structObject))
bool readStruct_(HardwareSerial& Serial, char* s, int ssize) {
    if (Serial.available() >= ssize) {
        Serial.readBytes(s,ssize);
        return true;
    }
    return false;
}

uint8_t checksum(uint8_t* data, int length) {
    if (length==0) return 0;
    uint8_t csum = data[0];
    for (int i=1;i<length;i++) {
        csum = csum ^ data[i];
    }
    return csum;
}

void runget(HardwareSerial& Serial) {
    if (readStruct(Serial,cMsg)) {
        Serial.println(cMsg.checksum);
        Serial.println(cMsg.value1);
        //sMsg.checksum = cMsg.checksum;
        //sMsg.value2 = cMsg.value1;
        //writeStruct(Serial,sMsg);
    }
}