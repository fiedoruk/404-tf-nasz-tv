# AZR 3.0.3 — pasek podczas PVR

Ten patch jest opcją ręczną. Instalator Nasz TV GUI sam wykonuje tę zmianę;
nie stosuj obu metod na tym samym pliku.

Baza:
https://raw.githubusercontent.com/beatmasterRS/skin.arctic.zephyr.mod/28247cbd44417bbfc3bb63d6686f140df10e8748/1080i/DialogSeekBar.xml

SHA256 wejścia: `ae88943851c92b74bd1368091c15e636477e15eb75a2ab21116980b9859889b2`.
SHA256 wyniku: `e7cf8b1e1a2d813336781fb646f812d5dc10c3f509da119a6b8916f5fd299890`.

Zachowaj kopię pliku. W katalogu skórki zawierającym `1080i/` uruchom
`patch -p1 -i /sciezka/do/azr-3.0.3-dialogseekbar.patch`, a potem przeładuj
skórkę w Kodi. Cofnięcie na niezmienionym wyniku:
`patch -R -p1 -i /sciezka/do/azr-3.0.3-dialogseekbar.patch`.
Jeśli hash się nie zgadza, zatrzymaj operację; nie używaj wymuszenia.

CC BY-NC-SA 3.0; autorzy, źródło i opis zmian w NOTICE.md.
