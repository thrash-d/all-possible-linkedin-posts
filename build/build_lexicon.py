#!/usr/bin/env python3
"""Build lexicon.json for All Possible LinkedIn Posts.

WordNet vocabulary sorted into POS buckets, with spaCy similarity scores
precomputed so a static page can use them without spaCy.

Install:
    pip install spacy nltk pronouncing wordfreq lemminflect numpy
    python -m spacy download en_core_web_md
    python -c "import nltk; nltk.download('wordnet')"

Run:
    python build_lexicon.py            # writes ../lexicon.json
    python build_lexicon.py --min-zipf 2.0 --out /tmp/lexicon.json

Output shape (arrays, not objects, to keep the file small):
    words[POS]   one row per word, columns listed in "columns"
    themes[name] {POS: [row indexes of the closest words]}
    corp         0-100 closeness to the business centroid (in each row)
No word filtering: every WordNet lemma that clears the frequency floor is in.
Capitalized-only WordNet entries go to PROPN instead of being dropped.
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pronouncing
import spacy
from lemminflect import getInflection
from nltk.corpus import wordnet as wn
from wordfreq import zipf_frequency

BUSINESS_SEEDS = [
    "leadership", "growth", "strategy", "revenue", "synergy", "stakeholder",
    "pipeline", "scale", "innovation", "culture", "team", "customer", "market",
    "brand", "mindset", "hustle", "productivity", "alignment", "execution",
    "networking", "entrepreneur", "startup", "investor", "sales", "deliverable",
    "bandwidth", "leverage", "disruption", "vision", "mission", "value",
    "impact", "gratitude", "success", "career", "hiring", "manager", "founder",
    "motivation", "performance",
]

# One random topic per post pulls the words toward it.
THEMES = [
    "sourdough", "pickleball", "grief", "marathon", "toddler", "dog", "cat",
    "funeral", "wedding", "surfing", "golf", "chess", "gardening", "parenting",
    "marriage", "camping", "fishing", "hunting", "barbecue", "pizza", "coffee",
    "whiskey", "yoga", "meditation", "poker", "lottery", "casino", "divorce",
    "therapy", "church", "monastery", "prison", "military", "pirate",
    "samurai", "viking", "medieval", "empire", "astronaut", "dinosaur",
    "volcano", "tornado", "hurricane", "ocean", "desert", "jungle", "farm",
    "tractor", "cattle", "horse", "chicken", "bees", "ants", "wolves",
    "sharks", "octopus", "penguin", "pelican", "raccoon", "zombie", "vampire",
    "ghost", "wizard", "dragon", "castle", "circus", "clown", "magician",
    "ballet", "opera", "jazz", "karaoke", "bowling", "laundry", "plumbing",
    "dentist", "surgery", "hospital", "airport", "subway", "traffic", "taxes",
    "mortgage", "retirement", "kindergarten", "prom", "homework", "lemonade",
    "lawnmower", "dishwasher", "microwave", "printer", "hangover", "cruise",
    "wrestling", "football", "hockey", "rodeo", "bingo", "kombucha",
    "crossfit", "skateboarding", "snowboarding", "skiing", "hiking",
    "kayaking", "sailing", "cycling", "triathlon", "boxing", "karate",
    "fencing", "archery", "baseball", "basketball", "soccer", "cricket",
    "rugby", "tennis", "volleyball", "bakery", "sushi", "tacos", "burrito",
    "barista", "brunch", "avocado", "smoothie", "cheese", "chocolate", "donut",
    "pancakes", "ramen", "wine", "beer", "tequila", "cocktail", "minivan",
    "motorcycle", "bicycle", "submarine", "helicopter", "rocket", "train",
    "elevator", "garage", "basement", "attic", "treehouse", "igloo",
    "lighthouse", "library", "museum", "zoo", "aquarium", "carnival", "ninja",
    "cowboy", "knight", "gladiator", "pharaoh", "mermaid", "unicorn", "yeti",
    "alien", "robot", "superhero", "werewolf", "mummy", "witch", "goblin",
    "lego", "puzzle", "crossword", "sudoku", "arcade", "trampoline",
    "sandcastle", "snowman", "halloween", "thanksgiving", "christmas",
    "birthday", "graduation", "honeymoon", "vacation", "reunion", "sleepover",
    "picnic", "campfire", "fireworks", "firefighter", "lifeguard", "janitor",
    "lumberjack", "beekeeping", "blacksmith", "carpentry", "knitting",
    "pottery", "origami", "juggling", "comedy", "earthquake", "avalanche",
    "glacier", "swamp", "eclipse", "jellyfish", "flamingo", "sloth", "goose",
    "squirrel", "hamster", "goldfish", "llama", "walrus", "hedgehog", "turtle",
    "snail", "pigeon", "owl", "frog", "nap", "insomnia", "chiropractor", "gym",
    "sauna", "massage", "bitcoin",
]

# Themes with no vector of their own borrow the average of these.
THEME_ALIASES = {
    "pickleball": ["tennis", "paddle", "badminton"],
}

WN_POS = {"n": "NOUN", "v": "VERB", "a": "ADJ", "s": "ADJ", "r": "ADV"}
COLUMNS = {
    "NOUN": ["word", "plural", "syl", "zipf", "corp", "concrete"],
    "VERB": ["word", "s", "past", "ing", "pp", "syl", "zipf", "corp"],
    "ADJ": ["word", "syl", "zipf", "corp"],
    "ADV": ["word", "syl", "zipf", "corp"],
    "PROPN": ["word", "syl", "zipf"],
}
VOWEL_GROUPS = re.compile(r"[aeiouy]+")


def syllables(word):
    total = 0
    for part in word.split("-"):
        phones = pronouncing.phones_for_word(part.lower())
        if phones:
            total += pronouncing.syllable_count(phones[0])
        else:
            groups = VOWEL_GROUPS.findall(part.lower())
            n = len(groups)
            if part.lower().endswith("e") and n > 1 and not part.lower().endswith("le"):
                n -= 1
            total += max(1, n)
    return total


def inflect(lemma, tag):
    forms = getInflection(lemma, tag=tag)
    return forms[0] if forms else lemma


def is_concrete(lemma):
    for syn in wn.synsets(lemma, pos=wn.NOUN):
        for path in syn.hypernym_paths():
            if any(s.name().startswith("physical_entity") for s in path):
                return True
    return False


def collect_vocab(min_zipf):
    """lemma -> set of POS, and the proper-noun set, from every WordNet synset."""
    common = defaultdict(set)
    proper = {}
    for synset in wn.all_synsets():
        pos = WN_POS[synset.pos()]
        for lemma in synset.lemmas():
            name = lemma.name()
            if "_" in name or not name.replace("-", "").replace("'", "").isalpha():
                continue
            if not name.isascii():
                continue
            if name[0].isupper():
                if name.lower() not in common:
                    proper[name] = proper.get(name, 0)
                continue
            common[name].add(pos)

    kept = {}
    for word, poses in common.items():
        z = zipf_frequency(word, "en")
        if z >= min_zipf:
            kept[word] = (poses, z)

    kept_proper = {}
    for word in proper:
        if word.lower() in kept:
            continue
        z = zipf_frequency(word, "en")
        if z >= min_zipf:
            kept_proper[word] = z
    return kept, kept_proper


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-zipf", type=float, default=2.5,
                    help="wordfreq Zipf frequency floor")
    ap.add_argument("--neighbors", type=int, default=150,
                    help="closest words kept per theme per POS")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "lexicon.json"))
    args = ap.parse_args()

    print("Loading en_core_web_md...", file=sys.stderr)
    nlp = spacy.load("en_core_web_md")

    print("Collecting WordNet vocabulary...", file=sys.stderr)
    vocab, proper = collect_vocab(args.min_zipf)
    print(f"  {len(vocab)} common words, {len(proper)} proper nouns", file=sys.stderr)

    words = sorted(vocab)
    vecs = np.zeros((len(words), nlp.vocab.vectors_length), dtype=np.float32)
    has_vec = np.zeros(len(words), dtype=bool)
    for i, w in enumerate(words):
        lex = nlp.vocab[w]
        if lex.has_vector:
            vecs[i] = unit(lex.vector)
            has_vec[i] = True

    business = unit(np.mean([nlp.vocab[w].vector for w in BUSINESS_SEEDS if nlp.vocab[w].has_vector], axis=0))
    corp_raw = vecs @ business
    lo, hi = np.percentile(corp_raw[has_vec], [1, 99])
    corp = np.where(has_vec, np.clip((corp_raw - lo) / (hi - lo), 0, 1) * 100, 0).round().astype(int)

    rows = {p: [] for p in COLUMNS}
    row_of = {p: {} for p in COLUMNS}
    print("Inflecting and counting syllables...", file=sys.stderr)
    for i, w in enumerate(words):
        poses, z = vocab[w]
        syl = syllables(w)
        zq = round(z, 1)
        c = int(corp[i])
        if "NOUN" in poses:
            row_of["NOUN"][w] = len(rows["NOUN"])
            rows["NOUN"].append([w, inflect(w, "NNS"), syl, zq, c, int(is_concrete(w))])
        if "VERB" in poses:
            row_of["VERB"][w] = len(rows["VERB"])
            rows["VERB"].append([w, inflect(w, "VBZ"), inflect(w, "VBD"), inflect(w, "VBG"), inflect(w, "VBN"), syl, zq, c])
        if "ADJ" in poses:
            row_of["ADJ"][w] = len(rows["ADJ"])
            rows["ADJ"].append([w, syl, zq, c])
        if "ADV" in poses:
            row_of["ADV"][w] = len(rows["ADV"])
            rows["ADV"].append([w, syl, zq, c])
    for w, z in sorted(proper.items()):
        rows["PROPN"].append([w, syllables(w), round(z, 1)])

    print("Computing theme neighbors...", file=sys.stderr)
    themes = {}
    for theme in THEMES:
        sources = THEME_ALIASES.get(theme, [theme])
        found = [nlp.vocab[w].vector for w in sources if nlp.vocab[w].has_vector]
        if not found:
            print(f"  skip theme without a vector: {theme}", file=sys.stderr)
            continue
        sims = vecs @ unit(np.mean(found, axis=0))
        sims[~has_vec] = -1
        order = np.argsort(-sims)
        per_pos = {}
        for pos in ("NOUN", "VERB", "ADJ", "ADV"):
            picked = []
            for j in order:
                w = words[j]
                if w in row_of[pos] and w != theme:
                    picked.append(row_of[pos][w])
                    if len(picked) >= args.neighbors:
                        break
            per_pos[pos] = picked
        themes[theme] = per_pos

    out = {
        "version": 1,
        "minZipf": args.min_zipf,
        "columns": COLUMNS,
        "words": rows,
        "themes": themes,
        "businessSeeds": BUSINESS_SEEDS,
    }
    Path(args.out).write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    size = Path(args.out).stat().st_size
    counts = ", ".join(f"{p} {len(r)}" for p, r in rows.items())
    print(f"Wrote {args.out} ({size / 1e6:.2f} MB): {counts}; {len(themes)} themes", file=sys.stderr)


if __name__ == "__main__":
    main()
