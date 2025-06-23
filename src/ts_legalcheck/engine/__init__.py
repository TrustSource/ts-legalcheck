import logging
import typing as t
import glob


from pathlib import Path

from .marco import *
from .context import *

import ts_legalcheck.utils as utils

logger = logging.getLogger('ts_legalcheck.engine')


class TSConstObject(TSObject):
    """
    Base class for objects representable by logical constants
    """
    __const_counter = 0

    def __init__(self, key):
        super(TSConstObject, self).__init__(key)
        self.__const_key = TSConstObject.__const_counter
        TSConstObject.__const_counter += 1

    def const(self, dt):
        return dt.make(self.__const_key)



class Rule(TSObject):
    """
    Knowledge base types
    """

    def __init__(self, key, _type=""):
        super(Rule, self).__init__(key)
        self.__type = _type

    @property
    def type(self):
        return self.__type


class Constraint(TSConstObject):
    def __init__(self, key):
        super(Constraint, self).__init__(key)

        key_parts = self.key.split('.')

        self.scope = key_parts[0] if len(key_parts) > 1 else ''
        self.property = key_parts[1] if len(key_parts) > 1 else key

    def const(self, dt):
        return super(Constraint, self).const(dt.Constraint)


class License(TSConstObject):
    def __init__(self, key):
        super(License, self).__init__(key)

    def const(self, dt):
        return super(License, self).const(dt.License)



class EngineError(Exception):
    pass


class TSDataTypes:
    """
    ECS engine data types
    """
    def __init__(self, ctx = None):
        _Module = Datatype('Module', ctx)
        _Module.declare('make', ('id', IntSort(ctx)))

        _Component = Datatype('Component', ctx)
        _Component.declare('make', ('id', IntSort(ctx)))

        _License = Datatype('License', ctx)
        _License.declare('make', ('id', IntSort(ctx)))
#        _License.declare('None')

        _Constraint = Datatype('Constraint', ctx)
        _Constraint.declare('make', ('id', IntSort(ctx)))

        self.Module, self.Component = CreateDatatypes(_Module, _Component)
        self.License, self.Constraint = CreateDatatypes(_License, _Constraint)

        # Structure assignments
        self.ModuleComponent = Function('ModuleComponent', self.Module, self.Component, BoolSort(ctx))
        self.ComponentLicense = Function('ComponentLicense', self.Component, self.License, BoolSort(ctx))

        # Constraint assignments
        self.ModuleConstraint = Function('ModuleConstraint', self.Module, self.Constraint, BoolSort(ctx))
        self.ComponentConstraint = Function('ComponentConstraint', self.Component, self.Constraint, BoolSort(ctx))
        self.LicenseConstraint = Function('LicenseConstraint', self.License, self.Constraint, BoolSort(ctx))




class Engine:
    """
    TS Engine
    """
    def __init__(self, solver = None):
        if not solver:
            self.__solver = Solver()
        else:
            self.__solver = solver

        self.__ctx = self.__solver.ctx
        self.__dt = TSDataTypes(self.__ctx)

        self.__rules = {}
        self.__licenses = {}
        self.__constraints = {}
        self.__obligations = []

        self.__modsStack = []
        self.__compsStack = []
        self.__licsStack = []

    @property
    def types(self):
        return self.__dt

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

    def __addFact(self, fact, tag=''):
        if tag != '':
            fact = Implies(Bool(tag, self.__ctx), fact)

        self.__solver.add(fact)

    def __getCnstr(self, cnstrId):
        c_id = cnstrId.strip('!')
        cnstr = self.__constraints.get(c_id, None)

        if cnstr is None:
            cnstr = Constraint(c_id)
            self.__constraints[c_id] = cnstr

        return cnstr


    @staticmethod
    def __makeCnstrTerm(cnstrId, term):
        if cnstrId[0] == '!':
            return Not(term)
        else:
            return term


    def __makeCnstr(self, cnstrId: str):
        cnstr = self.__getCnstr(cnstrId)

        if cnstr.scope == 'Module':
            return self.__makeModuleCnstr(cnstrId)
        else:
            return self.__makeComponentCnstr(cnstrId)

    def __makeModuleCnstr(self, cnstrId, mConst = None):
        if mConst is None:
            mConst = Const('m', self.types.Module)

        term = self.types.ModuleConstraint(mConst, self.__getCnstr(cnstrId).const(self.types))
        return self.__makeCnstrTerm(cnstrId, term)

    def __makeComponentCnstr(self, cnstrId, cConst = None):
        if cConst is None:
            cConst = Const('c', self.types.Component)

        term = self.types.ComponentConstraint(cConst, self.__getCnstr(cnstrId).const(self.types))
        return self.__makeCnstrTerm(cnstrId, term)

    def __makeLicenseCnstr(self, cnstrId, lConst = None):
        if lConst is None:
            lConst = Const('l', self.types.License)

        term = self.types.LicenseConstraint(lConst, self.__getCnstr(cnstrId).const(self.types))
        return self.__makeCnstrTerm(cnstrId, term)


    def __makeCNFCnstr(self, cnstr: t.List[t.List[str]], builder):
        """
        Creates a fromula from the list presentation in CNF form
        Example: [[c1, c2], [c3]] is equal to a CNF formula (c1 || c2) && (c3)
        :param cnstr: List of lists of atomic clauses
        :return: Z3 term
        """
        return And([Or([builder(c) for c in clauses], self.__ctx) for clauses in cnstr], self.__ctx)


    def __makeCNFCnstrFromObject(self, obj: dict, key: str, builder):
        value = obj.get(key, [])
        if type(value) is not list or any(type(item) is not list for item in value):
            print(f"WARNING: Wrong type of the '{key}' in a definition. List of lists is expected.")
            value = []

        return self.__makeCNFCnstr(value, builder)



    # Fork

    def fork(self):
        ctx = Context()
        solver = Solver(ctx=ctx)        
        solver.add([a.translate(ctx) for a in self.__solver.assertions()])  # type: ignore

        newInst = Engine(solver)
        newInst.__rules = self.__rules
        newInst.__licenses = self.__licenses
        newInst.__constraints = self.__constraints
        newInst.__obligations = self.__obligations

        return newInst


    # Loading and initialization of facts from the data set

    def loadConstraints(self, constraints: dict):
        def __makeSettingCnstr(obj):
            return self.__makeCNFCnstrFromObject(obj, 'setting', self.__makeCnstr)

        def __makeValueCnstr(obj):
            return self.__makeCNFCnstrFromObject(obj, 'value', self.__makeCnstr)

        # Load constraints

        l = Const('l', self.types.License)
        c = Const('c', self.types.Component)

        # In contrast to the obligations, there are no additional conditions for rights and terms
        # hence the rights and terms constraints can be enabled by the licenses

        for k, _ in constraints.get('Rights', {}).items():
            cCnstr = self.__makeComponentCnstr(k)
            lCnstr = self.__makeLicenseCnstr(k)

            self.__addFact(ForAll([l, c], Implies(self.types.ComponentLicense(c, l), cCnstr == lCnstr)))

        for k, _ in constraints.get('Terms', {}).items():
            cCnstr = self.__makeComponentCnstr(k)
            lCnstr = self.__makeLicenseCnstr(k)

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

                    cCnstr = self.__makeComponentCnstr(key)
                    lCnstr = self.__makeLicenseCnstr(key)

                    sCnstr = And(sCnstr, self.__ctx)
                    vCnstr = Or(lCnstr, And(vCnstr, self.__ctx), self.__ctx) if vCnstr else lCnstr

                    impl = (cCnstr == And(sCnstr, vCnstr, self.__ctx))

                    self.__addFact(ForAll([l, c], Implies(self.types.ComponentLicense(c, l), impl)))
            else:
                cCnstr = self.__makeComponentCnstr(k)
                lCnstr = self.__makeLicenseCnstr(k)

                # Setting constraint
                # Setting is defined in the DNF form as: [[c1, c2], [c3]] == (c1 && c2) || c3
                sCnstr = []
                for conj in o.get('setting', []):
                    sCnstr.append(And([self.__makeComponentCnstr(k) for k in conj], self.__ctx))

                if len(sCnstr) == 0:
                    impl = (cCnstr == lCnstr)
                else:
                    impl = (cCnstr == And(lCnstr, Or(sCnstr, self.__ctx), self.__ctx))

                self.__addFact(ForAll([l, c], Implies(self.types.ComponentLicense(c, l), impl)))



    def loadRules(self, constraints: dict):
        rules = constraints.get('Rules', [])

        m = Const('m', self.types.Module)
        c = Const('c', self.types.Component)

        for rule in rules:
            ruleId = rule.get('key', '')
            if ruleId != '':
                self.__rules[ruleId] = Rule(ruleId, rule.get('type', ''))

            cond = self.__makeCNFCnstrFromObject(rule, 'setting', self.__makeCnstr)
            cond = And(self.types.ModuleComponent(m, c), cond, self.__ctx)

            # If require is empty, consider it as False, i.e. the rule should always trigger
            if 'require' in rule:
                require = self.__makeCNFCnstrFromObject(rule, 'require', self.__makeCnstr)
            else:
                require = False

            self.__addFact(ForAll([m, c], Implies(cond, require)), ruleId)



    def loadLicenses(self, constraints: dict):
        global logger

        constraints = constraints.get('Constraints', {})

        for key, cnstrs  in constraints.items():
            facts = []
            l = License(key)

            for k, c in cnstrs.items():
                if type(c) is bool:
                    val = c
                elif type(c) is dict and 'value' in c:
                    val = c.get('value')
                else:
                    logger.info('Invalid license {}: invalid set of constraints'.format(key))
                    break

                cnstr = self.__makeLicenseCnstr(k, l.const(self.types))
                facts.append(cnstr == val)


            if len(facts) == len(cnstrs):
                self.__licenses[l.key] = l
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
            m_cnstr = [self.__makeModuleCnstr(cnstr.key, m_const) == el.properties.get(cnstr.property, False)
                       for cnstr in self.__constraints.values() if cnstr.scope == 'Module']

            solver.add(m_cnstr)
            self.__modsStack.append(m_const)

        elif isinstance(el, Component):
            c_const = self.types.Component.make(0)
            c_cnstr = [self.__makeComponentCnstr(cnstr.key, c_const) == el.properties.get(cnstr.property, False)
                       for cnstr in self.__constraints.values() if cnstr.scope == 'Component']

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
                    if self.__eval(self.__makeComponentCnstr(_key, c_const)):
                        obligations.append(_key)

            return obligations

        solver = self.__solver
        assumptions = [Bool(key, solver.ctx) for key in self.__rules.keys()]

        if solver.check(assumptions) == sat:
            result = {
                'status': 'SAT',
                'obligations': extractObligations()
            }

        else:
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



def loadDefinitions(paths: t.List[Path]) -> t.Dict[str, t.Dict[str, t.Any]]:    
    from json import JSONDecodeError

    
    def resolve_path(path: Path, parent: t.Optional[Path] = None) -> t.Optional[Path]:
        if path.exists():
            return path
        
        search_paths = [            
            Path(__file__).parent / 'definitions'            
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
            with p.open('r') as fp:
                try:
                    defs = json.load(fp)
                    
                    for include in defs.pop('Includes', []):
                        if "*" in include:
                            for include_path in glob.glob(os.path.join(p.parent, include)):
                                _paths.append((Path(include_path), None))
                        else:            
                            _paths.append((Path(include), p.parent))
                    

                    for k, _d in defs.items():
                        if _e := result.get(k, None):
                            if type(_d) is list and type(_e) is list:
                                _e.extend(_d)
                            elif type(_d) is dict and type(_e) is dict:
                                _e.update(_d)
                            else:
                                raise ValueError(f"Cannot merge {k} definitions from {fp.name}. Not compatible types.")
                        else:
                            result[k] = _d

                except JSONDecodeError as err:
                    print(f'Cannot decode {str(p)}')
                    print(err)

    return result


def createEngine(paths: t.List[Path]) -> Engine:
    defs = loadDefinitions(paths)
    return createEngineWithDefinitions(defs)


def createEngineWithDefinitions(defs: dict) -> Engine:
    solver = Solver(ctx = Context())
    engine = Engine(solver)
    engine.load(defs)

    logger.info('ts-legalcheck engine loaded')

    return engine