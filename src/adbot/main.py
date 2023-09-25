import asyncio

from adbot.app.app import AdBotApp


async def main():
    app = await AdBotApp()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())