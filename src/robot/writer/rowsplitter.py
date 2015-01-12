#  Copyright 2008-2014 Nokia Solutions and Networks
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import itertools


class RowSplitter(object):
    _comment_mark = '#'
    _empty_cell_escape = '${EMPTY}'
    _line_continuation = '...'
    _setting_table = 'setting'
    _tc_table = 'test case'
    _kw_table = 'keyword'
    _else = 'ELSE'
    _else_if = 'ELSE IF'

    def __init__(self, cols=8, character_count=80, split_multiline_doc=True):
        self._cols = cols
        self._chars = character_count
        self._split_multiline_doc = split_multiline_doc

    def split(self, row, table_type):
        if not row:
            return self._split_empty_row()
        indent = self._get_indent(row, table_type)
        if self._split_multiline_doc and self._is_doc_row(row, table_type):
            return self._split_doc_row(row, indent)
        return self._split_row(row, indent)

    def _split_empty_row(self):
        yield []

    def _get_indent(self, row, table_type):
        indent = len(list(itertools.takewhile(lambda x: x == '', row)))
        min_indent = 1 if table_type in [self._tc_table, self._kw_table] else 0
        return max(indent, min_indent)

    def _is_doc_row(self, row, table_type):
        if table_type == self._setting_table:
            return len(row) > 1 and row[0] == 'Documentation'
        if table_type in [self._tc_table, self._kw_table]:
            return len(row) > 2 and row[1] == '[Documentation]'
        return False

    def _split_doc_row(self, row, indent):
        first, rest = self._split_doc(row[indent+1])
        yield row[:indent+1] + [first] + row[indent+2:]
        while rest:
            current, rest = self._split_doc(rest)
            current = [self._line_continuation, current] if current else [self._line_continuation]
            yield self._indent(current, indent)

    def _split_doc(self, doc):
        if '\\n' not in doc:
            return doc, ''
        if '\\n ' in doc:
            doc = doc.replace('\\n ', '\\n')
        return doc.split('\\n', 1)

    def _split_row(self, row, indent):
        while row:
            current, row = self._split(row)
            yield self._escape_last_empty_cell(current)
            if row and indent + 1 < self._cols:
                row = self._indent(row, indent)

    def _split(self, data):
        row, rest = self._split_else_else_if(data)
        if self._chars and not rest:
            row, rest = self._split_chars(data)
        if not rest:
            row, rest = data[:self._cols], data[self._cols:]
        self._in_comment = any(c.startswith(self._comment_mark) for c in row)
        rest = self._add_line_continuation(rest)
        return row, rest

    def _split_chars(self, data):
        row = []
        data_copy = data[:]
        while (data_copy and len('    '.join(row) + data_copy[0]) < self._chars
               and len(row) < self._cols):
            row.append(data_copy.pop(0))
        rest = data_copy
        return row, rest

    def _split_else_else_if(self, data):
        i = 0
        if self._line_continuation in data:
            cont_index = data.index(self._line_continuation)
            if data[cont_index + 1] in (self._else, self._else_if):
                i = cont_index + 2
        if self._else_if in data[i:]:
            i += data[i:].index(self._else_if)
        elif self._else in data[i:]:
            i += data[i:].index(self._else)
        else:
            return data, []
        return data[:i], data[i:]

    def _add_line_continuation(self, data):
        if data:
            if self._in_comment and not data[0].startswith(self._comment_mark):
                data[0] = self._comment_mark + data[0]
            data = [self._line_continuation] + data
        return data

    def _escape_last_empty_cell(self, row):
        if not row[-1].strip():
            row[-1] = self._empty_cell_escape
        return row

    def _indent(self, row, indent):
        return [''] * indent + row
