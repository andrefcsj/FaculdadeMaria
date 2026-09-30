from workers import Response, WorkerEntrypoint
from urllib.parse import urlparse


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        if urlparse(request.url).path != "/health":
            return Response("FaculdadeMaria Python runtime pilot")

        result = await self.env.DB.prepare("SELECT 1 AS ok").run()
        return Response.json({
            "service": "faculdademaria-python-pilot",
            "status": "ok" if result.success else "degraded",
            "database": "d1",
        })
