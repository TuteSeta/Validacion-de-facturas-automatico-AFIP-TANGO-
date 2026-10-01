import unittest

import pandas as pd

from src.compare import reconcile
from src.transform import LoadResult


def record(source, ncomp, cuit, date, total, *, net=0, vat=0, other=0, tc=1, row=1):
    return {
        "FUENTE": source,
        "FILA_EXCEL": row,
        "FILAS_EXCEL": (row,),
        "FECHA": pd.Timestamp(date),
        "MONEDA": "ARS",
        "N_COMP": ncomp,
        "IDENTIFTRI": cuit,
        "TC": tc,
        "IMP_EXENTO": other,
        "IMP_NETO": net,
        "IMP_IVA": vat,
        "IMP_TOTAL": total,
    }


class ReconciliationTests(unittest.TestCase):
    def test_bidirectional_period_and_document_rules(self):
        arca = pd.DataFrame([
            record("ARCA", "FA-A00001-00000001", "30711111111", "2026-08-01", 121, net=100, vat=21, row=3),
            record("ARCA", "FA-B00001-00000002", "30722222222", "2026-08-02", 200, row=4),
            record("ARCA", "FA-C00001-00000003", "30733333333", "2026-08-03", 300, row=5),
        ])
        odoo = pd.DataFrame([
            record("ODOO", "FA-A00001-00000001", "30711111111", "2026-08-01", 121, net=100, vat=21, row=4),
            # En B se ignora el desglose y se compara total.
            record("ODOO", "FA-B00001-00000002", "30722222222", "2026-08-02", 200, other=200, row=5),
            record("ODOO", "FA-A00001-00000009", "30799999999", "2026-08-02", 50, net=50, row=6),
            record("ODOO", "FA-A00001-00000010", "30799999998", "2026-07-31", 10, net=10, row=7),
        ])
        empty_issues = pd.DataFrame(columns=["FUENTE"])
        result = reconcile(
            LoadResult(arca, empty_issues),
            LoadResult(odoo, empty_issues),
            {name: 0.01 for name in ("IMP_EXENTO", "IMP_NETO", "IMP_IVA", "IMP_TOTAL")},
        )
        self.assertEqual(result.metrics["coincidencias"], 2)
        self.assertEqual(result.metrics["faltantes_en_odoo"], 1)
        self.assertEqual(result.metrics["faltantes_en_arca"], 1)
        self.assertEqual(result.metrics["fuera_periodo_odoo"], 1)

    def test_exchange_rate_and_tolerance(self):
        arca = pd.DataFrame([
            record("ARCA", "NC-A00001-00000001", "30711111111", "2026-08-01", -10, net=-10, tc=1000),
        ])
        odoo = pd.DataFrame([
            record("ODOO", "NC-A00001-00000001", "30711111111", "2026-08-01", -10000.01, net=-10000.01),
        ])
        empty = pd.DataFrame(columns=["FUENTE"])
        result = reconcile(
            LoadResult(arca, empty), LoadResult(odoo, empty),
            {name: 0.01 for name in ("IMP_EXENTO", "IMP_NETO", "IMP_IVA", "IMP_TOTAL")},
        )
        self.assertEqual(result.metrics["coincidencias"], 1)


if __name__ == "__main__":
    unittest.main()
