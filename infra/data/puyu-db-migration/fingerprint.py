"""Private-only fingerprints for a pinned MySQL 8.4.5 mysqldump format.

Pure Python: no files, SQL execution, processes, connections or printing.
Callers must keep returned DDL/row digests private. This parser is a format and
scope check, not a replacement for a least-privilege SQL importer.
"""
from __future__ import annotations
import hashlib
import re

DATABASES = ('puyu_auth_local', 'puyu_erp_local')
MAX_SQL_BYTES = 64 * 1024 * 1024
SERVER_VERSION = 80405


class FingerprintError(ValueError):
    """Messages are fixed codes, never SQL fragments or business values."""


def _need(ok, code):
    if not ok:
        raise FingerprintError(code)


def _quote_end(text, start):
    quote, i = text[start], start + 1
    while i < len(text):
        char = text[i]
        i += 1
        if ord(char) == 92:
            _need(i < len(text), 'truncated-quote-escape')
            i += 1
        elif char == quote:
            if i < len(text) and text[i] == quote:
                i += 1
            else:
                return i
    raise FingerprintError('unterminated-quote')


def statements(text):
    """Split only top-level semicolons, never Unicode or literal line breaks."""
    start, i = 0, 0
    while i < len(text):
        char, pair = text[i], text[i:i + 2]
        if ord(char) in (39, 34, 96):
            i = _quote_end(text, i)
            continue
        if char == '#' or (pair == '--' and (i + 2 == len(text) or text[i + 2].isspace())):
            end = text.find('\n', i)
            i = len(text) if end < 0 else end + 1
            continue
        if pair == '/*':
            end = text.find('*/', i + 2)
            _need(end >= 0, 'unterminated-comment')
            i = end + 2
            continue
        if char == ';':
            yield text[start:i + 1]
            start = i + 1
        i += 1
    _need(not _effective(text[start:]).strip(), 'unterminated-statement')


def _effective(text):
    """Preserve executable version-comment bodies, including database charset."""
    out, i = [], 0
    while i < len(text):
        char, pair = text[i], text[i:i + 2]
        if ord(char) in (39, 34, 96):
            end = _quote_end(text, i)
            out.append(text[i:end])
            i = end
        elif char == '#' or (pair == '--' and (i + 2 == len(text) or text[i + 2].isspace())):
            end = text.find('\n', i)
            i = len(text) if end < 0 else end + 1
            out.append(' ')
        elif pair == '/*':
            end = text.find('*/', i + 2)
            _need(end >= 0, 'unterminated-comment')
            content = text[i + 2:end]
            if content.startswith('!'):
                match = re.fullmatch(r'!(\d{5,6})\s+(.*)', content, re.S)
                _need(match and int(match[1]) <= SERVER_VERSION, 'unknown-versioned-sql')
                out.extend((' ', match[2], ' '))
            else:
                _need(not content.startswith('+'), 'unsupported-sql-hint')
                out.append(' ')
            i = end + 2
        else:
            out.append(char)
            i += 1
    return ''.join(out)


def _outside_parts(text):
    start, i = 0, 0
    while i < len(text):
        if ord(text[i]) in (39, 34, 96):
            if start < i:
                yield False, text[start:i]
            end = _quote_end(text, i)
            yield True, text[i:end]
            i = start = end
        else:
            i += 1
    if start < len(text):
        yield False, text[start:]


def semantic_ddl(ddl, collations):
    """MySQL bug110825: remove only CS proven redundant by following COLLATE.

    collations is an authoritative server COLLATIONS name -> charset mapping.
    Never guess using prefixes; do not touch any quoted identifier/literal.
    https://bugs.mysql.com/bug.php?id=110825
    https://dev.mysql.com/doc/refman/8.4/en/charset-column.html
    """
    mapping = {key.lower(): value.lower() for key, value in collations.items()}
    def outside(text):
        for match in re.finditer(r'\bCOLLATE\b\s*=?\s*([A-Za-z0-9_]+)\b', text, re.I):
            _need(match[1].lower() in mapping, 'unknown-collation')
        def replace(match):
            _need(mapping.get(match[3].lower()) == match[1].lower(), 'charset-collation-mismatch')
            return match[2]
        return re.sub(r'\bCHARACTER\s+SET\s+([A-Za-z0-9_]+)\s+(COLLATE\s+([A-Za-z0-9_]+)\b)',
                      replace, text, flags=re.I)
    return ''.join(part if quoted else outside(part) for quoted, part in _outside_parts(ddl))


def canonical_ddl(statement, collations=None):
    text = _effective(statement).strip()
    if text.endswith(';'):
        text = text[:-1].rstrip()
    # Collapse whitespace only outside quotes; preserve COMMENT literals exactly.
    out = ''.join(part if quoted else re.sub(r'\s+', ' ', part)
                  for quoted, part in _outside_parts(text)).strip()
    return semantic_ddl(out, collations) if collations is not None else out


def _ident(text, position=0):
    match = re.match(r'\s*`((?:``|[^`])+)`', text[position:])
    if match:
        value = match[1].replace('``', '`')
    else:
        match = re.match(r'\s*([A-Za-z_][A-Za-z0-9_$]*)', text[position:])
        _need(bool(match), 'expected-identifier')
        value = match[1]
    _need('\x00' not in value, 'identifier-nul')
    return value, position + match.end()


def _table(text, current):
    first, end = _ident(text)
    position = end
    while position < len(text) and text[position].isspace():
        position += 1
    if position < len(text) and text[position] == '.':
        second, end = _ident(text, position + 1)
        _need(first == current and first in DATABASES, 'foreign-schema')
        return second, end
    _need(current in DATABASES, 'missing-use-context')
    return first, end


def _code(text):
    return ''.join(' ' if quoted else part for quoted, part in _outside_parts(text))


def _check_references(ddl):
    # REFERENCES db.table is a real cross-schema dependency, even inside CREATE.
    pattern = re.compile(r'\bREFERENCES\b', re.I)
    # Ignore occurrences in COMMENT strings and quoted names; keep offsets.
    masked = ''.join(' ' * len(part) if quoted else part for quoted, part in _outside_parts(ddl))
    for match in pattern.finditer(masked):
        first, end = _ident(ddl, match.end())
        pos = end
        while pos < len(ddl) and ddl[pos].isspace():
            pos += 1
        if pos < len(ddl) and ddl[pos] == '.':
            _need(first in DATABASES, 'foreign-schema-reference')
            _ident(ddl, pos + 1)


def _literal(value):
    value = value.strip()
    _need(bool(value), 'empty-insert-value')
    if re.fullmatch(r'NULL|[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?|0[xX][0-9a-fA-F]*|0[bB][01]+', value):
        return
    match = re.match(r'(?:_[A-Za-z0-9_]+\s*|[xXbB])?([\'\"])', value)
    _need(bool(match), 'nonliteral-insert-value')
    quote_pos = match.end() - 1
    _need(_quote_end(value, quote_pos) == len(value), 'nonliteral-insert-suffix')


def _insert(statement, current):
    match = re.match(r'INSERT\s+INTO\s+', statement, re.I)
    table, end = _table(statement[match.end():], current)
    rest = statement[match.end() + end:].lstrip()
    _need(rest.startswith('('), 'complete-insert-required')
    columns, i = [], 1
    while True:
        column, i = _ident(rest, i)
        _need(column not in columns, 'duplicate-insert-column')
        columns.append(column)
        while i < len(rest) and rest[i].isspace():
            i += 1
        _need(i < len(rest), 'insert-column-list')
        if rest[i] == ')':
            i += 1
            break
        _need(rest[i] == ',', 'insert-column-list')
        i += 1
    values = rest[i:].strip()
    match = re.match(r'VALUES\s*\(', values, re.I)
    _need(bool(match), 'insert-values-required')
    i, start, tokens = match.end(), match.end(), []
    while i < len(values):
        char = values[i]
        if ord(char) in (39, 34, 96):
            _need(ord(char) != 96, 'identifier-in-values')
            i = _quote_end(values, i)
            continue
        _need(char != '(', 'nonliteral-value-expression')
        if char in ',)':
            tokens.append(values[start:i])
            _literal(tokens[-1])
            if char == ')':
                _need(values[i + 1:].strip() == ';', 'single-row-insert-required')
                _need(len(tokens) == len(columns), 'insert-value-width')
                return table, columns
            start = i + 1
        i += 1
    raise FingerprintError('unterminated-insert-values')


def fingerprint(sql, *, collations=None, max_bytes=MAX_SQL_BYTES):
    _need(type(sql) is bytes and 0 < len(sql) <= min(max_bytes, MAX_SQL_BYTES), 'sql-input-size')
    _need(b'\x00' not in sql, 'raw-nul-in-dump')
    try:
        text = sql.decode('utf-8')
    except UnicodeDecodeError:
        raise FingerprintError('dump-utf8') from None
    result = {'version': 1, 'databases': {}}
    current, lock_table = None, None
    row_hashes = {}
    for original in statements(text):
        effective = _effective(original).strip()
        if not effective or effective == ';':
            continue
        code = _code(effective)
        _need(code.rstrip().endswith(';') and code.count(';') == 1, 'compound-executable-statement')
        if re.match(r'^SET\b', effective, re.I):
            _need(not any(quoted and part.startswith('`') for quoted, part in _outside_parts(effective)),
                  'quoted-set-identifier')
            _need(not re.search(r'\b(?:GLOBAL|PERSIST|PERSIST_ONLY|SQL_LOG_BIN|GTID_PURGED|PASSWORD|ROLE|SELECT|OUTFILE|LOAD_FILE)\b', code, re.I)
                  and '(' not in code, 'unsafe-set-statement')
            if not re.fullmatch(r'SET\s+NAMES\s+[A-Za-z0-9_]+(?:\s+COLLATE\s+[A-Za-z0-9_]+)?\s*;', effective, re.I):
                variables = {'CHARACTER_SET_CLIENT', 'CHARACTER_SET_RESULTS', 'COLLATION_CONNECTION',
                             'TIME_ZONE', 'UNIQUE_CHECKS', 'FOREIGN_KEY_CHECKS', 'SQL_MODE', 'SQL_NOTES'}
                allowed = variables | {'OLD_' + name for name in variables} | {'SET', 'SESSION', 'LOCAL', 'SAVED_CS_CLIENT', 'UTF8MB4', 'UTF8MB3', 'UTF8', 'LATIN1', 'BINARY'}
                _need(set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', code.upper())) <= allowed,
                      'unsupported-set-variable')
            continue
        match = re.match(r'^CREATE\s+DATABASE\s+(?:IF\s+NOT\s+EXISTS\s+)?', effective, re.I)
        if match:
            db, end = _ident(effective, match.end())
            _need(db in DATABASES and db not in result['databases'], 'database-scope-or-duplicate')
            tail = _code(effective[end:])
            _need(not re.search(r'\b(?:SELECT|USE|DROP|CREATE|GRANT)\b', tail, re.I), 'unsafe-database-options')
            result['databases'][db] = {'create_database': canonical_ddl(effective, collations), 'tables': {}}
            continue
        match = re.match(r'^USE\s+', effective, re.I)
        if match:
            db, end = _ident(effective, match.end())
            _need(db in DATABASES and db in result['databases'] and effective[end:].strip() == ';', 'use-scope')
            _need(lock_table is None, 'use-with-table-lock')
            current = db
            continue
        _need(current in result['databases'], 'statement-before-database')
        tables = result['databases'][current]['tables']
        match = re.match(r'^DROP\s+TABLE\s+IF\s+EXISTS\s+', effective, re.I)
        if match:
            table, end = _table(effective[match.end():], current)
            _need(effective[match.end() + end:].strip() == ';' and table not in tables, 'unsafe-drop-table')
            continue
        match = re.match(r'^CREATE\s+TABLE\s+', effective, re.I)
        if match:
            table, end = _table(effective[match.end():], current)
            tail = effective[match.end() + end:].lstrip()
            _need(table not in tables and tail.startswith('(')
                  and re.search(r'\bENGINE\s*=\s*InnoDB\b', _code(tail), re.I)
                  and not re.search(r'\b(?:SELECT|DEFINER|OUTFILE)\b', _code(tail), re.I), 'unsupported-create-table')
            _check_references(effective)
            tables[table] = {'create_table': canonical_ddl(effective, collations),
                             'insert_columns': None, 'row_count': 0, 'row_multiset_sha256': None}
            row_hashes[current, table] = []
            continue
        match = re.match(r'^INSERT\s+INTO\s+', effective, re.I)
        if match:
            table, columns = _insert(effective, current)
            _need(table in tables and (lock_table is None or lock_table == (current, table)), 'insert-table-scope')
            meta = tables[table]
            _need(meta['insert_columns'] is None or meta['insert_columns'] == columns, 'insert-column-order')
            meta['insert_columns'] = columns
            meta['row_count'] += 1
            # Original statement bytes, no decoding of JSON/blob/decimal values.
            row_hashes[current, table].append(hashlib.sha256(original.strip().encode('utf-8')).digest())
            continue
        match = re.match(r'^LOCK\s+TABLES\s+', effective, re.I)
        if match:
            table, end = _table(effective[match.end():], current)
            _need(table in tables and lock_table is None
                  and re.fullmatch(r'\s+WRITE\s*;', effective[match.end() + end:], re.I), 'table-lock-scope')
            lock_table = current, table
            continue
        if re.fullmatch(r'UNLOCK\s+TABLES\s*;', effective, re.I):
            _need(lock_table is not None, 'unmatched-unlock')
            lock_table = None
            continue
        match = re.match(r'^ALTER\s+TABLE\s+', effective, re.I)
        if match:
            table, end = _table(effective[match.end():], current)
            _need(table in tables and re.fullmatch(r'\s+(?:ENABLE|DISABLE)\s+KEYS\s*;',
                  effective[match.end() + end:], re.I), 'unsupported-alter-table')
            continue
        raise FingerprintError('unsupported-statement')
    _need(set(result['databases']) == set(DATABASES) and lock_table is None, 'incomplete-dump-scope')
    for db, entry in result['databases'].items():
        for table, meta in entry['tables'].items():
            hashes = row_hashes[db, table]
            payload = b'puyu-sql-row-multiset-v1\0' + len(hashes).to_bytes(8, 'big') + b''.join(sorted(hashes))
            meta['row_multiset_sha256'] = hashlib.sha256(payload).hexdigest()
    return result
