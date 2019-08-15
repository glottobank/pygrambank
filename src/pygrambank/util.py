import collections
import warnings
import re

from csvw import dsv
import openpyxl
import xlrd

GB_COLS = collections.OrderedDict([
    ("Language_ID", ["iso-639-3", "Language", "Glottocode", "glottocode"]),
    ("Feature_ID", ["GramBank ID", "Grambank ID", "\* Feature number", "Grambank"]),
    ("Value", []),
    ("Source", []),
    ("Comment", ["Freetext comment"]),
    ("Feature Domain", ["Possible Values"]),
])


def normalized_feature_id(s):
    if s.isdigit():
        s = "GB" + str(s).zfill(3)
    elif s.startswith("GB") and len(s) != 5:
        s = "GB" + str(s[2:]).zfill(3)
    return s


def normalize_comment(s):
    """
    Normalize comments, turning things like "????" into "?".

    :param s: The original comment
    :return: The normalized comment as string
    """
    if s:
        if set(s) == {'#'}:
            return
        if set(s) == {'?'}:
            return '?'
        return s


def normalized_value(v):
    if v in {
        '?',
        '??',
        'n/a',
        'N/A',
        'n.a.',
        'n.a',
        'N.A.',
        'N.A',
        '-',
        'NODATA',
        '? - Not known'
        '*',
        "*",
        '\\',
        'x',
    }:
        return '?'
    return v


def _normalized_row(row):
    for k in row:
        row[k] = row[k].strip() if row[k] else row[k]

    # Normalize column names:
    if 'Grambank ID' in row and 'Feature_ID' in row:
        row['Feature'] = row.pop('Feature_ID')

    for col, aliases in GB_COLS.items():
        if col not in row:
            for k in list(row.keys()):
                if k in aliases:
                    row[col] = row.pop(k)
                    break
            else:
                row[col] = ''

    # Normalize colum values:
    row['Language_ID'] = None
    row['Feature_ID'] = normalized_feature_id(row['Feature_ID'])
    row['Value'] = normalized_value(row.get('Value'))
    row['Comment'] = normalize_comment(row['Comment'])
    return row


def _read_excel_value(x):
    if x is None:
        return ""
    if type(x) == type(0.0):
        return '{0}'.format(int(x))
    return '{0}'.format(x).strip()


def iter_tsv(fname):
    for row in dsv.reader(fname, delimiter='\t', encoding='utf-8-sig', dicts=True):
        yield _normalized_row(row)


def iter_xlsx(fname):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        sheet = openpyxl.load_workbook(str(fname), data_only=True).active

        header = None
        empty_rows = 0
        skip_cols = set()
        for i, row in enumerate(sheet.rows):
            if i == 0:
                for j, c in enumerate(row):
                    # There's a couple of sheets with > 10,000 columns, labeled with "Column<no>".
                    # We cut these out to reduce TSV bloat.
                    if re.match('Column[0-9]+$', '{0}'.format(c.value)):
                        skip_cols.add(j)
            row = [_read_excel_value(c.value) for j, c in enumerate(row) if j not in skip_cols]
            if set(row) == {''}:  # pragma: no cover
                empty_rows += 1
                if empty_rows > 1000:
                    # There's a couple of sheets with > 100,000 (mostly empty) rows.
                    # After encountering more than 1,000, we stop reading.
                    break
                else:
                    continue
            if header is None:
                header = row
                assert all(bool(c) for c in header), 'Empty column header: {0}'.format(header)
            else:
                assert len(header) == len(row), 'Header and row length mismatch'
                yield _normalized_row(collections.OrderedDict(zip(header, row)))


def iter_xls(fname):
    wb = xlrd.open_workbook(str(fname))
    rows_by_sheetname = collections.defaultdict(list)
    for sheet in wb.sheets():  # We read all sheets in the workbook.
        for row in range(sheet.nrows):
            rows_by_sheetname[sheet.name].append([
                _read_excel_value(sheet.cell_value(row, col))
                for col in range(sheet.ncols)])
    # Now select the proper sheet:
    rows = None
    if len(rows_by_sheetname) > 1:
        for sheetname in ["GramBank", '"Empty" GramBank Sheet']:
            if sheetname in rows_by_sheetname:
                rows = rows_by_sheetname[sheetname]
                break
    else:
        rows = list(rows_by_sheetname.values())[0]
    assert all(bool(c) for c in rows[0]), 'Empty column header'
    for row in rows[1:]:
        yield _normalized_row(collections.OrderedDict(zip(rows[0], row)))


def iter_csv(fname):
    def read(encoding):
        with fname.open(encoding=encoding) as csvfile:
            line = csvfile.readline()
            delimiter = ','
            if ';' in line and ((',' not in line) or (line.index(';') < line.index(','))):
                delimiter = ';'
        for row in dsv.reader(
                fname,
                delimiter=delimiter,
                quotechar='"',
                doublequote=True,
                encoding=encoding,
                dicts=True):
            yield _normalized_row(row)

    try:
        res = list(read('utf-8-sig'))
    except UnicodeDecodeError:  # pragma: no cover
        res = list(read('cp1252'))

    for r in res:
        yield r


def write_tsv(in_, out_, glottocode):
    rows = list({
        '.xlsx': iter_xlsx,
        '.xls': iter_xls,
        '.csv': iter_csv,
        '.tsv': iter_tsv,
    }[in_.suffix](in_))

    with dsv.UnicodeWriter(out_, delimiter='\t') as w:
        for i, row in enumerate(rows):
            if i == 0:
                w.writerow(list(row.keys()))
            row['Language_ID'] = glottocode
            w.writerow(list(row.values()))
