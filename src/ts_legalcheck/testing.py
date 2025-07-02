import json
import typing as t

from pathlib import Path
from dataclasses import dataclass, asdict

from .engine import Engine
from .engine.context import Component, Module

from .utils import load_file

@dataclass
class Result:
    warnings: t.List[str]
    violations: t.List[str]
    obligations: t.List[str]
    properties: t.Dict[str, bool]

    def to_dict(self):
        return asdict(self)

def test_license(engine: Engine, lic: str, situation_file: Path) -> t.Optional[Result]:
    situation = load_file(situation_file)

    if not situation:
        return None
        
    c = Component('test', situation['component'], [lic])
    m = Module('test', situation['module'], [c])
    
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