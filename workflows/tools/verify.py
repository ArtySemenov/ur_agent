"""Check a coded spreadsheet against the raw transcripts.

Usage:  python -I workflows/tools/verify.py <coded.xlsx> [data_dir]

For every row on the "Coded excerpts" sheet it checks that:
  - the tags are all listed under "# Tags" in CLAUDE.md (or given with --extra-tags=a,b),
  - the quoted turn exists and was spoken by the participant (not the interviewer),
  - every part of the excerpt appears word for word in that turn.
"[...]" marks text left out, and anonymisation placeholders such as [Town] are
treated as wildcards, so the anonymised spreadsheet can be checked directly.
Exits with code 1 if any problem is found.
"""
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import xlsx
import transcripts

def codebook_definitions(claude_md=pathlib.Path(__file__).parents[2] / 'CLAUDE.md'):
    """{tag: definition} for lines '- name - definition' under the '# Tags' heading of CLAUDE.md."""
    text = claude_md.read_text(encoding='utf-8').split('# Tags', 1)[1]
    text = re.split(r'^# ', text, flags=re.M)[0]
    return dict(re.findall(r'^- ([a-z][a-z-]*) - (.+)$', text, flags=re.M))


def codebook(claude_md=pathlib.Path(__file__).parents[2] / 'CLAUDE.md'):
    return set(codebook_definitions(claude_md))


def norm(s):
    s = s.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
    return re.sub(r'\s+', ' ', s).strip()


def pattern(segment):
    """Literal text, with [placeholders] allowed to stand for any short span (or a bracketed tag)."""
    parts = re.split(r'(\[[^\]]+\])', segment)
    rx = ''.join(r'(?:\[[^\]]*\]|.{1,120}?)' if re.fullmatch(r'\[[^\]]+\]', p) else re.escape(p) for p in parts)
    return re.compile(rx, re.I)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    extra = {t for a in sys.argv[1:] if a.startswith('--extra-tags=') for t in a.split('=', 1)[1].split(',')}
    book = pathlib.Path(args[0])
    data_dir = pathlib.Path(args[1]) if len(args) > 1 else pathlib.Path(__file__).parents[2] / 'data'
    allowed = codebook() | extra
    turns = transcripts.load_all(data_dir)

    rows = xlsx.read(book, 'Coded excerpts')
    h = {name: i for i, name in enumerate(rows[0])}
    col_ex = next(i for name, i in h.items() if name.startswith('Excerpt ('))
    problems = 0
    for r in rows[1:]:
        rid, pid, turn, tags, ex = r[h['Excerpt ID']], r[h['Participant']], int(float(r[h['Transcript turn']])), r[h['Tags']], r[col_ex]
        issues = [f'unknown tag "{t}"' for t in (x.strip() for x in tags.split(',')) if t not in allowed]
        who, text = turns.get(pid, {}).get(turn, ('?', ''))
        if who != 'P':
            issues.append(f'turn {turn} is not a participant turn (speaker {who})')
        text = norm(text)
        for seg in ex.split('[...]'):
            seg = norm(seg)
            if seg and not pattern(seg).search(text):
                issues.append(f'not found in turn {turn}: "{seg[:70]}"')
        if issues:
            problems += 1
            print(rid, '|', '; '.join(issues))
    print(f'{len(rows) - 1} rows checked. PROBLEMS: {problems}')
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
