import asyncio
import json

from starlette.responses import StreamingResponse


def add_custom_stream_api_route(app):
  @app.get("/my_stream")
  async def custom_stream(start: int, end: int):
    async def generate_numbers():
      current = start
      while current <= end:
        yield json.dumps({"number": current}) + "\n"
        await asyncio.sleep(0.2)
        current += 1

    return StreamingResponse(generate_numbers(), media_type="application/x-ndjson")
