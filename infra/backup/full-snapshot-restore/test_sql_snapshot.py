import unittest
import sql_snapshot as s
class SnapshotTests(unittest.TestCase):
 def test_escaped_utf8_null_numeric_and_hex(self):
  rows=s.parse_values("(1,'a\\n中\\\'b',NULL,0x000A),(-2,'semi;comma,',3.00,0x); ")
  self.assertEqual(rows,[(b'1',"a\n中'b".encode(),None,b'\x00\n'),(b'-2',b'semi;comma,',b'3.00',b'')])
 def test_semicolon_in_strings(self):
  self.assertEqual(len(list(s.statements("-- title\nINSERT INTO `a` VALUES ('x;y');\n/* comment; */ SET a=1;"))),2)
 def test_comment_text_inside_string_preserved(self):
  self.assertEqual(s.clean("-- comment\nINSERT INTO `a` VALUES ('x;-- y /* z */');"), "INSERT INTO `a` VALUES ('x;-- y /* z */');")
 def test_row_digest_order_and_null_distinction(self):
  self.assertEqual(s.row_digest([(b'a',None),(b'b',b'')]),s.row_digest([(b'b',b''),(b'a',None)]))
  self.assertNotEqual(s.row_digest([(None,)]),s.row_digest([(b'NULL',)]))
 def test_expression_rejected(self):
  with self.assertRaises(s.Unsupported):s.parse_values('(now());')
if __name__=='__main__':unittest.main()
