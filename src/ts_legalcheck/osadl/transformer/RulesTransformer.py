from typing import Any, List, Iterable, Dict, Optional

from .ConstraintsExtractor import ConstraintsExtractor


class RulesTransformer(ConstraintsExtractor):    
    """Transform methods for each OSADL license language element."""

    @staticmethod
    def _values_to_expr(values: Iterable[str], op: str) -> Optional[str]:
        values = [v for v in values if v]
        
        if len(values) > 1:
            return f"({op} {' '.join(values)})"
        elif len(values) == 1:
            return values[0]
        else:
            return None
        

    def NO_OP(self, value: Dict[str, str]) -> Optional[str]:                
        return self.AND(value.values())
    
    def AND(self, value: Iterable[str]) -> Optional[str]:
      return self._values_to_expr(value, 'and')
        

    def OR(self, value: Iterable[str]) -> Optional[str]:
        return self._values_to_expr(value, 'or')

    def EITHER(self, value: Iterable[str]) -> Optional[str]:
        return self._values_to_expr(value, 'xor')
    
    def IF(self, value: Dict[str, str]) -> Optional[str]:
        conds = [f"(implies {self._get_property(key)} {val})" for key, val in value.items()]
        return self.AND(conds)

    def USE_CASE(self, value: Dict[str, str]) -> Optional[str]:
        return self.IF(value)

    def YOU_MUST(self, value: Dict[str, Any]) -> Optional[str]:
        obligations = [self._get_obligation(key) for key in value.keys()]
        return self._values_to_expr(obligations, 'and')
    
    def YOU_MUST_NOT(self, value: Any) -> Optional[str]:
        obligations = [f"!{self._get_obligation(key)}" for key in value.keys()]
        return self._values_to_expr(obligations, 'and')


    def OR_IF(self, value: Any) -> Optional[str]:
        return None

    def EITHER_IF(self, value: Any) -> Optional[str]:
        return None

    def EXCEPT_IF(self, value: Any) -> Optional[str]:
        return None
    


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