import typing as t

from . import OSADLTransformer


class ConstraintsExtractor(OSADLTransformer):
    def __init__(self):
        self.__src: t.Optional[str] = None

        self.__properties: t.Dict[str, t.Dict] = {}
        self.__obligations: t.Dict[str, t.Dict] = {}        

    @property
    def properties(self) -> t.Dict[str, t.Dict]:
        return self.__properties

    @property
    def obligations(self) -> t.Dict[str, t.Dict]:
        return self.__obligations

    def transform_with_src(self, data: t.Any, src: str) -> t.Any:
        self.__src = src
        return super().transform(data)

    def _get_property(self, name: str) -> str:
        """
        Get the property key for a given string.
        If the string is not already a property, create a new one.
        """
        _name = self._normalize_name(name)
        if _name not in self.__properties:
            key = f"P{len(self.__properties) + 1}"
            self.__properties[_name] = {
                "key": key,
                "name": name
            }

        if src := self.__src:
            sources = self.__properties[_name].get("sources", set())
            sources.add(src)
            self.__properties[_name]["sources"] = sources
                
        return self.__properties[_name]["key"]

    def _get_obligation(self, name: str) -> str:
        """
        Get the obligation key for a given string.
        If the string is not already an obligation, create a new one.
        """
        _name = self._normalize_name(name)
        if _name not in self.__obligations:
            key = f"O{len(self.__obligations) + 1}"
            self.__obligations[_name] = {
                "key": key,
                "name": name
            }

        if src := self.__src:
            sources = self.__obligations[_name].get("sources", set())
            sources.add(src)
            self.__obligations[_name]["sources"] = sources

        return self.__obligations[_name]["key"]


    def _normalize_name(self, name: str) -> str:
        """
        Normalize the name by removing leading/trailing whitespace and converting to lowercase.
        """
        return name.strip().lower() if name else ""



    """Transform methods for each OSADL license language element."""

    def IF(self, value: t.Any) -> t.Any:
        return {self._get_property(key): val for key, val in value.items()}

    def USE_CASE(self, value: t.Any) -> t.Any:
        return {self._get_property(key): val for key, val in value.items()}

    def YOU_MUST_NOT(self, value: t.Any) -> t.Any:
        return [self._get_obligation(key) for key in value.keys()]

    def YOU_MUST(self, value: t.Any) -> t.Any:
        return [self._get_obligation(key) for key in value.keys()]

