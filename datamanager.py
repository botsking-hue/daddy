import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from config import Config

class DataManager:
    def __init__(self, db_name: str = Config.DATABASE_NAME):
        self.db_name = db_name
        self.connection = None
        self.create_tables()
        
    def connect(self):
        """Create database connection"""
        self.connection = sqlite3.connect(self.db_name, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        return self.connection
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
    def create_tables(self):
        """Create all necessary tables"""
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notification_enabled BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Games table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    download_link TEXT NOT NULL,
                    image_path TEXT,
                    file_size TEXT,
                    version TEXT,
                    requirements TEXT,
                    rating REAL DEFAULT 0.0,
                    download_count INTEGER DEFAULT 0,
                    is_featured BOOLEAN DEFAULT FALSE,
                    is_verified BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Categories table (for quick filtering)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    name TEXT PRIMARY KEY,
                    game_count INTEGER DEFAULT 0
                )
            ''')
            
            # Insert default categories
            for category in Config.CATEGORIES:
                cursor.execute('''
                    INSERT OR IGNORE INTO categories (name) VALUES (?)
                ''', (category,))
            
            # Platforms table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS platforms (
                    name TEXT PRIMARY KEY,
                    game_count INTEGER DEFAULT 0
                )
            ''')
            
            # Insert default platforms
            for platform in Config.PLATFORMS:
                cursor.execute('''
                    INSERT OR IGNORE INTO platforms (name) VALUES (?)
                ''', (platform,))
            
            # Notifications table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    notification_type TEXT DEFAULT 'info',
                    game_id INTEGER,
                    sent_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id),
                    FOREIGN KEY (sent_by) REFERENCES users(user_id)
                )
            ''')
            
            # User notifications (read status)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_notifications (
                    user_id INTEGER,
                    notification_id INTEGER,
                    is_read BOOLEAN DEFAULT FALSE,
                    read_at TIMESTAMP,
                    PRIMARY KEY (user_id, notification_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (notification_id) REFERENCES notifications(id)
                )
            ''')
            
            # User favorites
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS favorites (
                    user_id INTEGER,
                    game_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, game_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (game_id) REFERENCES games(id)
                )
            ''')
            
            # Search history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    query TEXT,
                    results_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            conn.commit()
    
    # User Management Methods
    def add_user(self, user_id: int, username: str = None, 
                 first_name: str = None, last_name: str = None):
        """Add or update user"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, last_active)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username, first_name, last_name))
            
            # Check if user is admin
            cursor.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            
            if user and user['is_admin']:
                return True  # Is admin
            return False  # Not admin
    
    def get_user(self, user_id: int):
        """Get user by ID"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            return cursor.fetchone()
    
    def update_user_activity(self, user_id: int):
        """Update user's last active timestamp"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET last_active = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (user_id,))
    
    # Game Management Methods
    def add_game(self, game_data: Dict) -> int:
        """Add a new game"""
        with self.connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO games (
                    title, description, category, platform, download_link,
                    image_path, file_size, version, requirements, is_verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_data['title'],
                game_data.get('description'),
                game_data['category'],
                game_data['platform'],
                game_data['download_link'],
                game_data.get('image_path'),
                game_data.get('file_size'),
                game_data.get('version'),
                game_data.get('requirements'),
                game_data.get('is_verified', True)
            ))
            
            game_id = cursor.lastrowid
            
            # Update category count
            cursor.execute('''
                UPDATE categories SET game_count = game_count + 1 
                WHERE name = ?
            ''', (game_data['category'],))
            
            # Update platform count
            cursor.execute('''
                UPDATE platforms SET game_count = game_count + 1 
                WHERE name = ?
            ''', (game_data['platform'],))
            
            conn.commit()
            return game_id
    
    def get_game(self, game_id: int):
        """Get game by ID"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM games WHERE id = ?', (game_id,))
            return cursor.fetchone()
    
    def update_game(self, game_id: int, game_data: Dict):
        """Update existing game"""
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Get old category and platform
            cursor.execute('SELECT category, platform FROM games WHERE id = ?', (game_id,))
            old_game = cursor.fetchone()
            
            # Update game
            cursor.execute('''
                UPDATE games SET 
                    title = ?, description = ?, category = ?, platform = ?,
                    download_link = ?, image_path = ?, file_size = ?,
                    version = ?, requirements = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                game_data['title'],
                game_data.get('description'),
                game_data['category'],
                game_data['platform'],
                game_data['download_link'],
                game_data.get('image_path'),
                game_data.get('file_size'),
                game_data.get('version'),
                game_data.get('requirements'),
                game_id
            ))
            
            # Update category counts if changed
            if old_game and old_game['category'] != game_data['category']:
                cursor.execute('''
                    UPDATE categories SET game_count = game_count - 1 
                    WHERE name = ?
                ''', (old_game['category'],))
                cursor.execute('''
                    UPDATE categories SET game_count = game_count + 1 
                    WHERE name = ?
                ''', (game_data['category'],))
            
            # Update platform counts if changed
            if old_game and old_game['platform'] != game_data['platform']:
                cursor.execute('''
                    UPDATE platforms SET game_count = game_count - 1 
                    WHERE name = ?
                ''', (old_game['platform'],))
                cursor.execute('''
                    UPDATE platforms SET game_count = game_count + 1 
                    WHERE name = ?
                ''', (game_data['platform'],))
            
            conn.commit()
    
    def delete_game(self, game_id: int):
        """Delete a game"""
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Get game info for updating counts
            cursor.execute('SELECT category, platform FROM games WHERE id = ?', (game_id,))
            game = cursor.fetchone()
            
            if game:
                # Delete game
                cursor.execute('DELETE FROM games WHERE id = ?', (game_id,))
                
                # Update category count
                cursor.execute('''
                    UPDATE categories SET game_count = game_count - 1 
                    WHERE name = ?
                ''', (game['category'],))
                
                # Update platform count
                cursor.execute('''
                    UPDATE platforms SET game_count = game_count - 1 
                    WHERE name = ?
                ''', (game['platform'],))
                
                # Delete from favorites
                cursor.execute('DELETE FROM favorites WHERE game_id = ?', (game_id,))
            
            conn.commit()
    
    def search_games(self, query: str, category: str = None, 
                    platform: str = None, limit: int = 10, offset: int = 0):
        """Search games with filters"""
        with self.connect() as conn:
            cursor = conn.cursor()
            
            sql = '''
                SELECT * FROM games 
                WHERE (title LIKE ? OR description LIKE ?)
            '''
            params = [f'%{query}%', f'%{query}%']
            
            if category:
                sql += ' AND category = ?'
                params.append(category)
            
            if platform:
                sql += ' AND platform = ?'
                params.append(platform)
            
            sql += ' AND is_verified = TRUE ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(sql, params)
            return cursor.fetchall()
    
    def get_games_by_category(self, category: str, limit: int = 10, offset: int = 0):
        """Get games by category"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM games 
                WHERE category = ? AND is_verified = TRUE 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (category, limit, offset))
            return cursor.fetchall()
    
    def get_games_by_platform(self, platform: str, limit: int = 10, offset: int = 0):
        """Get games by platform"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM games 
                WHERE platform = ? AND is_verified = TRUE 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (platform, limit, offset))
            return cursor.fetchall()
    
    def get_featured_games(self, limit: int = 5):
        """Get featured games"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM games 
                WHERE is_featured = TRUE AND is_verified = TRUE 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
    
    def increment_download_count(self, game_id: int):
        """Increment download counter"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE games SET download_count = download_count + 1 
                WHERE id = ?
            ''', (game_id,))
            conn.commit()
    
    # Notification Methods
    def add_notification(self, title: str, message: str, 
                        notification_type: str = 'info', 
                        game_id: int = None, sent_by: int = None):
        """Add a notification"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notifications 
                (title, message, notification_type, game_id, sent_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, message, notification_type, game_id, sent_by))
            
            notification_id = cursor.lastrowid
            
            # Distribute to all users with notifications enabled
            cursor.execute('''
                INSERT INTO user_notifications (user_id, notification_id)
                SELECT user_id, ? FROM users 
                WHERE notification_enabled = TRUE
            ''', (notification_id,))
            
            conn.commit()
            return notification_id
    
    def get_user_notifications(self, user_id: int, limit: int = 10, offset: int = 0):
        """Get notifications for a user"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT n.*, un.is_read, un.read_at 
                FROM notifications n
                JOIN user_notifications un ON n.id = un.notification_id
                WHERE un.user_id = ?
                ORDER BY n.created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            return cursor.fetchall()
    
    def mark_notification_read(self, user_id: int, notification_id: int):
        """Mark notification as read"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_notifications 
                SET is_read = TRUE, read_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND notification_id = ?
            ''', (user_id, notification_id))
            conn.commit()
    
    def get_unread_count(self, user_id: int):
        """Get count of unread notifications"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count FROM user_notifications
                WHERE user_id = ? AND is_read = FALSE
            ''', (user_id,))
            result = cursor.fetchone()
            return result['count'] if result else 0
    
    # Favorites Methods
    def add_favorite(self, user_id: int, game_id: int):
        """Add game to favorites"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO favorites (user_id, game_id)
                VALUES (?, ?)
            ''', (user_id, game_id))
            conn.commit()
    
    def remove_favorite(self, user_id: int, game_id: int):
        """Remove game from favorites"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM favorites 
                WHERE user_id = ? AND game_id = ?
            ''', (user_id, game_id))
            conn.commit()
    
    def get_user_favorites(self, user_id: int, limit: int = 10, offset: int = 0):
        """Get user's favorite games"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT g.* FROM games g
                JOIN favorites f ON g.id = f.game_id
                WHERE f.user_id = ? AND g.is_verified = TRUE
                ORDER BY f.created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            return cursor.fetchall()
    
    def is_favorite(self, user_id: int, game_id: int):
        """Check if game is in user's favorites"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM favorites 
                WHERE user_id = ? AND game_id = ?
            ''', (user_id, game_id))
            return cursor.fetchone() is not None
    
    # Statistics Methods
    def get_statistics(self):
        """Get overall statistics"""
        with self.connect() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total games
            cursor.execute('SELECT COUNT(*) as count FROM games WHERE is_verified = TRUE')
            stats['total_games'] = cursor.fetchone()['count']
            
            # Total downloads
            cursor.execute('SELECT SUM(download_count) as total FROM games')
            stats['total_downloads'] = cursor.fetchone()['total'] or 0
            
            # Total users
            cursor.execute('SELECT COUNT(*) as count FROM users')
            stats['total_users'] = cursor.fetchone()['count']
            
            # Most popular category
            cursor.execute('''
                SELECT category, COUNT(*) as count FROM games 
                WHERE is_verified = TRUE 
                GROUP BY category 
                ORDER BY count DESC 
                LIMIT 1
            ''')
            stats['popular_category'] = cursor.fetchone()
            
            # Most popular platform
            cursor.execute('''
                SELECT platform, COUNT(*) as count FROM games 
                WHERE is_verified = TRUE 
                GROUP BY platform 
                ORDER BY count DESC 
                LIMIT 1
            ''')
            stats['popular_platform'] = cursor.fetchone()
            
            return stats
    
    def get_all_categories(self):
        """Get all categories with counts"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name, game_count FROM categories 
                ORDER BY game_count DESC
            ''')
            return cursor.fetchall()
    
    def get_all_platforms(self):
        """Get all platforms with counts"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name, game_count FROM platforms 
                ORDER BY game_count DESC
            ''')
            return cursor.fetchall()
