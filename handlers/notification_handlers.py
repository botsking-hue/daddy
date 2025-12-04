from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datamanager import DataManager

router = Router()
db = DataManager()

@router.message(Command("notifications"))
@router.message(F.text == "🔔 Notifications")
async def show_notifications(message: Message):
    """Show user notifications"""
    user_id = message.from_user.id
    notifications = db.get_user_notifications(user_id, limit=10)
    unread_count = db.get_unread_count(user_id)
    
    if not notifications:
        await message.answer(
            "🔔 *Your Notifications*\n\n"
            "No notifications yet.\n"
            "You'll get notified when new games are added!"
        )
        return
    
    text = f"🔔 *Your Notifications* ({unread_count} unread)\n\n"
    
    builder = InlineKeyboardBuilder()
    
    for i, notif in enumerate(notifications, 1):
        status = "📨" if notif['is_read'] else "📬"
        text += f"{i}. {status} *{notif['title']}*\n"
        text += f"   {notif['message'][:50]}...\n"
        text += f"   📅 {notif['created_at'][:10]}\n\n"
        
        # Add view button for each notification
        builder.button(
            text=f"View #{i}",
            callback_data=f"view_notif:{notif['id']}"
        )
    
    builder.adjust(3)  # 3 buttons per row
    
    await message.answer(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("view_notif:"))
async def view_notification(callback: CallbackQuery):
    """View notification details"""
    notification_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT n.*, un.is_read 
            FROM notifications n
            JOIN user_notifications un ON n.id = un.notification_id
            WHERE n.id = ? AND un.user_id = ?
        ''', (notification_id, user_id))
        
        notif = cursor.fetchone()
    
    if not notif:
        await callback.answer("Notification not found!", show_alert=True)
        return
    
    # Mark as read if not already
    if not notif['is_read']:
        db.mark_notification_read(user_id, notification_id)
    
    text = f"📨 *{notif['title']}*\n\n"
    text += f"{notif['message']}\n\n"
    text += f"📅 *Date:* {notif['created_at']}\n"
    
    if notif['notification_type']:
        text += f"📋 *Type:* {notif['notification_type']}\n"
    
    # Build keyboard
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Back", callback_data="back_to_notifications")
    
    # If notification has a game link
    if notif['game_id']:
        builder.button(text="🎮 View Game", 
                      callback_data=f"view_game:{notif['game_id']}")
    
    builder.adjust(1)
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "back_to_notifications")
async def back_to_notifications(callback: CallbackQuery):
    """Go back to notifications list"""
    await show_notifications(callback.message)
