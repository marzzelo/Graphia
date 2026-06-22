"""Shared CSV parsing utilities for importing plugins."""
import json
from datetime import datetime

DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S.%f",
    "%Y/%m/%d %H:%M:%S",
    "%d-%m-%Y %H:%M:%S.%f",
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S.%f",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%H:%M:%S.%f",
    "%H:%M:%S",
]


def read_comment_header(file_path):
    """
    Counts leading comment rows (lines starting with '#') and parses the first
    comment line as JSON.  Returns (n_comment_rows, rate_hz_or_None, start_utc_or_None).
    """
    n_comments = 0
    rate_hz = None
    start_utc = None
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            for line in f:
                stripped = line.rstrip('\n\r')
                if stripped.startswith('#'):
                    if n_comments == 0:
                        try:
                            data = json.loads(stripped[1:].strip())
                            if isinstance(data, dict):
                                if 'rate_hz' in data:
                                    rate_hz = float(data['rate_hz'])
                                if 'start_utc' in data:
                                    start_utc = str(data['start_utc'])
                        except (ValueError, KeyError, TypeError):
                            pass
                    n_comments += 1
                else:
                    break
    except Exception:
        pass
    return n_comments, rate_hz, start_utc


def try_parse_datetime(value):
    """Attempts to parse a value as datetime. Returns datetime or None."""
    value = value.strip().strip('"').strip("'")
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def try_parse_number(value, separator):
    """Attempts to parse a value as float. Returns float or None."""
    value = value.strip().strip('"').strip("'")
    try:
        return float(value)
    except ValueError:
        pass
    if separator != ',':
        try:
            return float(value.replace(',', '.'))
        except ValueError:
            pass
    return None


def detect_separator(file_path, has_header, skip_rows=0):
    """Automatically detects the CSV field separator."""
    separators = [',', ';', '\t', '|']
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        all_lines = []
        for i, line in enumerate(f):
            if i >= 6 + skip_rows:
                break
            all_lines.append(line.rstrip('\n\r'))
    if not all_lines:
        return ','
    all_lines = all_lines[skip_rows:]
    if not all_lines:
        return ','
    # Skip header — it may have a different column count than data rows
    lines = all_lines[1:] if has_header and len(all_lines) > 1 else all_lines
    best_sep, best_count = ',', 0
    for sep in separators:
        counts = [line.count(sep) for line in lines if line]
        if counts and min(counts) > 0 and max(counts) == min(counts):
            if counts[0] > best_count:
                best_count = counts[0]
                best_sep = sep
    return best_sep


def detect_column_types(file_path, has_header, separator, skip_rows=0):
    """
    Detects column types ('numeric', 'datetime', 'ignore') by sampling data rows.
    Returns (headers, column_types, n_cols).
    """
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        lines = [line.rstrip('\n\r') for line in f if line.strip()]
    if not lines:
        raise ValueError("File is empty")
    lines = lines[skip_rows:]
    if not lines:
        raise ValueError("No data after skipped rows")
    start_idx = 0
    headers = None
    if has_header:
        headers = [h.strip().strip('"').strip("'") for h in lines[0].split(separator)]
        start_idx = 1
    if start_idx >= len(lines):
        raise ValueError("No data after header")
    first_data = lines[start_idx].split(separator)
    n_cols = len(first_data)
    if headers is None:
        headers = [str(i) for i in range(n_cols)]
    sample = lines[start_idx:start_idx + min(10, len(lines) - start_idx)]
    column_types = []
    for col_idx in range(n_cols):
        num_c = dt_c = empty_c = 0
        for line in sample:
            parts = line.split(separator)
            if col_idx >= len(parts):
                continue
            v = parts[col_idx].strip().strip('"').strip("'")
            if not v:
                empty_c += 1
                continue
            if try_parse_number(v, separator) is not None:
                num_c += 1
            elif try_parse_datetime(v) is not None:
                dt_c += 1
        total = len(sample) - empty_c
        if total > 0:
            if num_c >= total * 0.8:
                column_types.append('numeric')
            elif dt_c >= total * 0.8:
                column_types.append('datetime')
            else:
                column_types.append('ignore')
        else:
            column_types.append('ignore')
    return headers, column_types, n_cols


def count_data_rows(file_path, has_header, skip_rows=0):
    """Count the total number of data rows in the file."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        lines = [line.strip() for line in f if line.strip()]
    start_idx = skip_rows + (1 if has_header else 0)
    return max(0, len(lines) - start_idx)
