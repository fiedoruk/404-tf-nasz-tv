# Patche

Bazowy OrangeGo pobierz samodzielnie z adresu i SHA w `patch-index.json`.
Wydany `plugin.video.orange_go-1.0.15-nasz-tv.zip` ma już wszystkie zmiany;
poniższa procedura jest alternatywą dla budujących własną pochodną.

Rozpakuj bazę do osobnego katalogu. Przed zastosowaniem patchy zamień CRLF
na LF wyłącznie w plikach tekstowych wymienionych w `patch-index.json` oraz
`plugin.video.orange_go/resources/settings.xml`. Zachowaj niezmienioną kopię
bazy. W katalogu zawierającym `plugin.video.orange_go/` uruchom:

```sh
patch -p1 < /sciezka/do/nasz-tv/patches/orange/orange-1.0.5-to-1.0.15.patch
patch -p1 < /sciezka/do/nasz-tv/patches/orange/orange-1.0.15-zero-news.patch
patch -p1 < /sciezka/do/nasz-tv/patches/orange/orange-public-packaging.patch
```

Z powstałego drzewa usuń dokładnie `icon.png`, `resources/img/fanart.jpg`
i `resources/img/empty.png` wewnątrz dodatku. Dodaj tekst GPL-2.0 i notę
autorstwa z `src/kodi/plugin.video.orange_go`. Nie dołączaj pobranych bibliotek.
Własne ZIP-y najprościej odtworzysz z gotowych pełnych źródeł przez `tools/build.py`.
Cofnięcie patchy tekstowych: `patch -R -p1` w odwrotnej kolejności, na kopii
bez późniejszych zmian. Oryginalne grafiki odtwarza się wyłącznie z własnej bazy.

Orange: autor lg, dystrybucja mtr81/kodi_addons, pin
`5c7d7e1ebf78eea8e24ecdce74b5e6c80ed169ad`; nasze zmiany: Tomasz Fiedoruk, 2026.
Licencja wszystkich trzech diffów: GPL-2.0. Pełny tekst w katalogu `orange/`.

Patch AZR jest w osobnym katalogu `azr/` na CC BY-NC-SA 3.0.
Normalny instalator GUI nakłada równoważną zmianę samodzielnie i tworzy kopię.
Nie nakładaj obu sposobów na ten sam plik. Ręcznie, w katalogu czystej skórki
AZR 3.0.3, można użyć `patch -p1 < .../azr-3.0.3-dialogseekbar.patch`;
cofnięcie przez `patch -R -p1` przy niezmienionym wyniku.
Wejście i wynik mają SHA podane w `patch-index.json`.
