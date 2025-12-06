#!/usr/bin/env python3

'''
tpn.py : an Eleven-like program converter for MEGA65 BASIC programs.

Usage:
    tpn.py <tpn.bas >mega65.bas
    tpn.py tpn.bas | petcat -w65 -o myprogram.prg
'''

from dataclasses import dataclass
import fileinput
import re
from typing import Optional


BASIC65_KEYWORDS = {
    'abs', 'and', 'append', 'asc', 'atn', 'auto',
    'background', 'backup', 'bank', 'begin', 'bend', 'bit',
    'bload', 'boot', 'border', 'box', 'bsave', 'bump',
    'bverify', 'catalog', 'change', 'char', 'chdir', 'circle',
    'close', 'clr', 'cmd', 'collect', 'collision', 'color',
    'concat', 'cont', 'copy', 'cos', 'cursor', 'cut',
    'data', 'dclear', 'dclose', 'dec', 'decbin', 'def',
    'delete', 'dim', 'dir', 'disk', 'dload', 'dma',
    'dmode', 'do', 'dopen', 'dot', 'dpat', 'dsave',
    'dverify', 'ectory', 'edit', 'edma', 'ellipse', 'else',
    'end', 'envelope', 'erase', 'exit', 'exp', 'fast',
    'fgosub', 'fgoto', 'filter', 'find', 'fn', 'font',
    'for', 'foreground', 'format', 'fre', 'freezer', 'gcopy',
    'get', 'go', 'gosub', 'goto', 'graphic', 'hasbit',
    'header', 'help', 'highlight', 'if', 'import', 'info',
    'input', 'instr', 'int', 'joy', 'key', 'len',
    'let', 'line', 'list', 'load', 'loadiff', 'lock',
    'log', 'log10', 'log2', 'loop', 'lpen', 'mem',
    'merge', 'mkdir', 'mod', 'monitor', 'mount', 'mouse',
    'movspr', 'new', 'next', 'not', 'off', 'on',
    'open', 'or', 'paint', 'palette', 'paste', 'peek',
    'pen', 'pixel', 'play', 'pointer', 'poke', 'polygon',
    'pos', 'pot', 'print', 'rcolor', 'rcursor', 'rdisk',
    'read', 'record', 'rem', 'rename', 'renumber', 'restore',
    'resume', 'return', 'rgraphic', 'rmouse', 'rnd', 'rpalette',
    'rpen', 'rplay', 'rreg', 'rspcolor', 'rspeed', 'rsppos',
    'rsprite', 'rsprsys', 'run', 'rwindow', 'save', 'saveiff',
    'scnclr', 'scratch', 'screen', 'set', 'sgn', 'sin',
    'sleep', 'sound', 'speed', 'sprcolor', 'sprite', 'sprsav',
    'sqr', 'step', 'stop', 'sys', 'tan', 'tempo',
    'then', 'to', 'trap', 'troff', 'tron', 'turbo',
    'type', 'unlock', 'until', 'using', 'usr', 'val',
    'verify', 'viewport', 'vol', 'vsync', 'wait', 'while',
    'window', 'wpeek', 'wpoke', 'xor'
}


class TpnError(Exception):
    '''There is an error in the user input.'''
    pass


class Directive:
    '''Base class for directive tokens.'''
    @staticmethod
    def _parse_line(line):
        '''Attempts to parse a source line as a directive.

        Args:
            line: The line string.

        Returns:
            (directive, rest), or (None, None) if the line is not a directive.
        '''
        m = re.match(r'\s*#(\w+)\b(.*)', line, re.IGNORECASE)
        if m is None:
            return None, None

        directive = m.group(1).lower()
        rest = m.group(2).strip()
        return directive, rest


@dataclass
class VarDeclare(Directive):
    '''A variable declaration.

        #declare varName
        #declare varName = <expr>
        #declare varName(<dim>)
    '''
    name: str
    init_short: None | str = None
    array_dim_short: None | str = None

    @classmethod
    def parse_line(cls, line):
        '''Parses a line as a variable declaration.

        Args:
            line: The line string.

        Returns:
            A VarDeclare object, or None if the line is not a variable
            declaration.

        Raises:
            TpnError: Syntax error for a #declare.
        '''
        directive, rest = cls._parse_line(line)
        if directive is None or directive != 'declare':
            return None

        m = re.match(r'(\w+[$%]?)(.*)', rest)
        if m is None:
            raise TpnError('#declare must be followed by a variable name')
        name = m.group(1)
        declare_rest = m.group(2).strip()

        if declare_rest.startswith('='):
            declare_init = declare_rest[1:].strip()
            if declare_init == '':
                raise TpnError(
                    '#declare initializer must be followed by an expression')
            return VarDeclare(name=name, init_short=declare_init)

        m = re.match(r'\((.*)\)$', declare_rest)
        if m is not None:
            dim = m.group(1).strip()
            if dim == '':
                raise TpnError(
                    '#declare array dimension must be followed by '
                    'an expression')
            return VarDeclare(name=name, array_dim_short=dim)

        if declare_rest != '':
            raise TpnError('#declare must be on its own line')

        return VarDeclare(name=name)

    def handle(self, state, last_pass):
        '''Handles a variable declaration.

        Args:
            state: The TpnGenerator state.
            last_pass: Whether this is the last pass.

        Returns:
            Either a handled Line of the initializer or array dimension, or
            None if the declaration does not have an initializer.

        Raises:
            TpnError: Evaluation error, such as a duplicate symbol declaration.
        '''
        if not last_pass and self.name in state.vars:
            raise TpnError(f'Duplicate variable declaration: {self.name}')
        short_name = state.make_var_short(self.name)
        state.vars[self.name] = short_name
        if self.init_short is not None:
            return Line(
                statement=Statement(
                    f'{short_name}={self.init_short}')
                ).handle(state, last_pass)
        elif self.array_dim_short is not None:
            return Line(
                statement=Statement(
                    f'dim {short_name}({self.array_dim_short})')
                ).handle(state, last_pass)
        return None


@dataclass
class Define(Directive):
    '''A constant definition.

        #define SYMBOL
        #define SYMBOL = <literal>
    '''
    name: str
    value: None | str

    @classmethod
    def parse_line(cls, line):
        '''Parses a line as a constant definition.

        Args:
            line: The line string.

        Returns:
            A Define object, or None if the line is not a constant definition.

        Raises:
            TpnError: Syntax error for a #define.
        '''
        directive, rest = cls._parse_line(line)
        if directive is None or directive != 'define':
            return None

        m = re.match(r'(\w+)(.*)', rest)
        if m is None:
            raise TpnError('#define must be followed by a symbol name')
        name = m.group(1)
        define_rest = m.group(2).strip()
        if define_rest == '':
            return Define(name=name, value=None)
        if not define_rest.startswith('='):
            raise TpnError('#define must be followed by an expression')
        value = define_rest[1:].strip()
        return Define(name=name, value=value)

    def handle(self, state, last_pass):
        '''Handles a constant definition.

        Args:
            state: The TpnGenerator state.
            last_pass: Whether this is the last pass.

        Returns:
            None.

        Raises:
            TpnError: Duplicate define symbol.
        '''
        if not last_pass and self.name in state.defines:
            raise TpnError(f'Duplicate define: {self.name}')
        state.defines[self.name] = self.value
        return None


@dataclass
class IfDef(Directive):
    '''An ifdef or endif directive.

        #ifdef SYMBOL
        #endif
    '''
    def_name: None | str
    is_endif: bool

    @classmethod
    def parse_line(cls, line):
        '''Parses a line as an ifdef or endif directive.

        Args:
            line: The line string.

        Returns:
            An IfDef object, or None if the line is not an ifdef or endif.

        Raises:
            TpnError: Syntax error for an #ifdef or #endif.
        '''
        directive, rest = cls._parse_line(line)
        if (directive is None or
                (directive != 'ifdef' and directive != 'endif')):
            return None

        if directive == 'ifdef':
            if rest == '':
                raise TpnError('#ifdef must be followed by a symbol')
            return IfDef(def_name=rest, is_endif=False)

        if rest != '':
            raise TpnError('#endif must be on its own line')
        return IfDef(def_name=None, is_endif=True)

    def handle(self, state, last_pass):
        '''Handles an ifdef or endif directive.

        Args:
            state: The TpnGenerator state.
            last_pass: Whether this is the last pass.

        Returns:
            None.
        '''
        if self.is_endif:
            state.in_false_ifdef = False
        elif self.def_name is None or self.def_name in state.defines:
            state.in_false_ifdef = True
        return None


@dataclass
class Output(Directive):
    '''An output directive.

        #output <filename>

    Output directives are ignored, so no syntax checking is done.
    '''
    @classmethod
    def parse_line(cls, line):
        '''Parses a line as an output directive.

        Args:
            line: The line string.

        Returns:
            An Output object, or None if the line is not an output directive.
        '''
        directive, rest = cls._parse_line(line)
        if directive is None or directive != 'output':
            return None
        return Output()

    def handle(self, state, last_pass):
        '''Handles an output directive.

        Always returns None.
        '''
        # Ignore #output.
        return None


@dataclass
class Statement:
    '''A line of BASIC statements.'''
    full_text: str

    def find_symbols(self):
        return [
            (m.start(), m.end())
            for m in re.finditer(r'\w+[$%]', self.full_text)
            if m.group(0).lower() not in BASIC65_KEYWORDS]

    def to_basic(self, state):
        '''Returns the generated BASIC line string.

        Args:
            state: The TpnGenerator state.

        Returns:
            The generated BASIC line string.
        '''
        symbol_positions = self.find_symbols()
        parts = []
        last_end = 0
        for start, end in symbol_positions:
            sym = self.full_text[start:end]
            replacement = None
            if sym in state.vars:
                replacement = state.vars[sym]
            elif sym in state.defines:
                replacement = state.defines[sym]
            elif sym in state.labels:
                replacement = str(state.labels[sym])
            else:
                raise TpnError(f'Undeclared symbol: {sym}')
            parts.append(self.full_text[last_end:start])
            parts.append(replacement)
            last_end = end

        parts.append(self.full_text[last_end:])
        return ''.join(parts)


@dataclass
class Line:
    '''A source line.

    A source line can contain any combination of a label, a line number, a
    series of statements, and a comment. Every element is optional, but all
    elements must appear in this order.

        .label
        print "hello"
        100 print "hello"
        ' comment
        .label 100 print "hello" : poke 53281,0 ' comment

    The statement list may contain string literals surrounded by double-quote
    characters ("). A string literal may contain a single-quote character (');
    if so, this does not start a comment. The first single-quote that appears
    outside of a string literal starts the line comment, which continues to
    the end of the line.

        print "that's all, folks"  ' this is a comment. it's great.
    '''
    line_number: Optional[int] = None
    statement: Optional[Statement] = None
    comment: Optional[str] = None
    label: Optional[str] = None

    @classmethod
    def parse_line(cls, line):
        '''Parses a line as a source line.

        Args:
            line: The line string.

        Returns:
            A Line object, or None if the line is not a source line.

        Raises:
            TpnError: Syntax error for a source line.
        '''
        line_num = None
        label = None
        statement = None
        comment = None

        m = re.match(r'\s*(\.\w+)(.*)', line)
        if m is not None:
            label = m.group(1)[1:]
            line = m.group(2)

        m = re.match(r'\s*(\d+)(.*)', line)
        if m is not None:
            line_num = int(m.group(1))
            line = m.group(2)

        i = 0
        in_string = False
        while i < len(line):
            if line[i] == '"':
                in_string = not in_string
            elif line[i] == "'" and not in_string:
                break
            i += 1
        statement = Statement(line[:i])
        line = line[i:]

        if line.startswith("'"):
            comment = line[1:]

        return Line(
            line_number=line_num,
            statement=statement,
            comment=comment,
            label=label)

    def handle(self, state, last_pass):
        '''Handles a source line.

        Args:
            state: The TpnGenerator state.
            last_pass: Whether this is the last pass.

        Returns:
            The generated BASIC line string, or None if this Line doesn't
            represent an output line or last_pass is False.
        '''
        if self.line_number is not None:
            state.cur_line = self.line_number

        if self.label is not None:
            if not last_pass and self.label in state.labels:
                raise TpnError(f'Duplicate label: {self.label}')
            state.labels[self.label] = state.cur_line

        if self.statement is None and self.comment is None:
            return None
        self.line_number = state.cur_line
        state.cur_line += state.line_incr

        if last_pass:
            return self.to_basic_string()
        return None

    def to_basic_string(self):
        '''Returns the generated BASIC line string.

        This assumes the Line object properties are fully populated, such as by
        parse_line() or handle().
        '''
        parts = []
        if self.line_number is not None:
            parts.append(str(self.line_number))

        statement_str = self.statement.to_basic(self)
        if statement_str:
            parts.append(statement_str)

        if self.comment is not None:
            comment_str = self.comment.lower()
            if statement_str:
                parts.append(f":rem {comment_str}")
            else:
                parts.append(f"rem {comment_str}")

        return ' '.join(parts)


class TpnGenerator:
    def __init__(self):
        self.defines = dict()
        self.vars = dict()
        self.var_shorts = set()
        self.labels = dict()
        self.tokens = []
        self.reset_state()

    def reset_state(self):
        self.cur_line = 100
        self.line_incr = 10
        self.label_line_align = 100
        self.in_false_ifdef = False

    def make_var_short(self, orig_name):
        if orig_name is None:
            raise TpnError('Variable name must not be None')
        if len(orig_name) == 0:
            raise TpnError('Variable name must not be empty')

        name = orig_name.lower()
        if name.endswith('$') or name.endswith('%'):
            if len(name) <= 1:
                raise TpnError('Variable name must not be a single $ or %')
            suffix = name[-1]
            name = name[:-1]
        else:
            suffix = ''

        if len(name) == 1:
            if name + suffix not in self.var_shorts:
                return name + suffix
            name = name + 'a'

        orig_second = name[1]
        while name + suffix in self.var_shorts:
            if name[0] == 'z':
                new_second = 'a'
            else:
                new_second = chr(ord(orig_second) + 1)
            if new_second == orig_second:
                raise TpnError(
                    'Could not find a short variable name for ' +
                    orig_name)
            name = name[0] + chr(ord(name[1]) + 1)

        self.var_shorts.add(name + suffix)
        return name + suffix

    def tokenize_line(self, line_str):
        line_str = line_str.strip()
        if line_str == '':
            return None

        token = None
        for cls in (VarDeclare, Define, IfDef, Output, Line):
            token = cls.parse_line(line_str)
            if token is not None:
                break

        if token is not None:
            self.tokens.append(token)

    def output_basic(self):
        for token in self.tokens:
            if (not self.in_false_ifdef or
                    (isinstance(token, IfDef) and token.is_endif)):
                token.handle(self, False)

        self.reset_state()
        result = []
        for token in self.tokens:
            output_line = token.handle(self, True)
            if output_line is not None and not self.in_false_ifdef:
                result.append(output_line)

        return '\n'.join(result)


def main():
    tpn_generator = TpnGenerator()
    for line in fileinput.input():
        tpn_generator.tokenize_line(line)
    print(tpn_generator.output_basic())


if __name__ == "__main__":
    main()
