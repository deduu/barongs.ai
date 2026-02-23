from __future__ import annotations

from mangum import Mangum

from src.applications.search_agent.main import create_search_app

app = create_search_app()
handler = Mangum(app, lifespan="auto")
