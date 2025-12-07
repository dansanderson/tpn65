import io
import unittest
from unittest.mock import patch, MagicMock
from tpn import Statement, TpnGenerator, Line, VarDeclare, TpnError, Define
from tpn import IfDef, Output, main


class TestStatement(unittest.TestCase):
    def test_to_basic(self):
        statement = Statement("print \"hello\"")
        state = TpnGenerator()
        self.assertEqual(statement.to_basic(state), "print \"hello\"")

    def test_find_symbols(self):
        statement = Statement("a$ = b$")
        self.assertEqual(statement.find_symbols(), [(0, 2), (5, 7)])

    def test_find_symbols_with_quotes(self):
        statement = Statement("print \"hello\"")
        self.assertEqual(statement.find_symbols(), [])


class TestStatementToBasic(unittest.TestCase):
    def test_replace_var(self):
        statement = Statement("a$ = b$")
        state = TpnGenerator()
        state.vars = {"a$": "a$", "b$": "b$"}
        self.assertEqual(statement.to_basic(state), "a$ = b$")

    def test_replace_define(self):
        statement = Statement("a = FOO")
        state = TpnGenerator()
        state.vars = {"a": "a"}
        state.var_shorts = {"a"}
        state.defines = {"FOO": "123"}
        self.assertEqual(statement.to_basic(state), "a = 123")

    def test_replace_label(self):
        statement = Statement("goto label")
        state = TpnGenerator()
        state.labels = {"label": 1000}
        self.assertEqual(statement.to_basic(state), "goto 1000")


class TestLine(unittest.TestCase):
    def test_parse_line_statement(self):
        line = Line.parse_line("print \"hello\"")
        self.assertEqual(line.statement.full_text, "print \"hello\"")
        self.assertIsNone(line.label)
        self.assertIsNone(line.line_number)
        self.assertIsNone(line.comment)

    def test_parse_line_label_statement(self):
        line = Line.parse_line(".label print \"hello\"")
        self.assertEqual(line.label, "label")
        self.assertEqual(line.statement.full_text, " print \"hello\"")
        self.assertIsNone(line.line_number)
        self.assertIsNone(line.comment)

    def test_parse_line_line_number_statement(self):
        line = Line.parse_line("100 print \"hello\"")
        self.assertEqual(line.line_number, 100)
        self.assertEqual(line.statement.full_text, " print \"hello\"")
        self.assertIsNone(line.label)
        self.assertIsNone(line.comment)

    def test_parse_line_label_line_number_statement(self):
        line = Line.parse_line(".label 100 print \"hello\"")
        self.assertEqual(line.label, "label")
        self.assertEqual(line.line_number, 100)
        self.assertEqual(line.statement.full_text, " print \"hello\"")
        self.assertIsNone(line.comment)

    def test_parse_line_statement_comment(self):
        line = Line.parse_line("print \"hello\" ' comment")
        self.assertEqual(line.statement.full_text, "print \"hello\" ")
        self.assertEqual(line.comment, " comment")
        self.assertIsNone(line.label)
        self.assertIsNone(line.line_number)

    def test_parse_line_label_line_number_statement_comment(self):
        line = Line.parse_line(".label 100 print \"hello\" ' comment")
        self.assertEqual(line.label, "label")
        self.assertEqual(line.line_number, 100)
        self.assertEqual(line.statement.full_text, " print \"hello\" ")
        self.assertEqual(line.comment, " comment")

    def test_parse_line_label_only(self):
        line = Line.parse_line(".label")
        self.assertEqual(line.label, "label")
        self.assertEqual(line.statement.full_text, "")
        self.assertIsNone(line.line_number)
        self.assertIsNone(line.comment)

    def test_parse_line_comment_only(self):
        line = Line.parse_line("' comment")
        self.assertEqual(line.comment, " comment")
        self.assertEqual(line.statement.full_text, "")
        self.assertIsNone(line.label)
        self.assertIsNone(line.line_number)

    def test_handle(self):
        state = TpnGenerator()
        line = Line(statement=Statement("print \"hello\""))
        self.assertEqual(line.handle(state, True), "100 print \"hello\"")
        self.assertEqual(state.cur_line, 110)

    def test_handle_with_line_number(self):
        state = TpnGenerator()
        line = Line(line_number=200, statement=Statement("print \"hello\""))
        self.assertEqual(line.handle(state, True), "200 print \"hello\"")
        self.assertEqual(state.cur_line, 210)

    def test_handle_with_label(self):
        state = TpnGenerator()
        line = Line(label="label", statement=Statement("print \"hello\""))
        self.assertEqual(line.handle(state, True), "100 print \"hello\"")
        self.assertEqual(state.labels["label"], 100)
        self.assertEqual(state.cur_line, 110)

    def test_line_with_label_only_no_output(self):
        state = TpnGenerator()
        line = Line.parse_line(".label")
        self.assertIsNone(line.handle(state, False))
        self.assertIsNone(line.handle(state, True))

    def test_comment_with_statement(self):
        state = TpnGenerator()
        line = Line.parse_line("print 1 ' comment")
        self.assertEqual(
            line.handle(state, True),
            "100 print 1  :rem comment")

    def test_comment_without_statement(self):
        state = TpnGenerator()
        line = Line.parse_line("' comment")
        self.assertEqual(line.handle(state, True), "100 rem comment")

    def test_parse_empty_string(self):
        state = TpnGenerator()
        line = Line.parse_line("")
        self.assertIsNone(line.handle(state, True))


class TestVarDeclare(unittest.TestCase):
    def test_parse_line(self):
        var_declare = VarDeclare.parse_line("#declare varName")
        self.assertEqual(var_declare.name, "varName")
        self.assertIsNone(var_declare.init_short)
        self.assertIsNone(var_declare.array_dim_short)

    def test_parse_line_with_initializer(self):
        var_declare = VarDeclare.parse_line("#declare varName = 123")
        self.assertEqual(var_declare.name, "varName")
        self.assertEqual(var_declare.init_short, "123")
        self.assertIsNone(var_declare.array_dim_short)

    def test_parse_line_with_array_dim(self):
        var_declare = VarDeclare.parse_line("#declare varName(10)")
        self.assertEqual(var_declare.name, "varName")
        self.assertIsNone(var_declare.init_short)
        self.assertEqual(var_declare.array_dim_short, "10")

    def test_parse_line_no_var_name(self):
        with self.assertRaises(TpnError):
            VarDeclare.parse_line("#declare")

    def test_parse_line_empty_initializer(self):
        with self.assertRaises(TpnError):
            VarDeclare.parse_line("#declare varName =")

    def test_parse_line_empty_array_dim(self):
        with self.assertRaises(TpnError):
            VarDeclare.parse_line("#declare varName()")

    def test_parse_line_extra_tokens(self):
        with self.assertRaises(TpnError):
            VarDeclare.parse_line("#declare varName foo")

    def test_handle(self):
        state = TpnGenerator()
        var_declare = VarDeclare(name="varName")
        var_declare.handle(state, False)
        self.assertEqual(state.vars["varName"], "va")

    def test_handle_with_initializer(self):
        state = TpnGenerator()
        var_declare = VarDeclare(name="varName", init_short="123")
        var_declare.handle(state, False)
        state.reset_state()
        line = var_declare.handle(state, True)
        self.assertEqual(state.vars["varName"], "va")
        self.assertEqual(line, "100 va=123")

    def test_handle_with_array_dim(self):
        state = TpnGenerator()
        var_declare = VarDeclare(name="varName", array_dim_short="10")
        var_declare.handle(state, False)
        state.reset_state()
        line = var_declare.handle(state, True)
        self.assertEqual(state.vars["varName"], "va")
        self.assertEqual(line, "100 dim va(10)")


class TestDefine(unittest.TestCase):
    def test_parse_line(self):
        define = Define.parse_line("#define SYMBOL")
        self.assertEqual(define.name, "SYMBOL")
        self.assertIsNone(define.value)

    def test_parse_line_with_value(self):
        define = Define.parse_line("#define SYMBOL = 123")
        self.assertEqual(define.name, "SYMBOL")
        self.assertEqual(define.value, "123")

    def test_parse_line_no_symbol(self):
        with self.assertRaises(TpnError):
            Define.parse_line("#define")

    def test_parse_line_stuff_after_symbol(self):
        with self.assertRaises(TpnError):
            Define.parse_line("#define SYMBOL foo")

    def test_parse_line_empty_value(self):
        define = Define.parse_line("#define SYMBOL = ")
        self.assertEqual(define.name, "SYMBOL")
        self.assertEqual(define.value, "")

    def test_handle(self):
        state = TpnGenerator()
        define = Define(name="SYMBOL", value="123")
        define.handle(state, False)
        self.assertEqual(state.defines["SYMBOL"], "123")

    def test_non_duplicate_define(self):
        state = TpnGenerator()
        define1 = Define(name="SYMBOL1", value="123")
        define2 = Define(name="SYMBOL2", value="456")
        define1.handle(state, False)
        define2.handle(state, False)
        self.assertEqual(len(state.defines), 2)

    def test_duplicate_define(self):
        state = TpnGenerator()
        define1 = Define(name="SYMBOL", value="123")
        define2 = Define(name="SYMBOL", value="456")
        define1.handle(state, False)
        with self.assertRaises(TpnError):
            define2.handle(state, False)


class TestIfDef(unittest.TestCase):
    def test_parse_line_ifdef(self):
        if_def = IfDef.parse_line("#ifdef SYMBOL")
        self.assertEqual(if_def.def_name, "SYMBOL")
        self.assertFalse(if_def.is_endif)

    def test_parse_line_endif(self):
        if_def = IfDef.parse_line("#endif")
        self.assertIsNone(if_def.def_name)
        self.assertTrue(if_def.is_endif)

    def test_parse_line_no_symbol(self):
        with self.assertRaises(TpnError):
            IfDef.parse_line("#ifdef")

    def test_parse_line_extra_tokens(self):
        with self.assertRaises(TpnError):
            IfDef.parse_line("#endif foo")

    def test_handle_ifdef_defined(self):
        state = TpnGenerator()
        state.defines["SYMBOL"] = None
        if_def = IfDef(def_name="SYMBOL", is_endif=False)
        if_def.handle(state, False)
        self.assertFalse(state.in_false_ifdef)

    def test_handle_ifdef_undefined(self):
        state = TpnGenerator()
        if_def = IfDef(def_name="SYMBOL", is_endif=False)
        if_def.handle(state, False)
        self.assertTrue(state.in_false_ifdef)

    def test_handle_endif(self):
        state = TpnGenerator()
        state.in_false_ifdef = True
        if_def = IfDef(def_name=None, is_endif=True)
        if_def.handle(state, False)
        self.assertFalse(state.in_false_ifdef)

    def test_ifdef_no_symbol(self):
        state = TpnGenerator()
        if_def = IfDef(def_name=None, is_endif=False)
        if_def.handle(state, False)
        self.assertTrue(state.in_false_ifdef)


class TestOutput(unittest.TestCase):
    def test_parse_line(self):
        output = Output.parse_line("#output foo.prg")
        self.assertIsNotNone(output)

    def test_handle(self):
        state = TpnGenerator()
        output = Output()
        self.assertIsNone(output.handle(state, False))


class TestMakeVarShort(unittest.TestCase):
    def test_simple(self):
        generator = TpnGenerator()
        self.assertEqual(generator.make_var_short("var"), "va")

    def test_suffix(self):
        generator = TpnGenerator()
        self.assertEqual(generator.make_var_short("var$"), "va$")

    def test_collision(self):
        generator = TpnGenerator()
        self.assertEqual(generator.make_var_short("var"), "va")
        self.assertEqual(generator.make_var_short("vaz"), "vb")

    def test_collision_suffix(self):
        generator = TpnGenerator()
        self.assertEqual(generator.make_var_short("var$"), "va$")
        self.assertEqual(generator.make_var_short("vaz$"), "vb$")

    def test_wrap(self):
        generator = TpnGenerator()
        generator.make_var_short("vz")
        self.assertEqual(generator.make_var_short("vz"), "va")

    def test_no_name_available(self):
        generator = TpnGenerator()
        for i in range(26):
            generator.make_var_short("v" + chr(ord("a") + i))
        with self.assertRaises(TpnError):
            generator.make_var_short("vx")

    def test_make_var_short_single_char(self):
        generator = TpnGenerator()
        self.assertEqual(generator.make_var_short("a"), "a")
        self.assertEqual(generator.make_var_short("b"), "b")

    def test_make_var_short_single_char_collision(self):
        generator = TpnGenerator()
        generator.make_var_short("a")
        self.assertEqual(generator.make_var_short("a"), "aa")

    def test_make_var_short_none(self):
        generator = TpnGenerator()
        with self.assertRaises(TpnError):
            generator.make_var_short(None)

    def test_make_var_short_empty(self):
        generator = TpnGenerator()
        with self.assertRaises(TpnError):
            generator.make_var_short("")

    def test_make_var_short_symbol_only(self):
        generator = TpnGenerator()
        with self.assertRaises(TpnError):
            generator.make_var_short("$")
        with self.assertRaises(TpnError):
            generator.make_var_short("%")


class TestTpnGenerator(unittest.TestCase):
    def test_smoke(self):
        generator = TpnGenerator()
        generator.tokenize_line("print \"hello\"")
        self.assertEqual(generator.output_basic(), "100 print \"hello\"")

    def test_forward_label(self):
        generator = TpnGenerator()
        generator.tokenize_line("goto label")
        generator.tokenize_line(".label")
        self.assertEqual(generator.output_basic(), "100 goto 110")

    def test_duplicate_label(self):
        generator = TpnGenerator()
        generator.tokenize_line(".label")
        generator.tokenize_line(".label")
        with self.assertRaises(TpnError):
            generator.output_basic()

    def test_duplicate_var(self):
        generator = TpnGenerator()
        generator.tokenize_line("#declare var")
        generator.tokenize_line("#declare var")
        with self.assertRaises(TpnError):
            generator.output_basic()

    def test_undeclared_symbol(self):
        generator = TpnGenerator()
        generator.tokenize_line("print a$")
        with self.assertRaises(TpnError):
            generator.output_basic()

    def test_undeclared_symbol_no_output(self):
        generator = TpnGenerator()
        generator.tokenize_line("#define FOO")
        generator.tokenize_line("#ifdef FOO")
        generator.tokenize_line("print a$")
        generator.tokenize_line("#endif")
        with self.assertRaises(TpnError):
            generator.output_basic()

    def test_empty_line(self):
        generator = TpnGenerator()
        self.assertEqual(len(generator.tokens), 0)
        generator.tokenize_line("")
        self.assertEqual(len(generator.tokens), 0)


class TestMain(unittest.TestCase):
    @patch('fileinput.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main(self, mock_stdout, mock_fileinput_input):
        mock_fi = MagicMock()
        mock_fi.filename.return_value = '<stdin>'
        mock_fi.filelineno.return_value = 1
        mock_fi.__iter__.return_value = ['print "hello"']

        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_fi
        mock_cm.__exit__.return_value = None
        mock_fileinput_input.return_value = mock_cm

        main()
        self.assertEqual(mock_stdout.getvalue(), '100 print "hello"\n')


if __name__ == "__main__":
    unittest.main()
