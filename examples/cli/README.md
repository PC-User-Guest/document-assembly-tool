# CLI Example Fixture Set

This folder contains a small example setup that demonstrates how to run the Document Assembly Tool from the command line.

## Run the example

From the `examples/cli` folder, run:

```bash
python generate_example.py
```

This will:
- Generate example `data.docx` (Word table) and `template.docx` (with placeholders)
- Execute the CLI: `python -m src.document_assembler -d data.docx -t template.docx -o output.docx`
- Produce `output.docx` with placeholders replaced

## Notes

- You can inspect `output.docx` to verify that:
  - placeholders were replaced with the fixture values
  - inline placeholder formatting (e.g., bold) is preserved
