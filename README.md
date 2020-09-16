[![Travis Build Status](https://travis-ci.org/googlefonts/nototools.svg?branch=master)](https://travis-ci.org/googlefonts/nototools)
[![PyPI](https://img.shields.io/pypi/v/notofonttools.svg)](https://pypi.org/project/notofonttools/)
[![pyup](https://pyup.io/repos/github/googlefonts/nototools/shield.svg)](https://pyup.io/repos/github/googlefonts/nototools)

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
