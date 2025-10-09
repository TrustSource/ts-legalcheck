# Init file for ts_legalcheck.ui package

from .app import app

def run(port):
  app.run(debug=True, host="0.0.0.0", port=port)