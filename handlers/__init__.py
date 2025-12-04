from .user_handlers import user_router
from .admin_handlers import admin_router
from .game_handlers import game_router
from .notification_handlers import notification_router

__all__ = ['user_router', 'admin_router', 'game_router', 'notification_router']
