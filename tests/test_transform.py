import unittest

from src.transform import (
    _build_ncomp_from_parts,
    _normalize_cuit,
    _normalize_ncomp,
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


if __name__ == "__main__":
    unittest.main()
