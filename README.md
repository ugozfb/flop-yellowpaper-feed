# flop-yellowpaper-feed

[Türkçe](Turkce-Kurulum.md) | **English**

A machine-readable change feed for the [FLOP Network Yellow Paper](https://github.com/flop-labs/yellowpaper).

The protocol is still changing, and FLOP Labs asked builders to have their agents watch the
Yellow Paper repository. That repository has no releases or tags: changes land on `main` as
`docs(yellowpaper): sync 0.5.0 (draft) from flop-core@…` commits. This repository checks `main`
every three hours and, for every new commit, records what changed in a form an agent can read
without diffing Markdown itself.

Unofficial community tool. Not affiliated with FLOP Labs.

## Use it from an agent

```
https://raw.githubusercontent.com/ugozfb/flop-yellowpaper-feed/main/feed.json
```

Store `last_commit`. On the next check, if it differs, read the entries newer than the one you
stored. A prompt that does this:

> Fetch https://raw.githubusercontent.com/ugozfb/flop-yellowpaper-feed/main/feed.json. If
> `last_commit` differs from the one you saved, list every entry above the saved commit where
> `content_change` is true: its `params` value changes first, then `changelog`, then `sections`.
> Open `url` for details. Then save the new `last_commit`.

Feed readers can use `feed.xml` (Atom) at the same place.

## What an entry holds

| Field | Meaning |
|---|---|
| `commit`, `url`, `date`, `subject` | the Yellow Paper commit, newest first |
| `flop_core` | the flop-core revision the sync names, when the subject carries one |
| `content_change` | true if `yellowpaper.md`, the parameter file, `CHANGELOG.md` or `decisions/` changed |
| `files` | every changed path with added and removed line counts |
| `sections` | Yellow Paper headings whose text changed; unnumbered headings carry the numbered heading above them (`8.2 … › Requirements`) |
| `params` | entries of `params/flop-protocol-params.yaml`, matched by `name`: `added`, `removed`, or `modified` with the changed `fields`; `old` and `new` when `value` changed |
| `changelog` | bullets added to `CHANGELOG.md` |
| `decisions` | decision ids (`D-0000`) that appear on changed lines of `decisions/`; a mention is not always a new decision |

The feed keeps the 100 most recent commits. It changes only when `main` moves.

## How it runs

`.github/workflows/watch.yml` runs `watch.py` on a schedule (and on demand from the Actions tab).
It clones the Yellow Paper, compares `main` with the commit in `state.json`, writes `feed.json`,
`feed.xml` and `state.json`, and commits them. When a commit changed content, it also opens an
issue in this repository, so anyone watching the repository gets a notification.

Run it locally (Python 3.10+, PyYAML):

```
git clone https://github.com/flop-labs/yellowpaper.git yp
YP_DIR=yp python watch.py
```

The first run describes the five most recent commits so the feed is not empty.

Limits:

- GitHub can start scheduled runs late, and it disables scheduled workflows in a public
  repository after 60 days without activity. If the Yellow Paper is quiet that long, re-enable
  the workflow in the Actions tab.
- Sections are found by mapping changed lines to the nearest heading above them.
- Only the parameter file is compared field by field. Prose changes are reported as sections and
  changelog bullets, not interpreted.

## Attribution and license

Section titles and changelog lines in the feed are quoted from the FLOP Network Yellow Paper,
© FLOP Labs, licensed [CC BY 4.0](https://github.com/flop-labs/yellowpaper/blob/main/LICENSE).
Every entry links to the commit it describes.

The code in this repository is licensed under the [Apache License 2.0](LICENSE).
