require('dotenv').config();

const config = {
  // Bot Configuration
  BOT_TOKEN: process.env.BOT_TOKEN,
  ADMIN_IDS: process.env.ADMIN_IDS 
    ? process.env.ADMIN_IDS.split(',').map(id => parseInt(id.trim())) 
    : [],
  
  // Database
  DATABASE_NAME: "game_download.db",
  
  // Game Categories
  CATEGORIES: ["Arcade", "Racing", "Soccer", "Action", "Adventure", 
              "Puzzle", "RPG", "Simulation", "Sports", "Strategy"],
  
  // Platforms
  PLATFORMS: ["Android", "PC", "iOS", "PlayStation", "Xbox", "Nintendo"],
  
  // WhatsApp Channels
  WHATSAPP_CHANNELS: {
    main: process.env.WHATSAPP_MAIN_LINK || "",
    updates: process.env.WHATSAPP_UPDATES_LINK || "",
    new_games: process.env.WHATSAPP_NEWGAMES_LINK || ""
  },
  
  // Settings
  MAX_GAMES_PER_PAGE: 10,
  MAX_NOTIFICATIONS_PER_USER: 50,
  IMAGE_STORAGE_PATH: "game_images/",
  
  // Validation
  validate() {
    if (!this.BOT_TOKEN) {
      throw new Error("BOT_TOKEN is required in .env file");
    }
    if (this.ADMIN_IDS.length === 0) {
      console.warn("⚠️  No ADMIN_IDS specified. Admin features will be disabled.");
    }
  }
};

module.exports = config;
