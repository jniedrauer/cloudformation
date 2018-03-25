"""Central configuration management using YAML config file"""


from os.path import dirname, join, realpath
from typing import Type

import yaml

from resources.singleton import Singleton


CONFIG_PATH = join(
    dirname(dirname(realpath(__file__))),
    'config',
)


class AttributeDict(dict): #defaultdict):
    """Allow access to members as first class objects"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs) #AttributeDict)
        self.__dict__.update(kwargs)

    def __getitem__(self, key: str):
        value = super().__getitem__(key)
        if isinstance(value, dict):
            return AttributeDict(**value)

        return value

    def __getattr__(self, key: str):
        try:
            return self.__getitem__(key)
        except KeyError:
            raise AttributeError(key)


class Config(metaclass=Singleton):
    """Maintain a global configuration state"""

    base_config = join(CONFIG_PATH, 'all.yml')
    env_config = join(CONFIG_PATH, '{env}.yml')

    def __init__(self, env=None):
        if env:
            env_file = self.env_config.format(env=env)
            config = {
                **self.get_config(self.base_config),
                **self.get_config(env_file),
                **{'env': env},
            }
            self._config = AttributeDict(**config)

        if not self.env:
            raise RuntimeError('Singleton class env should already be defined')

    def __getattr__(self, key: str) -> Type:
        return self._config[key]

    def __setattr__(self, key: str, value: Type):
        if key.startswith('_'):
            super().__setattr__(key, value)
        else:
            self._config[key] = value

    @staticmethod
    def get_config(path: str) -> dict:
        """Return a dict from a config file"""
        with open(path) as f:
            return yaml.safe_load(f)
