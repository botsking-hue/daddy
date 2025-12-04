from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datamanager import DataManager
import keyboards as kb
from config import Config

router = Router()
db = DataManager()

@router.message(Command("categories"))
@router.message(F.text == "📁 Categories")
async def show_categories(message: Message):
    """Show all game categories"""
    categories = db.get_all_categories()
    
    if not categories:
        await message.answer("No categories available yet.")
        return
    
    text = "📁 *Browse Games by Category:*\n\n"
    for cat in categories:
        text += f"• *{cat['name']}* - {cat['game_count']} games\n"
    
    text += "\n_Select a category to view games:_"
    
    # Create inline keyboard with categories
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=f"{cat['name']} ({cat['game_count']})", 
                      callback_data=f"category:{cat['name']}")
    builder.adjust(2)  # 2 buttons per row
    
    await message.answer(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.message(Command("platforms"))
@router.message(F.text == "📱 Platforms")
async def show_platforms(message: Message):
    """Show all platforms"""
    platforms = db.get_all_platforms()
    
    if not platforms:
        await message.answer("No platforms available yet.")
        return
    
    text = "📱 *Browse Games by Platform:*\n\n"
    for platform in platforms:
        text += f"• *{platform['name']}* - {platform['game_count']} games\n"
    
    text += "\n_Select a platform to view games:_"
    
    # Create inline keyboard with platforms
    builder = InlineKeyboardBuilder()
    for platform in platforms:
        builder.button(text=f"{platform['name']} ({platform['game_count']})", 
                      callback_data=f"platform:{platform['name']}")
    builder.adjust(2)
    
    await message.answer(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.message(Command("featured"))
@router.message(F.text == "🔥 Featured")
async def show_featured_games(message: Message):
    """Show featured games"""
    games = db.get_featured_games(limit=5)
    
    if not games:
        await message.answer("No featured games available yet.")
        return
    
    text = "🔥 *Featured Games:*\n\n"
    for i, game in enumerate(games, 1):
        text += f"{i}. *{game['title']}*\n"
        text += f"   📁 {game['category']} | 📱 {game['platform']}\n"
        text += f"   ⬇️ {game['download_count']} downloads\n\n"
    
    # Create inline keyboard for each game
    builder = InlineKeyboardBuilder()
    for game in games:
        builder.button(
            text=f"View {game['title'][:15]}...",
            callback_data=f"view_game:{game['id']}"
        )
    builder.adjust(1)
    
    await message.answer(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("category:"))
async def handle_category_selection(callback: CallbackQuery):
    """Handle category selection"""
    category = callback.data.split(":")[1]
    games = db.get_games_by_category(category, limit=Config.MAX_GAMES_PER_PAGE)
    
    if not games:
        await callback.message.edit_text(
            f"No games found in *{category}* category.\n"
            "Check back later!",
            parse_mode="Markdown"
        )
        return
    
    text = f"🎮 *Games in {category}:*\n\n"
    for i, game in enumerate(games, 1):
        text += f"{i}. *{game['title']}*\n"
        text += f"   📱 {game['platform']} | ⬇️ {game['download_count']}\n\n"
    
    # Create inline keyboard for games
    builder = InlineKeyboardBuilder()
    for game in games:
        builder.button(
            text=f"{game['title'][:20]}...",
            callback_data=f"view_game:{game['id']}"
        )
    builder.adjust(1)
    
    # Add back button
    builder.row(InlineKeyboardButton(text="⬅️ Back to Categories", 
                                    callback_data="back_to_categories"))
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("platform:"))
async def handle_platform_selection(callback: CallbackQuery):
    """Handle platform selection"""
    platform = callback.data.split(":")[1]
    games = db.get_games_by_platform(platform, limit=Config.MAX_GAMES_PER_PAGE)
    
    if not games:
        await callback.message.edit_text(
            f"No games found for *{platform}* platform.\n"
            "Check back later!",
            parse_mode="Markdown"
        )
        return
    
    text = f"🎮 *Games for {platform}:*\n\n"
    for i, game in enumerate(games, 1):
        text += f"{i}. *{game['title']}*\n"
        text += f"   📁 {game['category']} | ⬇️ {game['download_count']}\n\n"
    
    # Create inline keyboard for games
    builder = InlineKeyboardBuilder()
    for game in games:
        builder.button(
            text=f"{game['title'][:20]}...",
            callback_data=f"view_game:{game['id']}"
        )
    builder.adjust(1)
    
    # Add back button
    builder.row(InlineKeyboardButton(text="⬅️ Back to Platforms", 
                                    callback_data="back_to_platforms"))
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("view_game:"))
async def view_game_details(callback: CallbackQuery):
    """View game details"""
    game_id = int(callback.data.split(":")[1])
    game = db.get_game(game_id)
    user_id = callback.from_user.id
    
    if not game:
        await callback.answer("Game not found!", show_alert=True)
        return
    
    # Check if game is in favorites
    is_favorite = db.is_favorite(user_id, game_id)
    
    # Build game details
    text = f"🎮 *{game['title']}*\n\n"
    
    if game['description']:
        text += f"📝 *Description:*\n{game['description']}\n\n"
    
    text += f"📁 *Category:* {game['category']}\n"
    text += f"📱 *Platform:* {game['platform']}\n"
    
    if game['file_size']:
        text += f"📦 *Size:* {game['file_size']}\n"
    
    if game['version']:
        text += f"🔄 *Version:* {game['version']}\n"
    
    if game['requirements']:
        text += f"⚙️ *Requirements:* {game['requirements']}\n"
    
    text += f"⬇️ *Downloads:* {game['download_count']}\n"
    text += f"📅 *Added:* {game['created_at'][:10]}\n\n"
    
    # Build inline keyboard
    builder = InlineKeyboardBuilder()
    
    # Download button
    builder.button(text="⬇️ Download", url=game['download_link'])
    
    # Favorite button
    fav_text = "⭐ Remove Favorite" if is_favorite else "⭐ Add to Favorites"
    builder.button(text=fav_text, callback_data=f"toggle_fav:{game_id}")
    
    builder.adjust(1)
    
    # Add navigation buttons
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data=f"back_from_game:{game['category']}"),
        InlineKeyboardButton(text="🏠 Home", callback_data="back_to_menu")
    )
    
    # If there's an image, we could send it separately
    # For now, just send the text with buttons
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("toggle_fav:"))
async def toggle_favorite(callback: CallbackQuery):
    """Toggle game in favorites"""
    game_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    is_favorite = db.is_favorite(user_id, game_id)
    
    if is_favorite:
        db.remove_favorite(user_id, game_id)
        await callback.answer("Removed from favorites! ✅")
    else:
        db.add_favorite(user_id, game_id)
        await callback.answer("Added to favorites! ⭐")
    
    # Refresh the game view
    await view_game_details(callback)

@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery):
    """Go back to categories"""
    await show_categories(callback.message)

@router.callback_query(F.data == "back_to_platforms")
async def back_to_platforms(callback: CallbackQuery):
    """Go back to platforms"""
    await show_platforms(callback.message)

@router.callback_query(F.data.startswith("back_from_game:"))
async def back_from_game(callback: CallbackQuery):
    """Go back from game view to category"""
    category = callback.data.split(":")[1]
    await handle_category_selection(callback)

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Go back to main menu"""
    user_id = callback.from_user.id
    is_admin = db.get_user(user_id)['is_admin'] if db.get_user(user_id) else False
    
    await callback.message.edit_text(
        "📱 *Main Menu*",
        reply_markup=kb.get_main_menu_keyboard(is_admin),
        parse_mode="Markdown"
    )
