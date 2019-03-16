#! /bin/bash
set -e

mkdir -p /app/pkgs

# gtk2 for pango, ragel for autogen, gperf for fontconfig, python-lxml for fc build
# qt5-default for qtmake and to default to use qt5, for ttfautohint
# (installing qt5-qmake and then export QT_SELECT=qt5 didn't work:
#   qmake: could not find a Qt installation of 'qt5'
# so perhaps qt5-qmake does not pull in qt5 dependencies automatically)
# udhr tooling uses dos2unix
# fontconfig 2.13 requires uuid-dev, but config files claims it requires util-linux.
apt-get update && apt-get install -y python-gtk2 ragel gperf python-lxml qt5-default dos2unix uuid-dev

# install a newer version of git
GIT="git-2.19.2"
cd /app/pkgs
wget https://www.kernel.org/pub/software/scm/git/${GIT}.tar.xz -O - | tar -xJ
cd $GIT
make configure
./configure --prefix=/usr/local
make all NO_GETTEXT=1
make install NO_GETTEXT=1
# update bash cache 
hash git

# patch lookup path so our python in /usr/local/lib can find pango in /usr/lib
cat << EOF >> /usr/local/lib/python2.7/sitecustomize.py
import sys
sys.path.append('/usr/lib/python2.7/dist-packages')
sys.path.append('/usr/lib/python2.7/dist-packages/gtk-2.0')
EOF

# for harfbuzz
cd /app/pkgs
git clone https://github.com/behdad/harfbuzz.git
cd harfbuzz
# git checkout 1.4.6
./autogen.sh
make
make install

/sbin/ldconfig /usr/local/lib

# get ttfautohint for font swatting
# requires harfbuzz >= 1.3.0, so install after installing harfbuzz
cd /app/pkgs
AUTOHINT="1.8.2"
wget https://sourceforge.net/projects/freetype/files/ttfautohint/${AUTOHINT}/ttfautohint-${AUTOHINT}.tar.gz -O - | tar -xz
cd "ttfautohint-${AUTOHINT}"

./configure
make
make check
make install

# behdad's cairo fork is no longer needed, base cairo has the patch for color emoji

# fontconfig needs a newer libfreetype, >= 21.0.5
cd /app/pkgs
FREETYPE="2.10.0"
wget https://download.savannah.gnu.org/releases/freetype/freetype-${FREETYPE}.tar.gz -O - | tar -xz
cd "freetype-${FREETYPE}"
./configure
make
make check
make install

# newer fontconfigs know how to scale bitmap emoji font
# 2.13.1 can handle lxml issue with PyFPE_jbuf, but adds dependency on uuid-dev, and
# also requires a newer freetype
cd /app/pkgs
FONTCONFIG="2.13.1"
wget https://www.freedesktop.org/software/fontconfig/release/fontconfig-${FONTCONFIG}.tar.gz -O - | tar -xz
cd "fontconfig-${FONTCONFIG}"
./configure
make
make check
make install

# install pngquant, version in noto-emoji is old
cd /app/pkgs
PNGQUANT="2.12.2"
wget http://pngquant.org/pngquant-${PNGQUANT}-src.tar.gz -O - | tar -xz
cd "pngquant-${PNGQUANT}"
./configure
make
make install

# install optipng for emoji quick build
OPTIPNG="optipng-0.7.6"
cd /app/pkgs
wget http://prdownloads.sourceforge.net/optipng/${OPTIPNG}.tar.gz -O - | tar -xz
cd $OPTIPNG
./configure
make
make check
make install

# install zopflipng for much slower but somewhat better compression.
# but png can only compress so much.
cd /app/pkgs
git clone https://github.com/google/zopfli.git
cd zopfli
make zopflipng
cp zopflipng /usr/local/bin

# get pycairo
cd /app/pkgs
git clone git://git.cairographics.org/git/py2cairo
cd py2cairo
./waf configure
./waf build
./waf install

# ensure libraries get found
/sbin/ldconfig /usr/local/lib

# at this point we could clean all these repos but perhaps we want to have them in
# the image for debugging?

echo "DONE"
