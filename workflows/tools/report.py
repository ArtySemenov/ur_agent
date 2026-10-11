"""Build a shareable, self-contained HTML research report.

Usage:
  python -I workflows/tools/report.py <brief.md> <coded.xlsx> <themes.json> <out.html>
         [--board=<theme-board.xlsx>] [--include-candidates]

Inputs (topic-agnostic - see workflows/report.md):
  brief.md      the researcher's report brief: title, summary, insights, method, etc.
  coded.xlsx    "Coded excerpts" and "Participants" sheets (optional "Group" column)
  themes.json   theme definitions from the synthesis workflow
  board.xlsx    the theme board; its Decision column decides which themes are included

Every quote and every count in the report is taken from the spreadsheets, not from the brief.
Writes nothing if validation fails.
"""
import re
import sys
import json
import html
import datetime
import pathlib
import collections

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import xlsx
import themes as th
import verify

TEMPLATE = pathlib.Path(__file__).parent / 'report_template.html'
PLACEHOLDER = re.compile(r'\[TO WRITE[^\]]*\]', re.I)
COUNT_WORDS = r'\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve'
TYPED_COUNT = re.compile(rf'\b({COUNT_WORDS})\s+(?:of\s+(?:the\s+)?\d+\s+|out of\s+\d+\s+)?'
                         r'(participants|parents|people|users|respondents|interviewees|customers|families)\b', re.I)
SECTIONS = {'research questions', 'executive summary', 'method', 'quality and anonymisation', 'limitations', 'next steps'}


# ---------- brief parsing ----------

def parse_brief(text):
    brief = {'title': '', 'fields': {}, 'sections': {}, 'insights': [], 'unknown': []}
    current = None
    for line in text.splitlines():
        if line.startswith('# ') and not brief['title']:
            brief['title'] = line[2:].strip()
            continue
        m = re.match(r'^##\s+(.+?)\s*$', line)
        if m:
            name = m.group(1)
            if name.lower().startswith('insight:'):
                current = {'title': name.split(':', 1)[1].strip(), 'lines': [], 'kind': 'insight'}
                brief['insights'].append(current)
            elif name.lower() in SECTIONS:
                current = {'title': name, 'lines': [], 'kind': name.lower()}
                brief['sections'][name.lower()] = current
            else:
                current = {'title': name, 'lines': [], 'kind': 'unknown'}
                brief['unknown'].append(name)
            continue
        if current is None:
            m = re.match(r'^(Subtitle|Audience|Date|Round|Contact):\s*(.*)$', line)
            if m:
                brief['fields'][m.group(1).lower()] = m.group(2).strip()
            continue
        current['lines'].append(line)
    for sec in list(brief['sections'].values()) + brief['insights']:
        split_meta(sec)
    return brief


def split_meta(sec):
    """Pull 'Themes:', 'Quotes:', 'Status:' and 'Implications:' out of a section's lines."""
    body, impl, meta, in_impl = [], [], {}, False
    for line in sec['lines']:
        m = re.match(r'^(Themes|Quotes|Status):\s*(.*)$', line.strip())
        if m and not in_impl:
            meta[m.group(1).lower()] = m.group(2).strip()
            continue
        m = re.match(r'^Implications:\s*(.*)$', line.strip())
        if m:
            in_impl = True
            impl.append(m.group(1))
            continue
        (impl if in_impl else body).append(line)
    sec['body'] = '\n'.join(body).strip()
    sec['implications'] = '\n'.join(impl).strip()
    sec['themes'] = [t.strip() for t in re.split(r'[,\s]+', meta.get('themes', '')) if t.strip()]
    sec['quotes'] = [q.strip() for q in re.split(r'[,\s]+', meta.get('quotes', '')) if q.strip()]
    sec['status'] = (meta.get('status') or 'researcher').lower()


# ---------- tiny markdown ----------

def md(text, theme_ids, tokens):
    """Paragraphs, '- ' bullets, **bold**, *italic*, [T01] theme links, {{tokens}} from the data."""
    if not text:
        return ''
    for k, v in tokens.items():
        text = text.replace('{{' + k + '}}', str(v))

    def inline(s):
        s = html.escape(s, quote=False)
        s = PLACEHOLDER.sub(lambda m: f'<span class="todo">{m.group(0)}</span>', s)
        s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
        s = re.sub(r'(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)', r'<em>\1</em>', s)
        s = re.sub(r'\[(T\d{2,})\]', lambda m: f'<a class="tref" href="#theme-{m.group(1)}" data-theme="{m.group(1)}">{m.group(1)}</a>'
                   if m.group(1) in theme_ids else m.group(1), s)
        return s

    out, para, items = [], [], []

    def flush():
        if para:
            out.append('<p>' + inline(' '.join(para)) + '</p>'); para.clear()
        if items:
            out.append('<ul>' + ''.join(f'<li>{inline(i)}</li>' for i in items) + '</ul>'); items.clear()

    for line in text.splitlines():
        s = line.strip()
        if not s:
            flush()
        elif s.startswith('- ') or s.startswith('* '):
            if para:
                flush()
            items.append(s[2:])
        else:
            if items:
                flush()
            para.append(s)
    flush()
    return ''.join(out)


# ---------- board decisions ----------

def decisions(board):
    if not board or not pathlib.Path(board).exists():
        return {}
    rows = xlsx.read(board, 'Themes')
    h = {name: i for i, name in enumerate(rows[0])}
    get = lambda r, c: r[h[c]] if c in h and h[c] < len(r) else ''
    return {r[0]: {'decision': get(r, th.HUMAN_COLS[0]).strip(), 'interpretation': get(r, th.HUMAN_COLS[2]).strip(),
                   'implications': get(r, th.HUMAN_COLS[3]).strip()} for r in rows[1:] if r}


def participants_sheet(book):
    try:
        rows = xlsx.read(book, 'Participants')
    except StopIteration:
        return []
    h = rows[0]
    ctx = next((i for i, c in enumerate(h) if c.lower().startswith('context')), None)
    return [{'id': r[h.index('Participant')], 'context': (r[ctx] if ctx is not None and ctx < len(r) else '')} for r in rows[1:] if r]


# ---------- build ----------

def build(brief_path, coded_path, themes_path, out_path, board=None, include_candidates=False):
    errors, warnings = [], []
    brief = parse_brief(pathlib.Path(brief_path).read_text(encoding='utf-8'))
    coded = th.load_coded(coded_path)
    spec = json.loads(pathlib.Path(themes_path).read_text(encoding='utf-8'))
    terr, _ = th.validate(spec, coded)
    errors += [f'themes file: {e}' for e in terr]
    dec = decisions(board)
    status = th.groups(coded)
    gn = th.group_names(status)
    pids = sorted(status)

    # which themes go in
    included = []
    for t in spec['themes']:
        d = dec.get(t['id'], {}).get('decision', '')
        if d.lower().startswith('keep') or (include_candidates and not d.lower().startswith(('drop', 'merge'))):
            included.append(t)
    candidates = include_candidates and any(not dec.get(t['id'], {}).get('decision', '').lower().startswith('keep') for t in included)
    if not included:
        errors.append('no themes to include: mark themes Keep on the theme board, or use --include-candidates for a draft')
    ids = {t['id'] for t in included}

    # brief checks
    if not brief['title']:
        errors.append('brief: missing "# Title" line')
    if 'executive summary' not in brief['sections']:
        errors.append('brief: missing "## Executive summary" section')
    if not brief['insights']:
        errors.append('brief: no "## Insight: ..." sections')
    for name in brief['unknown']:
        warnings.append(f'brief: unknown section "{name}" was ignored')
    for ins in brief['insights']:
        if not ins['themes']:
            errors.append(f'insight "{ins["title"]}": add a "Themes:" line linking it to at least one theme')
        for t in ins['themes']:
            if t not in ids:
                errors.append(f'insight "{ins["title"]}": theme {t} is not in the report (unknown, dropped or not marked Keep)')
        for q in ins['quotes']:
            if q not in coded:
                errors.append(f'insight "{ins["title"]}": quote {q} is not an excerpt ID in the coded spreadsheet')
        if ins['status'] not in ('draft', 'researcher'):
            errors.append(f'insight "{ins["title"]}": Status must be "draft" or "researcher"')
    prose = [brief['title'], *brief['fields'].values()] + [s['body'] + '\n' + s['implications'] for s in brief['sections'].values()] + \
            [i['title'] + '\n' + i['body'] + '\n' + i['implications'] for i in brief['insights']]
    for chunk in prose:
        for m in TYPED_COUNT.finditer(chunk):
            warnings.append(f'typed count "{m.group(0)}": counts should come from the data - use {{{{n_participants}}}} or rely on the computed figures')
        for m in PLACEHOLDER.finditer(chunk):
            warnings.append(f'placeholder still to fill: {m.group(0)}')
    drafts = [i['title'] for i in brief['insights'] if i['status'] == 'draft'] + \
             [s['title'] for s in brief['sections'].values() if s['status'] == 'draft']

    if errors:
        print('NOT BUILT - fix these first:')
        for e in errors:
            print(' -', e)
        sys.exit(1)

    # data
    group_index = {g: i for i, (g, _) in enumerate(gn)}
    theme_of = collections.defaultdict(list)
    for t in included:
        for i in t['supporting']:
            theme_of[i].append(t['id'])
    tokens = {'n_participants': len(pids), 'n_excerpts': len(coded), 'n_themes': len(included),
              'n_groups': len(gn), 'groups': ', '.join(f'{k} {g.lower()}' for g, k in gn),
              'n_tags': len({t for e in coded.values() for t in e['tags']})}
    render = lambda s: md(s, ids, tokens)
    defs = verify.codebook_definitions()
    tag_people = collections.defaultdict(set); tag_count = collections.Counter()
    for e in coded.values():
        for t in e['tags']:
            tag_people[t].add(e['pid']); tag_count[t] += 1

    def theme_obj(t):
        sp = th.people(t['supporting'], coded)
        d = dec.get(t['id'], {})
        return {'id': t['id'], 'name': t['name'], 'description': t['description'],
                'people': sp, 'counterPeople': th.people(t.get('counter', []), coded),
                'strength': th.strength(len(sp)), 'supporting': t['supporting'], 'counter': t.get('counter', []),
                'keyQuotes': t['key_quotes'], 'counterSummary': t['counter_summary'],
                'tags': [k for k, _ in collections.Counter(x for i in t['supporting'] for x in coded[i]['tags']).most_common(3)],
                'decision': d.get('decision', ''), 'interpretation': d.get('interpretation', ''),
                'researcherImplications': d.get('implications', '')}

    ctx = {p['id']: p['context'] for p in participants_sheet(coded_path)}
    data = {
        'meta': {'title': brief['title'], 'subtitle': brief['fields'].get('subtitle', ''),
                 'audience': brief['fields'].get('audience', ''), 'date': brief['fields'].get('date', ''),
                 'round': brief['fields'].get('round', ''), 'contact': brief['fields'].get('contact', ''),
                 'generated': datetime.date.today().isoformat(),
                 'draftItems': drafts, 'candidateThemes': candidates,
                 'sources': [pathlib.Path(p).name for p in (brief_path, coded_path, themes_path) + ((board,) if board else ())]},
        'sections': {k: {'title': s['title'], 'html': render(s['body']), 'status': s['status']} for k, s in brief['sections'].items()},
        'groups': [{'name': g, 'n': k, 'slot': min(i, 3)} for i, (g, k) in enumerate(gn)],
        'participants': [{'id': p, 'group': status[p], 'context': ctx.get(p, '')} for p in pids],
        'insights': [{'id': f'I{n}', 'title': i['title'], 'html': render(i['body']), 'implications': render(i['implications']),
                      'themes': i['themes'], 'quotes': i['quotes'], 'status': i['status']} for n, i in enumerate(brief['insights'], 1)],
        'themes': [theme_obj(t) for t in included],
        'outliers': [o for o in spec.get('outliers', [])],
        'excerpts': [{'id': e['id'], 'pid': e['pid'], 'group': e['group'], 'topic': e['topic'], 'tags': e['tags'],
                      'text': e['excerpt'], 'note': e['note'], 'themes': theme_of.get(e['id'], [])} for e in coded.values()],
        'codebook': [{'tag': t, 'definition': defs.get(t, ''), 'excerpts': tag_count[t], 'people': len(tag_people[t])}
                     for t in sorted(tag_count, key=lambda t: -len(tag_people[t]))],
    }
    page = TEMPLATE.read_text(encoding='utf-8')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    page = page.replace('/*__DATA__*/null', payload).replace('__TITLE__', html.escape(brief['title']))
    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding='utf-8')
    print(f'wrote {out} ({out.stat().st_size // 1024} KB): {len(included)} themes, {len(data["insights"])} insights, '
          f'{len(coded)} excerpts, {len(pids)} participants')
    if candidates:
        print('NOTE: includes candidate themes not marked Keep - the report shows a "candidate themes" banner')
    if drafts:
        print(f'NOTE: {len(drafts)} draft item(s) - the report shows "Draft - not reviewed by researcher" on each:')
        for d in drafts:
            print('   -', d)
    for w in dict.fromkeys(warnings):
        print('WARNING:', w)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict(a[2:].split('=', 1) if '=' in a else (a[2:], True) for a in sys.argv[1:] if a.startswith('--'))
    if len(args) != 4:
        print(__doc__); sys.exit(2)
    build(*args, board=opts.get('board'), include_candidates=bool(opts.get('include-candidates')))
