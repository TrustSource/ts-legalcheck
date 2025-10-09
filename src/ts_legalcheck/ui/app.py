import os
import toml
import typing as t

from pathlib import Path
from flask import Flask, render_template, request, jsonify

from ts_legalcheck.engine import loadDefinitions, createEngineWithDefinitions
from ts_legalcheck.testing import create_test_module


app = Flask(__name__)

MODELS_DIR = Path(os.environ.get('TS_LEGALCHECK_MODELS_PATH', 'data'))
PRESETS_DIR = Path(os.environ.get('TS_LEGALCHECK_PRESETS_PATH', MODELS_DIR / 'use-cases/presets'))
LEGALSETTINGS_FILE = Path(os.environ.get('TS_LEGALCHECK_LEGALSETTINGS_PATH', MODELS_DIR / 'use-cases/LegalSettings.toml'))

# Helper to list presets (files in PRESETS_DIR)
def get_presets() -> t.List[str]:
    if not PRESETS_DIR.exists():
        return []
    return [f for f in os.listdir(PRESETS_DIR)
              if f.endswith('.toml') or f.endswith('.json')]

# Helper to load preset values
def load_preset(preset_file) -> dict:
    try:
        path = PRESETS_DIR / preset_file
        if preset_file.endswith('.toml'):
            return toml.load(path)
        elif preset_file.endswith('.json'):
            import json
            with open(path) as f:
                return json.load(f)
        else:
            return {}
    except Exception:
        return {}

# Helper to list models (files in MODELS_DIR)
def get_models() -> t.List[str]:
    return [f for f in os.listdir(MODELS_DIR) 
              if f.endswith('.toml') or f.endswith('.json')]

# Helper to load questions from LegalSettings.toml
def get_questions() -> dict:
    try:
        data = toml.load(LEGALSETTINGS_FILE)
        # Return all scopes as-is
        return data
    
    except Exception:
        return {}

# Helper to get licenses from a model file
def get_licenses(model_file) -> t.List[str]:
    app.logger.info(f"Loading licenses for model: {model_file}")    
    try:
        defs = loadDefinitions(MODELS_DIR / model_file)        
        return list(defs.get('Constraints', {}).keys())
    except Exception as err:
        app.logger.error(f"Error loading licenses")
        app.logger.exception        
        return []

@app.route('/')
def index():
    models = get_models()
    questions = get_questions()
    presets = get_presets()
    return render_template('index.html', models=models, questions=questions, presets=presets)

@app.route('/preset')
def preset():
    preset_name = request.args.get('preset')
    values = load_preset(preset_name) if preset_name else {}
    return jsonify(values)

@app.route('/licenses')
def licenses():
    model = request.args.get('model')
    licenses = get_licenses(model) if model else []
    return jsonify(licenses)


@app.route('/test', methods=['POST'])
def test():
    data = request.json or {}

    model = data.get('model')
    licenses = data.get('licenses', [])
    use_case = data.get('use-case', {})
      
    app.logger.info(f"Testing licenses: {licenses}")

    defs: dict = loadDefinitions(MODELS_DIR / model) if model else {}
    obligations = { key: obl['description'] for key, obl in defs.get('Obligations', {}).items() }

    engine = createEngineWithDefinitions(defs)
    m = create_test_module(use_case, licenses)
    check_result = engine.checkModule(m, extended_results=False)['test']

    # Obligations table
    obligations_tbl = []
    for lic in licenses:
        result = check_result[lic]
        result_obls = result.get('obligations', [])
        obligations_tbl.append([o in result_obls for o in obligations.keys()])

    # Collect all unique rule keys (violations/warnings) across all licenses from 'rules' field
    all_rule_keys = set()
    for lic in licenses:
        result = check_result[lic]
        for r in result.get('rules', []):
            all_rule_keys.add(r)

    # Get rule details (message/type) from defs
    rule_details = {}
    rules_defs = defs.get('Rules', [])

    for r in rules_defs:
        if (key := r.get('key')) and key in all_rule_keys:
            rule_details[key] = {
                'type': r.get('type', 'none'),
                'message': r.get('message', key)                
            }

    violations = [
        {'key': k, 'message': v['message'], 'type': v['type']} for k, v in rule_details.items()
    ]
    
    violations_tbl = []
    for lic in licenses:
        result = check_result[lic]
        lic_rules = set(result.get('rules', []))
        violations_tbl.append([v['key'] in lic_rules for v in violations])

    results = {
        'obligations': list(obligations.values()),
        'obligations_tbl': obligations_tbl,
        'licenses': licenses,
        'violations': violations,
        'violations_tbl': violations_tbl
    }

    return jsonify(results)
