from typing import List, Tuple, Union, Dict
import re
from argparse import ArgumentParser
from mosestokenizer import MosesDetokenizer, MosesPunctuationNormalizer
from tqdm import tqdm
from pprint import pprint
from dataclasses import dataclass
import cld3

REMOVE_TOKEN = "@Remove@"

x: int = 5


class DocumentPreprocessor:
    @staticmethod
    def build_documents(lines: List[str]) -> List[List[str]]:
        documents = []
        new_doc = []
        for line in lines:
            if line == '':
                documents.append(new_doc)
                new_doc = []
            else:
                new_doc.append(line)
        return documents

    @staticmethod
    def remove_long_sentences(document_list: List[List[str]]) -> List[List[str]]:
        k = 250
        preprocessed = []
        for document in document_list:
            max_length = 0
            for line in document:
                max_length = max(max_length, len(line.split()) + 1)
            if max_length <= k:
                preprocessed.append(document)
        return preprocessed


@dataclass
class SententialPreprocessor:
    languages: List[str]
    detok: Dict[str, MosesDetokenizer]
    norm: Dict[str, MosesPunctuationNormalizer]

    def preprocess(self, sent: str, lang: str) -> str:
        return self.manual_clean(
                self.remove_trailing_dashes(
                    self.moses_clean(
                        sent, self.detok[lang], self.norm[lang])), lang)

    @classmethod
    def init_from_langs(cls, languages):
        detok = {}
        norm = {}
        for lang in languages:
            detok[lang] = MosesDetokenizer(lang)
            norm[lang] = MosesPunctuationNormalizer(lang)
        return cls(languages, detok, norm)

    @staticmethod
    def remove_trailing_dashes(sentence: str) -> str:
        if not isinstance(sentence, str):
            return REMOVE_TOKEN
        if sentence == REMOVE_TOKEN: return sentence
        return re.sub(r'^ *-* *', '', sentence)

    @staticmethod
    def moses_clean(sentence: str, detokenize: MosesDetokenizer, normalize: MosesPunctuationNormalizer) -> str:
        if not isinstance(sentence, str):
            return REMOVE_TOKEN
        if sentence == REMOVE_TOKEN: return sentence
        return normalize(detokenize(sentence.split()))

    @staticmethod
    def manual_clean(sentence: str, lang: str) -> str:
        def common_errors(sentence: str, lang: str) -> str:
            """ https://github.com/rbawden/PrepCorpus-OpenSubs/blob/master/scripts-opensubs/clean-up-subs.py """
            if lang == "en":
                sentence = sentence.replace('l"m', "I'm")
                sentence = re.sub('([^ ])l" ?II', r"\1I'll", sentence)
                sentence = re.sub("(^| )l([',.-])", r"\1I\2", sentence)
                sentence = sentence.replace(" l...l", " I...I")
                sentence = re.sub("l\-[lI](['\- ])", r"I-I\1", sentence)
                sentence = re.sub("'lI[\- ]", "'ll ", sentence)
                sentence = re.sub("^lsn't", "Isn't", sentence)
                sentence = re.sub(r"^l ", "I ", sentence)
                sentence = re.sub(r"^l[tsnf] ", "Is ", sentence)
                sentence = re.sub(r"^lt'", "It'", sentence)
                sentence = sentence.replace(" l ", " I ")
                sentence = re.sub("[\- ]I'lI[\- ]", " I'll ", sentence)

                for word, replacement in [("belIeve", "believe"),
                                          ("feelIng", "feeling"),
                                          ("welI", "well"),
                                          ("wheelI've", "wheel I've"),
                                          ("LeguelIec", "Leguellec"),
                                          ("CampbelI", "Campbell"),
                                          ("telIJoe", "tell Joe"),
                                          ("tllI", "till"),
                                          ("y'alI", "y'all"),
                                          ("ﬀ", "ff")]:
                    sentence = sentence.replace(word, replacement)

            if lang == "fr":
                sentence = sentence.replace(r"\xc3'", "ô")
                sentence = sentence.replace(r"‡", "ç")
                sentence = re.sub("\|([ea\'])", r"l\1", sentence)

                # Replace certain words
                if "_" in sentence:
                    for word, rempl in [("di_icile", "difficile"),
                                        ("di_érent", "différent"),
                                        ("est_ce", "est-ce"),
                                        ("sou_rir", "sourir"),
                                        ("peut_être", "peut-être"),
                                        ("rendez_vous", "rendez-vous"),
                                        ("Avez_vous", "Avez-vous")]:
                        sentence = sentence.replace(word, rempl)
            # problem of I transcribed as l
            sentence = re.sub(r"^l([NnLmDdRrTtSsKkFf])", r"i\1", sentence)
            sentence = sentence.replace("¡", "i")

            return sentence

        if sentence == REMOVE_TOKEN: return sentence
        # Rule-based clean of regular errors
        brax = lambda text: re.sub(" *[\(\[\{].*?[\)\]\}] *", "", text)
        speakers = lambda text: re.sub("^[A-Z]+\: ", "", text)
        single_quot = lambda text: re.sub(" \"$", "", text)
        any_letter = lambda text, lang: re.search(r"[a-zA-Z]", text) if lang != 'ru' else re.search(r'[А-я]+', text)

        red_flag_chars = '♪/~'
        s = single_quot(speakers(brax(sentence)))
        if not any_letter(s, lang):
            return REMOVE_TOKEN
        if any(rfc in s for rfc in red_flag_chars):
            return REMOVE_TOKEN
        # Fix tokenizer mistakes in German
        s = common_errors(s, lang)
        if lang == 'de':
            # hab 's etc
            s = re.sub(r"(\w+) ?' ?s", r"\1's", s)
            # 'ne
            s = re.sub(r"(\w+)' ne", r"\1'ne", s)
        return s
