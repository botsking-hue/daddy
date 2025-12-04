from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import keyboards as kb
from datamanager import DataManager
from config import Config

router = Router()
db = DataManager()

class SearchStates(StatesGroup):
    waiting_for_query = State()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    is_admin = db.add_user(user_id, username, first_name, last_name)
    
    welcome_text = (
        "🎮 *Welcome to Game Download Hub Bot!*\n\n"
        "Your ultimate source for free game downloads!\n\n"
        "🌟 *Features:*\n"
        "• Browse games by category\n"
        "• Filter by platform (Android/PC/iOS)\n"
        "• Search for specific games\n"
        "• Get notifications for new games\n"
        "• Save favorites\n\n"
        "Use the menu below to get started!"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=kb.get_main_menu_keyboard(is_admin),
        parse_mode="Markdown"
    )

@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Show main menu"""
    user_id = message.from_user.id
    is_admin = db.get_user(user_id)['is_admin'] if db.get_user(user_id) else False
    
    await message.answer(
        "📱 *Main Menu*",
        reply_markup=kb.get_main_menu_keyboard(is_admin),
        parse_mode="Markdown"
    )

@router.message(Command("whatsapp"))
async def cmd_whatsapp(message: Message):
    """Show WhatsApp channel links"""
    whatsapp_text = (
        "📱 *Join our WhatsApp Channels:*\n\n"
        f"• 🎮 Main Channel: {Config.WHATSAPP_CHANNELS['main']}\n"
        f"• 🔔 Updates: {Config.WHATSAPP_CHANNELS['updates']}\n"
        f"• 🆕 New Games: {Config.WHATSAPP_CHANNELS['new_games']}\n\n"
        "_Join to stay updated with latest game releases!_"
    )
    
    await message.answer(whatsapp_text, parse_mode="Markdown")

@router.message(F.text == "🔍 Search Games")
async def search_games(message: Message, state: FSMContext):
    """Initiate game search"""
    await message.answer(
        "🔍 *Search Games*\n\n"
        "Please enter your search query (game name, keyword, etc.):",
        parse_mode="Markdown"
    )
    await state.set_state(SearchStates.waiting_for_query)

@router.message(SearchStates.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext):
    """Process search query"""
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("Please enter at least 2 characters to search.")
        return
    
    user_id = message.from_user.id
    
    # Save search to history
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO search_history (user_id, query)
            VALUES (?, ?)
        ''', (user_id, query))
    
    # Search games
    games = db.search_games(query, limit=Config.MAX_GAMES_PER_PAGE)
    
    if not games:
        await message.answer(
            "❌ No games found for your search.\n"
            "Try different keywords or browse by category."
        )
    else:
        response = f"🎮 *Found {len(games)} game(s):*\n\n"
        for i, game in enumerate(games, 1):
            response += f"{i}. *{game['title']}*\n"
            response += f"   📁 {game['category']} | 📱 {game['platform']}\n\n"
        
        response += "_Use /categories or /platforms to browse by filter._"
        
        await message.answer(response, parse_mode="Markdown")
    
    await state.clear()

@router.message(F.text == "⭐ Favorites")
async def show_favorites(message: Message):
    """Show user's favorite games"""
    user_id = message.from_user.id
    favorites = db.get_user_favorites(user_id)
    
    if not favorites:
        await message.answer(
            "⭐ *Your Favorites*\n\n"
            "You haven't added any games to favorites yet.\n"
            "Browse games and click the star button to add them!"
        )
    else:
        response = "⭐ *Your Favorite Games:*\n\n"
        for i, game in enumerate(favorites, 1):
            response += f"{i}. *{game['title']}*\n"
            response += f"   📁 {game['category']} | 📱 {game['platform']}\n\n"
        
        await message.answer(response, parse_mode="Markdown")

@router.message(F.text == "📊 Statistics")
async def show_statistics(message: Message):
    """Show bot statistics"""
    stats = db.get_statistics()
    
    stats_text = (
        "📊 *Game Download Hub Statistics*\n\n"
        f"• 🎮 Total Games: *{stats['total_games']}*\n"
        f"• 📥 Total Downloads: *{stats['total_downloads']}*\n"
        f"• 👥 Total Users: *{stats['total_users']}*\n"
    )
    
    if stats['popular_category']:
        stats_text += f"• 🏆 Popular Category: *{stats['popular_category']['category']}* ({stats['popular_category']['count']} games)\n"
    
    if stats['popular_platform']:
        stats_text += f"• 📱 Popular Platform: *{stats['popular_platform']['platform']}* ({stats['popular_platform']['count']} games)\n"
    
    await message.answer(stats_text, parse_mode="Markdown")
