import xml.etree.ElementTree as ET

from argparse import ArgumentParser
from preprocess_opensubs import SententialPreprocessor, REMOVE_TOKEN

from tqdm import tqdm
from utils import *
import random

random.seed(1)
import logging

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


def parse_documents(lg1_name: str, lg2_name: str, split_set: str, path_to_opensubs: str, apikey: str):
    """
    Given a file with alignments of subtitles between source and target language, produce a bitext of overlap at least 0.9
    """
    pairname = f"{lg1_name}-{lg2_name}"
    tgt_language = lg1_name if lg1_name != 'en' else lg2_name
    align_filename = f"{path_to_opensubs}/OpenSubtitles/{pairname}/{pairname}.xml"
    """
    Part 1: Parse alignments
    """
    try:
        align_tree = ET.parse(align_filename)
    except ET.ParseError:
        print("Parse error")
        return
    collection = align_tree.getroot()
    # Identify aligned files
    path_to_xml = f'{path_to_opensubs}/OpenSubtitles/xml'
    path_to_output = f"data/en-{tgt_language}"
    path_to_context_output = os.path.join(path_to_output, "context")

    blocklist = get_blocklist(f'blocklist/blocklist.{tgt_language}', path_to_xml)
    assert blocklist[0].startswith(
        path_to_xml), f"Paths from blocklist won't match: e.g. {blocklist[0] = }, {path_to_xml = }"

    middle_index = len(blocklist) // 2

    if not os.path.exists(path_to_output):
        os.makedirs(path_to_output)

    if not os.path.exists(path_to_context_output):
        os.makedirs(path_to_context_output)

    sent_prep = SententialPreprocessor.init_from_langs([lg1_name, lg2_name])
    write_until = 10_000
    for idx, document in enumerate(collection):
        logging.info(f"Parsing {idx}/{len(collection)} document: {document}")
        # Should not parse if on the
        lg1_file = os.path.join(path_to_xml, document.attrib['fromDoc'][:-3])
        lg2_file = os.path.join(path_to_xml, document.attrib['toDoc'][:-3])
        print(lg1_file, lg2_file)
        imdb_id = get_imdb_id(path=lg1_file, other_path=lg2_file, tgt_language=tgt_language)
        print(imdb_id)
        # blocklist is on en side for french and de side for german, either way it's the lg1_file
        if lg1_file in blocklist and split_set == 'train':
            print("In blocklist")
            continue
        elif lg1_file not in blocklist[:middle_index] and split_set == 'dev':
            continue
        elif lg1_file not in blocklist[middle_index:] and split_set == 'test':
            continue
        try:
            lg1_tree = ET.parse(lg1_file)
            lg1_root = lg1_tree.getroot()
            lg1_subtitles = parse_subtitles(lg1_root)
            lg2_tree = ET.parse(lg2_file)
            lg2_root = lg2_tree.getroot()
            lg2_subtitles = parse_subtitles(lg2_root)
        except FileNotFoundError:
            print("Error when parsing source file")
            continue
        
        metadata = process_metadata_from_omdb(imdb_id=imdb_id, apikey=apikey)
        logging.info(f"{metadata = }")
        if split_set != 'train' and metadata == {}: continue

        context = {
            'lg1': None,
            'lg2': None,
            'end': None,
            'id': 0
        }

        for alignment in document:
            print(document)
            # Only accept if it is a pair and it has the overlap of at least 0.9
            if 'overlap' in alignment.attrib.keys() and float(alignment.attrib['overlap']) > 0.9:
                lg1, lg2 = alignment.attrib['xtargets'].split(';')
                lg1, lg2 = lg1.split(), lg2.split()

                current_sub = {
                    'lg1_text': sent_prep.preprocess(
                        build_subtitle(lg1_subtitles, lg1), lg1_name),
                    'lg2_text': sent_prep.preprocess(
                        build_subtitle(lg2_subtitles, lg2), lg2_name),
                    'start': lg1_subtitles[lg1[0]][1],
                    'end': lg1_subtitles[lg1[-1]][2],
                    'id': int(alignment.attrib['id'][2:])
                }
                print(current_sub['lg1_text'])
                if current_sub['lg1_text'] != REMOVE_TOKEN and current_sub['lg2_text'] != REMOVE_TOKEN:

                    # Reset context if time difference is too big
                    if context['end'] is None or current_sub['start'] - context['end'] > 7000 \
                            or current_sub['id'] != context['id'] + 1:
                        context = {k: "" for k in context.keys()}

                    # Fill context with the newest sentence
                    # Doing this beforehand to include current sentence in the context
                    context = {
                        'lg1': f"{context['lg1']}▁{current_sub['lg1_text']}",
                        'lg2': f"{context['lg2']}▁{current_sub['lg2_text']}",
                        'end': current_sub['end'],
                        'id': current_sub['id']
                    }

                    # If more than 6 sentences, clip the last one
                    if context['lg1'].count('▁') > 6:
                        context['lg1'] = re.sub(r'^.*?▁', '', context['lg1'])
                        context['lg2'] = re.sub(r'^.*?▁', '', context['lg2'])

                    if split_set == 'train' or random.random() < 0.2: # to diversify dev/test, skip this 80% of the time
                        write_until -= 1
                        print(f"writing to {path_to_output} {split_set}.{lg1_name}")
                        # Write current sentences to files
                        with open(os.path.join(path_to_output, f"{split_set}.{lg1_name}"), 'a+') as f:
                            f.write(current_sub['lg1_text'] + "\n")
                        with open(os.path.join(path_to_output, f"{split_set}.{lg2_name}"), 'a+') as f:
                            f.write(current_sub['lg2_text'] + "\n")

                        write_metadata_to_file(metadata, path_to_context_output, split_set)
    
                        # Writing context:
                        sents = context['lg1'].split('▁')[::-1]
                        for i in range(0, 6):
                            with open(os.path.join(path_to_context_output, f"{split_set}.{i}.{lg1_name}"), 'a+') as f:
                                try:
                                    f.write(sents[i] + "\n")
                                except IndexError:
                                    f.write("\n")
                        sents = context['lg2'].split('▁')[::-1]
                        for i in range(0, 6):
                            with open(os.path.join(path_to_context_output, f"{split_set}.{i}.{lg2_name}"), 'a+') as f:
                                try:
                                    f.write(sents[i] + "\n")
                                except IndexError:
                                    f.write("\n")

            if split_set != 'train' and write_until <= 0: return


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-l', '--language', choices=['de', 'fr', 'pl', 'ru'], required=True)
    parser.add_argument('-s', '--split_set', default="train")
    parser.add_argument('-p', '--path_to_opensubs', default="raw_os")
    parser.add_argument('-a', '--apikey', required=True, help='API key for OMDb')

    args = parser.parse_args()
    l1, l2 = min('en', args.language), max('en', args.language)
    parse_documents(l1, l2, args.split_set, path_to_opensubs=args.path_to_opensubs, apikey=args.apikey)
