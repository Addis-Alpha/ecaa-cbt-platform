from waitress import serve
from run import app

import logging
logging.basicConfig(level=logging.INFO)

from waitress import serve
from run import app

serve(app, host='0.0.0.0', port=8080, threads=8)
