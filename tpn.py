#!/usr/bin/env python3

'''
tpn.py : a BASIC-like program converter for MEGA65 BASIC programs.

Usage:
    tpn.py <tpn.bas >mega65.bas
    tpn.py tpn.bas | petcat -w65 -o myprogram.prg
'''

from dataclasses import dataclass
import fileinput
import re
import sys
from typing import Optional


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
    line_number: Optional[int] = None
    statement: Optional[str] = None
    comment: Optional[str] = None
    label: Optional[str] = None
    var_declare: Optional[VarDeclare] = None
    define: Optional[Define] = None
    if_def: Optional[IfDef] = None

    def __str__(self):
        parts = []
        if self.line_number is not None:
            parts.append(str(self.line_number))

        statement_str = (self.statement or '').strip()
        if statement_str:
            parts.append(statement_str)

        if self.comment is not None:
            comment_str = self.comment.lower()
            if statement_str:
                parts.append(f":rem {comment_str}")
            else:
                parts.append(f"rem {comment_str}")

        return ' '.join(parts)


def parse_line(line):
    line = line.rstrip()

    m = re.match(r'\s*#output\b.*', line, re.IGNORECASE)
    if m is not None:
        return None

    # TODO: return None for #output "..."
    # TODO: support line labels
    # TODO: support var declarations, inits, array dims
    # TODO: support define
    # TODO: support ifdef, endif

    # TODO: parse statements into components with var names, string literals
    # TODO: support string literals in statements that contain single quotes

    statement = line
    comment = None

    # TODO: this is wrong, but fine for now
    if "'" in line:
        parts = line.rsplit("'", 1)
        statement = parts[0]
        comment = parts[1]

    m = re.match(r'(\d+)?\s*(.*)', statement)
    if m is None:
        return None

    line_num = int(m.group(1)) if m.group(1) else None
    statement = m.group(2)

    return Line(
        line_number=line_num,
        statement=statement,
        comment=comment)


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

        if line.statement is not None and line.statement.strip() == "" and line.comment is None:
            return ""

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
        if processed_line is not None:
            sys.stdout.write(processed_line + '\n')


if __name__ == "__main__":
    main()
