#include <Arduino.h>

void setup() {
  Serial.begin(115200);

  delay(1000);

  Serial.write('B');
  Serial.write('\r');
  Serial.write('\n');

  delay(2000);
}

void loop() {
  Serial.write('1');
  delay(300);

  Serial.write('2');
  delay(300);

  Serial.write('3');
  delay(300);

  Serial.write('4');
  delay(300);

  Serial.write('5');
  delay(300);

  Serial.write('6');
  delay(300);

  Serial.write('7');
  delay(300);

  Serial.write('8');
  delay(300);

  Serial.write('9');
  delay(300);

  Serial.write('\r');
  Serial.write('\n');

  delay(2000);
}
