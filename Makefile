#  Copyright 2013 Google Inc. All Rights Reserved
#  Author: thaths@google.com (Sudhakar "Thaths" Chandra)
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
TAR=$(shell which tar)
ZIP=$(shell which zip)
RM=$(shell which rm)
LN=$(shell which ln)
TODAY=$(shell date "+%Y-%m-%d")
TARBALLDIR=packages
ZIPDIR=packages
HINTEDFONTDIR=./fonts/individual/hinted
UNHINTEDFONTDIR=./fonts/individual/unhinted

all: tarball zip

tarball: hintedtarball unhintedtarball

hintedtarball: $(HINTEDFONTDIR)/*.ttf cleanhintedtarball
	$(TAR) zcvf $(TARBALLDIR)/NotoFonts-hinted-$(TODAY).tgz $(HINTEDFONTDIR)/Noto*.ttf LICENSE
	cd $(TARBALLDIR); ln -s NotoFonts-hinted-$(TODAY).tgz NotoFonts-hinted-latest.tgz

unhintedtarball: $(UNHINTEDFONTDIR)/*.ttf cleanunhintedtarball
	$(TAR) zcvf $(TARBALLDIR)/NotoFonts-unhinted-$(TODAY).tgz $(UNHINTEDFONTDIR)/Noto*.ttf LICENSE
	cd $(TARBALLDIR); ln -s NotoFonts-unhinted-$(TODAY).tgz NotoFonts-unhinted-latest.tgz

zip: hintedzip unhintedzip

hintedzip: $(HINTEDFONTDIR)/*.ttf cleanhintedzip
	$(ZIP) $(ZIPDIR)/NotoFonts-hinted-$(TODAY).zip $(HINTEDFONTDIR)/Noto*.ttf LICENSE
	cd $(ZIPDIR); ln -s NotoFonts-hinted-$(TODAY).zip NotoFonts-hinted-latest.zip

unhintedzip: $(UNHINTEDFONTDIR)/*.ttf cleanunhintedzip
	$(ZIP) $(ZIPDIR)/NotoFonts-unhinted-$(TODAY).zip $(UNHINTEDFONTDIR)/Noto*.ttf LICENSE
	cd $(ZIPDIR); ln -s NotoFonts-unhinted-$(TODAY).zip NotoFonts-unhinted-latest.zip

clean: cleantarball cleanzip

cleantarball: cleanhintedtarball cleanunhintedtarball

cleanhintedtarball:
	$(RM) -f $(TARBALLDIR)/NotoFonts-hinted-$(TODAY).tgz
	$(RM) -f $(TARBALLDIR)/NotoFonts-hinted-latest.tgz

cleanunhintedtarball:
	$(RM) -f $(TARBALLDIR)/NotoFonts-unhinted-$(TODAY).tgz
	$(RM) -f $(TARBALLDIR)/NotoFonts-unhinted-latest.tgz

cleanzip: cleanhintedzip cleanunhintedzip

cleanhintedzip:
	$(RM) -f $(ZIPDIR)/NotoFonts-hinted-$(TODAY).zip
	$(RM) -f $(ZIPDIR)/NotoFonts-hinted-latest.zip

cleanunhintedzip:
	$(RM) -f $(ZIPDIR)/NotoFonts-unhinted-$(TODAY).zip
	$(RM) -f $(ZIPDIR)/NotoFonts-unhinted-latest.zip
