import re
import math
from typing import List
from tqdm import tqdm
import logging
import os
import re
import requests

logging.basicConfig(level=logging.INFO)


def get_imdb_id(path: str, other_path: str = None, tgt_language: str = None) -> str:
    lg1_imdb_id = path.split('/')[-2]
    if other_path is None:
        return f"tt{lg1_imdb_id}"

    else:
        assert tgt_language is not None, "Please provide explicitly the target language"
        lg2_imdb_id = other_path.split('/')[-2]
        if lg1_imdb_id != lg2_imdb_id and tgt_language == 'de':
            # ids are different; take English one
            imdb_id = lg2_imdb_id
        else:
            imdb_id = lg1_imdb_id

        return f"tt{imdb_id}"

def process_metadata_from_omdb(imdb_id, apikey):
    base_url = f'http://www.omdbapi.com/?apikey={apikey}&'
    req = f"{base_url}i={imdb_id}"
    try:
        response = requests.get(req).json()
    except requests.exceptions.JSONDecodeError:
        logging.info("JSON error.")
        return {}
    if response["Response"] != "False":
        response = {k: v for k, v in response.items() if v not in ["N/A", "Not rated", "Not Rated", "Unrated"]}
        context = {
            "rated": f"PG rating: {response['Rated']}" if 'Rated' in response.keys() else "",
            "year_of_release": f"Released in {response['Year']}" if 'Year' in response.keys() else "",
            "genre": response["Genre"] if 'Genre' in response.keys() else "",
            "plot": response["Plot"] if 'Plot' in response.keys() else "",
            "country": response["Country"] if 'Country' in response.keys() else "",
            "writers": f"Written by: {response['Writer']}" if 'Writer' in response.keys() else "",
        }

        return context
    return {}

def write_metadata_to_file(metadata, path_to_context_output, split_set):
    for field in ["rated", "year_of_release", "genre", "plot", "country", "writers"]:
        with open(os.path.join(path_to_context_output, f"{split_set}.{field}.cxt"), 'a+') as f:
            if field in metadata.keys():
                f.write(repr(metadata[field])[1:-1] + "\n")
            else:
                f.write("\n")

def get_blocklist(path: str, path_to_xml: str) -> List[str]:
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        print("No blocklist file found (we need one before corpus is extracted!). Quitting")
        exit(1)
    lines = [os.path.join(path_to_xml, l) for l in lines]
    return lines


def time_converter(time_str):
    time_str = time_str.replace(',', ':').replace('.', ':').replace(' ', '')
    time_str = re.split(r'[^0-9]', time_str)
    # Bugproofing
    if len(time_str) < 4:
        time_str.append('000')
    try:
        hours, mins, secs, msecs = list(time_str)
    except:
        hours, mins, secs, msecs = ['00', '00', '00', '00']
    msecs = int(msecs) + int(hours) * 3600000 + int(mins) * 60000 + int(secs) * 1000

    return msecs


def parse_subtitles(tree_root, return_type=dict()):
    """
    Extract subtitles from xml files as text
    :param tree_root: root of the xml tree
    :return: subtitles : a dictionary where key is subtitle ID and value is text and timestamps
    """
    time_start = -1
    sub_count = 0
    group_buffer = []
    # Making a nan array to store subs
    subtitles = dict() if return_type == dict() else []
    for sub in tree_root:
        if sub.tag == 's':
            # Check for time start
            if sub[0].tag == 'time':
                time_start = time_converter(sub[0].attrib['value'])
                sub_count = 1
            else:
                sub_count += 1
            if sub[-1].tag == 'time':
                time_end = time_converter(sub[-1].attrib['value'])
            else:
                time_end = -1
            # Collecting subtitles
            single_buffer = ""
            for element in sub:
                if element.tag == 'w':
                    single_buffer = single_buffer + ' ' + element.text
            group_buffer.append((single_buffer, sub.attrib['id']))
            # Subtitles collected. Flush with time stamps if done
            if time_end != -1:
                duration = time_end - time_start
                fragment = math.floor(duration / sub_count)
                # Assigning time fragments to subs
                stamp = time_start
                for single_sub, sub_id in group_buffer:
                    if return_type == dict():
                        subtitles[sub_id] = (single_sub, stamp, stamp + fragment - 80)
                    else:
                        subtitles.append((single_sub, stamp, stamp + fragment - 80))
                    stamp = stamp + fragment + 80
                group_buffer = []
    # Bugproofing: if last sub is not closed
    if group_buffer:
        time_end = time_start + 1000
        duration = time_end - time_start
        fragment = math.floor(duration / sub_count)
        for single_sub, sub_id in group_buffer:
            if return_type == dict():
                subtitles[sub_id] = (single_sub, stamp, stamp + fragment - 80)
            else:
                subtitles.append((single_sub, stamp, stamp + fragment - 80))
            stamp = stamp + fragment + 80
        group_buffer = []
    return subtitles


def build_subtitle(subs, indices) -> str:
    buffer = ''
    for index in indices:
        try:
            buffer = buffer + subs[index][0]
        except KeyError:
            buffer = buffer + "-"
    return buffer
