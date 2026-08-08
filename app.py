"""Local development entry point for EcoLogic."""

from __future__ import annotations

import os

from ecologic import create_app
from ecologic.config import load_local_environment

load_local_environment()
app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("ECOLOGIC_HOST", "127.0.0.1"),
        port=int(os.getenv("ECOLOGIC_PORT", "5000")),
        debug=False,
    )
