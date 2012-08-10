# For Apache Server

# Virtualenv activation
from os.path import abspath, dirname, join
activate_this = abspath(join(dirname(__file__), 'venv/bin/activate_this.py'))
execfile(activate_this, dict(__file__=activate_this))

# Since the application isn't on the path
import sys
sys.path.insert(0, abspath(join(dirname(__file__)))

# App factory
from app import make_app
application = make_app()
