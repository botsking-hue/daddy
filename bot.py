import asyncio
import logging
import sys
import os
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.filters import Command
from aiogram import types

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import your modules
try:
    from config import Config
    from datamanager import DataManager
    import handlers
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure all required files exist: config.py, datamanager.py, handlers/")
    sys.exit(1)

# Initialize bot
bot = None
dp = None
db = None
is_running = False

# ==================== HELPER FUNCTIONS ====================

async def setup_bot_commands():
    """Setup bot menu commands"""
    commands = [
        BotCommand(command="start", description="🚀 Start bot"),
        BotCommand(command="menu", description="📱 Main menu"),
        BotCommand(command="help", description="❓ Help"),
        BotCommand(command="search", description="🔍 Search games"),
        BotCommand(command="categories", description="📁 Categories"),
        BotCommand(command="platforms", description="📱 Platforms"),
        BotCommand(command="featured", description="🔥 Featured"),
        BotCommand(command="notifications", description="🔔 Notifications"),
        BotCommand(command="favorites", description="⭐ Favorites"),
        BotCommand(command="whatsapp", description="📱 WhatsApp"),
        BotCommand(command="stats", description="📊 Statistics"),
        BotCommand(command="admin", description="👑 Admin"),
    ]
    
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("Bot commands set successfully")
    except Exception as e:
        logger.error(f"Failed to set commands: {e}")

async def notify_admins(message_text: str):
    """Send notification to all admins"""
    if not Config.ADMIN_IDS:
        return
    
    for admin_id in Config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📢 {message_text}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

async def backup_database():
    """Create database backup"""
    import shutil
    import datetime as dt
    
    try:
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_game_db_{timestamp}.db"
        
        if os.path.exists(Config.DATABASE_NAME):
            shutil.copy2(Config.DATABASE_NAME, backup_file)
            logger.info(f"Database backed up to {backup_file}")
            
            # Keep only last 7 backups
            import glob
            backups = glob.glob("backup_game_db_*.db")
            if len(backups) > 7:
                backups.sort()
                for old_backup in backups[:-7]:
                    os.remove(old_backup)
                    logger.info(f"Removed old backup: {old_backup}")
                    
    except Exception as e:
        logger.error(f"Backup failed: {e}")

async def check_broken_links():
    """Check for broken download links"""
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            with db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, title, download_link FROM games WHERE is_verified = 1")
                games = cursor.fetchall()
                
                broken_links = []
                for game in games:
                    try:
                        async with session.get(game['download_link'], timeout=10) as response:
                            if response.status >= 400:
                                broken_links.append(game['id'])
                    except:
                        broken_links.append(game['id'])
                
                if broken_links:
                    logger.warning(f"Found {len(broken_links)} broken links")
                    await notify_admins(f"⚠️ Found {len(broken_links)} broken game links!")
                    
    except Exception as e:
        logger.error(f"Link check failed: {e}")

async def update_statistics():
    """Update daily statistics"""
    try:
        with db.connect() as conn:
            cursor = conn.cursor()
            
            # Get today's date
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Count today's new users
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE DATE(created_at) = ?
            """, (today,))
            new_users = cursor.fetchone()[0]
            
            # Count today's downloads
            cursor.execute("""
                SELECT COUNT(*) FROM download_history 
                WHERE DATE(downloaded_at) = ?
            """, (today,))
            today_downloads = cursor.fetchone()[0]
            
            logger.info(f"📈 Today: {new_users} new users, {today_downloads} downloads")
            
    except Exception as e:
        logger.error(f"Statistics update failed: {e}")

async def maintenance_tasks():
    """Run periodic maintenance tasks"""
    while is_running:
        try:
            # Run every hour
            await asyncio.sleep(3600)
            
            current_hour = datetime.now().hour
            
            # Backup at 3 AM
            if current_hour == 3:
                await backup_database()
            
            # Check links at 6 AM
            if current_hour == 6:
                await check_broken_links()
            
            # Update stats every 6 hours
            if current_hour % 6 == 0:
                await update_statistics()
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Maintenance task error: {e}")

# ==================== MAIN BOT FUNCTIONS ====================

async def on_startup():
    """Run when bot starts"""
    global db, is_running
    
    logger.info("=" * 50)
    logger.info("🎮 GAME DOWNLOAD BOT STARTING UP")
    logger.info("=" * 50)
    
    # Initialize database
    db = DataManager()
    logger.info("✅ Database initialized")
    
    # Notify admins
    await notify_admins("🤖 Bot is now ONLINE!")
    
    # Start maintenance tasks
    is_running = True
    asyncio.create_task(maintenance_tasks())
    
    logger.info("✅ Bot is ready and running!")

async def on_shutdown():
    """Run when bot stops"""
    global is_running
    
    logger.info("🛑 Bot shutting down...")
    is_running = False
    
    # Notify admins
    await notify_admins("🛑 Bot is going OFFLINE!")
    
    # Close database
    if db:
        db.close()
        logger.info("✅ Database connection closed")
    
    logger.info("✅ Bot shutdown complete")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Show help message"""
    help_text = """
🎮 *Game Download Bot Help*

*Basic Commands:*
/start - Start the bot
/menu - Show main menu
/help - This help message

*Browse Games:*
/search - Search for games
/categories - Browse by category
/platforms - Browse by platform
/featured - Featured games

*User Features:*
/notifications - Your notifications
/favorites - Your favorite games
/stats - Bot statistics
/whatsapp - Join WhatsApp channels

*Admin Commands:*
/admin - Admin panel

*How to Use:*
1. Use /categories or /platforms to browse
2. Click on a game to view details
3. Click "Download" to get the game
4. Add games to favorites with the ⭐ button

*Need Help?*
Contact admin or use /whatsapp to join our channels!
"""
    
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Show bot statistics"""
    try:
        stats = db.get_statistics()
        
        stats_text = f"""
📊 *Bot Statistics*

🎮 *Games:*
Total Games: {stats['total_games']}
Total Downloads: {stats['total_downloads']}

👥 *Users:*
Total Users: {stats['total_users']}

🏆 *Popular:*
"""
        
        if stats['popular_category']:
            stats_text += f"Top Category: {stats['popular_category']['category']} ({stats['popular_category']['count']} games)\n"
        
        if stats['popular_platform']:
            stats_text += f"Top Platform: {stats['popular_platform']['platform']} ({stats['popular_platform']['count']} games)\n"
        
        stats_text += f"\n🕐 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        await message.answer(stats_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Stats command error: {e}")
        await message.answer("⚠️ Could not fetch statistics. Please try again later.")

# ==================== ERROR HANDLING ====================

async def on_error(event, exception):
    """Handle errors"""
    logger.error(f"Unhandled exception: {exception}", exc_info=True)
    
    try:
        # Notify admins about critical errors
        await notify_admins(f"🚨 BOT ERROR:\n{type(exception).__name__}: {str(exception)[:100]}")
    except:
        pass

# ==================== MAIN FUNCTION ====================

async def main():
    """Main function to run the bot"""
    global bot, dp
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"ERROR: {e}")
        print("Please check your .env file")
        return
    
    # Initialize bot
    bot = Bot(token=Config.BOT_TOKEN, parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Setup error handler
    dp.errors.register(on_error)
    
    # Include routers
    dp.include_router(handlers.user_handlers.router)
    dp.include_router(handlers.game_handlers.router)
    dp.include_router(handlers.notification_handlers.router)
    dp.include_router(handlers.admin_handlers.router)
    
    # Add help command handler
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_stats, Command("stats"))
    
    # Setup startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Setup bot commands
    await setup_bot_commands()
    
    # Start bot
    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Polling error: {e}")
    finally:
        logger.info("Bot stopped")

def run_bot():
    """Run the bot with proper shutdown handling"""
    # For Windows compatibility
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
    finally:
        print("\n" + "=" * 50)
        print("Bot has stopped. Press Enter to exit.")
        print("=" * 50)
        input()

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("game_images", exist_ok=True)
    
    # Print welcome message
    print("=" * 50)
    print("🎮 GAME DOWNLOAD TELEGRAM BOT")
    print("=" * 50)
    print("Starting up...")
    
    # Run the bot
    run_bot()
