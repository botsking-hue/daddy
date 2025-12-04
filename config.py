import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Bot Configuration
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    ADMIN_IDS: List[int] = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
    
    # Database Configuration
    DATABASE_NAME: str = "game_download.db"
    
    # Game Categories
    CATEGORIES: List[str] = ["Arcade", "Racing", "Soccer", "Action", "Adventure", 
                            "Puzzle", "RPG", "Simulation", "Sports", "Strategy"]
    
    # Platforms
    PLATFORMS: List[str] = ["Android", "PC", "iOS", "PlayStation", "Xbox", "Nintendo"]
    
    # WhatsApp Channel Links
    WHATSAPP_CHANNELS: dict = {
        "main": os.getenv("WHATSAPP_MAIN_LINK", "https://whatsapp.com/channel/your-main"),
        "updates": os.getenv("WHATSAPP_UPDATES_LINK", "https://whatsapp.com/channel/your-updates"),
        "new_games": os.getenv("WHATSAPP_NEWGAMES_LINK", "https://whatsapp.com/channel/your-newgames")
    }
    
    # Bot Settings
    MAX_GAMES_PER_PAGE: int = 10
    MAX_NOTIFICATIONS_PER_USER: int = 50
    
    # Image Storage (local path for now)
    IMAGE_STORAGE_PATH: str = "game_images/"
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required in .env file")
        if not cls.ADMIN_IDS:
            print("Warning: No ADMIN_IDS specified. Admin features will be disabled.")
