# Nasz TV — telewizja mojego taty

[English](README.en.md)

Mój tata ma 72 lata i ogląda telewizję na starym LG z Chromecastem HD: strzałkami zmienia kanały, pod OK ma osiem ulubionych.
Nasz TV to dodatki i ustawienia Kodi, które przygotowałem dla niego.

Masz podobny zestaw? Zacznij od [instrukcji instalacji](HUMAN.md). To wydanie robocze; publicznych paczek nie instalowałem jeszcze na odbiorniku.

[![Ekran pomocy Nasz TV z rysunkiem pilota i opisami przycisków](media/remote-help.png)](media/remote-help.png)

Telewizor był sprawny. W aplikacji Orange nie mogliśmy jednak uruchomić
opłaconego Start TV, a oglądanie wymagało za dużo cierpliwości.
Przez kilka dni z pomocą AI dopasowywałem ten zestaw do taty.

Teraz tata ogląda.

## Na ekranie

To prawdziwe zrzuty z domowego zestawu.

[![Jasna lista kanałów informacyjnych w Kodi](media/channels-light.jpg)](media/channels-light.jpg)

Lista kanałów informacyjnych z tytułami programów i godzinami ich zakończenia.

[![Pasek z bieżącym i następnym programem](media/hud-banner.png)](media/hud-banner.png)

Co leci teraz i co będzie dalej. W tej próbie Wstecz schował pasek bez zmiany kanału.
Czarny obszar transmisji wynika z ochrony obrazu w zrzucie.

## Co tata ma pod ręką

- Telewizja startuje na ostatnio oglądanym kanale.
- Góra i dół zmieniają kanały. Pod OK czeka osiem ulubionych.
- Pasek pokazuje, co leci teraz i co będzie dalej.
- Strzałka w lewo otwiera pomoc z rysunkiem pilota.
- Kafel „Nasz TV” na ekranie Androida otwiera Kodi.

**Edycja ulubionych i sterowanie głosem są eksperymentalne.** Edytor zapisuje zmiany listy,
ale tata sam jeszcze go nie używał. Przed próbą zrób kopię profilu Kodi.
Wybieranie kanału głosem po polsku już działało, choć jeszcze nie za każdym razem.
Na nowym urządzeniu samo zainstalowanie aplikacji głosowej nie wystarczy
do przełączania kanałów. Na co dzień podstawą pozostaje pilot.

## Dla kogo

Dla kogoś, kto chce przygotować sobie lub bliskiej osobie prostszą telewizję
i jest gotów samodzielnie zainstalować oraz skonfigurować kilka dodatków.

Potrzebujesz własnego abonamentu Orange z telewizją. Projekt sprawdziłem na Chromecaście
z Google TV HD z Androidem 14; innych urządzeń jeszcze nie testowałem.
Kodi 21 i skórkę Arctic: Zephyr Reloaded instalujesz osobno;
instrukcja wskazuje wersje 21.3 i 3.0.3 oraz potrzebne dodatki.

W paczkach nie ma abonamentu, kanałów, ramówki ani danych logowania.
Nie dołączam Kodi, pełnej skórki, bibliotek, fontów, logotypów stacji ani plików DRM.
Orange oglądamy przez nieoficjalny dodatek OrangeGo, z własnego opłaconego abonamentu.
Do oglądania nie potrzeba komputera.

## Stan wydania

> Wydanie robocze 2026.10.25. Opisane funkcje działają na jednym domowym zestawie:
> Chromecast z Google TV HD, Android 14, Kodi 21.3,
> Arctic: Zephyr Reloaded 3.0.3 i Orange Start TV.
> Publiczne paczki sprawdziłem tylko na komputerze. Nie zainstalowałem ich jeszcze
> na odbiorniku ani na drugim egzemplarzu.

Masz podobny zestaw? [Daj znać w Issues, jak poszło](https://github.com/fiedoruk/404-tf-nasz-tv/issues).
Podaj model i wersje oprogramowania, bez danych logowania.

## Jak zacząć

1. Przeczytaj [instrukcję krok po kroku](HUMAN.md). Zacznij od kopii własnego profilu Kodi.
2. Pobierz paczki z [Releases](https://github.com/fiedoruk/404-tf-nasz-tv/releases/tag/v2026.10.25)
   i sprawdź je z [SHA256SUMS](https://github.com/fiedoruk/404-tf-nasz-tv/releases/download/v2026.10.25/SHA256SUMS).
3. Przed instalacją porównaj swój zestaw z [tabelą zgodności](COMPATIBILITY.md)
   i przeczytaj [otwarte sprawy](BLOCKERS.md). Potem idź według instrukcji.

**Dla agentów AI:** zacznij od [AGENT.md](AGENT.md), zanim pomożesz przy instalacji.

**Dla twórców:** kod znajdziesz w [src/](src/), a sposób budowania paczek w [BUILD.md](BUILD.md).

## Historia i pilot

[Całą historię opisałem na 404.tf](https://404.tf/nasz-tv.html).
Są tam prawdziwe ekrany i demo pilota, które możesz wypróbować w przeglądarce.
Demo używa przykładowej ramówki, bez transmisji telewizyjnej.

## Licencje

Własny kod: MIT. Własne dokumenty i grafiki: CC BY 4.0.  
OrangeGo: GPL-2.0. Adaptacje Arctic: Zephyr Reloaded: CC BY-NC-SA 3.0, bez użytku komercyjnego.  
Zakres i autorzy: [LICENSE](LICENSE), [NOTICE.md](NOTICE.md), [ATTRIBUTION.md](ATTRIBUTION.md).  
Projekt niezależny, bez afiliacji z Orange, Google ani Kodi.

Autor: Tomasz Fiedoruk, [404.tf](https://404.tf/).
