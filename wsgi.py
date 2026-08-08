"""Production WSGI entry point."""

from ecologic import create_app
from ecologic.config import load_local_environment

load_local_environment()
app = create_app()
