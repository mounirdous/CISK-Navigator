"""
CISK Navigator Enhanced - Flask Application
Supports multi-links, priorities, weights, and impacts
"""

import json
import yaml
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, make_response
from typing import Dict, List

app = Flask(__name__)

# App version - displayed in generated HTML files
APP_VERSION = "2.2"


def load_yaml_data(file_path: str) -> Dict:
    """Load and parse the YAML input file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data


def convert_enhanced_format(yaml_data: Dict) -> Dict:
    """
    Convert enhanced YAML format with multi-links to JavaScript format

    Handles:
    - Challenge/sub-challenge priorities
    - Initiative -> multiple challenges (with weight & impact)
    - System -> multiple initiatives (with weight)
    - KPI -> multiple systems (with weight)
    """
    js_data = {
        "meta": {
            "generated": yaml_data.get("meta", {}).get("generated", datetime.now().isoformat()),
            "sourceDeck": yaml_data.get("meta", {}).get("title", "CISK Navigator Enhanced")
        },
        "challengeGroups": [],
        "subChallenges": [],
        "initiatives": [],
        "systems": [],
        "kpis": []
    }

    # Convert challenge groups (with priority)
    for group in yaml_data.get("challenge_groups", []):
        js_data["challengeGroups"].append({
            "id": group["id"],
            "number": group["number"],
            "title": group["title"],
            "priority": group.get("priority", 3)  # Default to lowest priority
        })

    # Convert sub-challenges (with priority)
    for sub in yaml_data.get("sub_challenges", []):
        js_data["subChallenges"].append({
            "id": sub["id"],
            "groupId": sub["group_id"],
            "text": sub["text"],
            "priority": sub.get("priority", 3)
        })

    # Convert initiatives (with challenge links, weights, and impacts)
    for init in yaml_data.get("initiatives", []):
        init_obj = {
            "id": init["id"],
            "season": init.get("season", ""),
            "text": init["text"],
            "raw": init.get("raw", init["text"]),
            "challenges": []
        }

        # Add challenge links with weight and impact
        for link in init.get("challenges", []):
            init_obj["challenges"].append({
                "challengeId": link["challenge_id"],
                "weight": link.get("weight", 5),
                "impact": link.get("impact", "M")  # L, M, or H
            })

        js_data["initiatives"].append(init_obj)

    # Convert systems (with initiative links and weights)
    for sys in yaml_data.get("systems", []):
        sys_obj = {
            "id": sys["id"],
            "text": sys.get("text", ""),
            "title": sys.get("title", ""),
            "initiatives": []
        }

        # Handle both simple text and detailed format
        if "bullets" in sys:
            sys_obj["bullets"] = sys["bullets"]
        if "type" in sys:
            sys_obj["type"] = sys["type"]

        # Add initiative links with weights
        for link in sys.get("initiatives", []):
            sys_obj["initiatives"].append({
                "initiativeId": link["initiative_id"],
                "weight": link.get("weight", 5)
            })

        js_data["systems"].append(sys_obj)

    # Convert KPIs (with system links and weights)
    for kpi in yaml_data.get("kpis", []):
        kpi_obj = {
            "id": kpi["id"],
            "text": kpi["text"],
            "systems": []
        }

        # Add system links with weights
        for link in kpi.get("systems", []):
            kpi_obj["systems"].append({
                "systemId": link["system_id"],
                "weight": link.get("weight", 5)
            })

        js_data["kpis"].append(kpi_obj)

    return js_data


def convert_legacy_format(yaml_data: Dict) -> Dict:
    """
    Convert legacy YAML format (with groupId) to enhanced format
    For backward compatibility
    """
    js_data = {
        "meta": {
            "generated": yaml_data.get("meta", {}).get("generated", datetime.now().isoformat()),
            "sourceDeck": yaml_data.get("meta", {}).get("title", "CISK Navigator")
        },
        "challengeGroups": [],
        "subChallenges": [],
        "initiatives": [],
        "systems": [],
        "kpis": []
    }

    # Convert challenge groups
    for group in yaml_data.get("challenge_groups", []):
        js_data["challengeGroups"].append({
            "id": group["id"],
            "number": group["number"],
            "title": group["title"],
            "priority": group.get("priority", 2)
        })

    # Convert sub-challenges
    for sub in yaml_data.get("sub_challenges", []):
        js_data["subChallenges"].append({
            "id": sub["id"],
            "groupId": sub["group_id"],
            "text": sub["text"],
            "priority": sub.get("priority", 2)
        })

    # Convert initiatives (legacy format - use groupId to infer challenge)
    for init in yaml_data.get("initiatives", []):
        init_obj = {
            "id": init["id"],
            "season": init.get("season", ""),
            "text": init["text"],
            "raw": init.get("raw", init["text"]),
            "challenges": []
        }

        # Legacy: use groupId to create implicit link
        if "group_id" in init:
            init_obj["legacyGroupId"] = init["group_id"]

        js_data["initiatives"].append(init_obj)

    # Convert systems
    for sys in yaml_data.get("systems", []):
        sys_obj = {
            "id": sys["id"],
            "text": sys.get("text", ""),
            "title": sys.get("title", ""),
            "initiatives": []
        }

        if "group_id" in sys:
            sys_obj["legacyGroupId"] = sys["group_id"]
        if "bullets" in sys:
            sys_obj["bullets"] = sys["bullets"]
        if "type" in sys:
            sys_obj["type"] = sys["type"]

        js_data["systems"].append(sys_obj)

    # Convert KPIs
    for kpi in yaml_data.get("kpis", []):
        kpi_obj = {
            "id": kpi["id"],
            "text": kpi["text"],
            "systems": []
        }

        if "group_id" in kpi:
            kpi_obj["legacyGroupId"] = kpi["group_id"]

        js_data["kpis"].append(kpi_obj)

    return js_data


def auto_detect_format(yaml_data: Dict) -> Dict:
    """
    Auto-detect if YAML is enhanced or legacy format
    """
    # Check if any initiative has 'challenges' array (enhanced format)
    initiatives = yaml_data.get("initiatives", [])
    if initiatives and "challenges" in initiatives[0]:
        return convert_enhanced_format(yaml_data)
    else:
        return convert_legacy_format(yaml_data)


@app.route('/')
def index():
    """Main route - display the enhanced navigator"""
    data_file = Path(__file__).parent / "data" / "full_sample_enhanced.yaml"

    try:
        yaml_data = load_yaml_data(str(data_file))
        js_data = auto_detect_format(yaml_data)

        title = yaml_data.get("meta", {}).get("title", "CISK Navigator Enhanced")

        return render_template(
            'navigator_enhanced.html',
            data=js_data,
            title=title,
            version=APP_VERSION
        )
    except Exception as e:
        return f"Error loading data: {str(e)}", 500


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Show upload form or process uploaded YAML file"""
    if request.method == 'GET':
        return render_template('upload.html', version=APP_VERSION)

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith(('.yaml', '.yml')):
        return jsonify({"error": "File must be YAML format"}), 400

    try:
        yaml_content = file.read().decode('utf-8')
        yaml_data = yaml.safe_load(yaml_content)
        js_data = auto_detect_format(yaml_data)

        title = yaml_data.get("meta", {}).get("title", "CISK Navigator Enhanced")

        # Calculate statistics from uploaded data
        stats = {
            'groups': len(js_data.get('challengeGroups', [])),
            'challenges': len(js_data.get('subChallenges', [])),
            'initiatives': len(js_data.get('initiatives', [])),
            'systems': len(js_data.get('systems', [])),
            'kpis': len(js_data.get('kpis', []))
        }

        return render_template(
            'navigator_enhanced.html',
            data=js_data,
            title=title,
            version=APP_VERSION,
            upload_stats=stats
        )
    except Exception as e:
        return jsonify({"error": f"Error parsing file: {str(e)}"}), 500


@app.route('/api/data')
def get_data():
    """API endpoint to get the current data as JSON"""
    data_file = Path(__file__).parent / "data" / "full_sample_enhanced.yaml"

    try:
        yaml_data = load_yaml_data(str(data_file))
        js_data = auto_detect_format(yaml_data)
        return jsonify(js_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/generate', methods=['POST'])
def generate_standalone():
    """Generate a standalone HTML file from uploaded YAML"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith(('.yaml', '.yml')):
        return jsonify({"error": "File must be YAML format"}), 400

    try:
        yaml_content = file.read().decode('utf-8')
        yaml_data = yaml.safe_load(yaml_content)
        js_data = auto_detect_format(yaml_data)

        title = yaml_data.get("meta", {}).get("title", "CISK Navigator Enhanced")

        html_content = render_template(
            'navigator_enhanced.html',
            data=js_data,
            title=title,
            version=APP_VERSION
        )

        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        response.headers['Content-Disposition'] = f'attachment; filename="cisk_navigator_enhanced_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html"'

        return response
    except Exception as e:
        return jsonify({"error": f"Error generating file: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
