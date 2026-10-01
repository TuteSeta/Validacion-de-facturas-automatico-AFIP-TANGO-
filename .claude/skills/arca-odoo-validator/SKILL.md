---
name: arca-odoo-validator
description: Maintain, diagnose, or extend this repository's ARCA-to-Odoo Excel invoice validator, including mappings, matching rules, output workbooks, and regression verification. Use for validator code or export-format changes; not for general Odoo module development.
---

# ARCA–Odoo validator

Treat the Excel files supplied beside the repository as the source of truth for export
layout. Inspect workbook sheet names and initial rows before changing mappings; keep
layout-specific names in `config.yaml`, not scattered through Python.

Preserve these domain invariants unless the user supplies evidence that the exports
changed:

- Match on canonical document type, letter, five-digit point of sale, eight-digit
  number, and normalized 11-digit CUIT.
- Do not collapse invoices, credit notes, and debit notes into the same identifier.
- ARCA credit-note amounts are converted to Odoo's negative accounting sign.
- Apply ARCA's exchange rate before comparing monetary values.
- Reject invalid document keys and require a positive exchange rate for non-ARS
  currencies; invalid rows are incidents and never enter reconciliation.
- For B and C documents compare the total because ARCA does not reliably expose the
  same tax breakdown as Odoo. For A documents compare net, VAT, other amounts, and
  total.
- Reconcile in both directions within ARCA's inclusive date range. Classify Odoo
  outside that range separately.
- Never modify either input workbook. Preserve every sheet and existing formatting
  in both validated copies.

Keep normalization in `src/transform.py` and all business comparisons exclusively in
`src/compare.py`. Workbook writers must consume the structured reconciliation result
and must not reimplement tolerances, currency conversion, or field selection.

Run `python -m unittest discover -s tests -v`, compile the sources, and exercise
`src.main.run_validation` against the current real exports when they are available.
Report match/difference/missing totals as verification evidence, not as an assertion
that Odoo's business data is correct.
