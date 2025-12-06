import unittest
from tpn import Statement, TpnGenerator, Line, VarDeclare, TpnError, Define
from tpn import IfDef, Output


class TestStatement(unittest.TestCase):
    def test_to_basic(self):
        statement = Statement("print ""hello""")
        state = TpnGenerator()
        self.assertEqual(statement.to_basic(state), "print ""hello""")


class TestLine(unittest.TestCase):
    def test_parse_line_statement(self):
        line = Line.parse_line("print ""hello""")
        self.assertEqual(line.statement.full_text, "print ""hello""")
        self.assertIsNone(line.label)
        self.assertIsNone(line.line_number)
        self.assertIsNone(line.comment)

    def test_parse_line_label_statement(self):
        line = Line.parse_line(".label print ""hello""")
        self.assertEqual(line.label, "label")
        self.assertEqual(line.statement.full_text, " print ""hello""")
        self.assertIsNone(line.line_number)
        self.assertIsNone(line.comment)

    def test_parse_line_line_number_statement(self):
        line = Line.parse_line("100 print ""hello""")
        self.assertEqual(line.line_number, 100)
        self.assertEqual(line.statement.full_text, " print ""hello""")
        self.assertIsNone(line.label)
        self.assertIsNone(line.comment)

    def test_parse_line_label_line_number_statement(self):
        line = Line.parse_line(".label 100 print ""hello""")
        self.assertEqual(line.label, "label")
        self.assertEqual(line.line_number, 100)
        self.assertEqual(line.statement.full_text, " print ""hello""")
        self.assertIsNone(line.comment)

    def test_parse_line_statement_comment(self):
        line = Line.parse_line("print ""hello"" ' comment")
        self.assertEqual(line.statement.full_text, "print ""hello"" ")
        self.assertEqual(line.comment, " comment")
        self.assertIsNone(line.label)
        self.assertIsNone(line.line_number)

    def test_parse_line_label_line_number_statement_comment(self):
        line = Line.parse_line(".label 100 print ""hello"" ' comment")
        self.assertEqual(line.label, "label")
        self.assertEqual(line.line_number, 100)
        self.assertEqual(line.statement.full_text, " print ""hello"" ")
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
        line = Line(statement=Statement("print ""hello"""))
        self.assertEqual(line.handle(state, True), "100 print ""hello""")
        self.assertEqual(state.cur_line, 110)

    def test_handle_with_line_number(self):
        state = TpnGenerator()
        line = Line(line_number=200, statement=Statement("print ""hello"""))
        self.assertEqual(line.handle(state, True), "200 print ""hello""")
        self.assertEqual(state.cur_line, 210)

    def test_handle_with_label(self):
        state = TpnGenerator()
        line = Line(label="label", statement=Statement("print ""hello"""))
        self.assertEqual(line.handle(state, True), "100 print ""hello""")
        self.assertEqual(state.labels["label"], 100)
        self.assertEqual(state.cur_line, 110)


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
        line = var_declare.handle(state, True)
        self.assertEqual(state.vars["varName"], "va")
        self.assertEqual(line, "100 va=123")

    def test_handle_with_array_dim(self):
        state = TpnGenerator()
        var_declare = VarDeclare(name="varName", array_dim_short="10")
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

    def test_parse_line_empty_value(self):
        define = Define.parse_line("#define SYMBOL = ")
        self.assertEqual(define.name, "SYMBOL")
        self.assertEqual(define.value, "")

    def test_handle(self):
        state = TpnGenerator()
        define = Define(name="SYMBOL", value="123")
        define.handle(state, False)
        self.assertEqual(state.defines["SYMBOL"], "123")


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
        self.assertTrue(state.in_false_ifdef)

    def test_handle_ifdef_undefined(self):
        state = TpnGenerator()
        if_def = IfDef(def_name="SYMBOL", is_endif=False)
        if_def.handle(state, False)
        self.assertFalse(state.in_false_ifdef)

    def test_handle_endif(self):
        state = TpnGenerator()
        state.in_false_ifdef = True
        if_def = IfDef(def_name=None, is_endif=True)
        if_def.handle(state, False)
        self.assertFalse(state.in_false_ifdef)


class TestOutput(unittest.TestCase):
    def test_parse_line(self):
        output = Output.parse_line("#output foo.prg")
        self.assertIsNotNone(output)

    def test_handle(self):
        state = TpnGenerator()
        output = Output()
        self.assertIsNone(output.handle(state, False))


class TestTpnGenerator(unittest.TestCase):
    def test_smoke(self):
        generator = TpnGenerator()
        generator.tokenize_line("print ""hello""")
        self.assertEqual(generator.output_basic(), "100 print ""hello""")


if __name__ == "__main__":
    unittest.main()
