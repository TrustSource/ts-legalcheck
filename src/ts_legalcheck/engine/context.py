import json
import typing as t

from pathlib import Path

class TSObject(object):
    def __init__(self, key):
        self.__key = key

    @property
    def key(self):
        return self.__key



class TSTargetObject(TSObject):
    def __init__(self, key, properties:t.Optional[dict]=None):
        super(TSTargetObject, self).__init__(key)

        self.__properties = properties if properties else {}

    # properties

    @property
    def properties(self):
        return self.__properties

    @properties.setter
    def properties(self, value):
        self.__properties = value

    def validate(self):
        if any(type(p) is not bool for p in self.properties.values()):
            raise ValueError(f'Object {self.key} is malformed: unsupported property value type. Bool is expected.')


class Component(TSTargetObject):
    def __init__(self, key, properties=None, licenses=None):
        super(Component, self).__init__(key, properties)
        self.__licenses = licenses if licenses else []

    @property
    def licenses(self) -> t.Iterable[str]:
        return self.__licenses

    @licenses.setter
    def licenses(self, licenses: t.Iterable[str]):
        self.__licenses = licenses

    def validate(self):
        super().validate()

        if any(type(lic) is not str for lic in self.licenses):
            raise ValueError(f'Object {self.key} is malformed: unsupported license type. String is expected.')


class Module(TSTargetObject):
    def __init__(self, key, properties=None, components=None):
        super(Module, self).__init__(key, properties)
        self.__components = {c.key:c for c in components} if components else {}


    @property
    def components(self) -> t.Iterable[Component]:
        return self.__components.values()

    @components.setter
    def components(self, components: t.Iterable[Component]):
        self.__components = {c.key:c for c in components}


    def findComponent(self, key) -> t.Optional[Component]:
        return self.__components.get(key)


def resolveComponentsProperties(module):
    # TODO: Move to the engine rules after reviewing rules and constraints
    m_props = module.properties
    for c in module.components:
        c.properties["dist_obj"] = \
            m_props.get("D_op", False) or \
            m_props.get("D_ipoa", False) or \
            m_props.get("D_xa", False) or \
            (m_props.get("D_sslib", False) and not m_props.get("OM_SaaS", False))

        c.properties["dist_src"] = m_props.get("D_cslib", False)


def loadModule(data: t.Union[str, bytes]) -> Module:
    def loadComponent(c_key, c):
        c_props = {k:v for k, v in c.items() if k != 'licenses'}
        comp = Component(c_key, c_props, c['licenses'])
        comp.validate()
        return comp

    m = json.loads(data)
    m_key = m['key']
    m_props = {k:v for k, v in m.items() if k not in ['key', 'components']}
    module = Module(m_key, m_props, [loadComponent(k, v) for k, v in m['components'].items()])
    resolveComponentsProperties(module)
    module.validate()
    return module


def loadModuleFromFile(path: Path) -> Module:
    with path.open('r') as fp:
        return loadModule(fp.read())
