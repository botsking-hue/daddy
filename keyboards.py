from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from config import Config

def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Create main menu keyboard"""
    builder = ReplyKeyboardBuilder()
    
    # Main features for all users
    builder.row(KeyboardButton(text="🔍 Search Games"))
    builder.row(KeyboardButton(text="📁 Categories"))
    builder.row(KeyboardButton(text="📱 Platforms"))
    builder.row(KeyboardButton(text="🔥 Featured"))
    builder.row(KeyboardButton(text="⭐ Favorites"))
    builder.row(KeyboardButton(text="🔔 Notifications"))
    
    # Optional row
    builder.row(
        KeyboardButton(text="📊 Statistics"),
        KeyboardButton(text="📱 WhatsApp")
    )
    
    # Admin button (only for admins)
    if is_admin:
        builder.row(KeyboardButton(text="👑 Admin Panel"))
    
    # Adjust layout
    builder.adjust(1, 1, 1, 1, 1, 2)
    
    return builder.as_markup(resize_keyboard=True)

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Create admin panel keyboard"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(KeyboardButton(text="➕ Add Game"))
    builder.row(KeyboardButton(text="📤 Send Notification"))
    builder.row(KeyboardButton(text="📊 Admin Stats"))
    builder.row(KeyboardButton(text="👥 List Users"))
    builder.row(KeyboardButton(text="🏠 Main Menu"))
    
    return builder.as_markup(resize_keyboard=True)

def get_categories_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard for categories"""
    builder = InlineKeyboardBuilder()
    
    for category in Config.CATEGORIES:
        builder.button(text=category, callback_data=f"category:{category}")
    
    builder.adjust(2)
    return builder.as_markup()

def get_platforms_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard for platforms"""
    builder = InlineKeyboardBuilder()
    
    for platform in Config.PLATFORMS:
        builder.button(text=platform, callback_data=f"platform:{platform}")
    
    builder.adjust(2)
    return builder.as_markup()

def get_game_actions_keyboard(game_id: int, is_favorite: bool = False) -> InlineKeyboardMarkup:
    """Create inline keyboard for game actions"""
    builder = InlineKeyboardBuilder()
    
    # Download button (URL button)
    builder.button(text="⬇️ Download", url="https://example.com")  # Will be replaced with actual URL
    
    # Favorite toggle
    fav_text = "⭐ Remove Favorite" if is_favorite else "⭐ Add to Favorites"
    builder.button(text=fav_text, callback_data=f"toggle_fav:{game_id}")
    
    # Back button
    builder.button(text="⬅️ Back", callback_data="back_to_list")
    
    builder.adjust(1)
    return builder.as_markup()
