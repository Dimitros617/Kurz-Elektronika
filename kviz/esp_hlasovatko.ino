/*
 * =====================================================================
 *                        ⚡ H L A S O V Á T K O ⚡
 * =====================================================================
 *  Tvoje ESP se připojí na WiFi a promění se v hlasovací zařízení!
 *
 *  Jak to funguje:
 *   1. ESP se každé 2 sekundy ptá serveru: "Je nová otázka?"  (GET)
 *   2. Když přijde nová otázka, vypíše se ti tady do Serial monitoru.
 *   3. Ty napíšeš A, B, C nebo D a zmáčkneš Enter.
 *   4. ESP pošle tvoji odpověď na server.                     (POST)
 *   5. Sleduj plátno — tvoje jméno tam přiletí i s konfetami! 🎉
 *
 *  Serial monitor nastav na 115200 baud a "Nový řádek" (Newline)!
 * =====================================================================
 */

#include <ESP8266WiFi.h>        // připojení k WiFi
#include <ESP8266HTTPClient.h>  // posílání požadavků (GET, POST)


// ---- 1) SEM napiš svoji PŘEZDÍVKU (bez mezer, max 20 znaků) ----
String NICK = "tvoje-prezdivka";

// ---- 2) SEM napiš WiFi (učitel ji má na plátně) ----
const char* SSID  = "nazev-wifi";
const char* HESLO = "heslo-k-wifi";

// ---- 3) SEM napiš IP adresu serveru (učitel ji má na plátně) ----
String SERVER = "http://192.168.0.10:8000";


// ---- Sem si ukládáme číslo poslední otázky, kterou jsme už viděli ----
// Díky tomu poznáme, že na serveru přibyla NOVÁ otázka.
String posledniOtazkaId = "";

// ---- Čas posledního dotazu na server (pro polling) ----
unsigned long posledniPoll = 0;


void setup() {
  Serial.begin(115200);
  delay(1000);

  // ===========================================================
  //   PŘIPOJENÍ K WIFI — to už znáš z minulé hodiny!
  // ===========================================================
  Serial.print("\nPripojuji se k WiFi");
  WiFi.begin(SSID, HESLO);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" hotovo!");
  Serial.println("Cekam na prvni otazku...\n");
}


void loop() {
  // ===========================================================
  //   ✨ NOVINKA DNEŠNÍ HODINY: POLLING ✨
  //
  //   Server nám neumí sám "zavolat" — my se ho musíme
  //   pravidelně PTÁT, jestli nemá něco nového.
  //   Tomu se říká POLLING (z angl. "dotazování").
  //
  //   Proč nepoužijeme delay(2000)?
  //   delay() ESP úplně USPÍ — a spící ESP by nepoznalo,
  //   že jsi mezitím napsal odpověď do Serial monitoru!
  //   Proto si jen pamatujeme ČAS posledního dotazu (millis()
  //   = počet milisekund od zapnutí) a ptáme se, až uplynou 2 s.
  //   Zbytek času může loop() svištět dál a hlídat klávesnici.
  // ===========================================================
  if (millis() - posledniPoll >= 2000) {
    posledniPoll = millis();
    zeptejSeNaOtazku();
  }

  // ===========================================================
  //   HLÍDÁNÍ KLÁVESNICE — napsal něco uživatel?
  // ===========================================================
  if (Serial.available() > 0) {
    // přečteme celý řádek (po Enter) a ořežeme mezery
    String vstup = Serial.readStringUntil('\n');
    vstup.trim();
    vstup.toUpperCase();   // a -> A, b -> B ...

    if (vstup == "A" || vstup == "B" || vstup == "C" || vstup == "D") {
      posliOdpoved(vstup);
    } else if (vstup.length() > 0) {
      Serial.println("To neznam! Napis jen A, B, C nebo D a Enter.");
    }
  }
}


// =============================================================
//   GET — zeptáme se serveru na aktuální otázku
//   Server vrací obyčejný text. První řádek = číslo otázky.
// =============================================================
void zeptejSeNaOtazku() {
  WiFiClient client;             // obyčejné HTTP — jsme v lokální síti,
  HTTPClient http;               // žádné HTTPS/certifikáty nepotřebujeme

  http.begin(client, SERVER + "/api/otazka");
  int kod = http.GET();          // <-- GET požadavek, jak ho znáš

  if (kod == 200) {
    String text = http.getString();

    // první řádek odpovědi = číslo otázky
    String id = text.substring(0, text.indexOf('\n'));

    // je to JINÉ číslo, než jsme viděli naposledy? -> NOVÁ otázka!
    if (id != "0" && id != posledniOtazkaId) {
      posledniOtazkaId = id;
      Serial.println("\n=============================================");
      Serial.println("  NOVA OTAZKA c. " + id);
      Serial.println("=============================================");
      // vypíšeme všechno za prvním řádkem (samotnou otázku)
      Serial.println(text.substring(text.indexOf('\n') + 1));
    }
  } else {
    Serial.println("Server neodpovida (kod " + String(kod) + "), zkusim za chvili...");
  }

  http.end();
}


// =============================================================
//   POST — pošleme svoji odpověď na server
//   Přezdívka jde v adrese (?nick=...), volba v těle jako JSON.
// =============================================================
void posliOdpoved(String volba) {
  WiFiClient client;
  HTTPClient http;

  http.begin(client, SERVER + "/api/odpoved?nick=" + NICK);
  http.addHeader("Content-Type", "application/json");

  // tělo požadavku — malý JSON, např. {"volba":"A"}
  String telo = "{\"volba\":\"" + volba + "\"}";

  int kod = http.POST(telo);     // <-- POST požadavek, jak ho znáš

  if (kod == 200) {
    Serial.println(">>> Odpoved " + volba + " odeslana! Sleduj platno! <<<");
    Serial.println("(Kdyz si to rozmyslis, posli jinou - plati posledni.)");
  } else if (kod == 409) {
    Serial.println("Zadna otazka jeste nebezi, pockej na ucitele.");
  } else {
    Serial.println("Chyba pri odesilani (kod " + String(kod) + "), zkus to znovu.");
  }

  http.end();
}
