#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

# with open("README.rst", 'r') as readme_file:
#    readme = readme_file.read()
readme = """Noto font tools are a set of scripts useful for release
engineering of Noto and similar fonts"""

setup(
    name="notofonttools",
    use_scm_version={"write_to": "nototools/_version.py"},
    description="Noto font tools",
    license="Apache",
    long_description=readme,
    python_requires=">=3.7",
    author="Noto Authors",
    author_email="noto-font@googlegroups.com",
    url="https://github.com/googlefonts/nototools",
    # more examples here http://docs.python.org/distutils/examples.html#pure-python-distribution-by-package
    packages=find_packages() + ["third_party"],
    include_package_data=True,
    setup_requires=["setuptools_scm"],
    install_requires=[
        "fontTools",
        # On Mac OS X these need to be installed with homebrew
        # 'cairo',
        # 'pango',
        # 'pygtk',
        # 'imagemagick'
    ],
    extras_require={
        # optional requirements for nototools.shape_diff module
        "shapediff": ["booleanOperations", "defcon", "Pillow",],
    },
    package_data={"nototools": ["*.sh", "data/*",]},
    # $ grep "def main(" nototools/* | cut -d: -f1
    scripts=[
        "nototools/autofix_for_release.py",
        "nototools/add_vs_cmap.py",
        "nototools/create_image.py",
        "nototools/decompose_ttc.py",
        "nototools/drop_hints.py",
        "nototools/dump_otl.py",
        "nototools/fix_khmer_and_lao_coverage.py",
        "nototools/fix_noto_cjk_thin.py",
        "nototools/generate_sample_text.py",
        "nototools/generate_website_2_data.py",
        "nototools/merge_noto.py",
        "nototools/merge_fonts.py",
        "nototools/noto_lint.py",
        "nototools/scale.py",
        "nototools/subset.py",
        "nototools/subset_symbols.py",
        "nototools/test_vertical_extents.py",
    ],
    entry_points={
        "console_scripts": [
            "notodiff = nototools.notodiff:main",
            "notocoverage = nototools.coverage:main",
        ]
    },
)
