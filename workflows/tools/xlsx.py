import zipfile, re
from xml.sax.saxutils import escape
def _col(i):
    s = ''
    while i >= 0: s = chr(65 + i % 26) + s; i = i // 26 - 1
    return s
def _esc(v): return escape(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(v)))
def write(path, sheets):
    """sheets: list of (name, rows, widths, opts) ; rows[0] is header."""
    z = zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED)
    n = len(sheets)
    z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' + ''.join(f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(n)) + '</Types>')
    z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    names = ''
    for i, (nm, rows, w, o) in enumerate(sheets):
        if o.get('filter'): names += f'<definedName name="_xlnm._FilterDatabase" localSheetId="{i}" hidden="1">\'{_esc(nm)}\'!$A$1:${_col(len(rows[0])-1)}${len(rows)}</definedName>'
    z.writestr('xl/workbook.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' + ''.join(f'<sheet name="{_esc(s[0])}" sheetId="{i+1}" r:id="rId{i+1}"/>' for i, s in enumerate(sheets)) + '</sheets>' + (f'<definedNames>{names}</definedNames>' if names else '') + '<calcPr fullCalcOnLoad="1"/></workbook>')
    z.writestr('xl/_rels/workbook.xml.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i+1}.xml"/>' for i in range(n)) + f'<Relationship Id="rId{n+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
    z.writestr('xl/styles.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFDDE6F0"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="4"><xf/><xf fontId="1" fillId="2" applyFont="1" applyFill="1"><alignment vertical="top" wrapText="1"/></xf><xf applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="9" applyNumberFormat="1" applyAlignment="1"><alignment vertical="top"/></xf></cellXfs></styleSheet>')
    for i, (nm, rows, widths, o) in enumerate(sheets):
        x = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">']
        if o.get('freeze'): x.append(f'<sheetViews><sheetView workbookViewId="0"><pane xSplit="{o.get("freeze_cols",0)}" ySplit="1" topLeftCell="{_col(o.get("freeze_cols",0))}2" activePane="bottomRight" state="frozen"/></sheetView></sheetViews>')
        hidden = set(o.get('hidden_cols', ()))
        hid = ' hidden="1"'
        x.append('<cols>' + ''.join('<col min="%d" max="%d" width="%s" customWidth="1"%s/>' % (j+1, j+1, w, hid if j in hidden else '') for j, w in enumerate(widths)) + '</cols><sheetData>')
        for r, row in enumerate(rows):
            st = 1 if (r == 0 and o.get('header', True)) else 2
            cells = []
            for c, v in enumerate(row):
                ref = f'{_col(c)}{r+1}'
                st = 3 if (r >= o.get('pct_from_row', 1) and c in o.get('pct_cols', ())) else (1 if (r == 0 and o.get('header', True)) else 2)
                if v is None or v == '': continue
                if isinstance(v, (int, float)) and not isinstance(v, bool): cells.append(f'<c r="{ref}" s="{st}"><v>{v}</v></c>')
                elif isinstance(v, str) and v.startswith('='): cells.append(f'<c r="{ref}" s="{st}"><f>{_esc(v[1:])}</f></c>')
                else: cells.append(f'<c r="{ref}" s="{st}" t="inlineStr"><is><t xml:space="preserve">{_esc(v)}</t></is></c>')
            x.append(f'<row r="{r+1}">' + ''.join(cells) + '</row>')
        x.append('</sheetData>')
        if o.get('filter'): x.append(f'<autoFilter ref="A1:{_col(len(rows[0])-1)}{len(rows)}"/>')
        x.append('</worksheet>')
        z.writestr(f'xl/worksheets/sheet{i+1}.xml', ''.join(x))
    z.close()

_NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
def read(path, sheet_name):
    """Return a sheet as a list of rows (lists of strings). Handles inline and shared strings."""
    from xml.etree import ElementTree as ET
    z = zipfile.ZipFile(path)
    rid = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    target = next(rid[s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
                  for s in wb.iter(_NS + 'sheet') if s.get('name') == sheet_name)
    target = target.lstrip('/').removeprefix('xl/')
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        shared = [''.join(t.text or '' for t in si.iter(_NS + 't')) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).iter(_NS + 'si')]
    rows = []
    for row in ET.fromstring(z.read('xl/' + target)).iter(_NS + 'row'):
        vals = {}
        for c in row.iter(_NS + 'c'):
            col = re.match(r'[A-Z]+', c.get('r')).group(0)
            idx = 0
            for ch in col: idx = idx * 26 + ord(ch) - 64
            if c.get('t') == 'inlineStr': v = ''.join(t.text or '' for t in c.iter(_NS + 't'))
            elif c.get('t') == 's': v = shared[int(c.find(_NS + 'v').text)]
            else: v = c.find(_NS + 'v').text if c.find(_NS + 'v') is not None else ''
            vals[idx - 1] = v
        rows.append([vals.get(j, '') for j in range(max(vals) + 1)] if vals else [])
    return rows
