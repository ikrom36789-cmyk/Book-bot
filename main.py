import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import config
from handlers import router
from handlers_admin import admin_router

async def start_bot(bot: Bot):
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text="Bot ishga tushdi")
        except:
            pass

async def stop_bot(bot: Bot):
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text="Bot to'xtadi")
        except:
            pass

async def main():
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    dp.startup.register(start_bot)
    dp.shutdown.register(stop_bot)
    
    dp.include_router(admin_router)
    dp.include_router(router)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi")
