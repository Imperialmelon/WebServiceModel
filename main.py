import asyncio
from app.app import Application
from app.logger import logger as context_logger

app = Application()


async def main():
    async with context_logger.app_logger():
        await app.run()

asyncio.run(main())