# Odtworzenie paczek

Kod narzędzi: MIT, Copyright (c) 2026 Tomasz Fiedoruk.

ZIP-y dodatków, źródła, integracja AZR i sumy powstają jednym poleceniem:

```sh
python3 -B tools/build.py --out ../release
```

Wymagany Python 3.8 lub nowszy. Builder korzysta wyłącznie z jawnej listy
`build-manifest.json`. Ustala kolejność, datę, prawa plików i format ZIP bez
kompresji, dzięki czemu wynik nie zależy od wersji biblioteki kompresji.
APK są kopiowane z `packages/`; ich osobna kompilacja jest opisana poniżej.

## Android

Potrzebne: JDK 17, Android SDK API 35 (`android.jar`), Build Tools 35.0.0
z `aapt2`, `zipalign`, `apksigner` i D8. Pobierz narzędzia z
[Android SDK](https://developer.android.com/tools) i [OpenJDK](https://jdk.java.net/).
Nie są dołączone do wydania. D8 można wskazać osobno przez `--d8-jar`;
szczegóły narzędzi użytych dla wydanych APK są w `android-build.json`.

W poniższych poleceniach ustaw `ANDROID_SDK_ROOT` i `JAVA_HOME` na własne
instalacje. Żadne polecenie nie łączy się z telewizorem.

```sh
python3 -B tools/build_android.py tv-shortcut \
  --android-jar "$ANDROID_SDK_ROOT/platforms/android-35/android.jar" \
  --build-tools "$ANDROID_SDK_ROOT/build-tools/35.0.0" \
  --java-home "$JAVA_HOME" --out ../shortcut-unsigned.apk
python3 -B tools/build_android.py voice \
  --android-jar "$ANDROID_SDK_ROOT/platforms/android-35/android.jar" \
  --build-tools "$ANDROID_SDK_ROOT/build-tools/35.0.0" \
  --java-home "$JAVA_HOME" --out ../voice-unsigned.apk
```

Wynik wymaga podpisania własnym keystore przez `apksigner sign --ks`;
narzędzie może zapytać interaktywnie o dane dostępu. Keystore przechowuj
poza repozytorium. Publiczne APK są podpisane istniejącą tożsamością autora,
bez dołączania materiału podpisu. Nowy podpis wymaga odinstalowania aplikacji
autora przed instalacją własnego wariantu; najpierw zachowaj ustawienia.
Nie obiecujemy identyczności całego podpisanego APK po własnej kompilacji.

Grafiki są gotowymi własnymi bitmapami w źródłach, na CC BY 4.0.
Do odtworzenia ZIP/APK nie trzeba generować ich ponownie ani instalować fontów.
