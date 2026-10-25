# Noty i zakres dystrybucji

Własny wkład: Copyright (c) 2026 Tomasz Fiedoruk. Kod MIT; własne teksty
i grafiki CC BY 4.0. Zobacz [LICENSE](LICENSE).

## OrangeGo

Autor `lg`, repozytorium dystrybucyjne
[mtr81/kodi_addons](https://github.com/mtr81/kodi_addons), commit
`5c7d7e1ebf78eea8e24ecdce74b5e6c80ed169ad`, wersja bazowa 1.0.5.
W `addon.xml` zadeklarowano „GNU GENERAL PUBLIC LICENSE. Version 2, June 1991”.
W sprawdzonej bazowej paczce nie było pliku LICENSE ani klauzuli określającej
prawo wyboru późniejszych wersji. Dystrybuujemy pochodną jako GPL-2.0,
z pełnym tekstem tej licencji, zachowując autora i oznaczając nasze zmiany.

Zmiany 2026: metadane i opisy, eksport M3U/XMLTV, most GUI, obsługa PVR,
grupa informacyjna z Kanałem Zero. Przygotowanie wydania 25.10.2026 usuwa
grafiki upstream, wybiera domyślną ikonę Kodi i aktualizuje opis/licencję.
Pełne odpowiadające źródła są w `src/kodi/plugin.video.orange_go`, a także
wewnątrz instalacyjnego ZIP-u. Nie dołączamy bazowego ZIP-u 1.0.5 ani
`script.module.*`. Ich manifesty i biblioteki pozostają odrębnymi składnikami.
Nie deklarujemy rozstrzygnięcia zgodności wszystkich zależności GPL/Apache.

## Arctic: Zephyr Reloaded

Autorzy: jurialmunkey i beatmasterRS. Źródło:
[skin.arctic.zephyr.mod](https://github.com/beatmasterRS/skin.arctic.zephyr.mod),
commit `28247cbd44417bbfc3bb63d6686f140df10e8748`, wersja 3.0.3.
Identyfikację CC BY-NC-SA 3.0 opieramy na LICENSE.txt w tym pinie;
skrót w addon.xml/README jest mniej precyzyjny.
Dołączony tekst CC BY-NC-SA 3.0 jest transkrypcją standardowego legalcode,
z odsyłaczem do tekstu właściwego. Nie jest bajtową kopią LICENSE.txt skórki.

Rozpowszechniane adaptacje: ukrycie DialogSeekBar podczas telewizji PVR
oraz zmiana dwóch okien dla lokalnej edycji Ulubionych. Zmiany: Tomasz
Fiedoruk, październik 2026. Zachowują CC BY-NC-SA 3.0. Nie dołączamy pełnej
skórki, jej tekstur, fontów, ikon ani zależności. Odwołania XML do zasobów
skórki korzystają z kopii skórki instalowanej samodzielnie przez odbiorcę.

## Własne grafiki i aplikacje

Bitmapy GUI i kafla powstały w projekcie z własnych prymitywów graficznych.
Zawierają wyrenderowane napisy, nie pliki ani osadzone kopie fontów.
Rysunek pilota jest własną ilustracją orientacyjną; nazwy przycisków i marek
identyfikują funkcje urządzenia i nie oznaczają poparcia właścicieli marek.
Nie dołączamy logotypów stacji ani obrazów z transmisji. Grafiki pobierane
przez działający dodatek pochodzą od operatora i nie stają się CC BY 4.0.

Źródła Androida używają API systemowych; narzędzia kompilacji nie są
dołączone do APK. Certyfikat publiczny podpisu jest częścią APK; materiał
prywatny potrzebny do podpisywania nie jest dystrybuowany. Głos pozostaje
debugowalnym eksperymentem i nie zawiera kwalifikacji odbiorcy.

## Składniki zewnętrzne

Kodi, pełna AZR, bazowy OrangeGo, InputStream, PVR, wszystkie biblioteki
`script.module.*`, Widevine, dane ramówki, logotypy i fonty nie są częścią
paczki. Źródła pobrania są w external-pins.json. Szczególna luka: przypięty
pyjsparser ma MIT w deklaracjach kodu oraz GPLv3 w dołączonym LICENSE.
Wydanie nie zmienia jego licencji i nie zawiera tej biblioteki.
