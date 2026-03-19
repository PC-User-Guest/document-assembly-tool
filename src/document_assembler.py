"""
Document Assembly Tool 	6 Core Module

This module provides the DocumentAssembler class which extracts data from a structured
source (Word table, CSV, JSON) and inserts it into a template document at placeholder
locations, preserving all formatting. It supports customizable placeholder syntax
and multiple data source types.
"""

import argparse
import csv
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from docx import Document
from docx.text.paragraph import Paragraph

# Configure module logger
logger = logging.getLogger(__name__)


class DocumentAssembler:
    """
    Assembles a document by merging data from a structured source into a template.

    The data source can be:
      - A Word document with a table (first table used).
      - A CSV file with header row.
      - A JSON file (list of objects or object with keys).

    The template contains placeholders (default: `{{field_name}}` or custom pattern).
    The tool replaces each placeholder with the corresponding data, preserving formatting.
    """

    # Default placeholder pattern (regex group name must match field name)
    DEFAULT_PLACEHOLDER_PATTERN = r'\{\{\s*(?P<field_name>\w+)\s*\}\}'

    def __init__(
        self,
        data_source: str,
        template_path: str,
        output_path: str,
        data_type: str = "word",
        placeholder_pattern: str = None,
        log_level: str = "INFO"
    ):
        """
        Initialize the assembler.

        Args:
            data_source: Path to the data source file (Word, CSV, JSON).
            template_path: Path to the template Word document.
            output_path: Path where the assembled document will be saved.
            data_type: Type of data source ('word', 'csv', 'json'). Default 'word'.
            placeholder_pattern: Regex pattern with named group 'field_name' to match placeholders.
                                 If None, uses DEFAULT_PLACEHOLDER_PATTERN.
            log_level: Logging verbosity.
        """
        self.data_source = data_source
        self.template_path = template_path
        self.output_path = output_path
        self.data_type = data_type.lower()
        self.placeholder_pattern = placeholder_pattern or self.DEFAULT_PLACEHOLDER_PATTERN
        self._setup_logging(log_level)

        self.data: Dict[str, Any] = {}  # Will hold merged data (field -> value)

    def _setup_logging(self, log_level: str) -> None:
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")

        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(numeric_level)
        logger.propagate = False

    def _load_data_from_word(self) -> Dict[str, Any]:
        """Extract key-value pairs from first table of a Word document."""
        logger.info(f"Loading data from Word table: {self.data_source}")
        doc = Document(self.data_source)
        if not doc.tables:
            raise ValueError("No tables found in the Word data source.")
        table = doc.tables[0]
        data = {}
        # Assume first row is header; subsequent rows are key-value pairs (key in col0, value in col1)
        for i, row in enumerate(table.rows):
            if i == 0:
                continue  # skip header
            cells = row.cells
            if len(cells) < 2:
                logger.warning(f"Skipping row {i} with fewer than 2 cells.")
                continue
            key = cells[0].text.strip()
            # For value, we need to capture formatted content, not just plain text
            # For simplicity, we store the full paragraph(s) as we did for answers.
            # But here we'll store a list of paragraph data (like before).
            value_paras = []
            for para in cells[1].paragraphs:
                if not para.text.strip() and not para.runs:
                    continue
                runs_data = []
                for run in para.runs:
                    runs_data.append({
                        'text': run.text,
                        'bold': run.bold,
                        'italic': run.italic,
                        'underline': run.underline
                    })
                value_paras.append({
                    'style': para.style.name if para.style else None,
                    'runs': runs_data
                })
            data[key] = value_paras
        logger.info(f"Loaded {len(data)} fields from Word.")
        return data

    def _load_data_from_csv(self) -> Dict[str, Any]:
        """Load data from CSV file. Assumes first row is header and there is only one data row."""
        logger.info(f"Loading data from CSV: {self.data_source}")
        with open(self.data_source, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if not rows:
                raise ValueError("CSV file has no data rows.")
            if len(rows) > 1:
                logger.warning("CSV has multiple rows; using only the first row.")
            data_row = rows[0]
        # For CSV, values are plain strings; we convert to a single-paragraph structure
        data = {}
        for key, value in data_row.items():
            # Create a simple paragraph data
            data[key] = [{
                'style': None,
                'runs': [{'text': value, 'bold': False, 'italic': False, 'underline': False}]
            }]
        return data

    def _load_data_from_json(self) -> Dict[str, Any]:
        """Load data from JSON file. Expects an object (mapping) or an array of objects (first used)."""
        logger.info(f"Loading data from JSON: {self.data_source}")
        with open(self.data_source, 'r', encoding='utf-8') as f:
            parsed = json.load(f)
        if isinstance(parsed, dict):
            data_dict = parsed
        elif isinstance(parsed, list) and parsed:
            data_dict = parsed[0]
            logger.warning("JSON is an array; using first object.")
        else:
            raise ValueError("JSON must be an object or non-empty array.")
        # Convert values to paragraph data (simple strings)
        data = {}
        for key, value in data_dict.items():
            if isinstance(value, (str, int, float)):
                text = str(value)
                data[key] = [{
                    'style': None,
                    'runs': [{'text': text, 'bold': False, 'italic': False, 'underline': False}]
                }]
            else:
                logger.warning(f"Field '{key}' has non-primitive type; converting to string.")
                text = json.dumps(value)
                data[key] = [{
                    'style': None,
                    'runs': [{'text': text, 'bold': False, 'italic': False, 'underline': False}]
                }]
        return data

    def load_data(self) -> Dict[str, Any]:
        """Load data from the specified source."""
        if self.data_type == "word":
            return self._load_data_from_word()
        elif self.data_type == "csv":
            return self._load_data_from_csv()
        elif self.data_type == "json":
            return self._load_data_from_json()
        else:
            raise ValueError(f"Unsupported data type: {self.data_type}")

    def find_placeholders(self, doc: Document) -> List[tuple]:
        """
        Find all placeholders in the document.

        Returns:
            List of tuples (paragraph, match) where match is a regex match object.
        """
        placeholders = []
        pattern = re.compile(self.placeholder_pattern)
        for para in doc.paragraphs:
            matches = list(pattern.finditer(para.text))
            for match in matches:
                placeholders.append((para, match))
        return placeholders

    def insert_data(self, data: Dict[str, Any]) -> None:
        """
        Replace placeholders in the template with corresponding data.

        Args:
            data: Dictionary mapping field names to paragraph data (list of paragraph dicts).
        """
        doc = Document(self.template_path)
        placeholders = self.find_placeholders(doc)
        logger.info(f"Found {len(placeholders)} placeholder(s).")

        # First, replace placeholders that occupy a full paragraph.
        # This preserves formatting of the inserted value paragraphs.
        full_para_placeholders = []
        pattern = re.compile(self.placeholder_pattern)
        for para in doc.paragraphs:
            text = para.text.strip()
            match = pattern.fullmatch(text)
            if match:
                full_para_placeholders.append((para, match.group('field_name')))

        logger.info(f"Found {len(full_para_placeholders)} full-paragraph placeholder(s).")

        for para, field_name in full_para_placeholders:
            if field_name not in data:
                logger.warning(f"Field '{field_name}' not found in data. Placeholder will remain.")
                continue

            value_paras = data[field_name]
            # Insert value paragraphs before the placeholder
            for para_data in reversed(value_paras):
                new_para = para.insert_paragraph_before('')
                if para_data['style']:
                    try:
                        new_para.style = para_data['style']
                    except KeyError:
                        logger.warning(f"Style '{para_data['style']}' not found; using default.")
                for run_data in para_data['runs']:
                    run = new_para.add_run(run_data['text'])
                    run.bold = run_data['bold']
                    run.italic = run_data['italic']
                    run.underline = run_data['underline']

            # Remove the placeholder paragraph
            p = para._element
            p.getparent().remove(p)
            logger.debug(f"Inserted data for field '{field_name}'.")

        # Next, handle placeholders that are inline within a paragraph.
        # This preserves existing run formatting in the template and applies
        # the placeholder value as plain text (or with its own formatting when using
        # a Word data source).
        def _flatten_value_paras(value_paras):
            return [
                "".join(run.get('text', "") for run in para_data.get('runs', []))
                for para_data in value_paras
            ]

        for para in list(doc.paragraphs):
            if not pattern.search(para.text):
                continue

            extra_paras = []

            def _replacer(match):
                field_name = match.group('field_name')
                if field_name not in data:
                    logger.warning(f"Field '{field_name}' not found in data. Placeholder will remain.")
                    return match.group(0)

                values = _flatten_value_paras(data[field_name])
                if not values:
                    return ""

                # Preserve additional paragraphs (if any) by inserting them after this paragraph.
                for extra in values[1:]:
                    extra_paras.append(extra)

                return values[0]

            # Replace placeholder text in runs (preserving each run's formatting)
            for run in list(para.runs):
                if not pattern.search(run.text):
                    continue
                run.text = pattern.sub(_replacer, run.text)

            # If placeholder spans multiple runs, we may still see it in paragraph text.
            # In that case, fall back to replacing the paragraph text (may lose fine-grained formatting).
            if pattern.search(para.text):
                new_text = pattern.sub(_replacer, para.text)
                for run in para.runs:
                    run.clear()
                if para.runs:
                    para.runs[0].text = new_text
                else:
                    para.add_run(new_text)

            # Insert any extra paragraphs captured from multi-paragraph field values.
            for extra in extra_paras:
                new_para = para.insert_paragraph_after(extra)
                try:
                    new_para.style = para.style
                except Exception:
                    pass

        doc.save(self.output_path)
        logger.info(f"Assembled document saved to: {self.output_path}")

    def run(self) -> None:
        """Execute the full assembly process."""
        try:
            self.data = self.load_data()
            self.insert_data(self.data)
        except Exception as e:
            logger.critical(f"An unexpected error occurred: {e}", exc_info=True)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Assemble a document by merging data from a structured source into a template."
    )
    parser.add_argument(
        '-d', '--data',
        required=True,
        help='Path to the data source (Word, CSV, JSON)'
    )
    parser.add_argument(
        '-t', '--template',
        required=True,
        help='Path to the template Word document'
    )
    parser.add_argument(
        '-o', '--output',
        default='assembled_document.docx',
        help='Path for the output document (default: assembled_document.docx)'
    )
    parser.add_argument(
        '--data-type',
        default='word',
        choices=['word', 'csv', 'json'],
        help='Type of data source (default: word)'
    )
    parser.add_argument(
        '--placeholder-pattern',
        default=r'\{\{\s*(?P<field_name>\w+)\s*\}\}',
        help='Regex pattern with named group field_name to match placeholders (default: {{ field_name }})'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set logging verbosity (default: INFO)'
    )

    args = parser.parse_args()

    assembler = DocumentAssembler(
        data_source=args.data,
        template_path=args.template,
        output_path=args.output,
        data_type=args.data_type,
        placeholder_pattern=args.placeholder_pattern,
        log_level=args.log_level
    )
    assembler.run()


if __name__ == "__main__":
    main()
