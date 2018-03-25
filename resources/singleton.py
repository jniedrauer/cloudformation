"""Singleton metaclass module"""


from typing import Dict


class Singleton(type):
    """Metaclass for singleton classes"""

    _instances: Dict[object, object] = {}

    def __call__(cls, *args, **kwargs) -> object:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
