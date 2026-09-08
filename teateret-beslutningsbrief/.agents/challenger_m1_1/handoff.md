# Challenger Handoff Report — Milestone 1

**Agent ID**: challenger_m1_1  
**Timestamp**: 2026-08-20T07:34:00Z  
**Verdict**: `APPROVE`

---

## 1. Observation

Direct code and dataset observations in the target files:

1. **Number Parsing & Regex in `teateret_brief/csv_adapter.py` (lines 166–217)**:
   - Non-breaking spaces (`\u00a0`, `\u202f`), tabs, and standard whitespace are cleanly stripped:
     ```python
     for ws in ("\u00a0", "\u202f", "\t", "\r", "\n", " "):
         text = text.replace(ws, "")
     ```
   - Currency tokens (`NOK`, `nok`, `kr.`, `kr`, `Kr`, `,-`, `.-`) are handled and mapped:
     ```python
     text = re.sub(r"(?i)\b(?:nok|kr\.?)\b", "", text)
     if text.endswith(",-") or text.endswith(".-"):
         text = text[:-2] + ",00"
     ```
   - Disambiguation of Norwegian thousand-separator dot vs. standard decimal:
     ```python
     if "." in text and "," in text:
         last_dot = text.rfind(".")
         last_comma = text.rfind(",")
         if last_comma > last_dot:
             text = text.replace(".", "").replace(",", ".")
         else:
             text = text.replace(",", "")
     elif "," in text:
         text = text.replace(",", ".")
     elif "." in text:
         if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", text):
             text = text.replace(".", "")
     ```
   - Negative numbers and non-finite values (`NaN`, `inf`, `-inf`) are explicitly rejected with `DataPolicyError`:
     ```python
     if not math.isfinite(val):
         raise DataPolicyError("Aggregert måleverdi må være et endelig tall.")
     if val < 0:
         raise DataPolicyError("Negative aggregerte måleverdier er ikke tillatt i piloten.")
     ```

2. **Date Parsing in `teateret_brief/csv_adapter.py` (lines 139–164)**:
   - Supports ISO (`%Y-%m-%d`, `%Y-%m-%dT%H:%M:%S`, with timezone via `fromisoformat`) and Norwegian dot/slash notations (`%d.%m.%Y`, `%d/%m/%Y`, with/without timestamps).
   - Strict date construction ensures invalid calendar dates (`2026-02-31`, `2026-02-29` on non-leap years, `31.04.2026`, `2026-13-01`) raise `DataPolicyError`.

3. **Delimiter Detection in `teateret_brief/csv_adapter.py` (lines 122–137)**:
   - Supports explicit delimiters (`;`, `,`, `\t`) and `auto` sniffing via `csv.Sniffer` with deterministic first-line fallback.

4. **PII and Data Policy Guard in `teateret_brief/security.py` and `csv_adapter.py`**:
   - Rejects forbidden column names containing customer/guest names, email, phone, personal national identity numbers (`fnr`), credit card numbers, free-text/notes.
   - Scans cell text for regex-matching emails, phone numbers, valid Luhn credit cards, and valid Modulo-11 Norwegian FNRs.

5. **Reference Dataset `sample_data/gastroplanner_sample_2026.csv`**:
   - Contains 9 rows and 5 aggregate metrics per event (tickets sold, capacity, table reservations, preorder menus, revenue).
   - Full ingestion with `config/gastroplanner_mapping.example.yml` produces exactly 45 valid `SalesObservation` instances.

---

## 2. Logic Chain

1. **Delimiter Handling**:
   - *Observation 1.3*: `_detect_delimiter` supports explicit configured delimiters or automatic sniffing. Tested with semicolon, comma, tab, and mixed commas in quoted text. In all modes, records are parsed into correct columns.
2. **Norwegian Number Edge Cases**:
   - *Observation 1.1*: Thousand separator dot patterns (`"1.200"`, `"185.000"`, `"1.200.000,50"`, `"1.234.567.890,75"`) match either mixed dot/comma or `re.fullmatch(r"\d{1,3}(?:\.\d{3})+", text)`. Dot is removed for thousand groupings.
   - Decimals without thousand separators (`"0.50"`, `"0.5"`, `"12.5"`, `"12.50"`, `"12,50"`) do not match 3-digit dot groupings and are parsed accurately as decimals (0.5, 12.5).
   - Blanks, dashes (`""`, `"-"`, `"–"`, `"—"`, `"N/A"`, `"null"`, `None`) cleanly return `0.0`.
   - Non-breaking spaces (`\u00a0`, `\u202f`) and currency tokens (`kr 18 500,00`, `18500,-`, `18500 NOK`) evaluate accurately to target numeric floats.
3. **Invalid Value Rejection**:
   - *Observation 1.1 & 1.2*: Negative numbers, `NaN`, `inf`, and non-numeric strings trigger `DataPolicyError`. Invalid dates (`2026-02-31`, `2026-02-29` non-leap) trigger `DataPolicyError`.
4. **Reference Dataset Verification**:
   - *Observation 1.5*: Reference sample `sample_data/gastroplanner_sample_2026.csv` parsed 45/45 observations with 100% field compliance (`period.year == 2026`, `source_system == 'GastroPlanner'`, valid canonical room normalization).

---

## 3. Caveats

- Delimiter `auto`-sniffing relies on standard standard-library `csv.Sniffer`. Files with irregular column counts or unescaped rogue delimiters should use an explicit delimiter setting (e.g. `delimiter: ";"`) in mapping configuration.
- No caveats regarding Milestone 1 specifications.

---

## 4. Conclusion

**Verdict**: `APPROVE`

`teateret_brief/csv_adapter.py` and `teateret_brief/models.py` demonstrate rigorous handling of Norwegian locale formats, edge cases, delimiter variations, invalid data rejection, and PII protection. All 45 sample observations in `sample_data/gastroplanner_sample_2026.csv` ingest cleanly and match domain models.

---

## 5. Verification Method

To independently verify the test suite:

```bash
pytest tests/test_csv_adapter_stress.py tests/test_csv_adapter.py tests/test_models_and_config.py -v
```

Inspected files:
- `teateret_brief/csv_adapter.py`
- `teateret_brief/models.py`
- `sample_data/gastroplanner_sample_2026.csv`
- `config/gastroplanner_mapping.example.yml`
- `tests/test_csv_adapter_stress.py`
