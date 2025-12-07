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
import sys
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
    def __init__(self, message='', filename='<no file>', filelineno=0):
        super().__init__(message)
        self.message = message
        self.filename = filename
        self.filelineno = filelineno

    def __str__(self):
        return f'{self.filename}:{self.filelineno} {self.message}'


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
    src_filename: None | str = None
    src_filelineno: None | str = None

    @classmethod
    def parse_line(cls, line, filename='<no file>', filelineno=0):
        '''Parses a line as a variable declaration.

        Args:
            line: The line string.
            filename: The name of the file being read (per fileinput).
            filelineno: The number of the line of the file being read.

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
            raise TpnError(
                '#declare must be followed by a variable name',
                filename, filelineno)
        name = m.group(1)
        declare_rest = m.group(2).strip()

        if declare_rest.startswith('='):
            declare_init = declare_rest[1:].strip()
            if declare_init == '':
                raise TpnError(
                    '#declare initializer must be followed by an expression',
                    filename, filelineno)
            return VarDeclare(name=name, init_short=declare_init)

        m = re.match(r'\((.*)\)$', declare_rest)
        if m is not None:
            dim = m.group(1).strip()
            if dim == '':
                raise TpnError(
                    '#declare array dimension must be followed by '
                    'an expression',
                    filename, filelineno)
            return VarDeclare(name=name, array_dim_short=dim)

        if declare_rest != '':
            raise TpnError(
                '#declare must be on its own line',
                filename, filelineno)

        return VarDeclare(
            name=name,
            src_filename=filename,
            src_filelineno=filelineno)

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
        if not last_pass:
            if self.name in state.vars:
                raise TpnError(
                    f'Duplicate variable declaration: {self.name}',
                    self.src_filename, self.src_filelineno)
            try:
                short_name = state.make_var_short(self.name)
            except TpnError as e:
                e.filename = self.src_filename
                e.filelineno = self.src_filelineno
                raise
            state.vars[self.name] = short_name
        if self.init_short is not None:
            return Line(
                statement=Statement(
                    f'{self.name}={self.init_short}')
                ).handle(state, last_pass)
        elif self.array_dim_short is not None:
            return Line(
                statement=Statement(
                    f'dim {self.name}({self.array_dim_short})')
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
    src_filename: None | str = None
    src_filelineno: None | str = None

    @classmethod
    def parse_line(cls, line, filename='<no file>', filelineno=0):
        '''Parses a line as a constant definition.

        Args:
            line: The line string.
            filename: The name of the file being read (per fileinput).
            filelineno: The number of the line of the file being read.

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
            raise TpnError(
                '#define must be followed by a symbol name',
                filename, filelineno)
        name = m.group(1)
        define_rest = m.group(2).strip()
        if define_rest == '':
            return Define(
                name=name,
                value=None,
                src_filename=filename,
                src_filelineno=filelineno)
        if not define_rest.startswith('='):
            raise TpnError(
                '#define must be followed by an expression',
                filename, filelineno)
        value = define_rest[1:].strip()
        return Define(
            name=name,
            value=value,
            src_filename=filename,
            src_filelineno=filelineno)

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
            raise TpnError(
                f'Duplicate define: {self.name}',
                self.src_filename, self.src_filelineno)
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
    src_filename: None | str = None
    src_filelineno: None | str = None

    @classmethod
    def parse_line(cls, line, filename='<no file>', filelineno=0):
        '''Parses a line as an ifdef or endif directive.

        Args:
            line: The line string.
            filename: The name of the file being read (per fileinput).
            filelineno: The number of the line of the file being read.

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
                raise TpnError(
                    '#ifdef must be followed by a symbol',
                    filename, filelineno)
            return IfDef(
                def_name=rest,
                is_endif=False,
                src_filename=filename,
                src_filelineno=filelineno)

        if rest != '':
            raise TpnError(
                '#endif must be on its own line',
                filename, filelineno)
        return IfDef(
            def_name=None,
            is_endif=True,
            src_filename=filename,
            src_filelineno=filelineno)

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
        elif self.def_name is None or self.def_name not in state.defines:
            state.in_false_ifdef = True
        return None


@dataclass
class Output(Directive):
    '''An output directive.

        #output <filename>

    Output directives are ignored, so no syntax checking is done.
    '''
    @classmethod
    def parse_line(cls, line, filename='<no file>', filelineno=0):
        '''Parses a line as an output directive.

        Args:
            line: The line string.
            filename: The name of the file being read (per fileinput).
            filelineno: The number of the line of the file being read.

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
        '''Locates all symbols in the statement text.

        A symbol is:
        * One or more word characters followed by an optional $ or %
        * Outside a pair of double-quotes, or before an unpaired double-quote
        * Not in the BASIC65_KEYWORDS set when lowercased

        Returns:
            A list of (start, end) index pairs of symbols in the text.
        '''
        quote_pairs = [
            (m.start(), m.end())
            for m in re.finditer(r'"[^"]*"', self.full_text)]
        candidates = [
            (m.start(), m.end())
            for m in re.finditer(r'[a-zA-Z_]\w*[$%]?', self.full_text)
            if m.group(0).lower() not in BASIC65_KEYWORDS]
        symbols = []
        for c in candidates:
            for q in quote_pairs:
                if q[0] < c[0] < q[1]:
                    break
            else:
                symbols.append(c)
        return symbols

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
    src_filename: None | str = None
    src_filelineno: None | str = None

    @classmethod
    def parse_line(cls, line, filename='<no file>', filelineno=0):
        '''Parses a line as a source line.

        Args:
            line: The line string.
            filename: The name of the file being read (per fileinput).
            filelineno: The number of the line of the file being read.

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
            label=label,
            src_filename=filename,
            src_filelineno=filelineno)

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
                raise TpnError(
                    f'Duplicate label: {self.label}',
                    self.src_filename, self.src_filelineno)
            state.labels[self.label] = state.cur_line

        if self.statement.full_text.strip() == '' and self.comment is None:
            return None
        self.line_number = state.cur_line
        state.cur_line += state.line_incr

        if last_pass:
            return self.to_basic_string(state)
        return None

    def to_basic_string(self, state):
        '''Returns the generated BASIC line string.

        This assumes the Line object properties are fully populated, such as by
        parse_line() or handle().
        '''
        parts = []
        if self.line_number is not None:
            parts.append(str(self.line_number))

        try:
            statement_str = self.statement.to_basic(state)
        except TpnError as e:
            e.filename = self.src_filename
            e.filelineno = self.src_filelineno
            raise
        if statement_str:
            parts.append(statement_str)

        if self.comment is not None:
            comment_str = self.comment.lower()
            if not comment_str.startswith(' '):
                # (Preserve intentional spaces, but don't conjoin "rem" with
                # comment text.)
                comment_str = ' ' + comment_str
            if statement_str:
                parts.append(f":rem{comment_str}")
            else:
                parts.append(f"rem{comment_str}")

        return ' '.join(parts)


class TpnGenerator:
    '''Stateful BASIC converter.

    To use, follow these steps:

    1. Call generator.tokenize_line(line_str) on each input source line in
       order.
    2. Call generator.output_basic(). This returns the converted BASIC output.
    '''
    def __init__(self):
        self.defines = dict()
        self.vars = dict()
        self.var_shorts = set()
        self.labels = dict()
        self.tokens = []
        self.reset_state()

    def reset_state(self):
        '''Resets the state for the next pass.'''
        self.cur_line = 100
        self.line_incr = 10
        self.label_line_align = 100
        self.in_false_ifdef = False

    def make_var_short(self, orig_name):
        '''Create and register a short name for a declared variable.

        orig_name can be a name of any length, followed by an optional $ or %.
        orig_name always starts with a letter. The short name is one or two
        lowercase letters, followed by the optional $ or % if it was provided
        on orig_name.

        All short names are unique across the entire program. make_var_short
        attempts to use the first two letters of orig_name, or just orig_name
        if it has one letter. If such a short name has already been
        registered, the second letter is incremented, wrapping around from 'z'
        to 'a', until an unused option is found. If all 26 letter options are
        found, it raises a TpnError.

        Args:
            orig_name: The original name of the variable.

        Returns:
            The short variable name.

        Raises:
            TpnError: Could not find a short variable name for the variable.
        '''
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

        # Assign a BASIC-compatible variable name. If the first two characters
        # of the original name are available, use them for the short name.
        short_name = name[0:2]
        if short_name + suffix not in self.var_shorts:
            self.var_shorts.add(short_name + suffix)
            return short_name + suffix

        # Short name in use. Search for an alternate.
        # One-char names start with an 'a' as the second letter.
        # Two-char names start with their first two characters.
        # If the original second character is a number, start at 'a'.
        if len(name) == 1:
            short_name = name + 'a'
        if short_name[1] in '0123456789':
            short_name = short_name[0] + 'a'

        # Search for replacements by iterating the second letter. This is
        # limited to 25 possible alternate short names per starting letter,
        # per type. (This could be extended to include numbers, if needed.)
        # This doesn't use a separate namespace for arrays as BASIC does, so
        # that's another opportunity to expand.
        start_char = short_name[1]
        while short_name + suffix in self.var_shorts:
            if short_name[1] == 'z':
                short_name = short_name[0] + 'a'
            else:
                short_name = short_name[0] + chr(ord(short_name[1]) + 1)
            if short_name[1] == start_char:
                raise TpnError(
                    'Could not find a short variable name for ' +
                    orig_name)
        self.var_shorts.add(short_name + suffix)
        return short_name + suffix

    def tokenize_line(self, line_str, filename='<no file>', filelineno=0):
        '''Tokenizes a line of input source, and stores it in the state.

        Args:
            line_str: The line string.
            filename: The name of the file being read (per fileinput).
            filelineno: The number of the line of the file being read.

        Raises:
            TpnError: Syntax error for a source line.
        '''
        line_str = line_str.strip()
        if line_str == '':
            return

        token = None
        for cls in (VarDeclare, Define, IfDef, Output, Line):
            token = cls.parse_line(line_str, filename, filelineno)
            if token is not None:
                break

        if token is not None:
            self.tokens.append(token)

    def output_basic(self):
        '''Returns the generated BASIC output.

        The routine makes two passes over the registered token list to resolve
        forward references to labels.

        Returns:
            The generated BASIC output.

        Raises:
            TpnError: An error was detected in the input.
        '''
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
    try:
        tpn_generator = TpnGenerator()
        with fileinput.input() as fi:
            for line in fi:
                tpn_generator.tokenize_line(
                    line,
                    fi.filename(),
                    fi.filelineno())

        print(tpn_generator.output_basic())

    except TpnError as e:
        sys.stderr.write(str(e) + '\n')
        sys.exit(1)


if __name__ == "__main__":
    main()
