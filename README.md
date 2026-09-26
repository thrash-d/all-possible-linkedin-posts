# All Possible LinkedIn Posts

A parody LinkedIn feed: an endless scroll of procedurally generated engagement bait. Every post is built from the whole English dictionary, so no two look alike.

## Use

Open `linkedin-posts-standalone.html` in a browser.

## The dials

- Coherence: chaos to on-brand. Low is pure dictionary nonsense. High clusters the words around business and the post's theme, so it reads closer to a real post.
- Humblebrag: how many "posting this from Bali" type asides get slipped in.
- Em dashes: from none to LinkedIn's favorite punctuation taking over.
- Hashtags: 0 to 8.
- Haiku: rewrites each post as a 5-7-5.

"Copy link" copies a link with the post's seed in it. Opening that link rebuilds the exact same post.

## Files

|File|What it is|Needed to run?|
|-|-|-|
|`linkedin-posts-standalone.html`|The finished page, dictionary embedded.|**Yes. This is the only file you need to run it.**|
|`linkedin-posts.html`|The editable source (about 24 KB). Same page, but it loads the dictionary from `lexicon.json` instead of embedding it. It won't run from a double-click, because browsers block a local file from fetching another. Edit here, then rebuild the standalone.|No, source only|
|`lexicon.json`|The word data: about 38,000 English words with their forms, syllable counts, a business-closeness score, and 99 theme word lists. No word filtering: every WordNet lemma that clears the frequency floor is in. Generated; don't hand-edit.|No, build input|
|`build/build_lexicon.py`|Regenerates `lexicon.json` from WordNet. Only needed if you change the word list, themes, or frequency floor. Slow, and needs spaCy.|No, build tool|
|`build/make_standalone.py`|Bundles `linkedin-posts.html` and `lexicon.json` into `linkedin-posts-standalone.html`.|No, build tool|
|`build/requirements.txt`|Python packages for `build_lexicon.py`.|No, build tool|

## Change it

To change templates, dials, layout, or styling, edit `linkedin-posts.html`, then run:

```sh
python build/make_standalone.py
```

That regenerates `linkedin-posts-standalone.html`. Done.

To change words or themes, edit the seed lists at the top of `build/build_lexicon.py` (`BUSINESS_SEEDS`, `THEMES`). Then install the build dependencies, regenerate the data, and rebuild the page, one command at a time:

```sh
pip install -r build/requirements.txt
```

```sh
python -m spacy download en_core_web_md
```

```sh
python -c "import nltk; nltk.download('wordnet')"
```

```sh
python build/build_lexicon.py
```

```sh
python build/make_standalone.py
```

## How a post is built

1. Pick a random seed. A shared link stores this seed.
2. From the seed, pick one of 99 themes. The Coherence dial sets how hard the theme pulls.
3. Pick a post shape. Most posts are a story skeleton, a chain of beats: hook, story, turn, lessons, brag, closer. The rest are job announcements, rejected-then-CEO stories, polls, listicles, open-to-work posts, intern parables, one-line-per-sentence posts, and acronym frameworks.
4. Fill each beat's sentence templates with words from the dictionary, in the right grammatical forms (plurals, tenses). The Coherence dial biases the picks toward the theme and toward business. Some slots draw from two pools built from the dictionary's scores: everyday objects and corporate nouns. Pairing them gives lines like "What my potato taught me about accountability." A framework's acronym is an everyday word, with each letter spelled out by a corporate noun.
5. Generate a fake name, title, company, and hashtags the same way.

LinkedIn's voice lives in its rhythm, so random words in the right sentence shapes still read as LinkedIn.

## License

The code is MIT. See [LICENSE](LICENSE).

The word data in `lexicon.json`, and the copy embedded in `linkedin-posts-standalone.html`, is derived from Princeton WordNet, wordfreq, the CMU Pronouncing Dictionary, LemmInflect, and spaCy word vectors. It's licensed under CC BY-SA 4.0 because wordfreq's data is. See [DATA-LICENSES.md](DATA-LICENSES.md) for the attributions.
