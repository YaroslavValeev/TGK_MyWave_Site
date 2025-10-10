import newrelic.agent
newrelic.agent.initialize('newrelic.ini')
from main import app
application = app 