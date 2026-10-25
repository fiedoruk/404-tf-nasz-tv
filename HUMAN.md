# Instalacja i cofnięcie

Wydanie 2026.10.25 opiera się na jednym zestawie: Chromecast z Google TV HD,
Android 14, Kodi 21.3 ARMv7, AZR 3.0.3, Orange Start TV. Drugi egzemplarz:
nie sprawdzony. Nie zakładamy, że instalacja na innym sprzęcie będzie identyczna.

## 1. Przygotuj własny odbiornik

Zachowaj kopię profilu Kodi przy zamkniętej aplikacji oraz poprzednie wersje
zmienianych dodatków. Kopia zawiera dane prywatne — przechowuj ją u siebie.
Nie zastępuj profilu cudzą kopią. Jeżeli zestaw jest teraz używany do oglądania,
wybierz osobny czas na instalację.

Pobierz potrzebne pliki wydania i `SHA256SUMS` do jednego katalogu.
Na macOS/Linux sprawdź je poleceniem `shasum -a 256 -c SHA256SUMS`.
Brak pliku z listy oznacza niepełne pobranie; można pobrać wszystkie pliki
wydania albo sprawdzić sumę konkretnego pobranego pliku poleceniem
`shasum -a 256 NAZWA_PLIKU` i porównać ją z manifestem.

Plik źródłowy ZIP rozpakowuje się na komputerze. ZIP dodatku Kodi instaluje
się przez **Dodatki → Instaluj z pliku ZIP**. Włącz zgodę na nieznane źródła
tylko świadomie, a po instalacji możesz ją wyłączyć.

## 2. Zainstaluj zewnętrzne składniki

W [external-pins.json](external-pins.json) znajdują się adresy źródłowe,
wersje i dostępne SHA256. `null` oznacza brak ustalonej sumy, a nie dowód
zgodności. Nie podmieniaj niepasującej sumy własną i nie zakładaj, że
najnowsza wersja jest równoważna wymienionej.

1. Zainstaluj Kodi 21.3 dla ARMv7 z [kodi.tv](https://kodi.tv/download/android/).
   W Kodi wybierz polski interfejs z oficjalnego repozytorium.
2. Zainstaluj AZR 3.0.3 z kanału
   [beatmasterRS](https://github.com/beatmasterRS/skin.arctic.zephyr.mod).
   Pozwól Kodi pobrać wymagane dodatki skórki ze źródeł ich autorów.
   Wybierz AZR, jasny motyw Light i czytelną odmianę czcionki Default bold.
   Nie pobieraj fontów z tego projektu — nie są dołączone.
3. Z repozytorium Kodi zainstaluj IPTV Simple 21.11.0, InputStream Adaptive
   21.5.25 i wymagane zależności. FFmpeg Direct/RTMP są odnotowane jako
   składniki zestawu, ale nie każdy kanał ich potrzebuje.
4. Zainstaluj wymagania OrangeGo: requests, inputstreamhelper oraz js2py
   z przypiętego [repozytorium mtr81](https://github.com/mtr81/kodi_addons).
   Pełna lista bibliotek i ich wersji jest w manifeście zewnętrznym.
   W przypiętym pyjsparser występuje sprzeczność licencji MIT/GPLv3.
   Nie dystrybuujemy tej biblioteki ani nie deklarujemy rozwiązania sprzeczności.
5. Widevine, jeśli wymagane przez kanał, jest pozyskiwane przez właściwe
   mechanizmy platformy/InputStream. Nie kopiuj materiału DRM między urządzeniami.

## 3. Uruchom OrangeGo i telewizję

Zainstaluj `plugin.video.orange_go-1.0.15-nasz-tv.zip`. Zawiera zmiany
1.0.5→1.0.15, dodanie Kanału Zero do grupy informacyjnej i komplet źródeł
pochodnej. Nie zawiera oryginalnych grafik, bibliotek ani ustawień konta.
Nie trzeba najpierw instalować bazowego ZIP-u 1.0.5. Jeśli wybierasz własne
nakładanie patchy, patrz [patches/README.md](patches/README.md).

W ustawieniach OrangeGo wpisz dane własnego konta. Otwórz dodatek, zaloguj
się i sprawdź, czy odtwarza dostępny w abonamencie kanał. Dane pozostają
w profilu Kodi. Nie wpisuj ich do zgłoszenia błędu ani do rozmowy z agentem.

Zainstaluj `script.orange.tata.setup-0.1.0.zip`. Otwórz go z dodatków
programowych i wybierz **Utwórz M3U i EPG z własnego konta Orange**.
Eksport wymaga już działającego zalogowania; sam nie przeprowadza logowania.
Powstają pliki w profilu Kodi:

```text
special://profile/addon_data/plugin.video.orange_go/tata/channels.m3u
special://profile/addon_data/plugin.video.orange_go/tata/epg.xml
```

W IPTV Simple dodaj konfigurację z **lokalnym** plikiem M3U i XMLTV pod tymi
ścieżkami. Gdy selektor plików nie przyjmuje `special://`, wybierz odpowiadający
im katalog w swoim profilu Kodi. Nie wklejaj ścieżki innego użytkownika.
Odśwież klienta PVR i sprawdź listę kanałów oraz przewodnik.

Zainstaluj `service.orange.tata.epg-0.1.1.zip` i
`service.orange.tata.reconnect-0.1.7.zip`, zezwalając na uruchomienie tych usług.
EPG odnawia eksport; reconnect pomaga przy odzyskiwaniu i sygnalizuje
gotowość odtwarzania potrzebną opisom GUI. Reconnect nie ma potwierdzonego
odzyskania naturalnego 419 w tej wersji. Nie wywołuj sztucznie awarii konta.

## 4. Włącz pilot i informacje

W dodatku setup wybierz **Zainstaluj mapę pilota**. Następnie zainstaluj
`script.nasztv.gui-0.1.9.zip` i uruchom go przy aktywnej AZR 3.0.3.
Instalator robi kopie zmienianych plików i odmawia nadpisania nieznanego stanu.
Sam nakłada zmianę DialogSeekBar; nie nakładaj osobnego patcha przed nim.
ZIP zawiera dwa napisy przypięcia HUD. To objaśnienie zachowania,
bez zmiany czasu automatycznego chowania.

Podczas telewizji: góra/dół zmienia kanał, OK otwiera listę i grupy,
lewo pokazuje pomoc, prawo przełącza czysty obraz → pasek → szczegóły →
czysty obraz. Wstecz chowa informacje. Nie zakładaj, że przycisk zasilania
telewizora zatrzymuje transmisję na przystawce.

Na czas używania tej integracji wyłącz automatyczną aktualizację **samej AZR**.
Przed jej aktualizacją cofnij integrację. Jeżeli masz już zmodyfikowaną skórkę
lub wcześniejszą nakładkę, najpierw użyj jej właściwego cofnięcia. Nie usuwaj
blokady instalatora i nie kopiuj ręcznie nowych plików ponad cudze zmiany.

## 5. Opcjonalny kafel Android

Zainstaluj `nasz-tv-shortcut-1.5.apk` standardowym instalatorem Androida.
Przed jego użyciem w Kodi włącz sterowanie przez aplikacje **na tym samym
urządzeniu**. Aplikacja łączy się z lokalnym TCP na porcie 9090. Nie włączaj
dostępu z innych systemów tylko dla tego kafla i nie udostępniaj portu w routerze.

W ustawieniach PVR Kodi wybierz uruchamianie ostatniego kanału przy starcie
(Watch TV / odtwarzanie ostatnio oglądanego kanału). Sprawdź najpierw ręczny
start Kodi. Kafel otwiera Kodi; przy określonym pustym stanie może poprosić
Kodi o normalne zamknięcie i ponownie go uruchomić. Wstecz anuluje ekran startu.
Wybrany launcher Androida może pokazać kafel; Projectivy jest opcjonalny.

**ADBboot jest opcjonalny i domyślnie nieaktywny bez dodatkowego uprawnienia.**
Zwykłe użycie kafla go nie wymaga. Zaawansowany użytkownik może świadomie
nadać aplikacji `android.permission.WRITE_SECURE_SETTINGS` przez ADB na
własnym urządzeniu. Moduł próbuje włączyć bezprzewodowe debugowanie po
uruchomieniu systemu, gdy spełnione są warunki Androida. Nie omija parowania.
Cofnięcie: odbierz to uprawnienie lub odinstaluj kafel i wyłącz debugowanie
w ustawieniach Androida. Nie dołączamy plików parowania.

## 6. Eksperymentalne Ulubione

**Ten moduł zapisuje przypisania kanałów do lokalnej grupy w bazie Kodi.
Przed użyciem zrób kopię profilu przy zamkniętym Kodi.** Odinstalowanie
dodatku nie przywraca poprzedniej listy.

Zainstaluj `script.nasztv.favourites-0.1.6-experimental.zip`. Otwórz dodatek
i wybierz **Przygotuj integrację AZR**. Po potwierdzeniu przygotuje prywatny
katalog kopii oraz dwa okna AZR i mapę klawiszy. Okna są na CC BY-NC-SA 3.0;
kod dodatku i instalatora jest na MIT. Instalator przyjmuje wyłącznie znane
pliki AZR 3.0.3. Przy odmowie zatrzymaj instalację, zamiast wymuszać zapis.

W natywnym menedżerze grup Kodi utwórz **lokalną** grupę dokładnie
`Moje ulubione` (nie grupę dostarczaną przez PVR). Potem wybierz w dodatku
**Edytuj listę** albo przytrzymaj OK na liście kanałów. Pierwsze użycie zrób
na jednej zmianie, sprawdzając listę po ponownym otwarciu. Moduł jest ograniczony
do Androida, Kodi 21 i schematu bazy 46; nie działa jako ogólny edytor innych baz.

Kopie usuwanych przypisań powstają w prywatnym katalogu aplikacji Kodi
`files/nasztv-favourites-backups` z ograniczonymi prawami. Nie są pełną kopią
profilu. Najbezpieczniejsze cofnięcie pojedynczej zmiany to ponowne wybranie
poprzednich kanałów w edytorze. Nie uruchamiaj automatycznego odtwarzania
całej bazy ponad późniejsze wybory. Narzędzie scalające usunięte przypisania
ze świeżą bazą nie jest częścią tego wydania.

## 7. Eksperymentalny głos

`nasz-tv-voice-0.1.4-experimental.apk` to osobny build dla Androida 14 lub
nowszego, z własnym źródłem i recepturą. Nie ma ikony startowej; jest usługą
asystenta wybieraną w ustawieniach Androida. Wymaga mikrofonu i zgodnego
polskiego rozpoznawania mowy Google. Nie włącza stałego nasłuchu, ale wybrany
asystent może pozostawać rezydentny.

**Nie jest to gotowa funkcja głosowego przełączania kanałów na nowym sprzęcie.**
Kod zachowuje blokadę sterowania do lokalnej kwalifikacji urządzenia; dane
kwalifikacyjne nie są częścią wydania. Nie usuwaj tej blokady i nie kopiuj
danych z innego urządzenia. Ten APK zachowuje tryb debugowalny wersji
eksperymentalnej. Do codziennego sterowania używaj pilota. Cofnięcie: wybierz
poprzedniego asystenta, odbierz dostęp do mikrofonu i odinstaluj aplikację.

## Cofnięcie całego zestawu

1. Zamknij edytor Ulubionych i w jego menu wybierz **Cofnij integrację AZR**.
   To cofa okna i mapę klawiszy, zachowując listę kanałów oraz kopie danych.
2. W setup wybierz **Cofnij GUI**, a następnie **Cofnij mapę pilota**.
   Ta kolejność jest konieczna, ponieważ GUI opiera się na mapie setup.
3. Wyłącz usługi reconnect/EPG, usuń niepotrzebne dodatki i przywróć własne
   wcześniejsze ustawienia PVR. Gdy wracasz do poprzedniego OrangeGo,
   zachowaj kopię swojego profilu i odpowiedni wcześniejszy ZIP.
4. Cofnij asystenta i kafel jak opisano wyżej. Przywróć ustawienia autostartu,
   sterowania lokalnego i aktualizacji skórki, które sam zmieniłeś.

Jeżeli instalator wykrywa późniejsze zmiany, nie nadpisze ich automatycznie.
Zachowaj jego kopie i porównaj pliki. Awaryjny powrót do pełnej kopii profilu
wykonuj tylko przy zamkniętym Kodi i ze świadomością utraty późniejszych zmian.
