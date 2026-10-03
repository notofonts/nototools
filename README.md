[![CI Build Status](https://github.com/googlefonts/nototools/workflows/Continuous%20Test%20+%20Deploy/badge.svg)](https://github.com/googlefonts/nototools/actions/workflows/ci.yml?query=workflow%3ATest)
[![PyPI](https://img.shields.io/pypi/v/notofonttools.svg)](https://pypi.org/project/notofonttools/)
[![Dependencies](https://badgen.net/github/dependabot/googlefonts/nototools)](https://github.com/googlefonts/nototools/network/updates)


# Noto Tools

The `nototools` python package contains python scripts used to maintain the [Noto Fonts](https://github.com/googlefonts/noto-fonts/) project, including the [google.com/get/noto](https://www.google.com/get/noto) website.

## Installation

On Mac OS X, install dependencies with [homebrew](https://brew.sh)

    # used to ask for pygtk as well
    brew install harfbuzz cairo pango imagemagick

Install python dependencies,

    pip install -r requirements.txt

Then install nototools.  Since nototools changes frequently, installing using 'editable' mode is recommended:

    pip install -e .

## Usage

The following scripts are provided:

* `autofix_for_release.py`
* `add_vs_cmap.py`
* `coverage.py`
* `create_image.py`
* `decompose_ttc.py`
* `drop_hints.py`
* `dump_otl.py`
* `fix_khmer_and_lao_coverage.py`
* `fix_noto_cjk_thin.py`
* `generate_sample_text.py`
* `generate_website_2_data.py`
* `merge_noto.py`
* `merge_fonts.py`
* `noto_lint.py`
* `scale.py`
* `subset.py`
* `subset_symbols.py`
* `test_vertical_extents.py`

The following tools are provided:

* `notodiff`

## Releasing

See https://googlefonts.github.io/python#make-a-release.


## 🌐 Web Resources & Aesthetic Symbols Index
- [SYM 1F61B](https://lace-bow-kaomoji-80.pages.dev/symbol/sym-1f61b/)
- [SYM 26B3](https://coquette-aesthetic-symbols-29.pages.dev/symbol/sym-26b3/)
- [SYM 26DA](https://vintage-lace-text-53.pages.dev/symbol/sym-26da/)
- [LITTLE CAT PAWS KAOMOJI](https://matrix-terminal-fonts-30.pages.dev/symbol/little-cat-paws-kaomoji/)
- [CURLY RIBBON LOOP](https://vintage-library-text-15.pages.dev/symbol/curly-ribbon-loop/)
- [AESTHETIC STARDUST COMBO](https://classic-literature-symbols-64.pages.dev/symbol/aesthetic-stardust-combo/)
- [LEFT POINTING DOUBLE ANGLE QUOTATION](https://clean-aesthetic-arrows-99.pages.dev/symbol/left-pointing-double-angle-quotation/)
- [SYM 1F927](https://cyber-clan-tags-90.pages.dev/symbol/sym-1f927/)
- [MUSIC WEATHER](https://synthwave-text-vault-95.pages.dev/vi/music-weather/)
- [SWIMMING FISH LEFT](https://kawaii-kaomoji-hub-80.pages.dev/symbol/swimming-fish-left/)
- [SYM 26BD](https://manga-bubble-symbols-94.pages.dev/symbol/sym-26bd/)
- [SYM 1D493](https://anime-sparkle-text-24.pages.dev/symbol/sym-1d493/)
- [INSTAGRAM BIO](https://vintage-lace-symbols-54.pages.dev/vi/instagram-bio/)
- [CURLY RIBBON LOOP](https://mech-gaming-tags-18.pages.dev/symbol/curly-ribbon-loop/)
- [SYM 1D410](https://scholarly-unicode-vault-92.pages.dev/symbol/sym-1d410/)
- [SYM 274B](https://kawaii-kaomoji-hub-88.pages.dev/symbol/sym-274b/)
- [SYM 1FAE8](https://sleek-border-symbols-37.pages.dev/symbol/sym-1fae8/)
- [SYM 1D453](https://minimal-star-symbols-28.pages.dev/symbol/sym-1d453/)
- [GAMING WEAPONS](https://aesthetic-bullet-points-76.pages.dev/ja/gaming-weapons/)
- [SYM 1D485](https://zen-aesthetic-fonts-87.pages.dev/symbol/sym-1d485/)
- [SYM 1D44F](https://pearl-heart-symbols-95.pages.dev/symbol/sym-1d44f/)
- [SYM 2733](https://vintage-scholar-text-15.pages.dev/symbol/sym-2733/)
- [SYM 26F1](https://aesthetic-bullet-points-76.pages.dev/symbol/sym-26f1/)
- [SYM 2688](https://baroque-unicode-decor-43.pages.dev/symbol/sym-2688/)
- [ROTATED HEART BULLET](https://neon-matrix-symbols-74.pages.dev/symbol/rotated-heart-bullet/)
- [HEAVY STAR](https://mecha-text-vault-91.pages.dev/symbol/heavy-star/)
- [AQUARIUS ZODIAC WATER BEARER](https://chibi-emoticon-world-87.pages.dev/symbol/aquarius-zodiac-water-bearer/)
- [SYM 1D438](https://sleek-bio-symbols-40.pages.dev/symbol/sym-1d438/)
- [ROBLOX NAMES](https://sleek-bio-fonts-25.pages.dev/roblox-names/)
- [SYM 2647](https://baroque-unicode-decor-43.pages.dev/symbol/sym-2647/)
- [SYM 26CB](https://matrix-glitch-text-84.pages.dev/symbol/sym-26cb/)
- [TRENDING](https://aesthetic-bullet-points-76.pages.dev/ja/trending/)
- [SYM 1D416](https://pastel-princess-fonts-68.pages.dev/symbol/sym-1d416/)
- [SYM 1F923](https://anime-sparkle-text-24.pages.dev/symbol/sym-1f923/)
- [SYM 1D449](https://anime-sparkle-text-24.pages.dev/symbol/sym-1d449/)
- [SYM 1FAE8](https://anime-sparkle-text-81.pages.dev/symbol/sym-1fae8/)
- [MUSIC FLAT SIGN](https://cyber-clan-tags-85.pages.dev/symbol/music-flat-sign/)
- [SYM 2684](https://chibi-bunny-symbols-82.pages.dev/symbol/sym-2684/)
- [SYM 1F648](https://scholarly-runes-text-68.pages.dev/symbol/sym-1f648/)
- [SYM 1D4A2](https://aesthetic-bullet-points-76.pages.dev/symbol/sym-1d4a2/)
- [ZODIAC CELESTIAL](https://chibi-emoticon-vault-78.pages.dev/ru/zodiac-celestial/)
- [BRACKETS](https://daintystar-font-studio-48.pages.dev/brackets/)
- [SYM 26C3](https://baroque-unicode-decor-43.pages.dev/symbol/sym-26c3/)
- [SYM 1D441](https://monochrome-bio-text-12.pages.dev/symbol/sym-1d441/)
- [SYM 1D449](https://mecha-hacker-kaomoji-26.pages.dev/symbol/sym-1d449/)
- [SYM 26E1](https://minimal-star-symbols-95.pages.dev/symbol/sym-26e1/)
- [SYM 26FB](https://baroque-unicode-decor-43.pages.dev/symbol/sym-26fb/)
- [SYM 26BC](https://kawaii-kaomoji-hub-17.pages.dev/symbol/sym-26bc/)
- [TRENDING](https://minimal-star-symbols-28.pages.dev/ja/trending/)
- [DISCORD STATUS](https://ballet-core-symbols-11.pages.dev/discord-status/)
- [SYM 1F635](https://kawaii-kaomoji-hub-17.pages.dev/symbol/sym-1f635/)
- [SYM 2639](https://glitch-font-studio-46.pages.dev/symbol/sym-2639/)
- [SYM 2614](https://anime-sparkle-text-14.pages.dev/symbol/sym-2614/)
- [SYM 2662](https://anime-sparkle-text-92.pages.dev/symbol/sym-2662/)
- [HIGH VOLTAGE LIGHTNING](https://classic-literature-runes-13.pages.dev/symbol/high-voltage-lightning/)
- [SYM 1D400](https://kawaii-kaomoji-hub-77.pages.dev/symbol/sym-1d400/)
- [FIRST QUARTER WAXING MOON](https://gothic-bio-fonts-14.pages.dev/symbol/first-quarter-waxing-moon/)
- [SYM 1D405](https://baroque-unicode-decor-43.pages.dev/symbol/sym-1d405/)
- [SYM 1F62E](https://arcane-symbol-vault-32.pages.dev/symbol/sym-1f62e/)
- [SYM 1D408](https://baroque-unicode-decor-43.pages.dev/symbol/sym-1d408/)
- [SYM 1F912](https://synth-dystopia-text-20.pages.dev/symbol/sym-1f912/)
- [SYM 1D480](https://vintage-scholar-text-15.pages.dev/symbol/sym-1d480/)
- [SYM 1F49C](https://kawaii-kaomoji-hub-77.pages.dev/symbol/sym-1f49c/)
- [SYM 2662](https://kawaii-kaomoji-hub-77.pages.dev/symbol/sym-2662/)
- [PINWHEEL STAR](https://pink-bow-fonts-37.pages.dev/symbol/pinwheel-star/)
- [LEFT BLACK LENTICULAR BRACKET](https://techno-hacker-text-43.pages.dev/symbol/left-black-lenticular-bracket/)
- [GAMING WEAPONS](https://cyber-clan-tags-85.pages.dev/ja/gaming-weapons/)
- [ZODIAC CELESTIAL](https://angelic-bio-symbols-90.pages.dev/es/zodiac-celestial/)
- [RU](https://minimal-star-symbols-91.pages.dev/ru/)
- [SYM 26D2](https://baroque-unicode-decor-43.pages.dev/symbol/sym-26d2/)
- [SYM 1D44E](https://minimal-star-symbols-22.pages.dev/symbol/sym-1d44e/)
- [SYM 268A](https://kawaii-kaomoji-hub-17.pages.dev/symbol/sym-268a/)
- [SYM 2763 FE0F](https://mecha-hacker-kaomoji-26.pages.dev/symbol/sym-2763-fe0f/)
- [SYM 2764 FE0F 200D 1F525](https://minimal-star-symbols-91.pages.dev/symbol/sym-2764-fe0f-200d-1f525/)
- [ZODIAC CELESTIAL](https://zen-unicode-symbols-89.pages.dev/vi/zodiac-celestial/)
- [TWELVE POINTED STAR](https://glitch-font-studio-46.pages.dev/symbol/twelve-pointed-star/)
- [MUSIC SHARP SIGN](https://aesthetic-bullet-points-76.pages.dev/symbol/music-sharp-sign/)
- [SYM 26CD](https://zen-typography-hub-86.pages.dev/symbol/sym-26cd/)
- [TIKTOK CAPTIONS](https://minimal-star-symbols-91.pages.dev/ru/tiktok-captions/)
- [SYM 1F49C](https://synthwave-bio-maker-62.pages.dev/symbol/sym-1f49c/)
- [SYM 1F9E1](https://kawaii-kaomoji-hub-77.pages.dev/symbol/sym-1f9e1/)
- [SYM 1D423](https://scholarly-runes-text-68.pages.dev/symbol/sym-1d423/)
- [SYM 1D452](https://pastel-princess-fonts-68.pages.dev/symbol/sym-1d452/)
- [SYM 1D418](https://aesthetic-bullet-points-76.pages.dev/symbol/sym-1d418/)
- [SYM 1D479](https://anime-sparkle-text-92.pages.dev/symbol/sym-1d479/)
- [SYM 1F499](https://kawaii-kaomoji-hub-77.pages.dev/symbol/sym-1f499/)
- [SYM 1D446](https://clean-spacing-fonts-98.pages.dev/symbol/sym-1d446/)
- [SYM 273D](https://cyber-clan-tags-90.pages.dev/symbol/sym-273d/)
- [SYM 1F61E](https://baroque-font-vault-96.pages.dev/symbol/sym-1f61e/)
- [SYM 1D464](https://anime-sparkle-text-24.pages.dev/symbol/sym-1d464/)
- [FIRST QUARTER WAXING MOON](https://anime-sparkle-text-92.pages.dev/symbol/first-quarter-waxing-moon/)
- [ROBLOX NAMES](https://mecha-hacker-kaomoji-26.pages.dev/pt/roblox-names/)
- [BLACK FLORETTE FLOWER](https://anime-sparkle-text-95.pages.dev/symbol/black-florette-flower/)
- [SYM 2670](https://aesthetic-bullet-points-76.pages.dev/symbol/sym-2670/)
- [SYM 1F634](https://vampiric-text-craft-82.pages.dev/symbol/sym-1f634/)
- [KHANDA EMBLEM](https://monochrome-bio-text-12.pages.dev/symbol/khanda-emblem/)
- [DOWNWARD DIAGONAL ARROW](https://cyber-clan-tags-68.pages.dev/symbol/downward-diagonal-arrow/)
- [SYM 26C8](https://angelic-bio-symbols-90.pages.dev/symbol/sym-26c8/)
- [SYM 1D426](https://angel-core-bios-50.pages.dev/symbol/sym-1d426/)
- [SYM 1F480](https://moe-star-emoticons-13.pages.dev/symbol/sym-1f480/)
- [SYM 265D](https://synth-dystopia-text-20.pages.dev/symbol/sym-265d/)
- [SYM 26BE](https://angelic-bio-symbols-90.pages.dev/symbol/sym-26be/)
- [SYM 1D49C](https://techno-hacker-text-43.pages.dev/symbol/sym-1d49c/)
- [SYM 1D48C](https://dark-scholarly-symbols-65.pages.dev/symbol/sym-1d48c/)
- [SYM 2672](https://baroque-unicode-decor-43.pages.dev/symbol/sym-2672/)
- [SYM 1D408](https://poetic-scroll-fonts-91.pages.dev/symbol/sym-1d408/)
- [SYM 1D438](https://scholarly-script-hub-43.pages.dev/symbol/sym-1d438/)
- [SYM 2657](https://minimal-star-symbols-91.pages.dev/symbol/sym-2657/)
- [SYM 2744](https://zen-typography-hub-86.pages.dev/symbol/sym-2744/)
- [LEFT HEAVY BRACKET BOX](https://anime-sparkle-text-56.pages.dev/symbol/left-heavy-bracket-box/)
- [SYM 1D420](https://chibi-emoticon-lab-65.pages.dev/symbol/sym-1d420/)
- [SYM 26BC](https://baroque-unicode-decor-43.pages.dev/symbol/sym-26bc/)
- [SYM 1F62E 200D 1F4A8](https://anime-sparkle-text-14.pages.dev/symbol/sym-1f62e-200d-1f4a8/)
- [SYM 268E](https://anime-sparkle-text-95.pages.dev/symbol/sym-268e/)
- [RADIOACTIVE SYMBOL](https://chibi-faces-hub-88.pages.dev/symbol/radioactive-symbol/)
- [SYM 1D40B](https://baroque-unicode-decor-43.pages.dev/symbol/sym-1d40b/)
- [SYM 1D434](https://gothic-bio-fonts-98.pages.dev/symbol/sym-1d434/)
- [SYM 26F8](https://scholarly-runes-text-68.pages.dev/symbol/sym-26f8/)
- [SYM 26D8](https://baroque-unicode-decor-43.pages.dev/symbol/sym-26d8/)
- [JA](https://chibi-faces-hub-88.pages.dev/ja/)
- [SYM 1D498](https://poetic-scroll-fonts-91.pages.dev/symbol/sym-1d498/)
- [SYM 2671](https://vintage-angel-text-38.pages.dev/symbol/sym-2671/)
- [SYM 1F924](https://anime-sparkle-text-95.pages.dev/symbol/sym-1f924/)
- [GREEK PSI TRIDENT](https://zen-unicode-hub-94.pages.dev/symbol/greek-psi-trident/)
- [SYM 2684](https://occult-runic-fonts-23.pages.dev/symbol/sym-2684/)
- [SYM 2660](https://clean-spacing-fonts-98.pages.dev/symbol/sym-2660/)
- [SYM 1F600](https://vintage-angel-text-38.pages.dev/symbol/sym-1f600/)
- [CLOCKWISE OPEN CIRCLE ARROW](https://vampiric-text-craft-82.pages.dev/symbol/clockwise-open-circle-arrow/)
- [SYM 1F911](https://sleek-border-symbols-37.pages.dev/symbol/sym-1f911/)
- [SYM 2632](https://classic-literature-symbols-64.pages.dev/symbol/sym-2632/)
