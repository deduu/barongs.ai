from __future__ import annotations

from mangum import Mangum

from src.applications.example_app.main import create_example_app

app = create_example_app()
handler = Mangum(app, lifespan="auto")
