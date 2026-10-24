# Module 15 Completion Report

## Script Metadata
- Filename: `tools/bulk_process_text.py`
- Language: Python
- Purpose: Recursively process UTF-8 `.txt` files in an input directory, replace literal text, and write the processed files to a separate output directory while preserving their relative paths and leaving the originals unchanged.

## Script Contents
```python
"""Apply a literal text replacement to UTF-8 .txt files in a directory tree."""

import argparse
from pathlib import Path


def process_files(input_dir, output_dir, search_text, replacement_text):
    source_root = input_dir.resolve()
    destination_root = output_dir.resolve()

    if not source_root.is_dir():
        raise ValueError(f"Input directory does not exist: {source_root}")

    try:
        destination_root.relative_to(source_root)
    except ValueError:
        pass
    else:
        raise ValueError("Output directory must be outside the input directory.")

    files = sorted(source_root.rglob("*.txt"))
    total_replacements = 0

    for source_file in files:
        relative_path = source_file.relative_to(source_root)
        output_file = destination_root / relative_path
        original_text = source_file.read_bytes().decode("utf-8")
        replacement_count = original_text.count(search_text)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(
            original_text.replace(search_text, replacement_text).encode("utf-8")
        )
        total_replacements += replacement_count
        print(f"Processed {relative_path.as_posix()}: {replacement_count} replacement(s)")

    print(
        f"Processed {len(files)} file(s); "
        f"{total_replacements} replacement(s) total."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Replace literal text in UTF-8 .txt files, writing results separately."
    )
    parser.add_argument("--input-dir", required=True, help="Directory containing input .txt files.")
    parser.add_argument("--output-dir", required=True, help="Directory for processed files.")
    parser.add_argument("--find", required=True, help="Non-empty literal text to replace.")
    parser.add_argument("--replace", required=True, help="Replacement text; an empty string is allowed.")
    args = parser.parse_args()

    if not args.find:
        parser.error("--find must not be empty.")

    try:
        process_files(
            Path(args.input_dir),
            Path(args.output_dir),
            args.find,
            args.replace,
        )
    except (OSError, UnicodeDecodeError, ValueError) as error:
        parser.error(str(error))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| `--input-dir` | Required directory containing the input `.txt` files; searched recursively. | Required |
| `--output-dir` | Required destination directory for processed files; must be outside the input directory. Relative paths are preserved. | Required |
| `--find` | Non-empty literal text to replace in each file. | Required |
| `--replace` | Replacement text. An empty string removes matching text. | Required |

## Test Run Output
```text
Processed nested/notes.txt: 1 replacement(s)
Processed root.txt: 2 replacement(s)
Processed 2 file(s); 3 replacement(s) total.
```
