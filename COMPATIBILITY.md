# Zgodność wydania 2026.10.25

**Sprawdzone na jednym zestawie: Chromecast z Google TV HD, Android 14,
Kodi 21.3 ARMv7, AZR 3.0.3, Orange Start TV. Drugi egzemplarz: nie sprawdzony.**
Status poniżej opisuje działanie bazowych wersji na tym zestawie. Nowe
publiczne opakowanie, menu konfiguracji i instalator integracji Ulubionych
sprawdzono na komputerze; instalacja tych dokładnych paczek na urządzeniu
pozostaje niewykonana.

| Moduł | Wersja | Status i zakres | Licencja |
|---|---|---|---|
| GUI + dwie etykiety HUD | 0.1.9 | Działa na jednym zestawie; wyłącznie AZR 3.0.3 | MIT; własne grafiki CC BY 4.0 |
| Setup | 0.1.0 | Mapa pilota działa; nowe menu publiczne sprawdzone na komputerze | MIT |
| Reconnect | 0.1.7 | Usługa działa; odzyskanie naturalnego 419 niepotwierdzone | MIT |
| EPG | 0.1.1 | Odnawianie eksportu działa; wymaga działającego konta | MIT |
| Ulubione | 0.1.6 | EKSPERYMENTALNE; lokalny zapis potwierdzony na jednym zestawie; Android/Kodi 21/schema 46 | Kod MIT; adaptacje XML AZR CC BY-NC-SA 3.0 |
| OrangeGo + Zero | 1.0.15 | Działa na jednym zestawie; wydanie bez grafik upstream | GPL-2.0 |
| DialogSeekBar AZR | 3.0.3 + patch | Działa na jednym zestawie; pełna skórka pobierana osobno | CC BY-NC-SA 3.0 |
| Kafel Nasz TV | 1.5 / code 7 | Działa na jednym zestawie; lokalne RPC i autostart Kodi | MIT; grafiki CC BY 4.0 |
| Głos | 0.1.4 / code 5 | EKSPERYMENTALNY; samodzielny APK; bez kwalifikacji brak przełączania kanałów | MIT |

Kodi 22, Chromecast 4K, inne wersje AZR, inne platformy i taryfy nie mają
odbioru w tym wydaniu. Minimum Androida deklarowane w manifeście kafla to
API 21, lecz nie oznacza to przeprowadzonego testu na Androidzie 5.
Głos deklaruje minimum API 34. Nie gwarantujemy rozdzielczości HD każdego kanału.

GUI nie zawiera fontów ani skórki. Jego własne okna używają nazw czcionek
udostępnianych przez AZR. Ulubione mają oddzielny katalog adaptacji
`src/kodi/script.nasztv.favourites/resources/azr/` i wymagają opt-in.
Nie dostarczamy cudzych dodatków `script.module.*`; zależności instaluje odbiorca.
