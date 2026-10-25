# OrangeGo — zastosowanie patchy

Baza 1.0.5:
https://raw.githubusercontent.com/mtr81/kodi_addons/5c7d7e1ebf78eea8e24ecdce74b5e6c80ed169ad/addons/plugin.video.orange_go/plugin.video.orange_go-1.0.5.zip

SHA256 bazowego ZIP-u:
`30da60b049dd647675a66ab5e0a7b4dd41de2360c9a2450f6d9ee33f60d7380f`.
Zachowaj niezmienioną kopię. Rozpakuj bazę, zamień CRLF na LF w addon.py,
addon.xml i resources/settings.xml. W katalogu zawierającym
`plugin.video.orange_go/` zastosuj przez `patch -p1 -i PLIK` kolejno:

1. `orange-1.0.5-to-1.0.15.patch`
2. `orange-1.0.15-zero-news.patch`
3. `orange-public-packaging.patch`

Następnie usuń z dodatku `icon.png`, `resources/img/fanart.jpg` oraz
`resources/img/empty.png`. Skopiuj LICENSE.txt i NOTICE.md do dodatku.
Nie dołączaj zewnętrznych bibliotek ani profilu użytkownika.
Cofnięcie tekstu: te same patche z `patch -R -p1 -i PLIK`, w odwrotnej
kolejności i przy braku późniejszych zmian. Grafiki przywraca własna kopia bazy.

Gotowy ZIP i pełne źródła pochodnej:
https://github.com/fiedoruk/404-tf-nasz-tv/releases
Licencja patchy: GPL-2.0; autorzy i opis zmian w NOTICE.md.
