#!/usr/bin/env python3

'''
tpn.py : a BASIC-like program converter for MEGA65 BASIC programs.

Usage:
    tpn.py <tpn.bas >mega65.bas
    tpn.py tpn.bas | petcat -w65 -o myprogram.prg
'''

from dataclasses import dataclass
import re
import sys
import fileinput


@dataclass
class VarDeclare:
    name: str
    init_short: None | str
    array_dim_short: None | str


@dataclass
class Define:
    name: str
    value: None | str


@dataclass
class IfDef:
    def_name: None | str
    is_endif: bool


@dataclass
class Line:
    line_number: None | int
    statement: None | str
    comment: None | str
    label: None | str
    var_declare: None | VarDeclare
    define: None | Define
    if_def: None | IfDef

    def __str__(self):
        if self.statement is None and self.comment is None:
            return ''
        parts = []
        if self.line_number is not None:
            parts.append(str(self.line_number))
        if self.statement is not None:
            parts.append(self.statement)
        if self.comment is not None:
            if self.statement is not None:
                parts.append(':')
            parts.append('rem ' + self.comment.lower())
        return ' '.join(parts)


def parse_line(line):
    # TODO: return None for #output "..."
    # TODO: support line labels
    # TODO: support var declarations, inits, array dims
    # TODO: support define
    # TODO: support ifdef, endif

    # TODO: parse statements into components with var names, string literals
    # TODO: support string literals in statements that contain single quotes
    m = re.match(r'(\d+)?\s*([^\']*)?(\'.*)?', line)
    if m is None:
        return None
    line_num = int(m.group(1)) if m.group(1) else None
    return Line(
        line_number=line_num,
        statement=m.group(2),
        comment=m.group(3))


class TpnGenerator:
    def __init__(self):
        self.cur_line = 100
        self.line_incr = 10
        self.label_line_align = 100
        self.in_false_ifdef = False

    def process_line(self, line_str):
        line = parse_line(line_str)
        if line is None:
            return None

        # TODO: If ifdef, test symbol for definedness; set in_false_ifdef;
        #     return None
        # TODO: If in a false ifdef, watch for endif, otherwise return None
        # TODO: Handle declaration
        # TODO: Handle define
        # TODO: Handle label; adjust cur_line to next label_line_align

        if line.statement is not None:
            # TODO: replace vars with short vars; undeclared var is error
            # TODO: replace defines with values; undefined symbol is error
            pass

        if line.statement is not None or line.comment is not None:
            if line.line_number is None:
                line.line_number = self.cur_line
                self.cur_line += self.line_incr
            else:
                self.cur_line = line.line_number

        return str(line)


def main():
    tpn_generator = TpnGenerator()
    for line in fileinput.input():
        processed_line = tpn_generator.process_line(line)
        sys.stdout.write(processed_line)


if __name__ == "__main__":
    main()
