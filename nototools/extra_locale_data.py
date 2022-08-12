#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Extra locale data that's still missing from CLDR."""

__author__ = "roozbeh@google.com (Roozbeh Pournader)"

LIKELY_SUBTAGS = {
    "abr": ("abr", "Latn", "GH"),  # Abron
    "abq": ("abq", "Cyrl", "RU"),  # Abaza
    "ada": ("ada", "Latn", "GH"),  # Adangme
    "ae": ("ae", "Avst", "ZZ"),  # Avestan
    "aeb": ("aeb", "Arab", "TN"),  # Tunisian Arabic
    "aii": ("aii", "Syrc", "IQ"),  # Assyrian Neo-Aramaic
    "ain": ("ain", "Kana", "JP"),  # Ainu
    "akk": ("akk", "Xsux", "ZZ"),  # Akkadian
    "akz": ("akz", "Latn", "US"),  # Alabama
    "ale": ("ale", "Latn", "US"),  # Aleut
    "aln": ("aln", "Latn", "XK"),  # Gheg Albanian
    "an": ("an", "Latn", "ES"),  # Aragonese
    "anp": ("anp", "Deva", "IN"),  # Angika
    "arc": ("arc", "Armi", "ZZ"),  # Imperial Aramaic
    "aro": ("aro", "Latn", "BO"),  # Araona
    "arp": ("arp", "Latn", "US"),  # Arapaho
    "arq": ("arq", "Arab", "DZ"),  # Algerian Arabic
    "arw": ("arw", "Latn", "GY"),  # Arawak
    "ary": ("ary", "Arab", "MA"),  # Moroccan Arabic
    "arz": ("arz", "Arab", "EG"),  # Egyptian Arabic
    "avk": ("avk", "Latn", "001"),  # Kotava
    "azb": ("azb", "Arab", "IR"),  # Southern Azerbaijani
    "bar": ("bar", "Latn", "AT"),  # Bavarian
    "ber": ("ber", "Arab", "MA"),  # Berber
    "bej": ("bej", "Arab", "SD"),  # Beja
    "bci": ("bci", "Latn", "CI"),  # Baoulé
    "bgc": ("bgc", "Deva", "IN"),  # Haryanvi
    "bhi": ("bhi", "Deva", "IN"),  # Bhilali
    "bhk": ("bhk", "Latn", "PH"),  # Albay Bikol
    "bla": ("bla", "Latn", "CA"),  # Blackfoot
    "blt": ("blt", "Tavt", "VN"),  # Tai Dam
    "bpy": ("bpy", "Beng", "IN"),  # Bishnupriya
    "bqi": ("bqi", "Arab", "IR"),  # Bakhtiari
    "bsq": ("bsq", "Bass", "LR"),  # Bassa
    "bzx": ("bzx", "Latn", "ML"),  # Kelengaxo Bozo
    "cad": ("cad", "Latn", "US"),  # Caddo
    "car": ("car", "Latn", "VE"),  # Galibi Carib
    "cay": ("cay", "Latn", "CA"),  # Cayuga
    "chn": ("chn", "Latn", "US"),  # Chinook Jargon
    "cho": ("cho", "Latn", "US"),  # Choctaw
    "chy": ("chy", "Latn", "US"),  # Cheyenne
    "cjs": ("cjs", "Cyrl", "RU"),  # Shor
    "ckt": ("ckt", "Cyrl", "RU"),  # Chukchi
    "cop": ("cop", "Copt", "EG"),  # Coptic
    "cpf": ("cpf", "Latn", "HT"),  # Creoles, French
    "cps": ("cps", "Latn", "PH"),  # Capiznon
    "crh": ("crh", "Latn", "UA"),  # Crimean Tatar
    "crs": ("crs", "Latn", "SC"),  # Seselwa Creole French
    "ctd": ("ctd", "Latn", "MM"),  # Tedim Chin
    "dak": ("dak", "Latn", "US"),  # Dakota
    "dcc": ("dcc", "Arab", "IN"),  # Deccan
    "del": ("del", "Latn", "US"),  # Delaware
    "din": ("din", "Latn", "SS"),  # Dinka
    "dng": ("dng", "Cyrl", "KG"),  # Dungan
    "dtp": ("dtp", "Latn", "MY"),  # Central Dusun
    "egl": ("egl", "Latn", "IT"),  # Emilian
    "egy": ("egy", "Egyp", "ZZ"),  # Ancient Egyptian
    "eka": ("eka", "Latn", "NG"),  # Ekajuk
    "eky": ("eky", "Kali", "TH"),  # Eastern Kayah
    "esu": ("esu", "Latn", "US"),  # Central Yupik
    "ett": ("ett", "Ital", "IT"),  # Etruscan
    "evn": ("evn", "Latn", "CN"),  # Evenki
    "ext": ("ext", "Latn", "ES"),  # Extremaduran
    "ffm": ("ffm", "Latn", "ML"),  # Maasina Fulfulde
    "frc": ("frc", "Latn", "US"),  # Cajun French
    "frr": ("frr", "Latn", "DE"),  # Northern Frisian
    "frs": ("frs", "Latn", "DE"),  # Eastern Frisian
    "fud": ("fud", "Latn", "WF"),  # East Futuna
    "fuq": ("fuq", "Latn", "NE"),  # Central-Eastern Niger Fulfulde
    "fuv": ("fuv", "Latn", "NG"),  # Nigerian Fulfulde
    "gan": ("gan", "Hans", "CN"),  # Gan Chinese
    "gay": ("gay", "Latn", "ID"),  # Gayo
    "gba": ("gba", "Latn", "CF"),  # Gbaya
    "gbz": ("gbz", "Arab", "IR"),  # Zoroastrian Dari
    "gld": ("gld", "Cyrl", "RU"),  # Nanai
    "gom": ("gom", "Deva", "IN"),  # Goan Konkani
    "got": ("got", "Goth", "ZZ"),  # Gothic
    "grb": ("grb", "Latn", "LR"),  # Grebo
    "grc": ("grc", "Grek", "ZZ"),  # Ancient Greek
    "guc": ("guc", "Latn", "CO"),  # Wayuu
    "gur": ("gur", "Latn", "GH"),  # Frafra
    "hai": ("hai", "Latn", "CA"),  # Haida
    "hak": ("hak", "Hant", "CN"),  # Hakka Chinese
    "haz": ("haz", "Arab", "AF"),  # Hazaragi
    "hif": ("hif", "Deva", "FJ"),  # Fiji Hindi
    "hit": ("hit", "Xsux", "ZZ"),  # Hittite
    "hmd": ("hmd", "Plrd", "CN"),  # A-Hmao
    "hmn": ("hmn", "Latn", "CN"),  # Hmong
    "hnj": ("hnj", "Latn", "LA"),  # Hmong Njua
    "hno": ("hno", "Arab", "PK"),  # Northern Hindko
    "hop": ("hop", "Latn", "US"),  # Hopi
    "hsn": ("hsn", "Hans", "CN"),  # Xiang Chinese
    "hup": ("hup", "Latn", "US"),  # Hupa
    "hz": ("hz", "Latn", "NA"),  # Herero
    "iba": ("iba", "Latn", "MY"),  # Iban
    "ikt": ("ikt", "Latn", "CA"),  # Inuinnaqtun
    "izh": ("izh", "Latn", "RU"),  # Ingrian
    "jam": ("jam", "Latn", "JM"),  # Jamaican Creole English
    "jpr": ("jpr", "Hebr", "IL"),  # Judeo-Persian
    "jrb": ("jrb", "Hebr", "IL"),  # Jedeo-Arabic
    "jut": ("jut", "Latn", "DK"),  # Jutish
    "kac": ("kac", "Latn", "MM"),  # Kachin
    "kca": ("kca", "Cyrl", "RU"),  # Khanty
    "kfy": ("kfy", "Deva", "IN"),  # Kumaoni
    "kjh": ("kjh", "Cyrl", "RU"),  # Khakas
    "kkh": ("kkh", "Lana", "MM"),  # Khün
    "khn": ("khn", "Deva", "IN"),  # Khandesi
    "kiu": ("kiu", "Latn", "TR"),  # Kirmanjki
    "kpy": ("kpy", "Cyrl", "RU"),  # Koryak
    "kr": ("kr", "Arab", "NG"),  # Kanuri
    "krj": ("krj", "Latn", "PH"),  # Kinaray-a
    "kut": ("kut", "Latn", "CA"),  # Kutenai
    "kxm": ("kxm", "Thai", "TH"),  # Northern Khmer
    "kyu": ("kyu", "Kali", "MM"),  # Western Kayah
    "lab": ("lab", "Lina", "ZZ"),  # Linear A
    "lad": ("lad", "Latn", "IL"),  # Ladino
    "lam": ("lam", "Latn", "ZM"),  # Lamba
    "laj": ("laj", "Latn", "UG"),  # Lango
    "lfn": ("lfn", "Latn", "001"),  # Lingua Franca Nova
    "lij": ("lij", "Latn", "IT"),  # Ligurian
    "liv": ("liv", "Latn", "LV"),  # Livonian
    "ljp": ("ljp", "Latn", "ID"),  # Lampung Api
    "lrc": ("lrc", "Arab", "IR"),  # Northern Luri
    "ltg": ("ltg", "Latn", "LV"),  # Latgalian
    "lui": ("lui", "Latn", "US"),  # Luiseno
    "lun": ("lun", "Latn", "ZM"),  # Lunda
    "lus": ("lus", "Latn", "IN"),  # Mizo
    "lut": ("lut", "Latn", "US"),  # Lushootseed
    "lzh": ("lzh", "Hant", "CN"),  # Literary Chinese
    "lzz": ("lzz", "Latn", "TR"),  # Laz
    "mdt": ("mdt", "Latn", "CG"),  # Mbere
    "mfa": ("mfa", "Arab", "TH"),  # Pattani Malay
    "mic": ("mic", "Latn", "CA"),  # Micmac
    "mnc": ("mnc", "Mong", "CN"),  # Manchu
    "mns": ("mns", "Cyrl", "RU"),  # Mansi
    "mro": ("mro", "Mroo", "BD"),  # Mru (dlf, also Latn?)
    "mtr": ("mtr", "Deva", "IN"),  # Mewari
    "mus": ("mus", "Latn", "US"),  # Creek
    "mwl": ("mwl", "Latn", "PT"),  # Mirandese
    "mwv": ("mwv", "Latn", "ID"),  # Mentawai
    "myx": ("myx", "Latn", "UG"),  # Masaaba
    "myz": ("myz", "Mand", "ZZ"),  # Classical Mandaic
    "mzn": ("mzn", "Arab", "IR"),  # Mazanderani
    "nan": ("nan", "Latn", "CN"),  # Min Nan Chinese
    "ndc": ("ndc", "Latn", "MZ"),  # Ndau
    "ngl": ("ngl", "Latn", "MZ"),  # Lomwe
    "nia": ("nia", "Latn", "ID"),  # Nias
    "njo": ("njo", "Latn", "IN"),  # Ao Naga
    "noe": ("noe", "Deva", "IN"),  # Nimadi
    "nog": ("nog", "Cyrl", "RU"),  # Nogai
    "non": ("non", "Runr", "ZZ"),  # Old Norse
    "nov": ("nov", "Latn", "001"),  # Novial
    "nyo": ("nyo", "Latn", "UG"),  # Nyoro
    "nzi": ("nzi", "Latn", "GH"),  # Nzima
    "ohu": ("ohu", "Hung", "HR"),  # Old Hungarian
    "oj": ("oj", "Latn", "CA"),  # Ojibwa
    "osa": ("osa", "Latn", "US"),  # Osage
    "osc": ("osc", "Ital", "ZZ"),  # Oscan
    "otk": ("otk", "Orkh", "ZZ"),  # Old Turkish
    "pal": ("pal", "Phli", "ZZ"),  # Pahlavi FIXME: should really be 'Phlv'
    "pcd": ("pcd", "Latn", "FR"),  # Picard
    "pdc": ("pdc", "Latn", "US"),  # Pennsylvania German
    "pdt": ("pdt", "Latn", "CA"),  # Plautdietsch
    "peo": ("peo", "Xpeo", "ZZ"),  # Old Persian
    "pfl": ("pfl", "Latn", "DE"),  # Palatine German
    "phn": ("phn", "Phnx", "ZZ"),  # Phoenician
    "pi": ("pi", "Brah", "ZZ"),  # Pali
    "pms": ("pms", "Latn", "IT"),  # Piedmontese
    "pnt": ("pnt", "Grek", "GR"),  # Pontic
    "prs": ("prs", "Arab", "AF"),  # Dari
    "qug": ("qug", "Latn", "EC"),  # Chimborazo Highland Quichua
    "rom": ("rom", "Latn", "RO"),  # Romany
    "sck": ("sck", "Deva", "IN"),  # Sadri
    "skr": ("skr", "Arab", "PK"),  # Seraiki
    "sou": ("sou", "Thai", "TH"),  # Southern Thai
    "swv": ("swv", "Deva", "IN"),  # Shekhawati
    "tab": ("tab", "Cyrl", "RU"),  # Tabassaran (dlf)
    "ude": ("ude", "Cyrl", "RU"),  # Udihe (dlf)
    "uga": ("uga", "Ugar", "ZZ"),  # Ugaritic
    "vep": ("vep", "Latn", "RU"),  # Veps
    "vmw": ("vmw", "Latn", "MZ"),  # Makhuwa
    "wbr": ("wbr", "Deva", "IN"),  # Wagdi
    "wbq": ("wbq", "Telu", "IN"),  # Waddar
    "wls": ("wls", "Latn", "WF"),  # Wallisian
    "wtm": ("wtm", "Deva", "IN"),  # Mewati
    "yrk": ("yrk", "Cyrl", "RU"),  # Nenets (dlf)
    "xnr": ("xnr", "Deva", "IN"),  # Kangri
    "xum": ("xum", "Ital", "ZZ"),  # Umbrian (dlf)
    "zdj": ("zdj", "Arab", "KM"),  # Ngazidja Comorian
    "und-Mult": ("skr", "Mult", "ZZ"),  # ancient writing system for Saraiki,
    # Arabic now used
    "und-Hung": ("ohu", "Hung", "ZZ"),  # Old Hungarian, Carpathian basin
    "und-Hluw": ("hlu", "Hluw", "ZZ"),  # Hieroglyphic Luwian
    "und-Ahom": ("aho", "Ahom", "ZZ"),  # Ahom
}


ENGLISH_SCRIPT_NAMES = {
    "Cans": "Canadian Aboriginal",  # shorten name for display purposes,
    # match Noto font name
}

ENGLISH_LANGUAGE_NAMES = {
    "abr": "Abron",
    "abq": "Abaza",
    "aho": "Ahom",
    "aii": "Assyrian Neo-Aramaic",
    "akz": "Alabama",
    "amo": "Amo",
    "aoz": "Uab Meto",
    "atj": "Atikamekw",
    "bap": "Bantawa",
    "bci": "Baoulé",
    "ber": "Berber",
    "bft": "Balti",
    "bfy": "Bagheli",
    "bgc": "Haryanvi",
    "bgx": "Balkan Gagauz Turkish",
    "bh": "Bihari",
    "bhb": "Bhili",
    "bhi": "Bhilali",
    "bhk": "Albay Bikol",
    "bjj": "Kanauji",
    "bku": "Buhid",
    "blt": "Tai Dam",
    "bmq": "Bomu",
    "bqi": "Bakhtiari",
    "bqv": "Koro Wachi",
    "bsq": "Bassa",
    "bto": "Rinconada Bikol",
    "btv": "Bateri",
    "buc": "Bushi",
    "bvb": "Bube",
    "bya": "Batak",
    "bze": "Jenaama Bozo",
    "bzx": "Kelengaxo Bozo",
    "ccp": "Chakma",
    "cja": "Western Cham",
    "cjs": "Shor",
    "cjm": "Eastern Cham",
    "ckt": "Chukchi",
    "cpf": "French-based Creoles",
    "crj": "Southern East Cree",
    "crk": "Plains Cree",
    "crl": "Northern East Cree",
    "crm": "Moose Cree",
    "crs": "Seselwa Creole French",
    "csw": "Swampy Cree",
    "ctd": "Tedim Chin",
    "dcc": "Deccan",
    "dng": "Dungan",
    "dnj": "Dan",
    "dtm": "Tomo Kan Dogon",
    "eky": "Eastern Kayah",
    "ett": "Etruscan",
    "evn": "Evenki",
    "ffm": "Maasina Fulfulde",
    "fud": "East Futuna",
    "fuq": "Central-Eastern Niger Fulfulde",
    "fuv": "Nigerian Fulfulde",
    "gbm": "Garhwali",
    "gcr": "Guianese Creole French",
    "ggn": "Eastern Gurung",
    "gjk": "Kachi Koli",
    "gju": "Gujari",
    "gld": "Nanai",
    "gos": "Gronings",
    "grt": "Garo",
    "gub": "Guajajára",
    "gvr": "Western Gurung",
    "haz": "Hazaragi",
    "hlu": "Hieroglyphic Luwian",
    "hmd": "A-Hmao",
    "hnd": "Southern Hindko",
    "hne": "Chhattisgarhi",
    "hnj": "Hmong Njua",
    "hnn": "Hanunoo",
    "hno": "Northern Hindko",
    "hoc": "Ho",
    "hoj": "Haroti",
    "hop": "Hopi",
    "ikt": "Inuinnaqtun",
    "jml": "Jumli",
    "kao": "Xaasongaxango",
    "kca": "Khanty",
    "kck": "Kalanga",
    "kdt": "Kuy",
    "kfr": "Kachchi",
    "kfy": "Kumaoni",
    "kge": "Komering",
    "khb": "Lü",
    "khn": "Khandesi",
    "kht": "Khamti",
    "kjg": "Khmu",
    "kjh": "Khakas",
    "kkh": "Khün",
    "kpy": "Koryak",
    "kvr": "Kerinci",
    "kvx": "Parkari Koli",
    "kxm": "Northern Khmer",
    "kxp": "Wadiyara Koli",
    "kyu": "Western Kayah",
    "lab": "Linear A",
    "laj": "Lango",
    "lbe": "Lak",
    "lbw": "Tolaki",
    "lcp": "Western Lawa",
    "lep": "Lepcha",
    "lif": "Limbu",
    "lis": "Lisu",
    "ljp": "Lampung Api",
    "lki": "Laki",
    "lmn": "Lambadi",
    "lrc": "Northern Luri",
    "lut": "Lushootseed",
    "luz": "Southern Luri",
    "lwl": "Eastern Lawa",
    "maz": "Central Mazahua",
    "mdh": "Maguindanaon",
    "mdt": "Mbere",
    "mfa": "Pattani Malay",
    "mgp": "Eastern Magar",
    "mgy": "Mbunga",
    "mns": "Mansi",
    "mnw": "Mon",
    "moe": "Montagnais",
    "mrd": "Western Magar",
    "mro": "Mru",
    "mru": "Cameroon Mono",
    "mtr": "Mewari",
    "mvy": "Indus Kohistani",
    "mwk": "Kita Maninkakan",
    "mxc": "Manyika",
    "myx": "Masaaba",
    "myz": "Classical Mandaic",
    "nch": "Central Huasteca Nahuatl",
    "ndc": "Ndau",
    "ngl": "Lomwe",
    "nhe": "Eastern Huasteca Nahuatl",
    "nhw": "Western Huasteca Nahuatl",
    "nij": "Ngaju",
    "nod": "Northern Thai",
    "noe": "Nimadi",
    "nsk": "Naskapi",
    "nxq": "Naxi",
    "ohu": "Old Hungarian",
    "osc": "Oscan",
    "otk": "Old Turkish",
    "pcm": "Nigerian Pidgin",
    "pka": "Ardhamāgadhī Prākrit",
    "pko": "Pökoot",
    "pra": "Prakrit",  # language family name
    "prd": "Parsi-Dari",
    "prs": "Dari",
    "puu": "Punu",
    "rcf": "Réunion Creole French",
    "rej": "Rejang",
    "ria": "Riang",  # (India)
    "rjs": "Rajbanshi",
    "rkt": "Rangpuri",
    "rmf": "Kalo Finnish Romani",
    "rmo": "Sinte Romani",
    "rmt": "Domari",
    "rmu": "Tavringer Romani",
    "rng": "Ronga",
    "rob": "Tae’",
    "ryu": "Central Okinawan",
    "saf": "Safaliba",
    "sck": "Sadri",
    "scs": "North Slavey",
    "sdh": "Southern Kurdish",
    "sef": "Cebaara Senoufo",
    "skr": "Seraiki",
    "smp": "Samaritan",
    "sou": "Southern Thai",
    "srb": "Sora",
    "srx": "Sirmauri",
    "swv": "Shekhawati",
    "sxn": "Sangir",
    "syi": "Seki",
    "syl": "Sylheti",
    "tab": "Tabassaran",
    "taj": "Eastern Tamang",
    "tbw": "Tagbanwa",
    "tdd": "Tai Nüa",
    "tdg": "Western Tamang",
    "tdh": "Thulung",
    "thl": "Dangaura Tharu",
    "thq": "Kochila Tharu",
    "thr": "Rana Tharu",
    "tkt": "Kathoriya Tharu",
    "tli": "Tlingit",
    "tsf": "Southwestern Tamang",
    "tsg": "Tausug",
    "tsj": "Tshangla",
    "ttj": "Tooro",
    "tts": "Northeastern Thai",
    "ude": "Udihe",
    "uli": "Ulithian",
    "unr": "Mundari",
    "unx": "Munda",
    "vic": "Virgin Islands Creole English",
    "vmw": "Makhu",
    "wbr": "Wagdi",
    "wbq": "Waddar",
    "wls": "Wallisian",
    "wtm": "Mewati",
    "xav": "Xavánte",
    "xcr": "Carian",
    "xlc": "Lycian",
    "xld": "Lydian",
    "xmn": "Manichaean Middle Persian",
    "xmr": "Meroitic",
    "xna": "Ancient North Arabian",
    "xnr": "Kangri",
    "xpr": "Parthian",
    "xsa": "Sabaean",
    "xsr": "Sherpa",
    "xum": "Umbrian",
    "yrk": "Nenets",
    "yua": "Yucatec Maya",
    "zdj": "Ngazidja Comorian",
    "zmi": "Negeri Sembilan Malay",
}

# Supplement mapping of languages to scripts
LANG_TO_SCRIPTS = {
    "ber": ["Arab", "Latn", "Tfng"],
    "hak": ["Hans", "Hant", "Latn"],
    "nan": ["Hans", "Hant", "Latn"],
    "yue": ["Hant"],
}

# Supplement mapping of regions to lang_scripts
REGION_TO_LANG_SCRIPTS = {
    "CN": ["hak-Hans", "hak-Latn", "nan-Hans", "nan-Latn", "yue-Hans"],
    "HK": ["yue-Hant"],
    "MN": ["mn-Mong"],
    "MY": ["zh-Hans"],
    "TW": ["hak-Hant", "hak-Latn", "nan-Hant", "nan-Latn"],
}

PARENT_LOCALES = {
    "ky-Latn": "root",
    "sd-Deva": "root",
    "tg-Arab": "root",
    "ug-Cyrl": "root",
}

NATIVE_NAMES = {
    "mn-Mong": "ᠮᠣᠨᠭᠭᠣᠯ ᠬᠡᠯᠡ",
}

EXEMPLARS = {
    "und-Avst": r"[\U010b00-\U010b35]",
    "und-Bali": r"[\u1b05-\u1b33]",
    "und-Bamu": r"[\ua6a0-\ua6ef]",
    "und-Cham": r"[\uaa00-\uaa28 \uaa50-\uaa59]",
    "und-Copt": r"[\u2c80-\u2cb1]",
    "und-Egyp": r"[\U013000-\U01303f]",
    "und-Hira": r"[\u3041-\u3096\u3099-\u309f\U01b000-\U01b001]",
    "und-Java": r"[\ua984-\ua9b2]",
    "und-Kali": r"[\ua90a-\ua925 \ua900-\ua909]",
    "und-Kana": r"[\u30a0-\u30ff \u31f0-\u31ff]",
    "und-Khar": r"[\U010a10-\U010a13\U010a15-\U010a17\U010a19-\U010a33"
    r"\U010A38-\U010a3a]",
    "und-Kthi": r"[\U11080-\U110C1]",
    "und-Lana": r"[\u1a20-\u1a4c]",
    "und-Lepc": r"[\u1c00-\u1c23]",
    "und-Linb": r"[\U010000-\U01000b \U010080-\U01009f]",
    "und-Mand": r"[\u0840-\u0858]",
    "und-Mtei": r"[\uabc0-\uabe2]",
    "und-Orkh": r"[\U010c00-\U010c48]",
    "und-Phag": r"[\ua840-\ua877]",
    "und-Saur": r"[\ua882-\ua8b3]",
    "und-Sund": r"[\u1b83-\u1ba0]",
    "und-Sylo": r"[\ua800-\ua82b]",
    "und-Tavt": r"[\uaa80-\uaaaf \uaadb-\uaadf]",
    "und-Tglg": r"[\u1700-\u170c \u170e-\u1711]",
    "und-Ugar": r"[\U010380-\U01039d \U01039f]",
    "und-Xsux": r"[\U012000-\U01202f]",
    "und-Zmth": r"[\U010AC0-\U010AE6 \U010AEB-\U010AF6]",
    "und-Zsye": r"[\u2049\u231a\u231b\u2600\u260e\u2614\u2615\u26fa\u2708\u2709"
    r"\u270f\u3297\U01f004\U01f170\U01f193\U01f197\U01f30d\U01f318"
    r"\U01f332\U01f334\U01f335\U01f344\U01f346\U01f352\U01f381"
    r"\U01f393\U01f3a7\U01f3b8\U01f3e1\U01f402\U01f40a\U01f418"
    r"\U01f419\U01f41b\U01f41f\U01f422\U01f424\U01f427\U01f44c"
    r"\U01f44d\U01f453\U01f463\U01f4bb\U01f4ce\U01f4d3\U01f4d6"
    r"\U01f4e1\U01f4fb\U01f511\U01f525\U01f565\U01F63a\U01f680"
    r"\U01f681\U01f683\U01f686\U01f68c\U01f6a2\U01f6a3\U01f6b4]",
    "und-Zsym": r"[\u20ac\u20b9\u2103\u2109\u2115\u2116\u211a\u211e\u2122"
    r"\u21d0-\u21d3\u2203\u2205\u2207\u2208\u220f\u221e\u2248\u2284"
    r"\u231a\u23e3\u23f3\u2400\u2460\u24b6\u2523\u2533\u2602\u260e"
    r"\u2615\u261c\u2637\u263a\u264f\u2656\u2663\u266b"
    r"\u267b\u267f\u26f9\u2708\u2740\u2762\u2a6b\u2a93\u2a64\u2e19"
    r"\u4dc3\U010137\U01017B\U0101ef\U01d122\U01d15e\U01d161]",
}
