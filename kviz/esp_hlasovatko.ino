// ===== HLASOVÁTKO =====
// Serial monitor: 115200 baud, "Nový řádek" (Newline)
// Až přijde otázka, napiš A, B, C nebo D a zmáčkni Enter.

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>


// ---- 1) SEM napiš svoji přezdívku (bez mezer) ----
String NICK = "tvoje-prezdivka";

// ---- 2) SEM napiš WiFi z plátna ----
const char* SSID  = "nazev-wifi";
const char* HESLO = "heslo-k-wifi";

// ---- 3) SEM napiš adresu serveru z plátna ----
String SERVER = "http://192.168.0.10:8000";


String posledniOtazkaId = "";
unsigned long posledniPoll = 0;


void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.print("\nPripojuji se k WiFi");
  WiFi.begin(SSID, HESLO);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" hotovo!");
  Serial.println("Cekam na otazku...\n");
}


void loop() {
  // NOVINKA: polling - každé 2 s se zeptáme serveru, jestli není nová otázka.
  // delay(2000) nepoužijeme, protože by ESP spalo a nevidělo by,
  // co mezitím píšeš do Serial monitoru. millis() = ms od zapnutí.
  if (millis() - posledniPoll >= 2000) {
    posledniPoll = millis();
    zeptejSeNaOtazku();
  }

  // napsal uživatel odpověď?
  if (Serial.available() > 0) {
    String vstup = Serial.readStringUntil('\n');
    vstup.trim();
    vstup.toUpperCase();

    if (vstup == "A" || vstup == "B" || vstup == "C" || vstup == "D") {
      posliOdpoved(vstup);
    } else if (vstup.length() > 0) {
      Serial.println("Napis jen A, B, C nebo D a Enter.");
    }
  }
}


// GET - server vraci text, prvni radek je cislo otazky
void zeptejSeNaOtazku() {
  WiFiClient client;
  HTTPClient http;

  http.begin(client, SERVER + "/api/otazka");
  int kod = http.GET();

  if (kod == 200) {
    String text = http.getString();
    String id = text.substring(0, text.indexOf('\n'));

    // jiné číslo než minule = nová otázka
    if (id != "0" && id != posledniOtazkaId) {
      posledniOtazkaId = id;
      Serial.println("\n========== NOVA OTAZKA ==========");
      Serial.println(text.substring(text.indexOf('\n') + 1));
    }
  } else {
    Serial.println("Server neodpovida (kod " + String(kod) + ")");
  }

  http.end();
}


// POST - nick jde v adrese, volba v tele jako JSON
void posliOdpoved(String volba) {
  WiFiClient client;
  HTTPClient http;

  http.begin(client, SERVER + "/api/odpoved?nick=" + NICK);
  http.addHeader("Content-Type", "application/json");

  int kod = http.POST("{\"volba\":\"" + volba + "\"}");

  if (kod == 200) {
    Serial.println(">>> Odpoved " + volba + " odeslana, sleduj platno! <<<");
  } else if (kod == 409) {
    Serial.println("Zadna otazka jeste nebezi.");
  } else {
    Serial.println("Chyba (kod " + String(kod) + "), zkus to znovu.");
  }

  http.end();
}
