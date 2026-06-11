void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println();
  Serial.println("ESP8266 nabehl, upload OK!");
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_BUILTIN, LOW);   // LED na ESP8266 sviti pri LOW (invertovana)
  delay(500);
  digitalWrite(LED_BUILTIN, HIGH);  // zhasnuto
  delay(500);
}