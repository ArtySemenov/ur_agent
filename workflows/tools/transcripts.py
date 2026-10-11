"""Turn raw .docx transcripts into numbered speaker turns.

Used by verify.py so that quotes in a coded spreadsheet can be checked against
the raw data in data/. Nothing is written to disk and data/ is only read.

Turn numbering: speaker turns in order, with consecutive lines from the same
speaker merged and bracketed notes such as [Laughter] kept as their own turn.
"""
import re
import zipfile
import pathlib
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
SPEAKER = re.compile(r'^\s*\[?(Timothy Price|Participant [0-9O]{2})\]?\s*(?::\s*|\s+(?=Yeah))(.*)$', re.I)
NOTE = re.compile(r'\[[^\]]*\]\.?')
# Transcripts whose unlabelled lines are participant answers rather than continuations.
UNLABELLED_IS_PARTICIPANT = {'P07'}


def docx_lines(path):
    root = ET.fromstring(zipfile.ZipFile(path).read('word/document.xml'))
    for p in root.iter(W + 'p'):
        t = ''.join(n.text or '' for n in p.iter(W + 't'))
        if t.strip():
            yield t.strip()


def participant_id(path):
    return 'P' + re.search(r'(\d{2})', pathlib.Path(path).name).group(1)


def turns(path):
    """Return {turn_number: (speaker, text)}; speaker is I, P or N (note)."""
    pid = participant_id(path)
    out = []
    for s in docx_lines(path):
        if s == 'WEBVTT' or re.fullmatch(r'\d+', s) or '-->' in s:
            continue
        m = SPEAKER.match(s)
        if m:
            who, text = ('I' if m.group(1).lower().startswith('timothy') else 'P'), m.group(2).strip()
        elif NOTE.fullmatch(s):
            who, text = 'N', s
        elif pid in UNLABELLED_IS_PARTICIPANT:
            who, text = 'P', s
        else:
            who, text = (out[-1][0] if out else '?'), s
        if not text:
            continue
        if out and out[-1][0] == who:
            out[-1][1] += ' ' + text
        else:
            out.append([who, text])
    return {i: (w, t) for i, (w, t) in enumerate(out, 1)}


def load_all(data_dir):
    return {participant_id(f): turns(f) for f in sorted(pathlib.Path(data_dir).glob('*.docx'))}
