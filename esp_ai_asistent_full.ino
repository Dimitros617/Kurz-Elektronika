
// ---- Knihovny, které známe ----
#include <ESP8266WiFi.h>        // připojení k WiFi
#include <ESP8266HTTPClient.h>  // posílání požadavků (GET, POST)
#include <WiFiClientSecure.h>   // HTTPS = zabezpečené spojení (https://)


// ---- 1) SEM napiš svoji WiFi ----
const char* SSID  = "nazev-wifi";
const char* HESLO = "heslo-k-wifi";


// ---- 2) Celé adresy serveru (jedna proměnná = celé URL i s tokenem) ----
String URL_NOVA_KONVERZACE = "https://ai-be-dev.k8s-dev.plzen.eu/api/kurz/nova-konverzace?token=";
String URL_ZPRAVA          = "https://ai-be-dev.k8s-dev.plzen.eu/api/kurz?token=";


// ---- Sem si uložíme číslo naší konverzace, které nám dá server ----
String session = "";



void setup() {
  Serial.begin(115200);
  delay(1000);

  // ===========================================================
  //   PŘIPOJENÍ ESP K INTERNETU (WiFi)
  // ===========================================================
  Serial.print("Pripojuji se k WiFi");
  WiFi.begin(SSID, HESLO);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" hotovo!");


  // ===========================================================
  //   KROK 1: požádáme server o novou konverzaci  (GET)
  //   Server nám vrátí číslo konverzace (session), uložíme si ho.
  // ===========================================================
  WiFiClientSecure client;
  client.setInsecure();        // jdeme přes HTTPS, ale certifikát nekontrolujeme

  HTTPClient http;
  http.begin(client, URL_NOVA_KONVERZACE);
  http.setTimeout(60000);      // počkáme klidně 60 sekund

  http.GET();                  // <-- TADY voláme první (GET) endpoint
  session = http.getString();  // server vrátí rovnou jen číslo konverzace
  http.end();

  Serial.println("Cislo konverzace: " + session);
  Serial.println();
  Serial.println("Napis otazku a stiskni Enter:");
}



void loop() {
  // Čekáme, dokud nenapíšeš otázku do Serial Monitoru a nedáš Enter
  if (Serial.available()) {
    String otazka = Serial.readStringUntil('\n');
    otazka.trim();                     // smaže mezery a Enter na konci
    if (otazka.length() == 0) return;  // prázdné neposíláme

    Serial.println("Ty: " + otazka);
    Serial.println("...premyslim...");


    // =========================================================
    //   KROK 2: pošleme otázku serveru  (POST + JSON)
    // =========================================================
    WiFiClientSecure client;
    client.setInsecure();

    HTTPClient http;
    http.begin(client, URL_ZPRAVA);
    http.setTimeout(60000);
    http.addHeader("Content-Type", "application/json");

    // Tělo požadavku zapsané jako JSON. Výsledek vypadá takhle:
    //   {"session": "...", "message": "tvoje otazka"}
    String telo = "{\"session\": \"" + session + "\", \"message\": \"" + otazka + "\"}";

    http.POST(telo);                    // <-- TADY posíláme POST i s tělem
    String odpoved = http.getString();  // odpověď je čistý text, nic neparsujeme
    http.end();

    Serial.println("AI: " + odpoved);
    Serial.println();
  }
}
