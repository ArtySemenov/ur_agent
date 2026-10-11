"""Synthesis helpers: an overview of the coded data, and a theme board for the researcher.

Usage:
  python -I workflows/tools/themes.py overview <coded.xlsx>
  python -I workflows/tools/themes.py board <coded.xlsx> <themes.json> <board.xlsx>

The AI writes only <themes.json>: theme names, descriptions, the excerpt IDs that support
or contradict each theme, and neutral prompts. This script pulls every quote from the coded
spreadsheet and calculates every count, so quotes and numbers can't be invented.
If <board.xlsx> already exists, the researcher's columns are carried over by Theme ID.
See workflows/synthesis.md.
"""
import re
import sys
import json
import pathlib
import collections

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import xlsx

# Words that signal interpretation or recommendation rather than description.
INTERPRETIVE = re.compile(r"\b(should|must|ought|recommend\w*|need(s)? to|have to|implies|implication\w*|therefore|"
                          r"so that|this means|because the system|opportunity to|key insight|it is clear)\b", re.I)
HUMAN_COLS = ['Decision (Keep / Merge / Split / Rename / Drop)', 'Decision notes', 'My interpretation (so what?)',
              'Implications / who needs to know', 'Confidence after review (High / Medium / Low)']


def load_groups(book):
    """{participant: group} from the optional 'Group' column of the Participants sheet."""
    try:
        rows = xlsx.read(book, 'Participants')
    except StopIteration:
        return {}
    if not rows or 'Group' not in rows[0]:
        return {}
    g, p = rows[0].index('Group'), rows[0].index('Participant')
    return {r[p]: r[g] for r in rows[1:] if r and len(r) > g and r[g]}


def load_coded(book):
    grp = load_groups(book)
    rows = xlsx.read(book, 'Coded excerpts')
    h = {name: i for i, name in enumerate(rows[0])}
    ex = next(i for name, i in h.items() if name.startswith('Excerpt ('))
    out = collections.OrderedDict()
    for r in rows[1:]:
        if not r:
            continue
        out[r[h['Excerpt ID']]] = {'id': r[h['Excerpt ID']], 'pid': r[h['Participant']], 'group': grp.get(r[h['Participant']], 'All participants'),
                                   'topic': r[h['Topic']], 'turn': int(float(r[h['Transcript turn']])),
                                   'tags': [t.strip() for t in r[h['Tags']].split(',')], 'excerpt': r[ex],
                                   'note': r[h['Analyst note']]}
    return out


def groups(coded):
    """{participant: group label}."""
    return {e['pid']: e['group'] for e in coded.values()}


def group_names(status):
    """Group labels in order of first appearance, with their sizes."""
    names = []
    for p in sorted(status):
        if status[p] not in names:
            names.append(status[p])
    return [(g, sum(v == g for v in status.values())) for g in names]


def abbrev(name):
    return ''.join(w[0].upper() for w in name.split()) or name


def people(ids, coded):
    return sorted({coded[i]['pid'] for i in ids})


def overview(book):
    coded = load_coded(book)
    status = groups(coded)
    pids = sorted(status)
    gn = group_names(status)
    print(f"{len(coded)} excerpts, {len(pids)} participants; groups: " + ', '.join(f'{g} ({k})' for g, k in gn))
    for g, _ in gn:
        print(f'  {g}:', ', '.join(p for p in pids if status[p] == g))
    by_tag = collections.defaultdict(lambda: collections.Counter())
    by_topic = collections.defaultdict(lambda: collections.Counter())
    for e in coded.values():
        for t in e['tags']:
            by_tag[t][e['pid']] += 1
            by_topic[e['topic']][t] += 1
    print('\nTAG: excerpts | participants | ' + ' | '.join(g for g, _ in gn) + ' | per participant')
    for t, c in sorted(by_tag.items(), key=lambda kv: -sum(kv[1].values())):
        split = ' | '.join(f"{sum(1 for p in c if status[p] == g)}/{k}" for g, k in gn)
        print(f"{t:20} {sum(c.values()):4} | {len(c):2}/{len(pids)} | {split} | " + ' '.join(f"{p[1:]}:{c.get(p, 0)}" for p in pids))
    print('\nTOPIC: tag counts')
    for topic, c in by_topic.items():
        print(f"{topic}: " + ', '.join(f"{t} {k}" for t, k in c.most_common()))
    return by_tag, by_topic, status


def validate(spec, coded):
    errors, warnings = [], []
    seen = set()
    for th in spec['themes']:
        tid = th.get('id', '?')
        for field in ('id', 'name', 'description', 'supporting', 'key_quotes', 'counter_summary', 'prompts'):
            if not th.get(field):
                errors.append(f"{tid}: missing '{field}'")
        if tid in seen:
            errors.append(f'{tid}: duplicate theme ID')
        seen.add(tid)
        for key in ('supporting', 'counter', 'key_quotes'):
            for i in th.get(key, []):
                if i not in coded:
                    errors.append(f"{tid}: {key} ID {i} not in coded spreadsheet")
        if not set(th.get('key_quotes', [])) <= set(th.get('supporting', [])):
            errors.append(f'{tid}: key_quotes must also be in supporting')
        if set(th.get('counter', [])) & set(th.get('supporting', [])):
            errors.append(f'{tid}: an excerpt cannot both support and contradict the same theme')
        if not th.get('counter') and not th.get('counter_summary', '').lower().startswith('none found'):
            errors.append(f"{tid}: no counter-evidence IDs, so counter_summary must start 'None found'")
        valid = [i for i in th.get('supporting', []) if i in coded]
        if len(people(valid, coded)) < 2:
            errors.append(f'{tid}: fewer than 2 participants - move it to outliers')
        for p in th.get('prompts', []):
            if not p.strip().endswith('?'):
                errors.append(f'{tid}: prompt is not a question: "{p}"')
        for field in ('name', 'description', 'counter_summary'):
            m = INTERPRETIVE.search(th.get(field, ''))
            if m:
                errors.append(f"{tid}: interpretive wording '{m.group(0)}' in {field}")
        for p in th.get('prompts', []):
            m = INTERPRETIVE.search(p)
            if m:
                errors.append(f"{tid}: leading wording '{m.group(0)}' in prompt: \"{p}\"")
    for o in spec.get('outliers', []):
        for i in o.get('excerpts', []):
            if i not in coded:
                errors.append(f"{o.get('id')}: outlier ID {i} not in coded spreadsheet")
        m = INTERPRETIVE.search(o.get('observation', ''))
        if m:
            errors.append(f"{o.get('id')}: interpretive wording '{m.group(0)}' in observation")
    return errors, warnings


def strength(n):
    return 'Strong' if n >= 6 else 'Moderate' if n >= 3 else 'Thin'


def previous_human_columns(path):
    if not path.exists():
        return {}
    try:
        rows = xlsx.read(path, 'Themes')
    except StopIteration:
        return {}
    h = {name: i for i, name in enumerate(rows[0])}
    keep = {}
    for r in rows[1:]:
        if r:
            vals = {c: (r[h[c]] if c in h and h[c] < len(r) else '') for c in HUMAN_COLS}
            if any(vals.values()):
                keep[r[0]] = vals
    return keep


def board(book, spec_path, out):
    coded = load_coded(book)
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding='utf-8'))
    errors, _ = validate(spec, coded)
    if errors:
        print('NOT BUILT - fix these in', spec_path)
        for e in errors:
            print(' -', e)
        sys.exit(1)
    status = groups(coded)
    pids = sorted(status)
    gn = group_names(status)
    out = pathlib.Path(out)
    carried = previous_human_columns(out)
    col = lambda p: f"{p} ({abbrev(status[p])})" if len(gn) > 1 else p

    # Themes
    hdr = ['Theme ID', 'Theme', 'Description (AI - descriptive only)', f'Participants (n of {len(pids)})'] + \
          [f'{g} (n of {k})' for g, k in gn] + ['Strength', 'Most common tags',
           'Key quotes', 'Counter-evidence', 'Prompts to think with'] + HUMAN_COLS
    trows = [hdr]
    evid = [['Theme ID', 'Theme', 'Role', 'Excerpt ID', 'Participant', 'Group', 'Topic', 'Tags', 'Excerpt', 'Analyst note']]
    grid = [['Theme ID', 'Theme'] + [col(p) for p in pids] + ['Supporting participants']]
    assigned = set()
    for th in spec['themes']:
        sup, con = th['supporting'], th.get('counter', [])
        assigned |= set(sup) | set(con)
        sp = people(sup, coded)
        tags = collections.Counter(t for i in sup for t in coded[i]['tags'])
        quotes = '\n\n'.join(f"{i}: \"{coded[i]['excerpt']}\"" for i in th['key_quotes'])
        counter = th['counter_summary'] + (('\n' + ', '.join(con)) if con else '')
        prev = carried.get(th['id'], {})
        trows.append([th['id'], th['name'], th['description'], len(sp)] +
                     [sum(status[p] == g for p in sp) for g, _ in gn] + [strength(len(sp)),
                      ', '.join(f'{t} ({k})' for t, k in tags.most_common(3)), quotes, counter,
                      '\n'.join('- ' + p for p in th['prompts'])] + [prev.get(c, '') for c in HUMAN_COLS])
        for role, ids in (('supports', sup), ('counter', con)):
            for i in ids:
                e = coded[i]
                evid.append([th['id'], th['name'], role, i, e['pid'], status[e['pid']], e['topic'],
                             ', '.join(e['tags']), e['excerpt'], e['note']])
        cp = set(people(con, coded))
        grid.append([th['id'], th['name']] + [('✓' if p in sp else '') + ('✗' if p in cp else '') for p in pids] + [len(sp)])

    # Outliers
    orows = [['Outlier ID', 'Observation (one participant or very few)', 'Excerpt IDs', 'Quotes', 'Researcher: worth following up?']]
    for o in spec.get('outliers', []):
        assigned |= set(o['excerpts'])
        orows.append([o['id'], o['observation'], ', '.join(o['excerpts']),
                      '\n\n'.join(f"{i} ({coded[i]['pid']}): \"{coded[i]['excerpt']}\"" for i in o['excerpts']), ''])

    # Unassigned
    urows = [['Excerpt ID', 'Participant', 'Group', 'Topic', 'Tags', 'Excerpt', 'Analyst note', 'Researcher: belongs in a theme? (which)']]
    for i, e in coded.items():
        if i not in assigned:
            urows.append([i, e['pid'], status[e['pid']], e['topic'], ', '.join(e['tags']), e['excerpt'], e['note'], ''])

    # Overview tables
    by_tag = collections.defaultdict(collections.Counter)
    by_topic = collections.defaultdict(collections.Counter)
    for e in coded.values():
        for t in e['tags']:
            by_tag[t][e['pid']] += 1
            by_topic[e['topic']][t] += 1
    tagrows = [['Tag', 'Excerpts', f'Participants (n of {len(pids)})'] + [f'{g} (n of {k})' for g, k in gn]
               + [col(p) for p in pids]]
    for t, c in sorted(by_tag.items(), key=lambda kv: -sum(kv[1].values())):
        tagrows.append([t, sum(c.values()), len(c)] + [sum(1 for p in c if status[p] == g) for g, _ in gn]
                       + [c.get(p, '') for p in pids])
    alltags = [r[0] for r in tagrows[1:]]
    toprows = [['Topic'] + alltags] + [[topic] + [c.get(t, '') for t in alltags] for topic, c in by_topic.items()]

    n_sup = sum(1 for r in trows[1:])
    readme = [[l] for l in [
        f"Theme board: {spec.get('round', '')}", '',
        'What this is',
        f"{n_sup} candidate themes drafted by the AI from {len(coded)} coded excerpts ({len(pids)} participants" + ('; groups: ' + ', '.join(f'{g} {k}' for g, k in gn) if len(gn) > 1 else '') + ").",
        'The AI grouped the evidence and described each theme in participants\' terms. It has NOT interpreted the themes, drawn conclusions or made recommendations: that is your job.',
        'Every quote on this board is pulled from the coded spreadsheet by script, and every count is calculated by script.', '',
        'How to work through it (about 1-2 hours)',
        '1. Themes: read each theme with its key quotes and counter-evidence. Use "Theme evidence" (filter by Theme ID) to see everything behind it.',
        '2. Fill in Decision: Keep, Merge (with which theme), Split (how), Rename (to what) or Drop. Add notes.',
        '3. Check Unassigned excerpts and Outliers: is anything important missing from the themes?',
        '4. For the themes you keep, write "My interpretation (so what?)" and "Implications / who needs to know". The prompts are there to think with; ignore them if they are not useful.',
        '5. Ask the AI to apply your Decisions. It rebuilds the board and keeps everything you wrote in your columns.', '',
        'Reading the numbers',
        f'Counts are people, not quotes: "Participants" = how many of the {len(pids)} participants gave supporting evidence. Talkative participants do not inflate a theme.',
        'Strength: Strong = 6 or more participants, Moderate = 3-5, Thin = 2. With 12 participants, these show how widely a pattern was voiced, not how common it is in the population.',
        'Theme x participant: ✓ = supporting evidence from that participant, ✗ = counter-evidence.' + (' Letters after each participant show their group: ' + ', '.join(f'{abbrev(g)} = {g}' for g, _ in gn) + '.' if len(gn) > 1 else ''),
        'Themes overlap on purpose: one excerpt can support several themes.', '',
        'Sheets', 'Themes | Theme evidence | Theme x participant | Outliers | Unassigned excerpts | Tags by participant | Tags by topic']]

    sheets = [('Read me', readme, [150], {}),
              ('Themes', trows, [8, 30, 50, 12] + [11] * len(gn) + [10, 30, 70, 45, 45, 18, 25, 50, 40, 14], {'freeze': True, 'freeze_cols': 2, 'filter': True}),
              ('Theme evidence', evid, [8, 30, 9, 10, 9, 13, 24, 26, 80, 45], {'freeze': True, 'freeze_cols': 2, 'filter': True}),
              ('Theme x participant', grid, [8, 40] + [9] * len(pids) + [12], {'freeze': True, 'freeze_cols': 2}),
              ('Outliers', orows, [10, 60, 18, 80, 25], {'freeze': True}),
              ('Unassigned excerpts', urows, [10, 10, 13, 24, 26, 80, 45, 30], {'freeze': True, 'filter': True}),
              ('Tags by participant', tagrows, [18, 9, 12] + [13] * len(gn) + [9] * len(pids), {'freeze': True, 'freeze_cols': 1}),
              ('Tags by topic', toprows, [34] + [11] * len(alltags), {'freeze': True, 'freeze_cols': 1})]
    try:
        xlsx.write(str(out), sheets)
    except PermissionError:
        print(f'Could not write {out}: it is probably open in Excel. Close it and run again.')
        sys.exit(1)
    print(f"wrote {out}: {n_sup} themes, {len(orows) - 1} outliers, {len(urows) - 1} unassigned of {len(coded)} excerpts;"
          f" researcher columns carried over for {len(carried)} themes")
    for r in trows[1:]:
        split = ' / '.join(f'{abbrev(g)} {r[4 + j]}' for j, (g, _) in enumerate(gn))
        print(f"  {r[0]} {r[4 + len(gn)]:8} {r[3]:2} people ({split})  {r[1]}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'overview':
        overview(sys.argv[2])
    elif cmd == 'board':
        board(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(__doc__)
