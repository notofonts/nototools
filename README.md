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
- [STARS](https://cute-face-emoticons-66.pages.dev/pt/stars/)
- [RU](https://sleek-bio-symbols-40.pages.dev/ru/)
- [DAGGER CROSS SYMBOL](https://futuristic-gaming-fonts-52.pages.dev/symbol/dagger-cross-symbol/)
- [SYM 2748](https://scholarly-cross-symbols-35.pages.dev/symbol/sym-2748/)
- [FREEFIRE NAMES](https://coquette-aesthetic-symbols-86.pages.dev/pt/freefire-names/)
- [SYM 1D407](https://vintage-library-rune-80.pages.dev/symbol/sym-1d407/)
- [SYM 2628](https://lace-heart-kaomoji-64.pages.dev/symbol/sym-2628/)
- [SYM 26B7](https://kawaii-kaomoji-hub-96.pages.dev/symbol/sym-26b7/)
- [SYM 1D431](https://scholarly-cross-symbols-35.pages.dev/symbol/sym-1d431/)
- [SYM 1FA77](https://theeduplaycampen.pages.dev/symbol/sym-1fa77/)
- [SYM 1F49D](https://lace-heart-kaomoji-64.pages.dev/symbol/sym-1f49d/)
- [STARRY LOVE AURA](https://coquette-symbols.pages.dev/symbol/starry-love-aura/)
- [SYM 1D490](https://theeduplaycampen.pages.dev/symbol/sym-1d490/)
- [SYM 1F624](https://coquette-symbols.pages.dev/symbol/sym-1f624/)
- [SYM 273C](https://coquette-aesthetic-symbols-86.pages.dev/symbol/sym-273c/)
- [OUTLINED STAR](https://nordic-minimal-fonts-67.pages.dev/symbol/outlined-star/)
- [SYM 1F970](https://theeduplaycampen.pages.dev/symbol/sym-1f970/)
- [SYM 1D434](https://theeduplaycampen.pages.dev/symbol/sym-1d434/)
- [TRENDING](https://coquette-aesthetic-symbols-86.pages.dev/es/trending/)
- [EIGHT POINTED BLACK STAR](https://minimal-star-symbols-93.pages.dev/symbol/eight-pointed-black-star/)
- [SYM 1D424](https://scholarly-cross-symbols-35.pages.dev/symbol/sym-1d424/)
- [SYM 268B](https://coquette-symbols.pages.dev/symbol/sym-268b/)
- [SYM 26EF](https://kawaii-kaomoji-hub-96.pages.dev/symbol/sym-26ef/)
- [SYM 1D404](https://sleek-line-symbols-51.pages.dev/symbol/sym-1d404/)
- [SYM 2660](https://vintage-library-rune-80.pages.dev/symbol/sym-2660/)
- [SYM 2733](https://scholarly-cross-symbols-35.pages.dev/symbol/sym-2733/)
- [SYM 1F625](https://lace-heart-kaomoji-64.pages.dev/symbol/sym-1f625/)
- [VIRGO ZODIAC MAIDEN](https://theeduplaycampen.pages.dev/symbol/virgo-zodiac-maiden/)
- [SYM 1D477](https://matrix-hacker-text-52.pages.dev/symbol/sym-1d477/)
- [SYM 1F63B](https://matrix-hacker-text-52.pages.dev/symbol/sym-1f63b/)
- [SYM 26DF](https://sleek-line-symbols-51.pages.dev/symbol/sym-26df/)
- [SYM 26F9](https://sleek-line-symbols-51.pages.dev/symbol/sym-26f9/)
- [LATIN CROSS HEAVY](https://matrix-hacker-text-52.pages.dev/symbol/latin-cross-heavy/)
- [SYM 274A](https://raven-gothic-kaomoji-25.pages.dev/symbol/sym-274a/)
- [SYM 2657](https://lace-heart-kaomoji-64.pages.dev/symbol/sym-2657/)
- [ARROWS LINES](https://matrix-hacker-text-52.pages.dev/pt/arrows-lines/)
- [SYM 2639](https://lace-heart-kaomoji-64.pages.dev/symbol/sym-2639/)
- [SYM 1F62F](https://matrix-hacker-text-52.pages.dev/symbol/sym-1f62f/)
- [SYM 265A](https://kawaii-kaomoji-hub-96.pages.dev/symbol/sym-265a/)
- [SYM 1F62B](https://vintage-library-rune-80.pages.dev/symbol/sym-1f62b/)
- [SYM 1F979](https://matrix-hacker-text-52.pages.dev/symbol/sym-1f979/)
- [SYM 1F916](https://lace-heart-kaomoji-64.pages.dev/symbol/sym-1f916/)
- [STARS](https://clean-dot-aesthetic-48.pages.dev/stars/)
- [SYM 1F47F](https://matrix-hacker-text-52.pages.dev/symbol/sym-1f47f/)
- [HEARTS](https://coquette-aesthetic-symbols-86.pages.dev/hearts/)
- [SYM 2728](https://lace-heart-kaomoji-64.pages.dev/symbol/sym-2728/)
- [SYM 2745](https://kawaii-kaomoji-hub-96.pages.dev/symbol/sym-2745/)
- [SYM 2764 FE0F 200D 1FA79](https://vintage-library-rune-80.pages.dev/symbol/sym-2764-fe0f-200d-1fa79/)
- [SYM 26CC](https://kawaii-kaomoji-hub-96.pages.dev/symbol/sym-26cc/)
- [SYM 2637](https://coquette-symbols.pages.dev/symbol/sym-2637/)
- [SYM 2624](https://vintage-library-rune-80.pages.dev/symbol/sym-2624/)
- [SYM 26D1](https://kawaii-kaomoji-hub-96.pages.dev/symbol/sym-26d1/)
- [SYM 1D484](https://lace-heart-kaomoji-64.pages.dev/symbol/sym-1d484/)
- [SYM 1F97A](https://matrix-hacker-text-52.pages.dev/symbol/sym-1f97a/)
- [STARS](https://matrix-hacker-text-52.pages.dev/ja/stars/)
- [SYM 1F4A9](https://scholarly-cross-symbols-35.pages.dev/symbol/sym-1f4a9/)
- [ZODIAC CELESTIAL](https://scholarly-cross-symbols-35.pages.dev/zodiac-celestial/)
- [SYM 1D45F](https://sleek-line-symbols-51.pages.dev/symbol/sym-1d45f/)
- [ARROWS LINES](https://raven-gothic-kaomoji-25.pages.dev/ru/arrows-lines/)
- [NATURE FLOWERS](https://matrix-hacker-text-52.pages.dev/pt/nature-flowers/)
- [SYM 1D458](https://angelic-bow-symbols-42.pages.dev/symbol/sym-1d458/)
- [WHITE FLORETTE BLOSSOM](https://theeduplaycampen.pages.dev/symbol/white-florette-blossom/)
- [SYM 1D470](https://sleek-line-symbols-51.pages.dev/symbol/sym-1d470/)
- [BLACK CENTRE STAR](https://gothic-bio-fonts-13.pages.dev/symbol/black-centre-star/)
- [SYM 1F49B](https://scholarly-cross-symbols-35.pages.dev/symbol/sym-1f49b/)
- [SYM 1F61F](https://matrix-hacker-text-52.pages.dev/symbol/sym-1f61f/)
- [STARS](https://kawaii-kaomoji-hub-96.pages.dev/stars/)
- [SYM 2646](https://kawaii-kaomoji-hub-96.pages.dev/symbol/sym-2646/)
- [NATURE FLOWERS](https://matrix-hacker-text-52.pages.dev/ja/nature-flowers/)
- [INSTAGRAM BIO](https://matrix-hacker-text-52.pages.dev/es/instagram-bio/)
- [TIKTOK CAPTIONS](https://clean-dot-aesthetic-48.pages.dev/tiktok-captions/)
- [KAOMOJI](https://matrix-hacker-text-52.pages.dev/ja/kaomoji/)
- [SYM 26F4](https://sleek-line-symbols-51.pages.dev/symbol/sym-26f4/)
- [HEARTS](https://matrix-hacker-text-52.pages.dev/ru/hearts/)
- [SYM 1D408](https://coquette-symbols.pages.dev/symbol/sym-1d408/)
- [SYM 1F47B](https://vintage-library-rune-80.pages.dev/symbol/sym-1f47b/)
- [SYM 267C](https://sleek-line-symbols-51.pages.dev/symbol/sym-267c/)
- [HEARTS](https://scholarly-cross-symbols-35.pages.dev/hearts/)
- [SYM 1F635](https://matrix-hacker-text-52.pages.dev/symbol/sym-1f635/)
- [SYM 1F493](https://vintage-library-rune-80.pages.dev/symbol/sym-1f493/)
- [MUSIC WEATHER](https://matrix-hacker-text-52.pages.dev/pt/music-weather/)
- [KHANDA EMBLEM](https://gothic-bio-fonts-13.pages.dev/symbol/khanda-emblem/)
- [FREEFIRE NAMES](https://matrix-hacker-text-52.pages.dev/es/freefire-names/)
- [SYM 26A8](https://matrix-hacker-text-52.pages.dev/symbol/sym-26a8/)
- [SCORPIO ZODIAC SCORPION](https://vintage-library-rune-80.pages.dev/symbol/scorpio-zodiac-scorpion/)
- [SYM 1D45F](https://theeduplaycampen.pages.dev/symbol/sym-1d45f/)
- [INSTAGRAM BIO](https://matrix-hacker-text-52.pages.dev/vi/instagram-bio/)
- [LEFT HEAVY BRACKET BOX](https://pearl-girly-fonts-86.pages.dev/symbol/left-heavy-bracket-box/)
- [STARS](https://matrix-hacker-text-52.pages.dev/vi/stars/)
- [SYM 1F493](https://matrix-hacker-text-52.pages.dev/symbol/sym-1f493/)
- [SYM 1D487](https://scholarly-cross-symbols-35.pages.dev/symbol/sym-1d487/)
- [SYM 26CE](https://vintage-library-rune-80.pages.dev/symbol/sym-26ce/)
- [SYM 1D456](https://coquette-aesthetic-symbols-86.pages.dev/symbol/sym-1d456/)
- [ROBLOX NAMES](https://clean-dot-aesthetic-48.pages.dev/es/roblox-names/)
- [SYM 26CC](https://matrix-hacker-text-52.pages.dev/symbol/sym-26cc/)
- [SYM 26CA](https://coquette-symbols.pages.dev/symbol/sym-26ca/)
- [SYM 1D427](https://scholarly-cross-symbols-35.pages.dev/symbol/sym-1d427/)
- [SYM 2639](https://kawaii-kaomoji-hub-96.pages.dev/symbol/sym-2639/)
- [SYM 26F5](https://coquette-aesthetic-symbols-86.pages.dev/symbol/sym-26f5/)
- [SYM 26B2](https://clean-dot-aesthetic-48.pages.dev/symbol/sym-26b2/)
- [SYM 260F](https://kawaii-kaomoji-hub-96.pages.dev/symbol/sym-260f/)
- [SYM 1D442](https://theeduplaycampen.pages.dev/symbol/sym-1d442/)
- [FLUTTERING BUTTERFLY](https://nordic-minimal-fonts-67.pages.dev/symbol/fluttering-butterfly/)
- [ANGEL WINGS HEART](https://theeduplaycampen.pages.dev/symbol/angel-wings-heart/)
- [BRACKETS](https://matrix-hacker-text-52.pages.dev/ru/brackets/)
- [BRACKETS](https://matrix-hacker-text-52.pages.dev/ja/brackets/)
- [SYM 2682](https://matrix-hacker-text-52.pages.dev/symbol/sym-2682/)
- [WHITE SUN WITH RAYS](https://matrix-hacker-text-52.pages.dev/symbol/white-sun-with-rays/)
- [SYM 26E1](https://coquette-symbols.pages.dev/symbol/sym-26e1/)
- [PISCES ZODIAC FISHES](https://gothic-bio-fonts-13.pages.dev/symbol/pisces-zodiac-fishes/)
- [SYM 1D468](https://theeduplaycampen.pages.dev/symbol/sym-1d468/)
- [SYM 26A9](https://kawaii-kaomoji-hub-96.pages.dev/symbol/sym-26a9/)
- [RINGED PLANET SATURN](https://matrix-hacker-text-52.pages.dev/symbol/ringed-planet-saturn/)
- [TIKTOK CAPTIONS](https://scholarly-cross-symbols-35.pages.dev/tiktok-captions/)
- [SYM 2677](https://matrix-hacker-text-52.pages.dev/symbol/sym-2677/)
- [SYM 1F49A](https://kawaii-kaomoji-hub-96.pages.dev/symbol/sym-1f49a/)
- [SYM 2646](https://matrix-hacker-text-52.pages.dev/symbol/sym-2646/)
- [SYM 2630](https://vintage-library-rune-80.pages.dev/symbol/sym-2630/)
- [LIBRA ZODIAC SCALES](https://matrix-hacker-text-52.pages.dev/symbol/libra-zodiac-scales/)
- [SYM 2620 FE0F](https://gothic-bio-fonts-13.pages.dev/symbol/sym-2620-fe0f/)
- [CRYING TEARS SAD KAOMOJI](https://raven-gothic-kaomoji-25.pages.dev/symbol/crying-tears-sad-kaomoji/)
- [SYM 26F0](https://raven-gothic-kaomoji-25.pages.dev/symbol/sym-26f0/)
- [MUSIC WEATHER](https://raven-gothic-kaomoji-25.pages.dev/ja/music-weather/)
- [SYM 1F627](https://matrix-hacker-text-52.pages.dev/symbol/sym-1f627/)
- [SYM 1D45D](https://sleek-line-symbols-51.pages.dev/symbol/sym-1d45d/)
- [SYM 26E1](https://sleek-line-symbols-51.pages.dev/symbol/sym-26e1/)
- [SYM 1F496](https://scholarly-cross-symbols-35.pages.dev/symbol/sym-1f496/)
- [SYM 26B8](https://coquette-symbols.pages.dev/symbol/sym-26b8/)
- [FREEFIRE NAMES](https://clean-dot-aesthetic-48.pages.dev/ja/freefire-names/)
- [TAURUS ZODIAC BULL](https://matrix-hacker-text-52.pages.dev/symbol/taurus-zodiac-bull/)
