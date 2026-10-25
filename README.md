# Nasz TV

Prosty pilot, czytelne informacje o programie i szybki powrót do telewizji
na Android TV. Projekt powstał dla osoby, która chce oglądać kanały,
a nie poruszać się po wielu aplikacjach. Wymaga własnej, działającej usługi
Orange i samodzielnie zainstalowanych Kodi oraz Arctic: Zephyr Reloaded.

**Wydanie 2026.10.25. Sprawdzone na jednym zestawie: Chromecast z Google TV HD,
Android 14, Kodi 21.3 ARMv7, AZR 3.0.3, Orange Start TV. Drugi egzemplarz:
nie sprawdzony.** Publiczne przepakowanie i nowe menu instalacyjne sprawdzono
na komputerze; nie wykonano nowej instalacji tych paczek na odbiorniku.

Działają wybór kanałów, lista i grupy, pomoc pilota, pasek z informacjami,
opisy programu, eksport M3U/EPG oraz kafel Android „Nasz TV”. Reconnect
uruchamia się na sprawdzonym zestawie, ale skuteczność odzyskania po
naturalnym błędzie 419 pozostaje niepotwierdzona. Ulubione i głos są
**eksperymentalne**; głos bez własnej kwalifikacji urządzenia nie przełącza kanałów.

Zacznij od [instrukcji krok po kroku](HUMAN.md). Pobierz ZIP-y i APK z
[Releases](https://github.com/fiedoruk/404-tf-nasz-tv/releases) i sprawdź
`SHA256SUMS`. W [COMPATIBILITY.md](COMPATIBILITY.md) opisujemy moduły,
a w [BLOCKERS.md](BLOCKERS.md) ograniczenia. Agent AI powinien przeczytać
[AGENT.md](AGENT.md). Źródła są w `src/`, receptura w [BUILD.md](BUILD.md).

Nie obiecujemy uniwersalnego instalatora, niezawodnego głosu, rozwiązania
uśpienia ani działania na Kodi 22. Wydanie nie zawiera abonamentu, kanałów,
ramówki, danych logowania, Kodi, pełnej skórki ani ich bibliotek.
To niezależny projekt, bez afiliacji z Orange, Google ani Kodi.

Własny kod: MIT. Własne dokumenty i grafiki: CC BY 4.0. OrangeGo: GPL-2.0.
Adaptacje AZR: CC BY-NC-SA 3.0, z ograniczeniem użycia komercyjnego.
Dokładne zakresy: [LICENSE](LICENSE), [NOTICE.md](NOTICE.md) i
[ATTRIBUTION.md](ATTRIBUTION.md).
