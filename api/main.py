"""Point d'entrée uvicorn : `uvicorn api.main:app`."""

from api.app import create_app

app = create_app()
