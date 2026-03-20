# Document Assembly Tool - User Guide

## Overview

The Document Assembly Tool automates the merging of structured data into a Word template, replacing placeholders with formatted content. It supports multiple data sources (Word tables, CSV, JSON) and preserves formatting such as bold, italic, underline, and lists.

### Typical Use Cases

* **Contract Generation** - Populate contract templates with client data.
* **Personalized Marketing Materials** - Create proposals, letters, and brochures.
* **Report Automation** - Generate recurring reports by merging data from databases or spreadsheets.
* **Document Personalization** - Insert names, dates, and other variable content into standard documents.

---

## System Requirements

* Python 3.10 or higher
* `python-docx` (install via `pip install -r requirements.txt`)

---

## Installation

1. Clone or download the project repository:
```bash
git clone https://github.com/PC-User-Guest/document-assembly-tool.git
```
2. Open a terminal in the project root directory:
```bash
cd <repository-directory>
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Data Source Formats

### Word Table (`--data-type word`)

- The first table in the document is used.
- First row is treated as header and skipped.
- Each subsequent row must contain:

  * Column 1: Field Name
  * Column 2: Value
- The Value column can contain formatted text (bold, italic, lists).

### CSV (`--data-type csv`)

- First row must be header (field names).
- Only the first data row is used (multiple rows are ignored with a warning).
- Values are plain text; formatting is not preserved.
  
### JSON (`--data-type json`)

- File must contain a JSON object (key-value pairs) or an array of objects (first object used).
- Values can be strings, numbers, or booleans; they are converted to plain text.

---

## Template Placeholders

Placeholders in the template document follow a configurable pattern. The default pattern is `{{ field_name }}` (curly braces with optional spaces). You can change the pattern using the `--placeholder-pattern` option (must include a named group `field_name`).

Default placeholder format:

```text
{{ field_name }}
```

Custom placeholder example:

```text
<<client_name>>
```

Recommended custom regex:

```regex
<<\s*(?P<field_name>[A-Za-z_][A-Za-z0-9_-]*)\s*>>
```

This pattern matches placeholder names such as:

* `client_name`
* `project_title`
* `line-item_01`
* `account-id`

### Notes

* The pattern must include a named group called `field_name`.
* Use single quotes around the regex in shell examples to avoid escaping issues.
* Placeholder names in the template must match the data keys exactly and are case-sensitive.
* Placeholders can be inline or standalone, but best results are achieved using standalone paragraphs.

---

## Usage

```bash
python -m src.document_assembler -d data.docx -t template.docx -o output.docx
```

---

## Command-Line Arguments

| Argument                | Description                   | Default                             |
| ----------------------- | ----------------------------- | ----------------------------------- |
| `-d, --data`            | Path to data source           | Required                            |
| `-t, --template`        | Path to template file         | Required                            |
| `-o, --output`          | Output file path              | `assembled_document.docx`           |
| `--data-type`           | `word`, `csv`, or `json`      | `word`                              |
| `--placeholder-pattern` | Regex with `field_name` group | `\{\{\s*(?P<field_name>\w+)\s*\}\}` |
| `--log-level`           | Logging level                 | `INFO`                              |

---

## Examples

### Word Data Source

```bash
python -m src.document_assembler -d data.docx -t template.docx -o contract.docx
```

### CSV Data Source

```bash
python -m src.document_assembler -d clients.csv -t proposal.docx -o output.docx --data-type csv
```

### JSON with Custom Placeholders

```bash
python -m src.document_assembler \
  -d data.json \
  -t template.docx \
  -o output.docx \
  --data-type json \
  --placeholder-pattern '<<\s*(?P<field_name>[A-Za-z_][A-Za-z0-9_-]*)\s*>>'
```

### Debug Logging

```bash
python -m src.document_assembler -d data.docx -t template.docx --log-level DEBUG
```

---

## Output

Generates a new `.docx` file with all placeholders replaced.

### Preserved Formatting

* Paragraph styles
* Bullet and numbered lists
* Inline formatting (bold, italic, underline)
* Multi-paragraph content (Word source only)

---

## Error Handling and Logging

Logs are written to stderr with timestamps.

### Common Warnings

| Warning                                           | Description            |
| ------------------------------------------------- | ---------------------- |
| `Skipping row with fewer than 2 cells`            | Invalid Word table row |
| `Field '{name}' not found in data`                | Placeholder mismatch   |
| `Style '{name}' not found`                        | Style fallback applied |
| `CSV has multiple rows; using only the first row` | CSV limitation         |
| `JSON is an array; using first object`            | Array handling         |

### Exit Codes

* Returns a non-zero exit code on critical failures (for example, missing files)

---

## Troubleshooting

### Placeholders Not Replaced

* Confirm the placeholder pattern matches the template syntax.
* Ensure field names match exactly and are case-sensitive.
* Prefer standalone paragraph placeholders.
* Use single quotes around custom regex patterns in shell commands.

### Formatting Lost (CSV/JSON)

* CSV and JSON do not support rich formatting.
* Use a Word data source for formatted content.

### Word Table Not Parsed Correctly

* Ensure:

  * The first row is a header.
  * Each row has exactly two columns.
  * Field names are strings.

### Custom Placeholder Pattern Issues

* The regex must include a named group called `field_name`.
* For placeholders like `<<client_name>>`, use:

```regex
<<\s*(?P<field_name>[A-Za-z_][A-Za-z0-9_-]*)\s*>>
```

* This recommended pattern supports letters, numbers, underscores, and hyphens in field names.
* Validate the pattern with a regex tester if needed.

---

## Customization

### Adding New Data Sources

Extend the `DocumentAssembler` class:

```python
_load_data_from_<source>()
```

Then update the dispatcher in `load_data`.

### Supporting Inline Placeholders

Requires modifying the `insert_data` method to:

* Split runs within paragraphs
* Preserve surrounding text

---

## Enterprise Use Cases

* **Legal and Compliance** - Contracts, NDAs, policies
* **Sales and Marketing** - Proposals, quotes, brochures
* **Human Resources** - Offer letters, reviews
* **Finance** - Reports and summaries
* **Education** - Certificates, transcripts

---

## Version History

| Version | Date       | Description                                                       |
| ------- | ---------- | ----------------------------------------------------------------- |
| 2.0.1   | 2025-03-19 | README fixes for custom placeholder regex and shell-safe examples |
| 2.0.0   | 2025-03-19 | Multi-source support and customizable placeholders                |
| 1.0.0   | 2025-03-19 | Initial release                                                   |
