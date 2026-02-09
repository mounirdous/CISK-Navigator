#!/usr/bin/env python3
"""
Generate standalone HTML files from example YAML files
"""

from pathlib import Path
from datetime import datetime
from app import load_yaml_data, auto_detect_format, extract_metadata, APP_VERSION
from flask import Flask, render_template
import os

# Create minimal Flask app for rendering
app = Flask(__name__)

def generate_html_from_yaml(yaml_path: Path, output_path: Path):
    """Generate standalone HTML from YAML file"""
    print(f"Generating {output_path.name} from {yaml_path.name}...")

    with app.app_context():
        # Load and convert YAML
        yaml_data = load_yaml_data(str(yaml_path))
        js_data = auto_detect_format(yaml_data)
        metadata = extract_metadata(yaml_data)

        # Render HTML
        html_content = render_template(
            'navigator_enhanced.html',
            data=js_data,
            app_version=APP_VERSION,
            **metadata
        )

        # Write to file
        output_path.write_text(html_content, encoding='utf-8')
        print(f"✓ Generated {output_path.name}")

def main():
    # Define example files
    examples_dir = Path(__file__).parent / "examples"
    output_dir = examples_dir / "html"
    output_dir.mkdir(exist_ok=True)

    examples = [
        ("getting_fit.yaml", "getting_fit.html"),
        ("getting_rich.yaml", "getting_rich.html"),
        ("staying_curious.yaml", "staying_curious.html"),
        ("finding_job.yaml", "finding_job.html"),
    ]

    print(f"\nGenerating example HTML files...")
    print(f"App version: {APP_VERSION}\n")

    for yaml_name, html_name in examples:
        yaml_path = examples_dir / yaml_name
        output_path = output_dir / html_name

        if yaml_path.exists():
            generate_html_from_yaml(yaml_path, output_path)
        else:
            print(f"✗ Warning: {yaml_name} not found")

    print(f"\n✓ All HTML files generated in {output_dir}/")
    print(f"\nYou can now open these HTML files directly in your browser!")

if __name__ == '__main__':
    main()
