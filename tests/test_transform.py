import unittest

from src.transform import (
    _build_ncomp_from_parts,
    _normalize_cuit,
    _normalize_ncomp,
    _parse_number,
    _tipo_to_doc_letter,
)


class TransformTests(unittest.TestCase):
    def test_normalizes_odoo_invoice(self):
        self.assertEqual(
            _normalize_ncomp("FA-A 00001-00001822"),
            "FA-A00001-00001822",
        )

    def test_keeps_credit_note_type(self):
        self.assertEqual(
            _normalize_ncomp("NC-B 00001-00000324"),
            "NC-B00001-00000324",
        )
        self.assertEqual(_tipo_to_doc_letter("8 - Nota de Crédito B"), ("NC", "B"))
        self.assertEqual(_tipo_to_doc_letter("2 - Nota de Débito A"), ("ND", "A"))

    def test_builds_arca_number_from_numeric_parts(self):
        self.assertEqual(
            _build_ncomp_from_parts(
                "1 - Factura A",
                1.0,
                1822.0,
                "{doc_type}-{letter}{pv:05d}{num:08d}",
            ),
            "FA-A00001-00001822",
        )

    def test_normalizes_cuit_with_or_without_hyphens(self):
        self.assertEqual(_normalize_cuit("33-71626966-9"), "33716269669")
        self.assertEqual(_normalize_cuit(33716269669), "33716269669")

    def test_parses_spanish_and_english_numbers(self):
        self.assertEqual(_parse_number("1.234,56"), 1234.56)
        self.assertEqual(_parse_number("1234.56"), 1234.56)
        self.assertEqual(_parse_number("1,234.56"), 1234.56)

    def test_rejects_unknown_document_type_and_zero_number(self):
        with self.assertRaises(ValueError):
            _tipo_to_doc_letter("99 - Formato futuro", strict=True)
        with self.assertRaises(ValueError):
            _build_ncomp_from_parts(
                "1 - Factura A", 1, 0, "{doc_type}-{letter}{pv:05d}{num:08d}"
            )


if __name__ == "__main__":
    unittest.main()
