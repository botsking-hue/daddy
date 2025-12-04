const TelegramBot = require('node-telegram-bot-api');
const sqlite3 = require('sqlite3').verbose();
require('dotenv').config();

// ==================== CONFIGURATION ====================
const config = {
  BOT_TOKEN: process.env.BOT_TOKEN,
  ADMIN_IDS: process.env.ADMIN_IDS 
    ? process.env.ADMIN_IDS.split(',').map(id => parseInt(id.trim())) 
    : [],
  
  DATABASE_NAME: "game_download.db",
  
  CATEGORIES: [
    { name: "🎮 Action", value: "Action" },
    { name: "🏎️ Racing", value: "Racing" },
    { name: "⚽ Sports", value: "Sports" },
    { name: "🧩 Puzzle", value: "Puzzle" },
    { name: "🗺️ Adventure", value: "Adventure" },
    { name: "👑 RPG", value: "RPG" },
    { name: "🎲 Simulation", value: "Simulation" },
    { name: "🏰 Strategy", value: "Strategy" },
    { name: "🕹️ Arcade", value: "Arcade" },
    { name: "🎯 Shooting", value: "Shooting" }
  ],
  
  PLATFORMS: [
    { name: "🤖 Android", value: "Android" },
    { name: "💻 PC", value: "PC" },
    { name: "📱 iOS", value: "iOS" },
    { name: "🎮 PlayStation", value: "PlayStation" },
    { name: "🎮 Xbox", value: "Xbox" },
    { name: "🎮 Nintendo", value: "Nintendo" }
  ],
  
  MAX_GAMES_PER_PAGE: 8,
  GAMES_PER_ROW: 2
};

// Validate configuration
if (!config.BOT_TOKEN) {
  console.error("❌ BOT_TOKEN is required in .env file");
  process.exit(1);
}

// ==================== STATE MANAGEMENT ====================
class StateManager {
  constructor() {
    this.userStates = new Map();
  }

  setState(userId, state, data = {}) {
    this.userStates.set(userId, { state, data, timestamp: Date.now() });
  }

  getState(userId) {
    return this.userStates.get(userId);
  }

  clearState(userId) {
    this.userStates.delete(userId);
  }

  updateData(userId, newData) {
    const state = this.getState(userId);
    if (state) {
      state.data = { ...state.data, ...newData };
      this.setState(userId, state.state, state.data);
    }
  }
}

const stateManager = new StateManager();

// ==================== DATABASE MANAGER ====================
class DatabaseManager {
  constructor(dbName = config.DATABASE_NAME) {
    this.db = new sqlite3.Database(dbName);
    this.initDatabase();
  }

  initDatabase() {
    this.db.serialize(() => {
      // Users table
      this.db.run(`
        CREATE TABLE IF NOT EXISTS users (
          user_id INTEGER PRIMARY KEY,
          username TEXT,
          first_name TEXT,
          last_name TEXT,
          is_admin BOOLEAN DEFAULT FALSE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // Games table
      this.db.run(`
        CREATE TABLE IF NOT EXISTS games (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          description TEXT,
          category TEXT NOT NULL,
          platform TEXT NOT NULL,
          download_link TEXT NOT NULL,
          image_url TEXT,
          file_size TEXT,
          version TEXT,
          requirements TEXT,
          rating REAL DEFAULT 0.0,
          download_count INTEGER DEFAULT 0,
          is_featured BOOLEAN DEFAULT FALSE,
          is_verified BOOLEAN DEFAULT TRUE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // Favorites table
      this.db.run(`
        CREATE TABLE IF NOT EXISTS favorites (
          user_id INTEGER,
          game_id INTEGER,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (user_id, game_id)
        )
      `);

      // Create some sample games
      this.createSampleGames();
    });
  }

  async createSampleGames() {
    try {
      const count = await this.get('SELECT COUNT(*) as count FROM games');
      if (count.count === 0) {
        const sampleGames = [
          {
            title: "Racing Thunder",
            description: "High-speed racing game with realistic graphics and multiple tracks",
            category: "Racing",
            platform: "Android",
            download_link: "https://example.com/racing-thunder",
            file_size: "250 MB",
            version: "2.1.4",
            is_featured: true
          },
          {
            title: "Soccer Stars",
            description: "Exciting soccer game with realistic physics and multiplayer mode",
            category: "Sports",
            platform: "iOS",
            download_link: "https://example.com/soccer-stars",
            file_size: "180 MB",
            version: "1.5.2",
            is_featured: true
          },
          {
            title: "Puzzle Quest",
            description: "Challenging puzzle game with hundreds of levels",
            category: "Puzzle",
            platform: "Android",
            download_link: "https://example.com/puzzle-quest",
            file_size: "95 MB",
            version: "3.0.1"
          }
        ];

        for (const game of sampleGames) {
          await this.run(`
            INSERT INTO games (title, description, category, platform, download_link, 
                             file_size, version, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
          `, [
            game.title, game.description, game.category, game.platform,
            game.download_link, game.file_size, game.version, true
          ]);
        }
        console.log("✅ Sample games created");
      }
    } catch (error) {
      console.error("Error creating sample games:", error);
    }
  }

  // Promise-based database methods
  run(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.run(sql, params, function(err) {
        if (err) reject(err);
        else resolve({ id: this.lastID, changes: this.changes });
      });
    });
  }

  get(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.get(sql, params, (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  }

  all(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.all(sql, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  }

  // User methods
  async addUser(userId, username, firstName, lastName) {
    try {
      await this.run(`
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name, last_active)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
      `, [userId, username, firstName, lastName]);
      
      // Check if user is admin
      const isAdmin = config.ADMIN_IDS.includes(userId);
      if (isAdmin) {
        await this.run('UPDATE users SET is_admin = TRUE WHERE user_id = ?', [userId]);
      }
      
      return isAdmin;
    } catch (error) {
      console.error('Error adding user:', error);
      return false;
    }
  }

  async getUser(userId) {
    try {
      return await this.get(
        'SELECT * FROM users WHERE user_id = ?',
        [userId]
      );
    } catch (error) {
      console.error('Error getting user:', error);
      return null;
    }
  }

  // Game methods
  async addGame(gameData) {
    try {
      const result = await this.run(`
        INSERT INTO games (
          title, description, category, platform, download_link,
          file_size, version, requirements, is_verified
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `, [
        gameData.title,
        gameData.description || null,
        gameData.category,
        gameData.platform,
        gameData.download_link,
        gameData.file_size || null,
        gameData.version || null,
        gameData.requirements || null,
        true
      ]);
      
      return result.id;
    } catch (error) {
      console.error('Error adding game:', error);
      return null;
    }
  }

  async getGame(gameId) {
    try {
      return await this.get(
        'SELECT * FROM games WHERE id = ? AND is_verified = TRUE',
        [gameId]
      );
    } catch (error) {
      console.error('Error getting game:', error);
      return null;
    }
  }

  async getGamesByCategory(category, limit = config.MAX_GAMES_PER_PAGE) {
    try {
      return await this.all(`
        SELECT * FROM games 
        WHERE category = ? AND is_verified = TRUE 
        ORDER BY created_at DESC 
        LIMIT ?
      `, [category, limit]);
    } catch (error) {
      console.error('Error getting games by category:', error);
      return [];
    }
  }

  async getGamesByPlatform(platform, limit = config.MAX_GAMES_PER_PAGE) {
    try {
      return await this.all(`
        SELECT * FROM games 
        WHERE platform = ? AND is_verified = TRUE 
        ORDER BY created_at DESC 
        LIMIT ?
      `, [platform, limit]);
    } catch (error) {
      console.error('Error getting games by platform:', error);
      return [];
    }
  }

  async getFeaturedGames(limit = 6) {
    try {
      return await this.all(`
        SELECT * FROM games 
        WHERE is_featured = TRUE AND is_verified = TRUE 
        ORDER BY created_at DESC 
        LIMIT ?
      `, [limit]);
    } catch (error) {
      console.error('Error getting featured games:', error);
      return [];
    }
  }

  async searchGames(query, limit = config.MAX_GAMES_PER_PAGE) {
    try {
      return await this.all(`
        SELECT * FROM games 
        WHERE (title LIKE ? OR description LIKE ?) 
        AND is_verified = TRUE 
        ORDER BY created_at DESC 
        LIMIT ?
      `, [`%${query}%`, `%${query}%`, limit]);
    } catch (error) {
      console.error('Error searching games:', error);
      return [];
    }
  }

  async getAllCategories() {
    try {
      const categories = await this.all(`
        SELECT category, COUNT(*) as count 
        FROM games 
        WHERE is_verified = TRUE 
        GROUP BY category 
        ORDER BY count DESC
      `);
      
      // Merge with config categories to include all
      const allCategories = config.CATEGORIES.map(cat => {
        const dbCat = categories.find(c => c.category === cat.value);
        return {
          name: cat.name,
          value: cat.value,
          count: dbCat ? dbCat.count : 0
        };
      });
      
      return allCategories;
    } catch (error) {
      console.error('Error getting categories:', error);
      return [];
    }
  }

  async getAllPlatforms() {
    try {
      const platforms = await this.all(`
        SELECT platform, COUNT(*) as count 
        FROM games 
        WHERE is_verified = TRUE 
        GROUP BY platform 
        ORDER BY count DESC
      `);
      
      // Merge with config platforms
      const allPlatforms = config.PLATFORMS.map(plat => {
        const dbPlat = platforms.find(p => p.platform === plat.value);
        return {
          name: plat.name,
          value: plat.value,
          count: dbPlat ? dbPlat.count : 0
        };
      });
      
      return allPlatforms;
    } catch (error) {
      console.error('Error getting platforms:', error);
      return [];
    }
  }

  // Statistics
  async getStatistics() {
    try {
      const stats = {};
      
      const totalGames = await this.get(
        'SELECT COUNT(*) as count FROM games WHERE is_verified = TRUE'
      );
      stats.totalGames = totalGames.count;
      
      const totalDownloads = await this.get(
        'SELECT SUM(download_count) as total FROM games'
      );
      stats.totalDownloads = totalDownloads.total || 0;
      
      const totalUsers = await this.get(
        'SELECT COUNT(*) as count FROM users'
      );
      stats.totalUsers = totalUsers.count;
      
      const popularCategory = await this.get(`
        SELECT category, COUNT(*) as count 
        FROM games 
        WHERE is_verified = TRUE 
        GROUP BY category 
        ORDER BY count DESC 
        LIMIT 1
      `);
      stats.popularCategory = popularCategory;
      
      const popularPlatform = await this.get(`
        SELECT platform, COUNT(*) as count 
        FROM games 
        WHERE is_verified = TRUE 
        GROUP BY platform 
        ORDER BY count DESC 
        LIMIT 1
      `);
      stats.popularPlatform = popularPlatform;
      
      return stats;
    } catch (error) {
      console.error('Error getting statistics:', error);
      return {};
    }
  }

  // Favorites
  async addFavorite(userId, gameId) {
    try {
      await this.run(`
        INSERT OR IGNORE INTO favorites (user_id, game_id)
        VALUES (?, ?)
      `, [userId, gameId]);
      return true;
    } catch (error) {
      console.error('Error adding favorite:', error);
      return false;
    }
  }

  async removeFavorite(userId, gameId) {
    try {
      await this.run(`
        DELETE FROM favorites 
        WHERE user_id = ? AND game_id = ?
      `, [userId, gameId]);
      return true;
    } catch (error) {
      console.error('Error removing favorite:', error);
      return false;
    }
  }

  async isFavorite(userId, gameId) {
    try {
      const result = await this.get(`
        SELECT 1 FROM favorites 
        WHERE user_id = ? AND game_id = ?
      `, [userId, gameId]);
      return result !== undefined;
    } catch (error) {
      console.error('Error checking favorite:', error);
      return false;
    }
  }

  async getUserFavorites(userId, limit = config.MAX_GAMES_PER_PAGE) {
    try {
      return await this.all(`
        SELECT g.* FROM games g
        JOIN favorites f ON g.id = f.game_id
        WHERE f.user_id = ? AND g.is_verified = TRUE
        ORDER BY f.created_at DESC
        LIMIT ?
      `, [userId, limit]);
    } catch (error) {
      console.error('Error getting favorites:', error);
      return [];
    }
  }

  close() {
    this.db.close();
  }
}

// ==================== UI HELPERS ====================
const UI = {
  // Main menu keyboard
  getMainMenu(isAdmin = false) {
    const buttons = [
      [
        { text: "🔍 Search", callback_data: "menu:search" },
        { text: "📁 Categories", callback_data: "menu:categories" }
      ],
      [
        { text: "📱 Platforms", callback_data: "menu:platforms" },
        { text: "🔥 Featured", callback_data: "menu:featured" }
      ],
      [
        { text: "⭐ Favorites", callback_data: "menu:favorites" },
        { text: "📊 Stats", callback_data: "menu:stats" }
      ],
      [
        { text: "ℹ️ Help", callback_data: "menu:help" }
      ]
    ];

    if (isAdmin) {
      buttons.push([{ text: "👑 Admin", callback_data: "menu:admin" }]);
    }

    return {
      reply_markup: {
        inline_keyboard: buttons
      }
    };
  },

  // Categories keyboard
  getCategoriesKeyboard(categories) {
    const buttons = categories.map(cat => ({
      text: `${cat.name} (${cat.count})`,
      callback_data: `category:${cat.value}`
    }));

    // Group buttons 2 per row
    const rows = [];
    for (let i = 0; i < buttons.length; i += 2) {
      rows.push(buttons.slice(i, i + 2));
    }
    
    // Add back button
    rows.push([{ text: "🔙 Back to Menu", callback_data: "menu:back" }]);

    return {
      reply_markup: {
        inline_keyboard: rows
      }
    };
  },

  // Platforms keyboard
  getPlatformsKeyboard(platforms) {
    const buttons = platforms.map(plat => ({
      text: `${plat.name} (${plat.count})`,
      callback_data: `platform:${plat.value}`
    }));

    const rows = [];
    for (let i = 0; i < buttons.length; i += 2) {
      rows.push(buttons.slice(i, i + 2));
    }
    
    rows.push([{ text: "🔙 Back to Menu", callback_data: "menu:back" }]);

    return {
      reply_markup: {
        inline_keyboard: rows
      }
    };
  },

  // Games list keyboard
  getGamesKeyboard(games, type, value) {
    const rows = [];
    
    // Add games as buttons (2 per row)
    for (let i = 0; i < games.length; i += config.GAMES_PER_ROW) {
      const rowGames = games.slice(i, i + config.GAMES_PER_ROW);
      const row = rowGames.map(game => ({
        text: `🎮 ${game.title.substring(0, 15)}...`,
        callback_data: `game:${game.id}`
      }));
      rows.push(row);
    }

    // Add back button based on context
    const backButton = type === 'category' 
      ? { text: `🔙 Back to ${value}`, callback_data: `category:${value}` }
      : type === 'platform'
        ? { text: `🔙 Back to ${value}`, callback_data: `platform:${value}` }
        : { text: "🔙 Back to Menu", callback_data: "menu:back" };

    rows.push([backButton]);

    return {
      reply_markup: {
        inline_keyboard: rows
      }
    };
  },

  // Game details keyboard
  async getGameDetailsKeyboard(gameId, userId, db) {
    const isFavorite = await db.isFavorite(userId, gameId);
    
    return {
      reply_markup: {
        inline_keyboard: [
          [
            { 
              text: "⬇️ Download Now", 
              url: "https://example.com/download" // This would be the actual download link
            }
          ],
          [
            { 
              text: isFavorite ? "💔 Remove Favorite" : "❤️ Add to Favorites", 
              callback_data: `toggle_fav:${gameId}`
            }
          ],
          [
            { text: "📱 Share", callback_data: `share:${gameId}` },
            { text: "⭐ Rate", callback_data: `rate:${gameId}` }
          ],
          [
            { text: "🔙 Back to Games", callback_data: "menu:back_to_games" },
            { text: "🏠 Main Menu", callback_data: "menu:back" }
          ]
        ]
      }
    };
  },

  // Admin keyboard
  getAdminKeyboard() {
    return {
      reply_markup: {
        inline_keyboard: [
          [
            { text: "➕ Add Game", callback_data: "admin:add_game" },
            { text: "📊 Stats", callback_data: "admin:stats" }
          ],
          [
            { text: "👥 Users", callback_data: "admin:users" },
            { text: "🎮 Games", callback_data: "admin:games" }
          ],
          [
            { text: "🔙 Back to Menu", callback_data: "menu:back" }
          ]
        ]
      }
    };
  },

  // Search keyboard
  getSearchKeyboard() {
    return {
      reply_markup: {
        inline_keyboard: [
          [
            { text: "🔍 Search Again", callback_data: "menu:search" },
            { text: "📁 Browse Categories", callback_data: "menu:categories" }
          ],
          [
            { text: "🔙 Back to Menu", callback_data: "menu:back" }
          ]
        ]
      }
    };
  }
};

// ==================== BOT INITIALIZATION ====================
const bot = new TelegramBot(config.BOT_TOKEN, { polling: true });
const db = new DatabaseManager();

// Set bot commands
bot.setMyCommands([
  { command: 'start', description: '🚀 Start the bot' },
  { command: 'menu', description: '📱 Show main menu' },
  { command: 'help', description: '❓ Get help' },
  { command: 'categories', description: '📁 Browse by category' },
  { command: 'platforms', description: '📱 Browse by platform' },
  { command: 'featured', description: '🔥 Featured games' },
  { command: 'favorites', description: '⭐ Your favorites' },
  { command: 'stats', description: '📊 Bot statistics' }
]);

// ==================== MESSAGE HANDLERS ====================
bot.onText(/\/start/, async (msg) => {
  const chatId = msg.chat.id;
  const userId = msg.from.id;
  const username = msg.from.username;
  const firstName = msg.from.first_name;
  const lastName = msg.from.last_name;

  try {
    const isAdmin = await db.addUser(userId, username, firstName, lastName);
    
    const welcomeText = 
      `✨ *Welcome to Game Download Hub!* ✨\n\n` +
      `🎮 *Your Ultimate Gaming Destination*\n\n` +
      `Discover thousands of free games across multiple platforms!\n\n` +
      `📱 *Available Platforms:* Android, iOS, PC, PlayStation, Xbox, Nintendo\n\n` +
      `🎯 *How to get started:*\n` +
      `1. Browse games by category or platform\n` +
      `2. Click on any game to view details\n` +
      `3. Download instantly with one click\n` +
      `4. Save favorites for quick access\n\n` +
      `⬇️ *Use the menu below to explore!*`;
    
    await bot.sendMessage(chatId, welcomeText, {
      parse_mode: 'Markdown',
      ...UI.getMainMenu(isAdmin)
    });
    
    console.log(`👤 New user: ${userId} (${firstName})`);
  } catch (error) {
    console.error('Start command error:', error);
    bot.sendMessage(chatId, '❌ Error starting bot. Please try again.');
  }
});

bot.onText(/\/menu/, async (msg) => {
  const chatId = msg.chat.id;
  const userId = msg.from.id;
  
  try {
    const user = await db.getUser(userId);
    const isAdmin = user ? user.is_admin : false;
    
    await bot.sendMessage(chatId, '📱 *Main Menu*', {
      parse_mode: 'Markdown',
      ...UI.getMainMenu(isAdmin)
    });
  } catch (error) {
    console.error('Menu command error:', error);
  }
});

bot.onText(/\/help/, (msg) => {
  const chatId = msg.chat.id;
  
  const helpText = 
    `🎮 *Game Download Bot Help*\n\n` +
    `*Main Features:*\n` +
    `• Browse games by category or platform\n` +
    `• Search for specific games\n` +
    `• Save games to favorites\n` +
    `• View game details and requirements\n` +
    `• One-click downloads\n\n` +
    `*Available Commands:*\n` +
    `/start - Start the bot\n` +
    `/menu - Show main menu\n` +
    `/categories - Browse by category\n` +
    `/platforms - Browse by platform\n` +
    `/featured - Featured games\n` +
    `/favorites - Your favorite games\n` +
    `/stats - Bot statistics\n\n` +
    `*Quick Tips:*\n` +
    `📍 Use the inline menu for faster navigation\n` +
    `⭐ Click the heart icon to save favorites\n` +
    `🔍 Use specific keywords for better search results\n\n` +
    `*Need Help?*\n` +
    `Contact support if you encounter any issues.`;
  
  bot.sendMessage(chatId, helpText, { 
    parse_mode: 'Markdown',
    ...UI.getMainMenu(false)
  });
});

// ==================== CALLBACK QUERY HANDLERS ====================
bot.on('callback_query', async (callbackQuery) => {
  const msg = callbackQuery.message;
  const data = callbackQuery.data;
  const userId = callbackQuery.from.id;
  const chatId = msg.chat.id;
  
  try {
    // Handle menu navigation
    if (data.startsWith('menu:')) {
      const action = data.split(':')[1];
      
      switch(action) {
        case 'back':
          const user = await db.getUser(userId);
          const isAdmin = user ? user.is_admin : false;
          await bot.editMessageText('📱 *Main Menu*', {
            chat_id: chatId,
            message_id: msg.message_id,
            parse_mode: 'Markdown',
            ...UI.getMainMenu(isAdmin)
          });
          break;
          
        case 'categories':
          const categories = await db.getAllCategories();
          const categoriesText = `📁 *Browse Games by Category*\n\n` +
            `Select a category to view available games:\n\n` +
            categories.map(cat => `• ${cat.name} - ${cat.count} games`).join('\n');
          
          await bot.editMessageText(categoriesText, {
            chat_id: chatId,
            message_id: msg.message_id,
            parse_mode: 'Markdown',
            ...UI.getCategoriesKeyboard(categories)
          });
          break;
          
        case 'platforms':
          const platforms = await db.getAllPlatforms();
          const platformsText = `📱 *Browse Games by Platform*\n\n` +
            `Select a platform to view available games:\n\n` +
            platforms.map(plat => `• ${plat.name} - ${plat.count} games`).join('\n');
          
          await bot.editMessageText(platformsText, {
            chat_id: chatId,
            message_id: msg.message_id,
            parse_mode: 'Markdown',
            ...UI.getPlatformsKeyboard(platforms)
          });
          break;
          
        case 'featured':
          const featuredGames = await db.getFeaturedGames(6);
          const featuredText = featuredGames.length > 0 
            ? `🔥 *Featured Games*\n\n` +
              `Check out our top picks this week:\n\n` +
              featuredGames.map((game, i) => 
                `${i + 1}. *${game.title}*\n   📱 ${game.platform} | ⬇️ ${game.download_count} downloads`
              ).join('\n\n')
            : `🔥 *Featured Games*\n\nNo featured games available yet. Check back soon!`;
          
          await bot.editMessageText(featuredText, {
            chat_id: chatId,
            message_id: msg.message_id,
            parse_mode: 'Markdown',
            ...UI.getGamesKeyboard(featuredGames, 'featured', '')
          });
          break;
          
        case 'favorites':
          const favorites = await db.getUserFavorites(userId);
          const favoritesText = favorites.length > 0
            ? `⭐ *Your Favorite Games*\n\n` +
              `You have ${favorites.length} game(s) in favorites:\n\n` +
              favorites.map((game, i) => 
                `${i + 1}. *${game.title}*\n   📁 ${game.category} | 📱 ${game.platform}`
              ).join('\n\n')
            : `⭐ *Your Favorite Games*\n\n` +
              `You haven't added any games to favorites yet.\n\n` +
              `Browse games and click the ❤️ button to add them to your favorites!`;
          
          await bot.editMessageText(favoritesText, {
            chat_id: chatId,
            message_id: msg.message_id,
            parse_mode: 'Markdown',
            ...UI.getGamesKeyboard(favorites, 'favorites', '')
          });
          break;
          
        case 'stats':
          const stats = await db.getStatistics();
          const statsText = 
            `📊 *Bot Statistics*\n\n` +
            `🎮 *Total Games:* ${stats.totalGames || 0}\n` +
            `📥 *Total Downloads:* ${stats.totalDownloads || 0}\n` +
            `👥 *Total Users:* ${stats.totalUsers || 0}\n\n` +
            `🏆 *Most Popular:*\n` +
            (stats.popularCategory ? `• Category: ${stats.popularCategory.category} (${stats.popularCategory.count} games)\n` : '') +
            (stats.popularPlatform ? `• Platform: ${stats.popularPlatform.platform} (${stats.popularPlatform.count} games)\n` : '');
          
          await bot.editMessageText(statsText, {
            chat_id: chatId,
            message_id: msg.message_id,
            parse_mode: 'Markdown',
            ...UI.getMainMenu(false)
          });
          break;
          
        case 'search':
          stateManager.setState(userId, 'searching');
          await bot.editMessageText(
            `🔍 *Search Games*\n\n` +
            `Please type your search query:\n` +
            `_Example: racing, puzzle, action, android_`,
            {
              chat_id: chatId,
              message_id: msg.message_id,
              parse_mode: 'Markdown',
              ...UI.getSearchKeyboard()
            }
          );
          break;
          
        case 'help':
          await bot.editMessageText(
            `❓ *Need Help?*\n\n` +
            `This bot helps you find and download games.\n\n` +
            `*Quick Guide:*\n` +
            `1. Use Categories or Platforms to browse\n` +
            `2. Click any game for details\n` +
            `3. Use Download button to get the game\n` +
            `4. Save favorites with ❤️ button\n\n` +
            `For issues, contact support.`,
            {
              chat_id: chatId,
              message_id: msg.message_id,
              parse_mode: 'Markdown',
              ...UI.getMainMenu(false)
            }
          );
          break;
          
        case 'admin':
          const userCheck = await db.getUser(userId);
          if (userCheck && userCheck.is_admin) {
            await bot.editMessageText('👑 *Admin Panel*', {
              chat_id: chatId,
              message_id: msg.message_id,
              parse_mode: 'Markdown',
              ...UI.getAdminKeyboard()
            });
          } else {
            await bot.answerCallbackQuery(callbackQuery.id, {
              text: '❌ Admin access only',
              show_alert: true
            });
          }
          break;
      }
    }
    
    // Handle category selection
    else if (data.startsWith('category:')) {
      const category = data.split(':')[1];
      const games = await db.getGamesByCategory(category);
      
      const categoryInfo = config.CATEGORIES.find(c => c.value === category);
      const categoryName = categoryInfo ? categoryInfo.name : category;
      
      const categoryText = games.length > 0
        ? `📁 *${categoryName} Games*\n\n` +
          `Found ${games.length} game(s):\n\n` +
          games.map((game, i) => 
            `${i + 1}. *${game.title}*\n   📱 ${game.platform} | ⬇️ ${game.download_count} downloads`
          ).join('\n\n')
        : `📁 *${categoryName} Games*\n\n` +
          `No games found in this category yet.\n` +
          `Check back soon or try another category!`;
      
      await bot.editMessageText(categoryText, {
        chat_id: chatId,
        message_id: msg.message_id,
        parse_mode: 'Markdown',
        ...UI.getGamesKeyboard(games, 'category', category)
      });
    }
    
    // Handle platform selection
    else if (data.startsWith('platform:')) {
      const platform = data.split(':')[1];
      const games = await db.getGamesByPlatform(platform);
      
      const platformInfo = config.PLATFORMS.find(p => p.value === platform);
      const platformName = platformInfo ? platformInfo.name : platform;
      
      const platformText = games.length > 0
        ? `📱 *${platformName} Games*\n\n` +
          `Found ${games.length} game(s):\n\n` +
          games.map((game, i) => 
            `${i + 1}. *${game.title}*\n   📁 ${game.category} | ⬇️ ${game.download_count} downloads`
          ).join('\n\n')
        : `📱 *${platformName} Games*\n\n` +
          `No games found for this platform yet.\n` +
          `Check back soon or try another platform!`;
      
      await bot.editMessageText(platformText, {
        chat_id: chatId,
        message_id: msg.message_id,
        parse_mode: 'Markdown',
        ...UI.getGamesKeyboard(games, 'platform', platform)
      });
    }
    
    // Handle game view
    else if (data.startsWith('game:')) {
      const gameId = parseInt(data.split(':')[1]);
      const game = await db.getGame(gameId);
      
      if (!game) {
        return bot.answerCallbackQuery(callbackQuery.id, {
          text: '❌ Game not found',
          show_alert: true
        });
      }
      
      // Format game details
      let gameText = 
        `🎮 *${game.title}*\n\n` +
        `📝 *Description:*\n${game.description || 'No description available'}\n\n` +
        `📋 *Details:*\n` +
        `• 📁 Category: ${game.category}\n` +
        `• 📱 Platform: ${game.platform}\n`;
      
      if (game.file_size) gameText += `• 📦 Size: ${game.file_size}\n`;
      if (game.version) gameText += `• 🔄 Version: ${game.version}\n`;
      if (game.requirements) gameText += `• ⚙️ Requirements: ${game.requirements}\n`;
      
      gameText += 
        `• ⬇️ Downloads: ${game.download_count}\n` +
        `• 📅 Added: ${game.created_at.substring(0, 10)}\n\n` +
        `⬇️ *Ready to download?* Click the button below!`;
      
      const keyboard = await UI.getGameDetailsKeyboard(gameId, userId, db);
      
      await bot.editMessageText(gameText, {
        chat_id: chatId,
        message_id: msg.message_id,
        parse_mode: 'Markdown',
        ...keyboard
      });
    }
    
    // Handle favorite toggle
    else if (data.startsWith('toggle_fav:')) {
      const gameId = parseInt(data.split(':')[1]);
      const isFavorite = await db.isFavorite(userId, gameId);
      
      if (isFavorite) {
        await db.removeFavorite(userId, gameId);
        await bot.answerCallbackQuery(callbackQuery.id, {
          text: '💔 Removed from favorites',
          show_alert: false
        });
      } else {
        await db.addFavorite(userId, gameId);
        await bot.answerCallbackQuery(callbackQuery.id, {
          text: '❤️ Added to favorites',
          show_alert: false
        });
      }
      
      // Update the message with new favorite status
      const game = await db.getGame(gameId);
      if (game) {
        const newIsFavorite = await db.isFavorite(userId, gameId);
        const keyboard = await UI.getGameDetailsKeyboard(gameId, userId, db);
        
        // Just update the favorite button, keep everything else
        await bot.editMessageReplyMarkup(keyboard.reply_markup, {
          chat_id: chatId,
          message_id: msg.message_id
        });
      }
    }
    
    // Handle share
    else if (data.startsWith('share:')) {
      const gameId = parseInt(data.split(':')[1]);
      const game = await db.getGame(gameId);
      
      if (game) {
        const shareText = 
          `🎮 Check out this game!\n\n` +
          `*${game.title}*\n` +
          `${game.description?.substring(0, 100)}...\n\n` +
          `Download via @${bot.options.username}`;
        
        await bot.answerCallbackQuery(callbackQuery.id, {
          text: '📱 Share link copied to clipboard',
          show_alert: false
        });
      }
    }
    
    // Answer all callback queries
    await bot.answerCallbackQuery(callbackQuery.id);
    
  } catch (error) {
    console.error('Callback query error:', error);
    bot.answerCallbackQuery(callbackQuery.id, {
      text: '❌ Error processing request',
      show_alert: true
    });
  }
});

// ==================== SEARCH HANDLER ====================
bot.on('message', async (msg) => {
  if (!msg.text || msg.text.startsWith('/')) return;
  
  const userId = msg.from.id;
  const chatId = msg.chat.id;
  const state = stateManager.getState(userId);
  
  // Handle search queries
  if (state && state.state === 'searching') {
    const query = msg.text.trim();
    
    if (query.length < 2) {
      return bot.sendMessage(chatId, 'Please enter at least 2 characters to search.');
    }
    
    try {
      const games = await db.searchGames(query);
      
      if (games.length === 0) {
        await bot.sendMessage(chatId,
          `🔍 *Search Results for "${query}"*\n\n` +
          `❌ No games found matching your search.\n\n` +
          `💡 *Suggestions:*\n` +
          `• Try different keywords\n` +
          `• Browse by category instead\n` +
          `• Check spelling`,
          {
            parse_mode: 'Markdown',
            ...UI.getSearchKeyboard()
          }
        );
      } else {
        const searchText = 
          `🔍 *Search Results for "${query}"*\n\n` +
          `Found ${games.length} game(s):\n\n` +
          games.map((game, i) => 
            `${i + 1}. *${game.title}*\n` +
            `   📁 ${game.category} | 📱 ${game.platform}\n` +
            `   ⬇️ ${game.download_count} downloads`
          ).join('\n\n');
        
        await bot.sendMessage(chatId, searchText, {
          parse_mode: 'Markdown',
          ...UI.getGamesKeyboard(games, 'search', query)
        });
      }
    } catch (error) {
      console.error('Search error:', error);
      bot.sendMessage(chatId, '❌ Error searching games. Please try again.');
    }
    
    stateManager.clearState(userId);
  }
});

// ==================== ERROR HANDLING ====================
bot.on('polling_error', (error) => {
  console.error('Polling error:', error);
});

bot.on('error', (error) => {
  console.error('Bot error:', error);
});

// ==================== STARTUP ====================
console.log('🎮 Game Download Bot is starting...');
console.log('✅ Bot initialized successfully');
console.log('📊 Use /start to begin');

// Cleanup on exit
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down bot...');
  bot.stopPolling();
  db.close();
  process.exit(0);
});

// Auto-clean old states every hour
setInterval(() => {
  const now = Date.now();
  for (const [userId, state] of stateManager.userStates.entries()) {
    if (now - state.timestamp > 3600000) { // 1 hour
      stateManager.clearState(userId);
    }
  }
}, 3600000);
