from typing import Any, Dict

class OSADLTransformer:
    """
    Transformer for OSADL JSON license language elements.
    """
    
    def _is_index_dict(self, data: dict) -> bool:
        """Check if a dictionary represents a list with numeric string keys."""
        if not data:
            return False
        
        keys = list(data.keys())
        # Check if all keys are numeric strings
        try:
            numeric_keys = [int(k) for k in keys]
            # Check if keys form a sequence starting from 1
            return sorted(numeric_keys) == list(range(1, len(keys) + 1))
        except (ValueError, TypeError):
            return False
    
    def NO_OP(self, value: dict) -> Any:
        return value
    
    def transform(self, data: Any) -> Any:
        if isinstance(data, dict):
            # Check if this dict represents a list with numeric indices
            if self._is_index_dict(data):
                # Convert to actual list, sorted by numeric key
                sorted_items = sorted(data.items(), key=lambda x: int(x[0]))
                return [self.transform(value) for _, value in sorted_items]
            
            # Normal dictionary processing
            result = {}
            for key, value in data.items():
                value = self.transform(value)                
                method = getattr(self, key.replace(" ", "_").replace("-", "_").upper(), None)  

                if callable(method):
                    result[key] = method(value)
                else:
                    result[key] = self.NO_OP(value)

            return result
        
        elif isinstance(data, list):
            return [self.transform(item) for item in data]
        
        else:
            return data