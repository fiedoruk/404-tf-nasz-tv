# Kontrakt dla agenta instalującego Nasz TV

Przeczytaj README, HUMAN, COMPATIBILITY, BLOCKERS, LICENSE i external-pins.json.
Zakres to własny odbiornik użytkownika i legalnie dostępna mu telewizja.

1. Ustal model, Android, architekturę, Kodi, skórkę i aktywny profil przez
   odczyt. Wybierz jawnie właściwe urządzenie. Nie publikuj jego identyfikatorów.
2. Sprawdź SHA pobranych paczek z SHA256SUMS. Brak sumy upstream to UNKNOWN.
   Nie traktuj zgodności plików ani udanego builda jako odbioru na sprzęcie.
3. Przed zmianą zachowaj prywatną kopię i konkretną drogę cofnięcia.
   Nie kopiuj ustawień innej osoby. Nie ujawniaj danych konta ani parowania.
4. Instaluj w kolejności HUMAN. GUI wymaga setup; opisy GUI wymagają gotowego
   OrangeGo i reconnect. Nie obchodź odmowy instalatora ani pinów skórki.
5. Ulubione wymagają osobnej, świadomej zgody użytkownika na zapis bazy.
   Przygotowanie integracji nie tworzy grupy i nie udziela zgody w imieniu
   innej osoby. Nie odtwarzaj całej bazy ponad nowe preferencje.
6. Głos pozostaje eksperymentalny i bez kwalifikacji nie steruje kanałami.
   Nie wytwarzaj fikcyjnej kwalifikacji. Mikrofon i zmiana asystenta wymagają
   decyzji użytkownika. ADBboot jest osobnym opt-in, nie krokiem domyślnym.
7. Nie resetuj konta, DRM ani urządzenia; nie odblokowuj bootloadera i nie
   zmieniaj firmware. Nie wykonuj celowych awarii dla sprawdzenia reconnect.
8. Po zmianie sprawdź to, na co użytkownik zezwolił: obraz, dźwięk, pilot,
   listę i cofnięcie. Zapisz krótko wykonane/niewykonane i zakończ własne
   procesy. Nie pozostawiaj monitoringu ani publicznego dostępu do sterowania.

Opis wspólnego zestawu: sprawdzone na jednym Chromecast z Google TV HD,
Android 14, Kodi 21.3 ARMv7, AZR 3.0.3, Orange Start TV; drugi egzemplarz:
nie sprawdzony. Ograniczenie pozostaje prawdziwe po samym rozpakowaniu wydania.
Publiczny build nie był ponownie instalowany na odbiorniku. Nie deklaruj
przenośności, stabilnego 419, gotowego głosu ani obsługi Kodi 22 bez nowego dowodu.

Modyfikacje źródeł buduj według BUILD. Rozdzielaj MIT, CC BY 4.0, GPL-2.0
i CC BY-NC-SA 3.0. Nie przypisuj MIT adaptacjom AZR ani praw do cudzych danych.
