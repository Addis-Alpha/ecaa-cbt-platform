import logging
from waitress import serve
from run import app

logging.basicConfig(level=logging.INFO)

serve(app, host="0.0.0.0", port=8080, threads=8)
