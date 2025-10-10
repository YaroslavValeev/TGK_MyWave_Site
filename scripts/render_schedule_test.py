import os
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates')
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)

def render(events_value):
    tpl = env.get_template('schedule.html')
    return tpl.render(events=events_value)

if __name__ == '__main__':
    print('Rendering with events=None')
    out1 = render(None)
    print('Contains #calendar?', '#calendar' in out1)
    print('Contains no-events message?', 'События для отображения отсутствуют.' in out1)

    print('\nRendering with events=[] (empty list)')
    out2 = render([])
    print('Contains #calendar?', '#calendar' in out2)
    print('Contains no-events message?', 'События для отображения отсутствуют.' in out2)

    print('\nRendering with events=[1] (non-empty)')
    out3 = render([{'title':'t'}])
    print('Contains #calendar?', '#calendar' in out3)
    print('Contains no-events message?', 'События для отображения отсутствуют.' in out3)
