


#include <ESP8266WiFi.h>        // připojení k WiFi
#include <ESP8266HTTPClient.h>  // posílání požadavků (GET, POST)
#include <WiFiClientSecure.h>   // HTTPS = zabezpečené spojení (https://)


// ---- 1) SEM napiš svoji WiFi ----
const char* SSID  = "Wific";
const char* HESLO = "d3E947fb65";


// ---- 2) Celé adresy serveru (jedna proměnná = celé URL i s tokenem) ----
String URL_NOVA_KONVERZACE = "https://ai-be-dev.k8s-dev.plzen.eu/api/kurz/nova-konverzace?token=IfhwEsI4QadO1B2T97RdDF6QNIpcOm91";
String URL_ZPRAVA          = "https://ai-be-dev.k8s-dev.plzen.eu/api/kurz?token=IfhwEsI4QadO1B2T97RdDF6QNIpcOm91";


// ---- 3) SEM napiš otázku, kterou se chceš zeptat ----
String OTAZKA = "Kolik je 2 plus 2?";


// ---- Sem si uložíme číslo naší konverzace, které nám dá server ----
String session = "3cda182f-bf33-450b-b31b-1725789a063d";



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
  //   Jeden zabezpečený klient pro OBA požadavky.
  //   (ESP8266 má málo paměti - dva HTTPS klienty najednou se
  //    do ní nevejdou a program by spadl na chybu OOM.)
  // ===========================================================
  WiFiClientSecure client;
  client.setInsecure();          // jdeme přes HTTPS, ale certifikát nekontrolujeme

  HTTPClient http;


  // ===========================================================
  //   KROK 1: požádáme server o novou konverzaci  (GET)
  //   Server nám vrátí číslo konverzace (session), uložíme si ho.
  // ===========================================================
  http.begin(client, URL_NOVA_KONVERZACE);
  http.setTimeout(60000);        // počkáme klidně 60 sekund

  http.GET();                    // <-- TADY voláme první (GET) endpoint
  session = http.getString();    // server vrátí rovnou jen číslo konverzace
  http.end();                    // spojení ukončíme, paměť se uvolní

  Serial.println("Cislo konverzace: " + session);


  // ===========================================================+
  //   KROK 2: pošleme naši otázku serveru  (POST + JSON)
  // ===========================================================
  http.begin(client, URL_ZPRAVA);
  http.setTimeout(60000);
  http.addHeader("Content-Type", "application/json");

  // Tělo požadavku zapsané jako JSON. Výsledek vypadá takhle:
  //   {"session": "...", "message": "tvoje otazka"}
  String telo = "{\"session\": \"" + session + "\", \"message\": \"" + x + "\"}";

  http.POST(telo);                    // <-- TADY posíláme POST i s tělem
  String odpoved = http.getString();  // odpověď je čistý text, nic neparsujeme
  http.end();

  Serial.println("Ty: " + OTAZKA);
  Serial.println("AI: " + odpoved);
}



void loop() {
  // Nic tady není - všechno proběhlo jednou v setup() po zapnutí.
}

