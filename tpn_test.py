import unittest
from tpn import parse_line, TpnGenerator


class TestParseLine(unittest.TestCase):

    def test_full_line(self):
        line = "10 print 'hello' ' a comment"
        parsed = parse_line(line)
        self.assertEqual(parsed.line_number, 10)
        self.assertEqual(parsed.statement.strip(), "print 'hello'")
        self.assertEqual(parsed.comment, " a comment")

    def test_statement_only(self):
        line = "  print 1"
        parsed = parse_line(line)
        self.assertIsNone(parsed.line_number)
        self.assertEqual(parsed.statement.strip(), "print 1")
        self.assertIsNone(parsed.comment)

    def test_comment_only(self):
        line = "  ' a comment"
        parsed = parse_line(line)
        self.assertIsNone(parsed.line_number)
        self.assertEqual(parsed.statement.strip(), "")
        self.assertEqual(parsed.comment, " a comment")

    def test_line_number_and_statement(self):
        line = "20 goto 10"
        parsed = parse_line(line)
        self.assertEqual(parsed.line_number, 20)
        self.assertEqual(parsed.statement.strip(), "goto 10")
        self.assertIsNone(parsed.comment)

    def test_line_number_and_comment(self):
        line = "30 ' comment"
        parsed = parse_line(line)
        self.assertEqual(parsed.line_number, 30)
        self.assertEqual(parsed.statement.strip(), "")
        self.assertEqual(parsed.comment, " comment")

    def test_statement_and_comment(self):
        line = "  end ' the end"
        parsed = parse_line(line)
        self.assertIsNone(parsed.line_number)
        self.assertEqual(parsed.statement.strip(), "end")
        self.assertEqual(parsed.comment, " the end")

    def test_empty_line(self):
        line = ""
        parsed = parse_line(line)
        self.assertIsNone(parsed.line_number)
        self.assertEqual(parsed.statement, "")
        self.assertIsNone(parsed.comment)

    def test_whitespace_line(self):
        line = "   "
        parsed = parse_line(line)
        self.assertIsNone(parsed.line_number)
        self.assertEqual(parsed.statement.strip(), "")
        self.assertIsNone(parsed.comment)

    def test_output_directive(self):
        line = "#output mega65.bas"
        parsed = parse_line(line)
        self.assertIsNone(parsed)

        line = "  #output mega65.bas"
        parsed = parse_line(line)
        self.assertIsNone(parsed)

        line = "#OUTPUT mega65.bas"
        parsed = parse_line(line)
        self.assertIsNone(parsed)


class TestTpnGenerator(unittest.TestCase):

    def setUp(self):
        self.generator = TpnGenerator()

    def test_process_statement(self):
        output = self.generator.process_line("print \"hello\"")
        self.assertEqual(output, "100 print \"hello\"")
        self.assertEqual(self.generator.cur_line, 110)

    def test_process_comment(self):
        output = self.generator.process_line("' a comment")
        self.assertEqual(output, "100 rem a comment")
        self.assertEqual(self.generator.cur_line, 110)

    def test_process_statement_and_comment(self):
        output = self.generator.process_line("a=1 ' set a")
        self.assertEqual(output, "100 a=1 :rem set a")
        self.assertEqual(self.generator.cur_line, 110)

    def test_process_line_with_number(self):
        output = self.generator.process_line("50 print")
        self.assertEqual(output, "50 print")
        self.assertEqual(self.generator.cur_line, 50)

    def test_process_multiple_lines(self):
        self.generator.process_line("a=1")
        output = self.generator.process_line("print a")
        self.assertEqual(output, "110 print a")
        self.assertEqual(self.generator.cur_line, 120)

    def test_process_empty_line(self):
        output = self.generator.process_line("")
        self.assertEqual(output, "")


if __name__ == '__main__':
    unittest.main()
