# Nasz TV

Nasz TV makes live TV on Android TV easier to navigate with a remote.
It provides channel navigation, readable programme information, a help
screen and an Android launcher tile.

You need your own working Orange subscription. You also need to obtain
Kodi and Arctic: Zephyr Reloaded separately.

## What has been tested

Release **2026.10.25** is based on one tested setup: Chromecast with
Google TV HD, Android 14, Kodi 21.3 ARMv7, AZR 3.0.3 and Orange Start TV.
**A second device has not been tested.**

The packaging for this public release and the new setup menus have been
checked only on a computer. These exact packages have not been reinstalled
on a device.

## Limitations

Favourites and voice control are experimental. The favourites feature
writes to the Kodi database, so back up your profile before using it.

Voice channel control stays disabled unless the device has been
individually qualified. This release does not include that device-specific
qualification.

Recovery after a natural HTTP 419 error, suspend behaviour and Kodi 22
support remain unresolved.

## Getting started

Start with the [step-by-step guide](HUMAN.md), currently in Polish.
Download the individual ZIP/APK files and `SHA256SUMS` from
[Releases](https://github.com/fiedoruk/404-tf-nasz-tv/releases).

For rebuilding instructions, see [BUILD.md](BUILD.md).
AI agents must follow [AGENT.md](AGENT.md).

## What is included and licensing

This release does not supply a subscription, account data, programme
listings, station logos or bundled third-party dependencies.

This is an independent project and is not endorsed by Orange, Google
or Kodi.

- Original code: MIT.
- Original documentation and artwork: CC BY 4.0.
- OrangeGo derivative: GPL-2.0.
- AZR adaptations: CC BY-NC-SA 3.0.

See [LICENSE](LICENSE) for details.
