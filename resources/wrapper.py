"""Base wrapper class"""


import os
import jinja2

from meta.config import Config


PATH = os.path.dirname(os.path.realpath(__file__))


class Wrapper:
    """Load static AWS configuration"""

    template_path = os.path.join(PATH, 'templates')

    def __init__(self):
        self.config = Config()

    @classmethod
    def render_template(cls, template, **kwargs):
        """Render a template and return a string"""
        t = jinja2.Environment(
            loader=jinja2.FileSystemLoader(cls.template_path)
        ).get_template(template)

        return t.render(**kwargs)
