import z3
import typing as t


class TSDataTypes:
    """
    ECS engine data types
    """
    def __init__(self, ctx: z3.Context):
        _Module = z3.Datatype('Module', ctx)
        _Module.declare('make', ('id', z3.IntSort(ctx)))

        _Component = z3.Datatype('Component', ctx)
        _Component.declare('make', ('id', z3.IntSort(ctx)))

        _License = z3.Datatype('License', ctx)
        _License.declare('make', ('id', z3.IntSort(ctx)))
#        _License.declare('None')

        _Constraint = z3.Datatype('Constraint', ctx)
        _Constraint.declare('make', ('id', z3.IntSort(ctx)))

        self.Module, self.Component = z3.CreateDatatypes(_Module, _Component)
        self.License, self.Constraint = z3.CreateDatatypes(_License, _Constraint)

        # Structure assignments
        self.ModuleComponent = z3.Function('ModuleComponent', self.Module, self.Component, z3.BoolSort(ctx))
        self.ComponentLicense = z3.Function('ComponentLicense', self.Component, self.License, z3.BoolSort(ctx))

        # Constraint assignments
        self.ModuleConstraint = z3.Function('ModuleConstraint', self.Module, self.Constraint, z3.BoolSort(ctx))
        self.ComponentConstraint = z3.Function('ComponentConstraint', self.Component, self.Constraint, z3.BoolSort(ctx))
        self.LicenseConstraint = z3.Function('LicenseConstraint', self.License, self.Constraint, z3.BoolSort(ctx))

    


class TSObject(object):
    """
    Base class for objects representable by logical constants
    """
    __const_counter = 0
    
    def __init__(self, key: str):
        self.__key = key
        self.__const_key = TSObject.__const_counter        
        TSObject.__const_counter += 1
    
    @property
    def key(self):
        return self.__key

    def const(self, dt):
        return dt.make(self.__const_key)


class License(TSObject):
    def const(self, dt):        
        return super().const(dt.License)


class Constraint(TSObject):
    def const(self, dt):        
        return super().const(dt.Constraint)


class Rule(object):
    """
    Knowledge base types
    """
    def __init__(self, key: str, _type=""):
        self.__key = key
        self.__type = _type
    
    @property
    def key(self):
        return self.__key
    
    @property
    def type(self):
        return self.__type
    

class ConstraintsBuilder(object):
    """
    Provides constraints for the knowledge base
    """
    def __init__(self, ctx: z3.Context):
        self.__ctx = ctx
        self.__dt = TSDataTypes(ctx)
        self.__constraints: t.Dict[str, Constraint] = {}

    @property
    def context(self):
        return self.__ctx

    @property
    def types(self):
        return self.__dt

    def makeCnstr(self, cnstrId: str) -> Constraint:
        cnstr = self.__constraints.get(cnstrId)
        if not cnstr:
            cnstr = Constraint(cnstrId)
            self.__constraints[cnstrId] = cnstr
        
        return cnstr
    

    def makeModuleConst(self, name: str) -> z3.ExprRef:
        return z3.Const(name, self.__dt.Module)
    
    def makeComponentConst(self, name: str) -> z3.ExprRef:
        return z3.Const(name, self.__dt.Component)

    def makeLicenseConst(self, name: str) -> z3.ExprRef:
        return z3.Const(name, self.__dt.License)

    def makeCnstrConst(self, cnstrId: str) -> z3.ExprRef:
        return self.makeCnstr(cnstrId).const(self.__dt)


    def makeModuleCnstrExpr(self, cnstrId: str, mConst = None) -> z3.ExprRef:
        if mConst is None:
            mConst = self.makeModuleConst('m')

        return self.__dt.ModuleConstraint(mConst, self.makeCnstrConst(cnstrId))

    def makeComponentCnstrExpr(self, cnstrId, cConst = None) -> z3.ExprRef:
        if cConst is None:
            cConst = self.makeComponentConst('c')

        return self.__dt.ComponentConstraint(cConst, self.makeCnstrConst(cnstrId))

    def makeLicenseCnstrExpr(self, cnstrId, lConst = None) -> z3.ExprRef:
        if lConst is None:
            lConst = self.makeLicenseConst('l')

        return self.__dt.LicenseConstraint(lConst, self.makeCnstrConst(cnstrId))
