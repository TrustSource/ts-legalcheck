import logging
import typing as t
import glob

import ts_legalcheck.utils as utils

from pathlib import Path

from .marco import *
from .context import Module, Component
from .constraints import ConstraintsBuilder, Constraint, License, Rule
from .constraints.parser import Parser


logger = logging.getLogger('ts_legalcheck.engine')

class EngineError(Exception):
    pass


class Engine(ConstraintsBuilder):
    """
    TS Engine
    """
    def __init__(self, solver = None):
        self.__solver = solver if solver else Solver()
        
        super().__init__(ctx=self.__solver.ctx)

        self.__parser = Parser(builder=self)

        self.__rules = {}
        self.__licenses = {}
        self.__obligations = []

        self.__modsStack = []
        self.__compsStack = []
        self.__licsStack = []


    @property
    def solver(self):
        return self.__solver

    @property
    def rules(self):
        return self.__rules

    @property
    def licenses(self):
        return self.__licenses


    # Solver utils
    def __eval(self, cnstr):
        return is_true(self.__solver.model().eval(cnstr, model_completion=True))

    def __addFact(self, fact, tag:t.Optional[str]=None):
        if tag:
            fact = Implies(Bool(tag, self.context), fact)
        
        self.__solver.add(fact)


    def __makeCnstrFromObject(self, obj: dict, key: str) -> t.Optional[BoolRef]:
        value = obj.get(key)
        if value is None:
            return None

        if type(value) is str:
            """ Parses a single string value as a constraint"""
            return self.__parser.parse_cnstr(value)
        
        elif type(value) is list and all(type(item) is list for item in value):            
            """ Parses a list of lists as a CNF constraint"""            
            clauses = [Or([self.__parser.parse_cnstr(c) for c in clauses], self.context) 
                       for clauses in value if len(clauses) > 0]

            if len(clauses) > 0:
                return t.cast(BoolRef, And(clauses, self.context))
            else:
                return t.cast(BoolRef, True)
        
        else:
            print(f"WARNING: Wrong type of the '{key}' in a definition. String or list of lists is expected.")
            return None
    
    
    # Fork

    def fork(self):
        ctx = Context()
        solver = Solver(ctx=ctx)
        solver.add([a.translate(ctx) for a in self.__solver.assertions()])  # type: ignore

        newInst = Engine(solver=solver)        
        
        newInst.__rules = self.__rules
        newInst.__licenses = self.__licenses        
        newInst.__obligations = self.__obligations
        newInst.__constraints = self.__constraints

        return newInst


    # Loading and initialization of facts from the data set

    def loadConstraints(self, constraints: dict):
        def __makeSettingCnstr(obj):
            cnstr = self.__makeCnstrFromObject(obj, 'setting')
            if cnstr is None:
                cnstr = z3.BoolVal(True, self.context)
            return cnstr
            
        def __makeValueCnstr(obj):
            cnstr = self.__makeCnstrFromObject(obj, 'value')
            if cnstr is None:
                cnstr = z3.BoolVal(True, self.context)
            return cnstr

        # Load constraints
        
        l = self.makeLicenseConst('l')
        c = self.makeComponentConst('c')

        # In contrast to the obligations, there are no additional conditions for rights and terms
        # hence the rights and terms constraints can be enabled by the licenses

        for k, _ in constraints.get('Rights', {}).items():
            cCnstr = self.makeComponentCnstrExpr(k)
            lCnstr = self.makeLicenseCnstrExpr(k)

            self.__addFact(ForAll([l, c], Implies(self.types.ComponentLicense(c, l), cCnstr == lCnstr)))

        for k, _ in constraints.get('Terms', {}).items():
            cCnstr = self.makeComponentCnstrExpr(k)
            lCnstr = self.makeLicenseCnstrExpr(k)

            self.__addFact(ForAll([l, c], Implies(self.types.ComponentLicense(c, l), cCnstr == lCnstr)))

        # An obligation holds for a component IFF.
        # the obligation condition (distribution form, modification, etc.) is satisfied AND
        # it is enabled by the component's license

        variants = constraints.get('Variants', {})
        vCnstrs = {k: __makeSettingCnstr(variant) for k, variant in variants.items()}

        for k, o in constraints.get('Obligations', {}).items():
            self.__obligations.append(k)

            o_variants = o.get('variants', {})
            o_variants.update({ vk: {} for vk in variants.keys() if vk not in o_variants })

            if o_variants:
                for vk, variant in o_variants.items():
                    key = k + '__' + vk

                    # Setting is built from the:
                    #   - obligation settings
                    #   - variant's global settings
                    #   - variant's custom settings defined at obligation level

                    # Value is built from the:
                    #   - obligation value
                    #   - variant's custom value defined at obligation level

                    sCnstr = [__makeSettingCnstr(o)]
                    vCnstr = [__makeValueCnstr(o)] if 'value' in o else []

                    if vk and vk in variants:
                        sCnstr.append(vCnstrs[vk])
                        sCnstr.append(__makeSettingCnstr(variant))

                        if 'value' in variant:
                            vCnstr.append(__makeValueCnstr(variant))

                    cCnstr = self.makeComponentCnstrExpr(key)
                    lCnstr = self.makeLicenseCnstrExpr(key)

                    sCnstr = And(sCnstr, self.context)
                    vCnstr = Or(lCnstr, And(vCnstr, self.context), self.context) if vCnstr else lCnstr

                    impl = (cCnstr == And(sCnstr, vCnstr, self.context))

                    self.__addFact(ForAll([l, c], Implies(self.types.ComponentLicense(c, l), impl)))
            else:
                cCnstr = self.makeComponentCnstrExpr(k)
                lCnstr = self.makeLicenseCnstrExpr(k)

                # Setting constraint
                # Setting is defined in the DNF form as: [[c1, c2], [c3]] == (c1 && c2) || c3
                sCnstr = []
                for conj in o.get('setting', []):
                    sCnstr.append(And([self.makeComponentCnstrExpr(k) for k in conj], self.context))

                if len(sCnstr) == 0:
                    impl = (cCnstr == lCnstr)
                else:
                    impl = (cCnstr == And(lCnstr, Or(sCnstr, self.context), self.context))

                self.__addFact(ForAll([l, c], Implies(self.types.ComponentLicense(c, l), impl)))



    def loadRules(self, constraints: dict):
        rules = constraints.get('Rules', [])

        m = self.makeModuleConst('m')
        c = self.makeComponentConst('c')
        l = self.makeLicenseConst('l')

        for rule in rules:            
            if ruleId := rule.get('key'):
                self.__rules[ruleId] = Rule(ruleId, rule.get('type', ''))

            cond = And(self.types.ModuleComponent(m, c), 
                       self.types.ComponentLicense(c, l),                       
                       self.context)
            
            setting = self.__makeCnstrFromObject(rule, 'setting')
            if setting is None:
                setting = z3.BoolVal(True, self.context)

            # If neither 'require' nor 'equal' are present, consider the setting as a condition that always holds 
            if 'require' in rule:
                require = self.__makeCnstrFromObject(rule, 'require')
                fact = Implies(And(cond, setting, self.context), require, self.context)                

            elif 'equal' in rule:
                equal = self.__makeCnstrFromObject(rule, 'equal')
                fact = And(Implies(And(cond, setting, self.context), equal, self.context), 
                           Implies(And(cond, equal, self.context), setting, self.context), 
                           self.context)

            else:
                fact = And(cond, setting, self.context)


            self.__addFact(ForAll([m, c, l], fact), ruleId)



    def loadLicenses(self, constraints: dict):
        global logger

        constraints = constraints.get('Constraints', {})

        for key, cnstrs  in constraints.items():
            facts = []
            lic = License(key)
            
            for k, c in cnstrs.items():
                if type(c) is bool:
                    val = c
                elif type(c) is dict and 'value' in c:
                    val = c.get('value')
                else:
                    logger.info('Invalid license {}: invalid set of constraints'.format(key))
                    break

                cnstr = self.makeLicenseCnstrExpr(k, lic.const(self.types))
                facts.append(cnstr == val)


            if len(facts) == len(cnstrs):
                self.__licenses[lic.key] = lic
                self.__addFact(self.makeLicenseNameExpr(lic.key, lic.const(self.types)))
                
                for f in facts:
                    self.__addFact(f)


    def load(self, constraints: dict):
        self.loadLicenses(constraints)
        self.loadConstraints(constraints)
        self.loadRules(constraints)


    def push(self, el: Module|Component|License):
        solver = self.__solver
        solver.push()

        if isinstance(el, Module):
            m_const = self.types.Module.make(0)
            m_cnstr = [self.makeModuleCnstrExpr(key, m_const) == val for key, val in el.properties.items()]

            solver.add(m_cnstr)
            self.__modsStack.append(m_const)

        elif isinstance(el, Component):
            c_const = self.types.Component.make(0)
            c_cnstr = [self.makeComponentCnstrExpr(key, c_const) == val for key, val in el.properties.items()]

            solver.add(c_cnstr)
            if len(self.__modsStack) > 0:
                m_const = self.__modsStack[len(self.__modsStack) - 1]
                solver.add(self.types.ModuleComponent(m_const, c_const))
            self.__compsStack.append(c_const)

        elif isinstance(el, License):
            if len(self.__compsStack) > 0:
                c_const = self.__compsStack[len(self.__compsStack) - 1]
                l_const = el.const(self.types)
                solver.add(self.types.ComponentLicense(c_const, l_const))
                self.__licsStack.append(l_const)


    def pop(self, ty: t.Type[Module|Component|License]):
        stack = None

        if ty == Module:
            stack = self.__modsStack
        elif ty == Component:
            stack = self.__compsStack
        elif ty == License:
            stack = self.__licsStack

        if stack is not None:
            stack.pop()
            self.__solver.pop()


    def checkLicense(self, lic):
        self.push(lic)

        def extractObligations():
            obligations = []
            if len(self.__compsStack) > 0:
                c_const = self.__compsStack[len(self.__compsStack) - 1]
                for _key in self.__obligations:
                    if self.__eval(self.makeComponentCnstrExpr(_key, c_const)):
                        obligations.append(_key)

                    # elif self.__eval(self.__makeComponentCnstr(f'{_key}__A', c_const)):                        
                    #     obligations.append(f'{_key}__A')
                    # elif self.__eval(self.__makeComponentCnstr(f'{_key}__B', c_const)):
                    #     obligations.append(f'{_key}__B')
                    # elif self.__eval(self.__makeComponentCnstr(f'{_key}__C', c_const)):
                    #     obligations.append(f'{_key}__C')
                    # elif self.__eval(self.__makeComponentCnstr(f'{_key}__D', c_const)):
                    #     obligations.append(f'{_key}__D')

            return obligations

        solver = self.__solver
        assumptions = [Bool(key, solver.ctx) for key in self.__rules.keys()]

        if solver.check(assumptions) == sat:
            logging.info(f'License {lic.key} is SAT')
            result = {
                'status': 'SAT',
                'obligations': extractObligations()
            }

        else:
            logging.info(f'License {lic.key} is UNSAT')

            c_solver = SubsetSolver(assumptions, solver)
            m_solver = MapSolver(n=c_solver.n)
            sets = enumerate_sets(c_solver, m_solver)

            violations = []
            for orig, tags in sets:
                if orig == 'MUS':
                    for tag in tags:
                        tn = tag.decl().name()
                        violations.append(self.__rules[tn].key)            

            result = {
                'status': 'UNSAT',
                'rules': violations
            }

            # Disable violated rules to make the context SAT and extract obligations
            assumptions = [Bool(key, solver.ctx) for key in self.__rules.keys() if key not in violations]
            if solver.check(assumptions) == sat:
                result['obligations'] = extractObligations()


        self.pop(License)
        return result


    def checkComponent(self, comp, *args):
        self.push(comp)

        lics = utils.get_args(args)
        if len(lics) == 0:
            lics = comp.licenses

        result = {}

        for l in lics:
            lic = self.__licenses.get(l, None)
            if lic is None:
                logging.warning(f'License {l} is not defined in the engine. Skipping...')
                result[l] = {
                    'status': 'UNKNOWN',
                    'reason': 'License could not be matched correctly'
                }
            else:
                result[l] = self.checkLicense(lic)

        self.pop(Component)
        return result


    def checkModule(self, mod, *args):
        self.push(mod)

        comps = utils.get_args(args)
        if len(comps) == 0:
            comps = mod.components

        result = {}
        for c in comps:
            result[c.key] = self.checkComponent(c)

        self.pop(Module)
        return result


_package_definitions_path=Path(__file__).parent / 'definitions'

def loadDefinitions(paths: t.List[Path]) -> t.Dict[str, t.Dict[str, t.Any]]:                
    def resolve_path(path: Path, parent: t.Optional[Path] = None) -> t.Optional[Path]:
        if path.exists():
            return path
        
        search_paths = [            
            _package_definitions_path
        ]

        if parent:
            search_paths.append(parent)

        for sp in search_paths:
            if (_path := sp / path).exists():
                return _path

        return None

    result = {}
    
    _paths: t.List[t.Tuple[Path, t.Optional[Path]]] = [(p, None) for p in paths]
    
    while len(_paths) > 0:
        if p := resolve_path(*_paths.pop()):
            logger.info(f'Loading definitions from {p}...')
            if defs := utils.load_file(p):
                for include in defs.pop('Includes', []):
                    if "*" in include:
                        includes = [(Path(include_path), p.parent) for include_path in glob.glob(include, root_dir=p.parent)]
                        if not includes:
                            includes = [(Path(include_path), None) for include_path in glob.glob(include, root_dir=_package_definitions_path)]                        
                        
                        _paths.extend(includes)                        
                    else:            
                        _paths.append((Path(include), p.parent))
                

                for k, _d in defs.items():
                    if _e := result.get(k, None):
                        if type(_d) is list and type(_e) is list:
                            _e.extend(_d)
                        elif type(_d) is dict and type(_e) is dict:
                            _e.update(_d)
                        else:
                            raise ValueError(f"Cannot merge {k} definitions from {p.name}. Not compatible types.")
                    else:
                        result[k] = _d

    return result


def createEngine(paths: t.List[Path]) -> Engine:
    defs = loadDefinitions(paths)
    return createEngineWithDefinitions(defs)


def createEngineWithDefinitions(defs: dict) -> Engine:
    solver = Solver(ctx = Context())
    engine = Engine(solver = solver)
    engine.load(defs)

    logger.info('ts-legalcheck engine loaded')

    return engine