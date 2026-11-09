#!/usr/bin/env python3
"""Pure synthetic SQL tests: never connects to or executes SQL on any server."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('puyu_fingerprint', Path(__file__).with_name('fingerprint.py'))
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
A, B = f.DATABASES
MAP = {'utf8mb4_0900_ai_ci': 'utf8mb4', 'utf8mb4_unicode_ci': 'utf8mb4',
       'utf8mb3_bin': 'utf8mb3', 'utf8mb3_general_ci': 'utf8mb3'}


def table_sql(name='same', *, column_type='text', comment='synthetic  comment', index=''):
    return ('DROP TABLE IF EXISTS `' + name + '`;\n'
            '/*!40101 SET @saved_cs_client = @@character_set_client */;\n'
            '/*!50503 SET character_set_client = utf8mb4 */;\n'
            'CREATE TABLE `' + name + '` (\n'
            '  `id` bigint NOT NULL,\n'
            '  `payload` ' + column_type + " COMMENT '" + comment + "',\n"
            '  `binary_value` blob,\n'
            '  `amount` decimal(20,4),\n'
            '  PRIMARY KEY (`id`)' + index + '\n'
            ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;\n'
            '/*!40101 SET character_set_client = @saved_cs_client */;\n')


def insert(number=1, payload="'{\"json\":[\"a;b\",null]}'", name='same'):
    return ('INSERT INTO `' + name + '` (`id`, `payload`, `binary_value`, `amount`) '
            'VALUES (' + str(number) + ',' + payload + ',0x000AFF,-123456789.6700);')


def dump(rows_a=None, rows_b=None, *, schema=None):
    rows_a = [insert()] if rows_a is None else rows_a
    rows_b = [insert(2)] if rows_b is None else rows_b
    out = ['/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;',
           '/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;',
           "/*!40103 SET TIME_ZONE='+00:00' */;", '/*!50503 SET NAMES utf8mb4 */;']
    for db, rows in [(A, rows_a), (B, rows_b)]:
        out += ['CREATE DATABASE /*!32312 IF NOT EXISTS*/ `' + db + '` '
                '/*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ '
                "/*!80016 DEFAULT ENCRYPTION='N' */;", 'USE `' + db + '`;',
                table_sql() if schema is None else schema, 'LOCK TABLES `same` WRITE;',
                '/*!40000 ALTER TABLE `same` DISABLE KEYS */;', *rows,
                '/*!40000 ALTER TABLE `same` ENABLE KEYS */;', 'UNLOCK TABLES;']
    out += ['/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;',
            '/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;']
    return ('\n'.join(out) + '\n').encode()


class FingerprintTests(unittest.TestCase):
    def test_two_databases_same_table_names_stay_separate(self):
        result = f.fingerprint(dump())
        self.assertEqual(set(result['databases']), {A, B})
        self.assertEqual(result['databases'][A]['tables']['same']['row_count'], 1)
        self.assertNotEqual(result['databases'][A]['tables']['same']['row_multiset_sha256'],
                            result['databases'][B]['tables']['same']['row_multiset_sha256'])

    def test_json_hex_NULL_decimal_and_escaped_semicolon_quote_newline(self):
        rows = [insert(1), insert(2, 'NULL'), insert(3, "'escaped\\nline;quote\\\'\\\\end'"),
                insert(4, "_binary 'bytes'"), insert(5, "''")]
        result = f.fingerprint(dump(rows, rows))
        self.assertEqual(result['databases'][A]['tables']['same']['row_count'], 5)
        self.assertEqual(result['databases'][A]['tables']['same']['insert_columns'],
                         ['id', 'payload', 'binary_value', 'amount'])
        self.assertNotEqual(f.fingerprint(dump([insert(1, 'NULL')])),
                            f.fingerprint(dump([insert(1, "'NULL'")])))

    def test_unicode_separators_VT_actual_literal_LF_not_splitlines(self):
        text = "'中\u2028文\u0085x\vline\nactual LF;still literal'"
        result = f.fingerprint(dump([insert(1, text)]))
        self.assertEqual(result['databases'][A]['tables']['same']['row_count'], 1)

    def test_extended_insert_missing_columns_and_functions_rejected(self):
        rows = [insert().replace(');', "),(2,'more',0x,0);"),
                "INSERT INTO `same` VALUES (1,'x',0x,0);",
                "INSERT INTO `same` (`id`) VALUES (ABS(1));",
                "INSERT INTO `same` (`id`) SELECT 1;"]
        for row in rows:
            with self.subTest(row=row), self.assertRaises(f.FingerprintError):
                f.fingerprint(dump([row]))

    def test_row_order_ignored_but_duplicate_multiplicity_preserved(self):
        first = f.fingerprint(dump([insert(1), insert(2)]))
        second = f.fingerprint(dump([insert(2), insert(1)]))
        self.assertEqual(first, second)
        repeated = f.fingerprint(dump([insert(1), insert(2), insert(1)]))
        self.assertEqual(repeated['databases'][A]['tables']['same']['row_count'], 3)
        self.assertNotEqual(first, repeated)

    def test_changed_type_index_or_comment_stays_different(self):
        original = f.fingerprint(dump(), collations=MAP)
        for schema in [table_sql(column_type='varchar(100)'),
                       table_sql(index=',\n  KEY `new_index` (`amount`)'),
                       table_sql(comment='synthetic comment')]:
            with self.subTest(schema_change=True):
                self.assertNotEqual(original, f.fingerprint(dump(schema=schema), collations=MAP))

    def test_redundant_charset_equivalent_only_with_authoritative_map(self):
        original = table_sql().replace('`payload` text COMMENT', '`payload` text COLLATE utf8mb3_bin COMMENT')
        replay = original.replace('text COLLATE', 'text CHARACTER SET utf8mb3 COLLATE')
        self.assertEqual(f.fingerprint(dump(schema=original), collations=MAP),
                         f.fingerprint(dump(schema=replay), collations=MAP))
        self.assertNotEqual(f.fingerprint(dump(schema=original)), f.fingerprint(dump(schema=replay)))
        with self.assertRaises(f.FingerprintError):
            f.fingerprint(dump(schema=replay.replace('CHARACTER SET utf8mb3', 'CHARACTER SET utf8mb4')), collations=MAP)
        different = original.replace('utf8mb3_bin', 'utf8mb3_general_ci')
        self.assertNotEqual(f.fingerprint(dump(schema=original), collations=MAP),
                            f.fingerprint(dump(schema=different), collations=MAP))

    def test_COMMENT_literal_fake_charset_phrase_and_escaped_quote_preserved(self):
        ddl = "CREATE TABLE `t` (`v` text COMMENT 'CHARACTER SET utf8mb3 COLLATE utf8mb3_bin; it\\'s  exact')"
        self.assertEqual(f.semantic_ddl(ddl, MAP), ddl)
        self.assertNotEqual(f.canonical_ddl(ddl, MAP), f.canonical_ddl(ddl.replace('  exact', ' exact'), MAP))

    def test_executable_comments_preserve_database_charset_encryption(self):
        result = f.fingerprint(dump())
        ddl = result['databases'][A]['create_database']
        self.assertIn('DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci', ddl)
        self.assertIn("DEFAULT ENCRYPTION='N'", ddl)

    def test_unknown_database_objects_and_global_operations_rejected(self):
        for sql in ['USE `mysql`;', 'CREATE DATABASE `puyux_other`;',
                    'CREATE VIEW `v` AS SELECT 1;',
                    'CREATE DEFINER=`root`@`localhost` EVENT `e` ON SCHEDULE EVERY 1 DAY DO SELECT 1;',
                    'SET @@GLOBAL.GTID_PURGED=\'bad\';', 'SET PASSWORD=\'bad\';',
                    'SET `sql_log_bin`=0;', 'CREATE PROCEDURE `p`() SELECT 1;',
                    'CREATE FUNCTION `f`() RETURNS INT RETURN 1;',
                    'GRANT ALL ON *.* TO x;', 'TRUNCATE TABLE `same`;', 'REPLACE INTO `same` VALUES (1);']:
            with self.subTest(statement_class=True), self.assertRaises(f.FingerprintError):
                f.fingerprint(dump() + sql.encode())

    def test_standard_dump_session_setup_is_accepted_without_data_changes(self):
        setup = "\n".join([
            "/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;",
            "/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;",
            "/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;",
            "/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;",
            "/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;",
            "/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;",
            "/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;",
            "/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;",
        ]).encode()
        self.assertEqual(f.fingerprint(dump()), f.fingerprint(dump() + setup))

    def test_foreign_qualified_table_or_reference_rejected(self):
        with self.assertRaises(f.FingerprintError):
            f.fingerprint(dump([insert().replace('`same`', '`mysql`.`same`', 1)]))
        schema = table_sql(index=',\n  FOREIGN KEY (`id`) REFERENCES `mysql`.`user` (`id`)')
        with self.assertRaises(f.FingerprintError):
            f.fingerprint(dump(schema=schema))

    def test_hidden_compound_versioned_sql_rejected(self):
        with self.assertRaises(f.FingerprintError):
            f.fingerprint(dump() + b'/*!40101 SET @OLD_SQL_MODE=1; DROP DATABASE `mysql` */;')
        with self.assertRaises(f.FingerprintError):
            f.fingerprint(dump() + b'/*!999999 CREATE VIEW `v` AS SELECT 1 */;')

    def test_empty_tables_and_unterminated_or_oversize_dump(self):
        result = f.fingerprint(dump([], []))
        self.assertEqual(result['databases'][A]['tables']['same']['row_count'], 0)
        self.assertIsNone(result['databases'][A]['tables']['same']['insert_columns'])
        for raw in [dump() + b'INSERT', dump() + b"'unterminated", dump() + b'/* unclosed']:
            with self.subTest(invalid_tail=True), self.assertRaises(f.FingerprintError):
                f.fingerprint(raw)
        with self.assertRaises(f.FingerprintError):
            f.fingerprint(dump(), max_bytes=10)

    def test_inconsistent_insert_columns_and_trailing_DML_rejected(self):
        with self.assertRaises(f.FingerprintError):
            f.fingerprint(dump([insert(1), insert(2).replace('`id`, `payload`', '`payload`, `id`')]))
        with self.assertRaises(f.FingerprintError):
            f.fingerprint(dump([insert().replace(');', ') ON DUPLICATE KEY UPDATE id=1;')]))


if __name__ == '__main__':
    unittest.main()
