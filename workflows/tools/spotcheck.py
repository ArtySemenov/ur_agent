"""Build a spot-check sample from a coded spreadsheet, for human review.

Usage:  python -I workflows/tools/spotcheck.py <coded.xlsx> [n=30] [seed=1]
Writes <coded>-spot-check.xlsx next to the input. The coded file is not changed.

The sample is stratified (see workflows/coding-qa.md):
  - at least 2 rows for every tag that was used (rarest tags first),
  - at least 2 rows per participant,
  - at least 3 rows carrying more than one tag,
  - the rest topped up with rows tagged only "belief" (the most likely catch-all), then at random.
The same seed always gives the same sample.
"""
import sys
import random
import pathlib
import collections

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import xlsx

PASS_TAGS = 0.8  # minimum share of sampled rows where reviewer and agent tags fully agree


def load(book):
    rows = xlsx.read(book, 'Coded excerpts')
    h = {name: i for i, name in enumerate(rows[0])}
    ex = next(i for name, i in h.items() if name.startswith('Excerpt ('))
    out = [{'id': r[h['Excerpt ID']], 'pid': r[h['Participant']], 'turn': int(float(r[h['Transcript turn']])),
            'topic': r[h['Topic']], 'tags': [t.strip() for t in r[h['Tags']].split(',')],
            'excerpt': r[ex], 'note': r[h['Analyst note']]} for r in rows[1:] if r]
    try:
        people = xlsx.read(book, 'Participants')
    except StopIteration:
        people = []
    return out, people


def sample(rows, n=30, seed=1):
    rng = random.Random(seed)
    pool = rows[:]
    rng.shuffle(pool)
    chosen, why = [], {}

    def take(pred, k, reason, count):
        for r in pool:
            if count() >= k:
                return
            if r['id'] not in why and pred(r):
                chosen.append(r); why[r['id']] = reason

    usage = collections.Counter(t for r in rows for t in r['tags'])
    for tag, _ in sorted(usage.items(), key=lambda kv: kv[1]):
        take(lambda r, t=tag: t in r['tags'], 2, f'tag: {tag}',
             lambda t=tag: sum(t in r['tags'] for r in chosen))
    for pid in sorted({r['pid'] for r in rows}):
        take(lambda r, p=pid: r['pid'] == p, 2, 'participant coverage',
             lambda p=pid: sum(r['pid'] == p for r in chosen))
    take(lambda r: len(r['tags']) > 1, 3, 'multi-tag row', lambda: sum(len(r['tags']) > 1 for r in chosen))
    take(lambda r: r['tags'] == ['belief'], n, 'belief-only (possible catch-all)', lambda: len(chosen))
    take(lambda r: True, n, 'random', lambda: len(chosen))
    chosen.sort(key=lambda r: r['id'])
    return chosen, why


def sheets(rows, people, n=30, seed=1):
    chosen, why = sample(rows, n, seed)
    hdr = ['Check #', 'Excerpt ID', 'Participant', 'Turn', 'Topic', 'Excerpt', 'Analyst note', 'Why sampled',
           'Quote found in .docx? (Y/N)', 'Your tags (fill BEFORE unhiding column L)', 'Meaning kept after [...] trimming? (Y/N)',
           'Agent tags (hidden - unhide after tagging)', 'Tags agree? (Y / Partly / N)', 'Note accurate? (Y/N)', 'Comments']
    spot = [hdr] + [[i, r['id'], r['pid'], r['turn'], r['topic'], r['excerpt'], r['note'], why[r['id']],
                     '', '', '', ', '.join(r['tags']), '', '', ''] for i, r in enumerate(chosen, 1)]
    status = [['Participant', 'Source file (data/)', "Agent's status", "Agent's reason", 'Correct? (Y/N)', 'Comments']]
    if people:
        h = {name: i for i, name in enumerate(people[0])}
        for p in people[1:]:
            status.append([p[0], p[h['Source file (data/)']], p[h['Preschool child flu-vaccinated (2019/20)']], p[h['Why / how']], '', ''])
    last, plast = len(spot), len(status)
    res = [['Check', 'Result', 'Pass mark', 'How to read it'],
           ['Rows reviewed', f"=COUNTA('Spot check'!I2:I{last})", f'{last - 1}', 'Fill in every row before reading the results.'],
           ['Quotes found', f"=IFERROR(COUNTIF('Spot check'!I2:I{last},\"Y\")/COUNTA('Spot check'!I2:I{last}),\"-\")", '100%',
            'Anything below 100% means a hallucinated or misplaced quote: stop and re-run verify.py.'],
           ['Meaning kept', f"=IFERROR(COUNTIF('Spot check'!K2:K{last},\"Y\")/COUNTA('Spot check'!K2:K{last}),\"-\")", '100%',
            'Each N needs the excerpt re-cut.'],
           ['Tags fully agree', f"=IFERROR(COUNTIF('Spot check'!M2:M{last},\"Y\")/COUNTA('Spot check'!M2:M{last}),\"-\")", f'{PASS_TAGS:.0%}',
            'Below the pass mark: find which tag the disagreements share, tighten its definition, re-code that tag everywhere.'],
           ['Tags partly agree', f"=IFERROR(COUNTIF('Spot check'!M2:M{last},\"Partly\")/COUNTA('Spot check'!M2:M{last}),\"-\")", '-',
            'Usually one tag missing or extra; look for a pattern.'],
           ['Notes accurate', f"=IFERROR(COUNTIF('Spot check'!N2:N{last},\"Y\")/COUNTA('Spot check'!N2:N{last}),\"-\")", '90%',
            'Notes are interpretation; rewrite any that overclaim.'],
           ['Participant statuses correct', f"=IFERROR(COUNTIF('Status check'!E2:E{plast},\"Y\")/COUNTA('Status check'!E2:E{plast}),\"-\")", '100%',
            'These group the whole analysis; fix any error before synthesis.']]
    return [('Spot check', spot, [7, 10, 10, 6, 22, 70, 40, 20, 12, 24, 14, 22, 12, 12, 30], {'freeze': True, 'freeze_cols': 2, 'hidden_cols': [11]}),
            ('Status check', status, [11, 30, 16, 60, 12, 30], {'freeze': True}),
            ('QA results', res, [26, 12, 10, 90], {'pct_cols': [1], 'pct_from_row': 2})]


if __name__ == '__main__':
    book = pathlib.Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    rows, people = load(book)
    out = book.with_name(book.stem + '-spot-check.xlsx')
    xlsx.write(str(out), sheets(rows, people, n, seed))
    print('wrote', out)
