# opensubtitles_parser
Code to download and parse OpenSubtitles, specifically for MTCue (ACL2023).

### Installation

A couple python packages are required to run the parser. Preferably in a conda environment, run:
```bash
pip install pycld3 mosestokenizer tqdm
```

To download the OpenSubtitles XML files, run
```bash
bash src/download_os_xml.sh
```

By default, this will download files necessary for four language pairs: English to-and-from Polish, German, French and Russian. Comment out the specific languages if they're not necessary.

To extract context files, you must obtain an API key from OMDb by subscribing to the (minimum Basic) Patreon [here](https://www.patreon.com/join/omdb). It costs only $1 and grants access to the API.

Once files are downloaded, run
```bash
python src/extract_bitext.py --language [de/fr/pl/ru] --split_set [train/dev/test] --apikey [OMDb API Key]
```

The relevant files will be saved under `data/en-[de/fr/pl/ru]`. Context files will be saved under `data/en-[de/fr/pl/ru]/context`.

