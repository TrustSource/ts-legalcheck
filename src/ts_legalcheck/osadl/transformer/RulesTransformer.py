from typing import Any, List, Iterable, Dict, Optional, Union

from .ConstraintsExtractor import ConstraintsExtractor

class UnsupportedRuleError(Exception):
    pass


class RulesTransformer(ConstraintsExtractor):    
    """Transform methods for each OSADL license language element."""

    def __init__(self):
        super().__init__()
        
        self.__OR_IFs: List[str] = []
    
    @staticmethod
    def _values_to_expr(values: Iterable[Union[str, Optional[str]]], op: str) -> Optional[str]:
        values = [v for v in values if v]
        
        if len(values) > 1:
            return f"({op} {' '.join(values)})"
        elif len(values) == 1:
            return values[0]
        else:
            return None
        

    def NO_OP(self, value: Dict[str, str]) -> Optional[str]:
        if or_if := value.pop('OR_IF', None):
            self.__OR_IFs.append(or_if)

        return self._values_to_expr(value.values(), 'and')
    
    def AND(self, value: Iterable[dict]) -> Optional[str]:
      return self._values_to_expr([self.NO_OP(val) for val in value], 'and')
        
    def OR(self, value: Iterable[dict]) -> Optional[str]:
        return self._values_to_expr([self.NO_OP(val) for val in value], 'or')

    def EITHER(self, value: Iterable[dict]) -> Optional[str]:
        return self._values_to_expr([self.NO_OP(val) for val in value], 'xor')

    def IF(self, value: Dict[str, str]) -> Optional[str]:
        conds = [f"(implies {self._get_property(key)} {val})" for key, val in value.items()]
        return self._values_to_expr(conds, 'and')
    
    def EXCEPT_IF(self, value: Dict[str, str]) -> Optional[str]:
        conds = [f"(implies !{self._get_property(key)} {val})" for key, val in value.items()]
        return self._values_to_expr(conds, 'and')
    
    def USE_CASE(self, value: Dict[str, str]) -> Optional[str]:
        return self.IF(value)

    def YOU_MUST(self, value: Dict[str, Any]) -> Optional[str]:
        obligations = [self._get_obligation(key) for key in value.keys()]
        return self._values_to_expr(obligations, 'and')
    
    def YOU_MUST_NOT(self, value: Any) -> Optional[str]:
        obligations = [f"!{self._get_obligation(key)}" for key in value.keys()]
        return self._values_to_expr(obligations, 'and')


    def OR_IF(self, value: Iterable[str]) -> Optional[str]:        
        raise UnsupportedRuleError()
        
        # """
        # OF_IF itself is equivalent to IF. 
        # The difference is only that it has to be disjoint with preceding OR_IFs or EITHER_IFs 
        # (w.r.t. to the tree level), i.e. not cojoint inside the current list. (really crazy)
        # """
        # or_if_expr = self._values_to_expr([self.IF(val) for val in value], 'and')

        # if self.__OR_IFs:
        #     or_conds = [self.__OR_IFs.pop()]            
        #     if or_if_expr:
        #         or_conds.append(or_if_expr)

        #     or_if_expr = self.OR(or_conds)
            
        # return or_if_expr


    def EITHER_IF(self, value: Iterable[str]) -> Optional[str]:
        raise UnsupportedRuleError()
    
        # conds = [f"(implies {self._get_property(key)} {val})" for key, val in value.items()]
        # if len(conds) > 0:
        #     either_conds = [self._get_property(key) for key in value.keys()]
        #     if either_expr := self._values_to_expr(either_conds, 'xor'):
        #         conds.append(either_expr)

        # either_if_expr = self.AND(conds)        
        
        # if self.__OR_IFs:
        #     or_conds = self.__OR_IFs
        #     if either_if_expr:
        #         or_conds.append(either_if_expr)
            
        #     either_if_expr = self.OR(conds)
        #     self.__OR_IFs = []
            
        
        # return either_if_expr

    

    def ATTRIBUTE(self, value: Any) -> Optional[str]:
        return None

    def COMPATIBILITY(self, value: Any) -> Optional[str]:
        return None

    def COPYLEFT_CLAUSE(self, value: Any) -> Optional[str]:
        return None

    def DEPENDING_COMPATIBILITY(self, value: Any) -> Optional[str]:
        return None

    def INCOMPATIBILITY(self, value: Any) -> Optional[str]:
        return None

    def INCOMPATIBLE_LICENSES(self, value: Any) -> Optional[str]:
        return None


    def PATENT_HINTS(self, value: Any) -> Optional[str]:
        return None

    def REMARKS(self, value: Any) -> Optional[str]:
        return None