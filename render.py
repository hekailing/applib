# coding: utf8
import jinja2

import util


class RenderError(Exception):
    pass


class NoEngine(RenderError):
    pass


class Render(object):
    def __init__(self):
        pass

    def __call__(self):
        pass


class Jinja2Render(Render):
    def __init__(self, template_path):
        loader = jinja2.FileSystemLoader(template_path)
        self._env = jinja2.Environment(loader=loader, autoescape=True)

    def __call__(self, file_path, data):
        encoding = 'utf-8'
        data = util.to_unicode(data, encoding)
        template = self._env.get_template(file_path)
        return template.render(**data).encode(encoding)


def make_render(engine, *args):
    if engine == 'jinja2':
        return Jinja2Render(*args)
    else:
        raise NoEngine()
