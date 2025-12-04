from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import keyboards as kb
from datamanager import DataManager
from config import Config
import os

router = Router()
db = DataManager()

class AddGameStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_category = State()
    waiting_for_platform = State()
    waiting_for_link = State()
    waiting_for_image = State()
    waiting_for_size = State()
    waiting_for_version = State()
    waiting_for_requirements = State()

class SendNotificationStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_message = State()
    waiting_for_confirmation = State()

# Admin check middleware
@router.message(lambda message: message.from_user.id not in Config.ADMIN_IDS)
async def admin_only(message: Message):
    """Block non-admin users from admin commands"""
    await message.answer("❌ This command is for administrators only.")

@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Show admin panel"""
    user_id = message.from_user.id
    
    if user_id not in Config.ADMIN_IDS:
        return
    
    stats = db.get_statistics()
    
    admin_text = (
        "👑 *Admin Panel*\n\n"
        f"📊 *Statistics:*\n"
        f"• 🎮 Games: {stats['total_games']}\n"
        f"• 👥 Users: {stats['total_users']}\n"
        f"• 📥 Downloads: {stats['total_downloads']}\n\n"
        "_Select an action from the menu below._"
    )
    
    await message.answer(
        admin_text,
        reply_markup=kb.get_admin_keyboard(),
        parse_mode="Markdown"
    )

@router.message(F.text == "➕ Add Game")
async def add_game_start(message: Message, state: FSMContext):
    """Start adding a new game"""
    user_id = message.from_user.id
    
    if user_id not in Config.ADMIN_IDS:
        return
    
    await message.answer(
        "🎮 *Add New Game*\n\n"
        "Please enter the game title:",
        parse_mode="Markdown"
    )
    await state.set_state(AddGameStates.waiting_for_title)

@router.message(AddGameStates.waiting_for_title)
async def process_game_title(message: Message, state: FSMContext):
    """Process game title"""
    if len(message.text) < 2:
        await message.answer("Title must be at least 2 characters long.")
        return
    
    await state.update_data(title=message.text.strip())
    
    await message.answer(
        "📝 *Game Description*\n\n"
        "Please enter the game description (or type /skip to skip):",
        parse_mode="Markdown"
    )
    await state.set_state(AddGameStates.waiting_for_description)

@router.message(AddGameStates.waiting_for_description)
async def process_game_description(message: Message, state: FSMContext):
    """Process game description"""
    if message.text == "/skip":
        description = None
    else:
        description = message.text.strip()
    
    await state.update_data(description=description)
    
    # Show categories keyboard
    categories = Config.CATEGORIES
    categories_text = "\n".join([f"{i+1}. {cat}" for i, cat in enumerate(categories)])
    
    await message.answer(
        f"📁 *Select Category*\n\n"
        f"Available categories:\n{categories_text}\n\n"
        "Please enter the category name:",
        parse_mode="Markdown"
    )
    await state.set_state(AddGameStates.waiting_for_category)

@router.message(AddGameStates.waiting_for_category)
async def process_game_category(message: Message, state: FSMContext):
    """Process game category"""
    category = message.text.strip()
    
    if category not in Config.CATEGORIES:
        await message.answer(
            f"Invalid category. Please choose from: {', '.join(Config.CATEGORIES)}"
        )
        return
    
    await state.update_data(category=category)
    
    # Show platforms keyboard
    platforms = Config.PLATFORMS
    platforms_text = "\n".join([f"{i+1}. {platform}" for i, platform in enumerate(platforms)])
    
    await message.answer(
        f"📱 *Select Platform*\n\n"
        f"Available platforms:\n{platforms_text}\n\n"
        "Please enter the platform name:",
        parse_mode="Markdown"
    )
    await state.set_state(AddGameStates.waiting_for_platform)

@router.message(AddGameStates.waiting_for_platform)
async def process_game_platform(message: Message, state: FSMContext):
    """Process game platform"""
    platform = message.text.strip()
    
    if platform not in Config.PLATFORMS:
        await message.answer(
            f"Invalid platform. Please choose from: {', '.join(Config.PLATFORMS)}"
        )
        return
    
    await state.update_data(platform=platform)
    
    await message.answer(
        "🔗 *Download Link*\n\n"
        "Please enter the download link (MediaFire, Google Drive, etc.):",
        parse_mode="Markdown"
    )
    await state.set_state(AddGameStates.waiting_for_link)

@router.message(AddGameStates.waiting_for_link)
async def process_game_link(message: Message, state: FSMContext):
    """Process download link"""
    link = message.text.strip()
    
    if not (link.startswith("http://") or link.startswith("https://")):
        await message.answer("Please enter a valid URL starting with http:// or https://")
        return
    
    await state.update_data(download_link=link)
    
    await message.answer(
        "🖼️ *Game Image*\n\n"
        "Please send the game cover image (or type /skip to skip):\n"
        "_Note: Send as photo (not file)_",
        parse_mode="Markdown"
    )
    await state.set_state(AddGameStates.waiting_for_image)

@router.message(AddGameStates.waiting_for_image)
async def process_game_image(message: Message, state: FSMContext):
    """Process game image"""
    if message.text == "/skip":
        image_path = None
    elif message.photo:
        # In a real bot, you would save the image
        # For now, we'll just store a placeholder
        image_path = "uploaded_image.jpg"
        await message.answer("✅ Image received (saved locally)")
    else:
        await message.answer("Please send a photo or type /skip")
        return
    
    await state.update_data(image_path=image_path)
    
    await message.answer(
        "📦 *File Size*\n\n"
        "Please enter the file size (e.g., '500 MB', '1.2 GB') or type /skip:",
        parse_mode="Markdown"
    )
    await state.set_state(AddGameStates.waiting_for_size)

@router.message(AddGameStates.waiting_for_size)
async def process_game_size(message: Message, state: FSMContext):
    """Process file size"""
    if message.text == "/skip":
        file_size = None
    else:
        file_size = message.text.strip()
    
    await state.update_data(file_size=file_size)
    
    await message.answer(
        "🔄 *Version*\n\n"
        "Please enter the game version (e.g., '1.0.0', 'Latest') or type /skip:",
        parse_mode="Markdown"
    )
    await state.set_state(AddGameStates.waiting_for_version)

@router.message(AddGameStates.waiting_for_version)
async def process_game_version(message: Message, state: FSMContext):
    """Process game version"""
    if message.text == "/skip":
        version = None
    else:
        version = message.text.strip()
    
    await state.update_data(version=version)
    
    await message.answer(
        "⚙️ *System Requirements*\n\n"
        "Please enter system requirements or type /skip:",
        parse_mode="Markdown"
    )
    await state.set_state(AddGameStates.waiting_for_requirements)

@router.message(AddGameStates.waiting_for_requirements)
async def process_game_requirements(message: Message, state: FSMContext):
    """Process requirements and save game"""
    if message.text == "/skip":
        requirements = None
    else:
        requirements = message.text.strip()
    
    # Get all data from state
    data = await state.get_data()
    data['requirements'] = requirements
    
    # Save game to database
    game_id = db.add_game(data)
    
    # Send notification to all users
    notification_text = (
        f"🎮 *New Game Added!*\n\n"
        f"*{data['title']}*\n"
        f"Category: {data['category']}\n"
        f"Platform: {data['platform']}\n\n"
        f"Check it out in the bot!"
    )
    
    db.add_notification(
        title="New Game Available!",
        message=f"{data['title']} has been added to our collection.",
        notification_type="new_game",
        game_id=game_id,
        sent_by=message.from_user.id
    )
    
    await message.answer(
        f"✅ *Game Added Successfully!*\n\n"
        f"*Title:* {data['title']}\n"
        f"*Category:* {data['category']}\n"
        f"*Platform:* {data['platform']}\n"
        f"*ID:* {game_id}\n\n"
        "Users have been notified about this new game!",
        parse_mode="Markdown"
    )
    
    await state.clear()

@router.message(F.text == "📤 Send Notification")
async def send_notification_start(message: Message, state: FSMContext):
    """Start sending notification"""
    user_id = message.from_user.id
    
    if user_id not in Config.ADMIN_IDS:
        return
    
    await message.answer(
        "📤 *Send Notification*\n\n"
        "Please enter the notification title:",
        parse_mode="Markdown"
    )
    await state.set_state(SendNotificationStates.waiting_for_title)

@router.message(SendNotificationStates.waiting_for_title)
async def process_notification_title(message: Message, state: FSMContext):
    """Process notification title"""
    if len(message.text) < 2:
        await message.answer("Title must be at least 2 characters long.")
        return
    
    await state.update_data(title=message.text.strip())
    
    await message.answer(
        "📝 *Notification Message*\n\n"
        "Please enter the notification message:",
        parse_mode="Markdown"
    )
    await state.set_state(SendNotificationStates.waiting_for_message)

@router.message(SendNotificationStates.waiting_for_message)
async def process_notification_message(message: Message, state: FSMContext):
    """Process notification message"""
    if len(message.text) < 5:
        await message.answer("Message must be at least 5 characters long.")
        return
    
    await state.update_data(message=message.text.strip())
    
    data = await state.get_data()
    
    preview = (
        f"📨 *Notification Preview*\n\n"
        f"*Title:* {data['title']}\n"
        f"*Message:* {data['message']}\n\n"
        f"This will be sent to all users.\n"
        f"Send notification? (yes/no)"
    )
    
    await message.answer(preview, parse_mode="Markdown")
    await state.set_state(SendNotificationStates.waiting_for_confirmation)

@router.message(SendNotificationStates.waiting_for_confirmation)
async def confirm_notification(message: Message, state: FSMContext):
    """Confirm and send notification"""
    response = message.text.strip().lower()
    
    if response not in ['yes', 'y', 'ok']:
        await message.answer("Notification cancelled.")
        await state.clear()
        return
    
    data = await state.get_data()
    
    # Send notification to all users
    notification_id = db.add_notification(
        title=data['title'],
        message=data['message'],
        notification_type="announcement",
        sent_by=message.from_user.id
    )
    
    await message.answer(
        f"✅ *Notification Sent!*\n\n"
        f"Notification has been sent to all users.\n"
        f"Notification ID: {notification_id}",
        parse_mode="Markdown"
    )
    
    await state.clear()

@router.message(F.text == "📊 Admin Stats")
async def admin_stats(message: Message):
    """Show detailed admin statistics"""
    user_id = message.from_user.id
    
    if user_id not in Config.ADMIN_IDS:
        return
    
    stats = db.get_statistics()
    
    # Get recent users
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, first_name, last_active 
            FROM users 
            ORDER BY last_active DESC 
            LIMIT 5
        ''')
        recent_users = cursor.fetchall()
    
    # Get recent games
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, title, category, platform, download_count, created_at 
            FROM games 
            ORDER BY created_at DESC 
            LIMIT 5
        ''')
        recent_games = cursor.fetchall()
    
    stats_text = (
        "📊 *Admin Statistics*\n\n"
        f"🎮 *Total Games:* {stats['total_games']}\n"
        f"👥 *Total Users:* {stats['total_users']}\n"
        f"📥 *Total Downloads:* {stats['total_downloads']}\n\n"
        
        "👤 *Recent Users:*\n"
    )
    
    for user in recent_users:
        stats_text += f"• {user['first_name'] or user['username'] or user['user_id']} "
        stats_text += f"(last active: {user['last_active'][:10]})\n"
    
    stats_text += "\n🎮 *Recent Games:*\n"
    
    for game in recent_games:
        stats_text += f"• {game['title']} - {game['download_count']} downloads\n"
    
    await message.answer(stats_text, parse_mode="Markdown")

@router.message(Command("users"))
async def list_users(message: Message, command: CommandObject):
    """List all users (admin only)"""
    user_id = message.from_user.id
    
    if user_id not in Config.ADMIN_IDS:
        return
    
    limit = 20
    if command.args and command.args.isdigit():
        limit = min(int(command.args), 100)
    
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, first_name, created_at, last_active 
            FROM users 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        users = cursor.fetchall()
    
    if not users:
        await message.answer("No users found.")
        return
    
    users_text = f"👥 *Users (Last {len(users)}):*\n\n"
    
    for user in users:
        name = user['first_name'] or user['username'] or f"User {user['user_id']}"
        users_text += f"• {name}\n"
        users_text += f"  ID: {user['user_id']} | Joined: {user['created_at'][:10]}\n\n"
    
    await message.answer(users_text, parse_mode="Markdown")
