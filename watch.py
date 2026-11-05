#!/usr/bin/env python3
"""Watch flop-labs/yellowpaper and publish what changed as a machine-readable feed.

Reads a local clone of the repository (YP_DIR), compares main with the last commit
recorded in state.json, and for every new commit writes one entry to feed.json and
feed.xml: changed files, changed Yellow Paper sections, protocol parameter values that
changed, new CHANGELOG bullets and decision ids. Nothing is written when main has not
moved. Standard library plus PyYAML only.
"""
import datetime
import json
import os
import re
import subprocess
from xml.sax.saxutils import escape

REPO_URL = "https://github.com/flop-labs/yellowpaper"
YP = os.environ.get("YP_DIR", "yp")
OUT = os.environ.get("OUT_DIR", ".")
SUMMARY = os.environ.get("SUMMARY_FILE", os.path.join(OUT, "summary.md"))
STATE = os.path.join(OUT, "state.json")
FEED = os.path.join(OUT, "feed.json")
ATOM = os.path.join(OUT, "feed.xml")
MAX_ENTRIES = 100
BOOTSTRAP = 5  # first run: describe the last few commits so the feed is not empty
SPEC = "yellowpaper.md"
PARAMS = "params/flop-protocol-params.yaml"
CHANGELOG = "CHANGELOG.md"
WATCHED = (SPEC, PARAMS, CHANGELOG, "decisions/")


def git(*args):
    return subprocess.run(["git", "-C", YP, *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout


def show(commit, path):
    try:
        return git("show", f"{commit}:{path}")
    except subprocess.CalledProcessError:
        return None


def parent_of(commit):
    parents = git("rev-list", "--parents", "-n", "1", commit).split()[1:]
    return parents[0] if parents else None


def changed_files(parent, commit):
    files = []
    for line in git("diff", "--numstat", parent, commit).splitlines():
        added, removed, path = line.split("\t", 2)
        files.append({"path": path, "added": None if added == "-" else int(added),
                      "removed": None if removed == "-" else int(removed)})
    return files


NUMBERED = re.compile(r"^(\d+(\.\d+)*\.?|[A-Z](\.\d+)+|Appendix [A-Z])\s")


def headings(text):
    """(line number, title) of every Markdown heading outside fenced code.

    Unnumbered headings ("Requirements", "Rationale & sources") repeat in many sections,
    so they are prefixed with the closest numbered heading above them."""
    out, fence, numbered = [], False, None
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("```") or line.startswith("~~~"):
            fence = not fence
        elif not fence and re.match(r"#{1,6} ", line):
            title = line.lstrip("#").strip()
            if NUMBERED.match(title):
                numbered = title
            elif numbered:
                title = f"{numbered} › {title}"
            out.append((n, title))
    return out


def changed_sections(parent, commit):
    new = show(commit, SPEC)
    if new is None:
        return []
    heads = headings(new)
    diff = git("diff", "-U0", parent, commit, "--", SPEC)
    found = []
    for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", diff, re.M):
        start, count = int(m.group(1)), int(m.group(2) or 1)
        for line in range(start, start + max(count, 1)):
            title = None
            for n, t in heads:
                if n <= line:
                    title = t
                else:
                    break
            if title and title not in found:
                found.append(title)
    return found


def load_params(commit):
    import yaml
    text = show(commit, PARAMS)
    if text is None:
        return {}
    data = yaml.safe_load(text) or {}
    return {p["name"]: p for p in data.get("parameters", []) if isinstance(p, dict) and "name" in p}


def jsonable(v):
    return v if isinstance(v, (str, int, float, bool)) or v is None else json.loads(json.dumps(v, default=str))


def changed_params(parent, commit, files):
    if PARAMS not in {f["path"] for f in files}:
        return []
    old, new = load_params(parent), load_params(commit)
    out = []
    for name in sorted(set(old) | set(new)):
        if name not in old:
            out.append({"name": name, "change": "added", "new": jsonable(new[name].get("value"))})
        elif name not in new:
            out.append({"name": name, "change": "removed", "old": jsonable(old[name].get("value"))})
        else:
            a, b = old[name], new[name]
            fields = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
            if not fields:
                continue
            item = {"name": name, "change": "modified", "fields": fields}
            if "value" in fields:
                item["old"], item["new"] = jsonable(a.get("value")), jsonable(b.get("value"))
            out.append(item)
    return out


def added_changelog(parent, commit):
    diff = git("diff", "-U0", parent, commit, "--", CHANGELOG)
    bullets = []
    for line in diff.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        text = line[1:]
        if re.match(r"\s*- ", text):
            bullets.append(text.strip()[2:].strip())
        elif text.strip() and bullets and text.startswith("  "):
            bullets[-1] += " " + text.strip()
    return [b[:600] for b in bullets]


def added_decisions(parent, commit):
    diff = git("diff", "-U0", parent, commit, "--", "decisions")
    ids = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            for d in re.findall(r"\bD-\d{4}\b", line):
                if d not in ids:
                    ids.append(d)
    return ids


def describe(commit):
    subject, date = git("log", "-1", "--format=%s%x00%cI", commit).strip().split("\x00")
    parent = parent_of(commit)
    entry = {"commit": commit, "url": f"{REPO_URL}/commit/{commit}", "date": date,
             "subject": subject}
    ref = re.search(r"flop-core@([0-9a-f]{7,40})", subject)
    if ref:
        entry["flop_core"] = ref.group(1)
    if parent is None:
        entry.update(content_change=True, files=[], sections=[], params=[], changelog=[], decisions=[])
        return entry
    files = changed_files(parent, commit)
    entry["files"] = files
    entry["content_change"] = any(f["path"] == w or f["path"].startswith(w) for f in files for w in WATCHED)
    entry["sections"] = changed_sections(parent, commit)
    entry["params"] = changed_params(parent, commit, files)
    entry["changelog"] = added_changelog(parent, commit)
    entry["decisions"] = added_decisions(parent, commit)
    return entry


def atom(feed):
    items = []
    for e in feed["entries"]:
        lines = [f"Files: {', '.join(f['path'] for f in e['files']) or '-'}"]
        if e["sections"]:
            lines.append("Sections: " + "; ".join(e["sections"]))
        for p in e["params"]:
            lines.append(f"Param {p['name']}: {p['change']}" +
                         (f" {p.get('old')} -> {p.get('new')}" if "new" in p and "old" in p else ""))
        lines += [f"Changelog: {c}" for c in e["changelog"]]
        items.append(
            "<entry>"
            f"<id>{escape(e['url'])}</id><title>{escape(e['subject'])}</title>"
            f"<updated>{escape(e['date'])}</updated><link href=\"{escape(e['url'])}\"/>"
            f"<content type=\"text\">{escape(chr(10).join(lines))}</content>"
            "</entry>")
    updated = feed["entries"][0]["date"] if feed["entries"] else feed["checked_at"]
    return ("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
            "<feed xmlns=\"http://www.w3.org/2005/Atom\">"
            f"<id>{REPO_URL}/commits/main</id><title>flop-labs/yellowpaper changes</title>"
            f"<updated>{escape(updated)}</updated><link href=\"{REPO_URL}\"/>"
            + "".join(items) + "</feed>\n")


def summary(new_entries):
    content = [e for e in new_entries if e["content_change"]]
    lines = [f"# Yellow Paper: {len(content)} new content commit(s)", ""]
    for e in content:
        lines.append(f"## [{e['commit'][:7]}]({e['url']}) {e['subject']}")
        lines.append(f"{e['date']}")
        if e["sections"]:
            lines.append("\n**Sections changed:** " + "; ".join(e["sections"][:20])
                         + (f" (+{len(e['sections']) - 20} more)" if len(e["sections"]) > 20 else ""))
        values = [p for p in e["params"] if p["change"] != "modified" or "value" in p.get("fields", [])]
        meta = len(e["params"]) - len(values)
        if values:
            lines.append("\n**Parameter values:**")
            for p in values:
                if p["change"] == "modified":
                    lines.append(f"- `{p['name']}`: `{p['old']}` → `{p['new']}`")
                else:
                    lines.append(f"- `{p['name']}` {p['change']}: `{p.get('new', p.get('old'))}`")
        if meta:
            lines.append(f"\n{meta} more parameter(s) changed only metadata (description, mutability, on_chain…); see feed.json.")
        if e["changelog"]:
            lines.append("\n**New CHANGELOG entries:**")
            lines += [f"- {c}" for c in e["changelog"]]
        if e["decisions"]:
            lines.append("\n**Decision ids in changed records:** " + ", ".join(e["decisions"]))
        lines.append("")
    text = "\n".join(lines)
    if len(text) > 60000:  # GitHub issue bodies stop at 65,536 characters
        text = text[:60000] + "\n\n… truncated; the full list is in feed.json.\n"
    return text


def output(**kv):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def main():
    head = git("rev-parse", "HEAD").strip()
    state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    last = state.get("last_commit")
    if last == head:
        print(f"No change: main is still {head[:7]}")
        output(changed="false", issue="false")
        return
    if last:
        commits = git("rev-list", "--reverse", "--first-parent", f"{last}..{head}").split()
    else:
        commits = git("rev-list", "--reverse", "--first-parent", f"-n{BOOTSTRAP}", head).split()
    new_entries = [describe(c) for c in commits]
    feed = json.load(open(FEED, encoding="utf-8")) if os.path.exists(FEED) else {"entries": []}
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    feed = {
        "source": REPO_URL, "branch": "main", "last_commit": head, "checked_at": now,
        "note": "Newest first. content_change is true when the spec, the parameter file, "
                "the changelog or a decision record changed.",
        "entries": (list(reversed(new_entries)) + feed["entries"])[:MAX_ENTRIES],
    }
    with open(FEED, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(ATOM, "w", encoding="utf-8") as f:
        f.write(atom(feed))
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump({"last_commit": head, "checked_at": now}, f, indent=2)
        f.write("\n")
    has_content = any(e["content_change"] for e in new_entries)
    if has_content:
        with open(SUMMARY, "w", encoding="utf-8") as f:
            f.write(summary(new_entries))
    print(f"{len(new_entries)} new commit(s), content change: {has_content}, main = {head[:7]}")
    output(changed="true", issue=str(has_content).lower(), head=head[:7])


if __name__ == "__main__":
    main()
