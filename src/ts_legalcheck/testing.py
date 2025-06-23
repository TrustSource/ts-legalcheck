import json

from typing import List, Dict
from pathlib import Path
from dataclasses import dataclass, asdict

from .engine import Engine
from .engine.context import Component, Module, loadModuleFromFile, resolveComponentsProperties

@dataclass
class Result:
    warnings: List[str]
    violations: List[str]
    obligations: List[str]
    properties: Dict[str, bool]

    def to_dict(self):
        return asdict(self)

def test_license(engine: Engine, lic: str, situation_file: Path) -> Result:
    with situation_file.open('r') as fp:
        situation = json.load(fp)

    c = Component('test', situation['component'], [lic])
    m = Module('test', situation['module'], [c])

    resolveComponentsProperties(m)

    result = engine.checkModule(m)['test'][lic]

    warnings = []
    violations = []

    for r in result.get('rules', []):
        rule = engine.rules[r]
        if rule.type == 'violation':
            violations.append(r)
        elif rule.type == 'warning':
            warnings.append(r)

    return Result(warnings=warnings,
                  violations=violations,
                  obligations=result.get('obligations', []),
                  properties=c.properties)