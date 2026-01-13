import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from data_models import ProductTemplate, PriceRule, ScheduledJob

class DatabaseManager:
    """SQLite database for analytics and history"""
    
    def __init__(self):
        db_path = Path.home() / ".pod_wizard.db"
        try:
            self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
            self._init_tables()
        except sqlite3.DatabaseError as e:
            print(f"Database error: {e}. The file at {db_path} may be missing or corrupted. Try deleting it and restarting the app.")
            raise
    
    def _init_tables(self):
        """Initialize database tables"""
        cursor = self.conn.cursor()
        
        # Products history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                shop_id TEXT,
                title TEXT,
                product_type TEXT,
                price REAL,
                prompt TEXT,
                image_path TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Templates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                product_type TEXT,
                base_price REAL,
                prompt_template TEXT,
                tags TEXT,
                collection_name TEXT,
                auto_publish INTEGER,
                generate_marketing INTEGER
            )
        """)
        
        # Price rules
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_type TEXT UNIQUE,
                base_price REAL,
                markup_percent REAL
            )
        """)
        
        # Shops
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id TEXT UNIQUE,
                shop_name TEXT,
                printify_token TEXT,
                is_active INTEGER DEFAULT 0
            )
        """)
        
        # Scheduled jobs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheduled_time TIMESTAMP,
                prompts TEXT,
                product_type TEXT,
                price REAL,
                shop_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Analytics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                products_created INTEGER,
                products_published INTEGER,
                total_value REAL,
                avg_generation_time REAL
            )
        """)
        
        self.conn.commit()
    
    def add_product(self, product_data: Dict):
        """Add product to history"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO products (product_id, shop_id, title, product_type, price, prompt, image_path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_data.get('product_id'),
            product_data.get('shop_id'),
            product_data.get('title'),
            product_data.get('product_type'),
            product_data.get('price'),
            product_data.get('prompt'),
            product_data.get('image_path'),
            product_data.get('status', 'created')
        ))
        self.conn.commit()
    
    def get_products(self, limit: int = 100) -> List[Dict]:
        """Get product history"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM products ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def save_template(self, template: ProductTemplate):
        """Save product template"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO templates 
            (name, product_type, base_price, prompt_template, tags, collection_name, auto_publish, generate_marketing)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template.name,
            template.product_type,
            template.base_price,
            template.prompt_template,
            ','.join(template.tags),
            template.collection_name,
            int(template.auto_publish),
            int(template.generate_marketing)
        ))
        self.conn.commit()
    
    def get_templates(self) -> List[ProductTemplate]:
        """Get all templates"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM templates")
        
        templates = []
        for row in cursor.fetchall():
            templates.append(ProductTemplate(
                name=row[1],
                product_type=row[2],
                base_price=row[3],
                prompt_template=row[4],
                tags=row[5].split(',') if row[5] else [],
                collection_name=row[6] or "",
                auto_publish=bool(row[7]),
                generate_marketing=bool(row[8])
            ))
        return templates
    
    def delete_template(self, name: str):
        """Delete template"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM templates WHERE name = ?", (name,))
        self.conn.commit()
    
    def save_price_rule(self, rule: PriceRule):
        """Save pricing rule"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO price_rules (product_type, base_price, markup_percent)
            VALUES (?, ?, ?)
        """, (rule.product_type, rule.base_price, rule.markup_percent))
        self.conn.commit()
    
    def get_price_rules(self) -> List[PriceRule]:
        """Get all price rules"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM price_rules")
        return [PriceRule(row[1], row[2], row[3]) for row in cursor.fetchall()]
    
    def get_price_for_type(self, product_type: str) -> float:
        """Get price for product type"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT base_price FROM price_rules WHERE product_type = ?", (product_type,))
        result = cursor.fetchone()
        return result[0] if result else 25.0
    
    def add_shop(self, shop_id: str, shop_name: str, token: str):
        """Add shop"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO shops (shop_id, shop_name, printify_token, is_active)
            VALUES (?, ?, ?, 0)
        """, (shop_id, shop_name, token))
        self.conn.commit()
    
    def get_shops(self) -> List[Dict]:
        """Get all shops"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM shops")
        columns = ['id', 'shop_id', 'shop_name', 'printify_token', 'is_active']
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def set_active_shop(self, shop_id: str):
        """Set active shop"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE shops SET is_active = 0")
        cursor.execute("UPDATE shops SET is_active = 1 WHERE shop_id = ?", (shop_id,))
        self.conn.commit()
    
    def get_active_shop(self) -> Optional[Dict]:
        """Get active shop"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM shops WHERE is_active = 1")
        row = cursor.fetchone()
        if row:
            columns = ['id', 'shop_id', 'shop_name', 'printify_token', 'is_active']
            return dict(zip(columns, row))
        return None
    
    def add_scheduled_job(self, job: ScheduledJob):
        """Add scheduled job"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO scheduled_jobs (scheduled_time, prompts, product_type, price, shop_id, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            job.scheduled_time.isoformat(),
            json.dumps(job.prompts),
            job.product_type,
            job.price,
            job.shop_id,
            job.status
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_pending_jobs(self) -> List[ScheduledJob]:
        """Get pending scheduled jobs"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            SELECT * FROM scheduled_jobs 
            WHERE status = 'pending' AND scheduled_time <= ?
        """, (now,))
        
        jobs = []
        for row in cursor.fetchall():
            jobs.append(ScheduledJob(
                id=row[0],
                scheduled_time=datetime.fromisoformat(row[1]),
                prompts=json.loads(row[2]),
                product_type=row[3],
                price=row[4],
                shop_id=row[5],
                status=row[6]
            ))
        return jobs
    
    def update_job_status(self, job_id: int, status: str):
        """Update job status"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE scheduled_jobs SET status = ? WHERE id = ?", (status, job_id))
        self.conn.commit()
    
    def get_analytics(self, days: int = 30) -> Dict:
        """Get analytics data"""
        cursor = self.conn.cursor()
        
        # Total products
        cursor.execute("SELECT COUNT(*) FROM products")
        total_products = cursor.fetchone()[0]
        
        # Products by status
        cursor.execute("""
            SELECT status, COUNT(*) FROM products GROUP BY status
        """)
        by_status = dict(cursor.fetchall())
        
        # Products by type
        cursor.execute("""
            SELECT product_type, COUNT(*) FROM products GROUP BY product_type
        """)
        by_type = dict(cursor.fetchall())
        
        # Recent products (last N days)
        cursor.execute("""
            SELECT COUNT(*) FROM products 
            WHERE created_at >= datetime('now', '-' || ? || ' days')
        """, (days,))
        recent_count = cursor.fetchone()[0]
        
        # Total value
        cursor.execute("SELECT SUM(price) FROM products")
        total_value = cursor.fetchone()[0] or 0.0
        
        return {
            'total_products': total_products,
            'by_status': by_status,
            'by_type': by_type,
            'recent_count': recent_count,
            'total_value': total_value
        }
