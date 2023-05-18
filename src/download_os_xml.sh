#!/bin/bash
set -e
# Downloads all required ${raw} OpenSubtitles data
TGTS=(
    "pl"
    "de"
    "fr"
    "ru"
)

SRC=en
raw=raw_os/OpenSubtitles

for TGT in "${TGTS[@]}"; do

  lgs=($SRC $TGT)
  IFS=$'\n' lgs=($(sort <<<"${lgs[*]}"))
  unset IFS
  pairname="${lgs[0]}-${lgs[1]}"
  echo $pairname

  mkdir -p $raw/$pairname $raw/xml
  for lang in $SRC $TGT; do
    if [ ! -d $raw/xml/$lang ]; then
      if [ ! -f $raw/xml/$lang.zip ]; then
        wget "http://opus.nlpl.eu/download.php?f=OpenSubtitles/v2018/xml/$lang.zip" -O $raw/xml/$lang.zip
      fi
      unzip $raw/xml/$lang.zip -d $raw && rm $raw/xml/$lang.zip
    fi
  done

  if [ ! -f $raw/"$pairname"/"$pairname".xml.gz ]; then
    wget "http://opus.nlpl.eu/download.php?f=OpenSubtitles/v2018/xml/$pairname.xml.gz" -O $raw/$pairname/$pairname.xml.gz
    zcat $raw/$pairname/$pairname.xml.gz > $raw/$pairname/$pairname.xml
    rm $raw/$pairname/$pairname.xml.gz
  fi
done
