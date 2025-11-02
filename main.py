import asyncio
from app.app import Application
from app.logger import logger as context_logger

app = Application()

async def main():
    logger = context_logger.setup_logger()
    token = context_logger.logger_var.set(logger)
    await app.run()
    # app.visualize()
    context_logger.logger_var.reset(token)

asyncio.run(main())