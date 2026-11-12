"""Generate American-English IPA for single-word flashcards with the Kokoro environment."""

import json
import re
import sys
from importlib.resources import files

from personal_vocab import PHRASE_MARKERS


SINGLE_WORD = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", re.UNICODE)
PHRASE_TAGS = PHRASE_MARKERS + ("片語", "片語動詞", "慣用語", "表達", "諺語", "句子", "搭配")
POS_TAGS = {"n": "NOUN", "noun": "NOUN", "v": "VERB", "verb": "VERB",
            "adj": "ADJ", "adjective": "ADJ", "adv": "ADV", "adverb": "ADV"}
MISAKI_TO_IPA = str.maketrans({"A": "eɪ", "I": "aɪ", "O": "oʊ", "W": "aʊ", "Y": "ɔɪ",
                              "ʤ": "dʒ", "ʧ": "tʃ", "ᵊ": "ə", "ᵻ": "ɪ"})
VOWELS = "aeiouæɑɔəɛɜɚɝɪʊʌ"
SINGLE_NUCLEUS = re.compile(rf"[^{VOWELS}]*[{VOWELS}]+[^{VOWELS}]*")
STRESSED_ONSET = re.compile(rf"([^{VOWELS}ˈˌː. ]+)([ˈˌ])(?=[{VOWELS}])")
ENGLISH_ONSETS = frozenset(
    "p b t d k ɡ f v θ ð s z ʃ ʒ h m n l ɹ ɾ w j dʒ tʃ "
    "pl bl kl ɡl fl pɹ bɹ tɹ dɹ kɹ ɡɹ fɹ θɹ ʃɹ tw dw kw ɡw sw θw "
    "pj bj kj ɡj fj vj hj mj nj lj sp st sk sm sn sl sf spl spɹ stɹ skɹ skw skj".split()
)
PRONUNCIATION_OVERRIDES = {"SME": "ˌɛsˌɛmˈiː", "kudos": "kˈuːdoʊs"}


def pronunciation_requests(cards):
    """Return distinct single-word and part-of-speech pairs in card order."""
    return list(dict.fromkeys(
        (word, pos)
        for word, _, pos, *_ in cards
        if SINGLE_WORD.fullmatch(word) and not any(tag in pos.casefold() for tag in PHRASE_TAGS)
    ))


def add_pronunciations(cards, pronunciations):
    for card in cards:
        card[1] = pronunciations.get((card[0], card[2]), "")


def format_ipa(phonemes):
    phonemes = phonemes.strip().replace("ᵻ", "ɪ").replace("ɐ", "ə")
    if not phonemes:
        return ""
    unstressed = phonemes.replace("ˈ", "").replace("ˌ", "")
    if SINGLE_NUCLEUS.fullmatch(unstressed):
        return f"/{unstressed}/"

    # The engines put stress before the vowel. Use a syllable onset for display.
    def place_stress(match):
        consonants, stress = match.groups()
        for split in range(len(consonants)):
            if consonants[split:] in ENGLISH_ONSETS:
                return consonants[:split] + stress + consonants[split:]
        return match[0]

    return f"/{STRESSED_ONSET.sub(place_stress, phonemes)}/"


def generate_pronunciations(requests):
    from espeakng_loader import get_data_path

    from audio_assets import configure_espeak

    configure_espeak(get_data_path())
    from phonemizer.backend import EspeakBackend

    backend = EspeakBackend("en-us", with_stress=True)
    dictionary = json.loads(files("misaki.data").joinpath("us_gold.json").read_text(encoding="utf-8"))
    words = [word for word, _ in requests]
    phonemes = backend.phonemize(words, strip=True)
    if len(phonemes) != len(words):
        raise RuntimeError("Pronunciation engine returned a different number of entries")

    results = []
    for (word, pos), sounds in zip(requests, phonemes):
        variant = dictionary.get(word.casefold())
        label = re.match(r"[a-z]+", pos.casefold())
        if isinstance(variant, dict) and label:
            preferred = variant.get(POS_TAGS.get(label[0]), variant.get("DEFAULT"))
            if preferred:
                sounds = preferred.translate(MISAKI_TO_IPA)
        sounds = PRONUNCIATION_OVERRIDES.get(word, sounds)
        results.append(format_ipa(sounds))
    return results


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    requests = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    print(json.dumps(generate_pronunciations(requests), ensure_ascii=False))
