# All Possible LinkedIn Posts

An endless feed of procedurally generated LinkedIn engagement bait. Every post is
built from the whole English dictionary, so no two look alike. Parody. Everyone in
the feed is made up.

## Just want to use it?

Open **`linkedin-posts-standalone.html`**. Double-click it. That's the whole thing:
one file, no server, no internet. The dictionary is baked in.

Everything else in this folder only matters if you want to *change* it.

## The dials

- **Coherence** — chaos to on-brand. Low: pure dictionary nonsense. High: the words
  cluster around business and the post's random theme, so it reads closer to a real
  (still deranged) post.
- **Humblebrag** — how many "posting this from Bali" asides get slipped in.
- **Em dashes** — none, to LinkedIn's favorite punctuation taking over.
- **Hashtags** — 0 to 8.
- **Haiku** — rewrites each post as a 5-7-5.

"Copy link" copies a link with the post's seed in it. Opening that link rebuilds the
exact same post.

## Files

| File | What it is | Needed to run? |
|---|---|---|
| `linkedin-posts-standalone.html` | The finished page, dictionary embedded. The deliverable. | **Yes. This is the only file you need to run it.** |
| `linkedin-posts.html` | The editable source (~24KB). Same page, but it loads the dictionary from `lexicon.json` instead of embedding it, so it's small enough to actually read and edit. Won't run from a double-click (browsers block a local file from fetching another) — edit here, then rebuild the standalone. | No — source only |
| `lexicon.json` | The word data: ~38k English words with their forms, syllable counts, a business-closeness score, and 99 theme word-lists. Generated; don't hand-edit. | No — build input |
| `build/build_lexicon.py` | Regenerates `lexicon.json` from WordNet. Only needed if you change the word list, themes, or frequency cutoff. Slow (needs spaCy). | No — build tool |
| `build/make_standalone.py` | Bundles `linkedin-posts.html` + `lexicon.json` into `linkedin-posts-standalone.html`. | No — build tool |
| `build/requirements.txt` | Python packages for `build_lexicon.py`. | No — build tool |

## Changing it

**Templates, dials, layout, styling** — edit `linkedin-posts.html`, then:

```
python build/make_standalone.py
```

That regenerates `linkedin-posts-standalone.html`. Done.

**Words or themes** — edit the seed lists at the top of `build/build_lexicon.py`
(`BUSINESS_SEEDS`, `THEMES`), then regenerate the data and rebuild the page:

```
pip install -r build/requirements.txt
python -m spacy download en_core_web_md
python build/build_lexicon.py
python build/make_standalone.py
```

## How a post is built

1. Pick a random seed (this is what a shared link stores).
2. From the seed, pick one of 99 themes and a Coherence setting.
3. Pick a post skeleton — a chain of beats: hook, story, turn, lessons, brag, closer.
4. Fill each beat's sentence templates with words pulled from the dictionary,
   biased toward the theme and toward business by the Coherence dial, with the
   right grammatical forms (plurals, tenses).
5. Generate a fake name, title, company, and hashtags the same way.

Same idea as the `all_possible_haikus.py` generator, pointed at LinkedIn: the voice
lives in the rhythm, so random words in the right sentence shapes still read as
LinkedIn.

## A note on words

No word filtering. The word list is the English dictionary as WordNet has it; if a
word is in there, it can appear. Words that WordNet only knows capitalized (names,
places) are used as names and places, not as regular vocabulary.
