// Bench-only firmware. NO actuator GPIOs and NO fabricated sensor readings.
// STOP is latched. MOVE / ARM commands are always rejected in this starter.
#include <Arduino.h>
#include <string.h>
char input[80];
uint8_t length=0;
bool overflowed=false;
uint32_t lastReport=0;
const char* reason="boot_disarmed";

void handle(const char *line) {
  if(strcmp(line,"STOP")==0) reason="stop_requested";
  else if(strcmp(line,"PING")==0) Serial.println(F("{\"type\":\"pong\",\"motion_enabled\":false}"));
  else {
    reason="command_rejected";
    Serial.println(F("{\"type\":\"reject\",\"reason\":\"motion_not_implemented\"}"));
  }
}

void setup() { Serial.begin(115200); }
void loop() {
  for(uint8_t count=0;count<32 && Serial.available();count++) {
    const char ch=(char)Serial.read();
    if(ch=='\n') {
      if(!overflowed) { input[length]='\0'; handle(input); }
      else reason="oversized_frame_rejected";
      length=0; overflowed=false;
    } else if(ch!='\r') {
      if(length<sizeof(input)-1 && !overflowed) input[length++]=ch;
      else overflowed=true;
    }
  }
  if(millis()-lastReport>=200) {
    lastReport=millis();
    Serial.print(F("{\"type\":\"telemetry\",\"source\":\"bench_firmware\",\"uptime_ms\":"));
    Serial.print(lastReport);
    Serial.print(F(",\"motion_enabled\":false,\"sensors_ready\":false,\"reason\":\""));
    Serial.print(reason); Serial.println(F("\"}"));
  }
}
