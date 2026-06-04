
// ---- Knihovny, které budeme potřebovat ----
#include <ESP8266WiFi.h>        // připojení k WiFi
#include <ESP8266HTTPClient.h>  // posílání požadavků (GET, POST)
#include <WiFiClientSecure.h>   // HTTPS = zabezpečené spojení (https://)


// ---- 1) SEM napiš svoji WiFi ----
const char* SSID  = "nazev-wifi";
const char* HESLO = "heslo-k-wifi";


// ---- 2) Celé adresy serveru (jedna proměnná = celé URL i s tokenem) ----
String URL_NOVA_KONVERZACE = "https://ai-be-dev.k8s-dev.plzen.eu/api/kurz/nova-konverzace?token=";
String URL_ZPRAVA          = "https://ai-be-dev.k8s-dev.plzen.eu/api/kurz?token=";


// ---- 3) SEM napiš otázku, kterou se chceš zeptat ----
String OTAZKA = "Kolik je 2 plus 2?";


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
  WiFiClientSecure client1;
  client1.setInsecure();         // jdeme přes HTTPS, ale certifikát nekontrolujeme 

  HTTPClient http1;
  http1.begin(client1, URL_NOVA_KONVERZACE);
  http1.setTimeout(60000);       // počkáme klidně 60 sekund

  http1.GET();                   // <-- TADY voláme první (GET) endpoint
  session = http1.getString();   // server vrátí rovnou jen číslo konverzace
  http1.end();

  Serial.println("Cislo konverzace: " + session);


  // ===========================================================
  //   KROK 2: POSLAT OTÁZKU (POST)
  //   Otázku musíme nejdřív zabalit do JSON - takhle:
  // ===========================================================
  String telo = "{\"session\": \"" + session + "\", \"message\": \"" + OTAZKA + "\"}";


  Serial.println(telo);   // vypíšeme si, jak náš JSON vypadá
}



void loop() {
  // Nic tady není 
}
