# Support panel profile images

The profile images below were supplied for the support panel. They are bundled
locally so opening the app does not request profile images from Discord.

- `awesomenull.webp`: https://cdn.discordapp.com/avatars/1466490539892412478/717336c0509b2a3ebb4956c61cacc3f5.webp?size=1024
- `windows11aero.webp`: https://cdn.discordapp.com/avatars/1469246021413507074/1dab1cb4a9d66dcec262391654fc53f2.webp?size=1024
- `kik4311.png`: https://avatars.githubusercontent.com/u/310088924?s=460 (GitHub avatar)
- `LeminLimez.png`: existing GoldenNugget credit artwork, retained for Nugget's creator.

Retrieved October 15, 2026. Profile artwork remains attributable to its original owners.

`awesomenull.png` and `windows11aero.png` are PNG conversions of the original
WebP files above, with the same decoded pixels. The UI uses PNG so packaged
builds do not need the optional Qt WebP decoder for profile images. Rebuild Qt
resources with `pyside6-rcc --compress-algo zlib src/qt/resources.qrc -o
src/qt/resources_rc.py`; Zstd resources fail on Qt builds without Zstd support.
