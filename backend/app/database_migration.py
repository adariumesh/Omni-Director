#!/usr/bin/env python3
"""Database migration script for FIBO Omni-Director Pro."""

import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles database schema migrations."""
    
    def __init__(self, database_path: str = None):
        """Initialize migrator.
        
        Args:
            database_path: Path to SQLite database file.
        """
        if database_path:
            self.database_path = database_path
        else:
            # Extract path from settings DATABASE_URL
            url = settings.database_url
            if url.startswith("sqlite:///"):
                self.database_path = url.replace("sqlite:///", "")
            else:
                raise ValueError("Only SQLite migrations supported")
        
        self.db_path = Path(self.database_path)
        logger.info(f"Database migrator initialized for: {self.db_path}")
    
    def get_current_schema(self) -> Dict[str, Any]:
        """Get current database schema.
        
        Returns:
            Dictionary describing current schema.
        """
        if not self.db_path.exists():
            return {"tables": {}, "version": 0}
        
        schema = {"tables": {}, "version": 1}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get table list
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                for (table_name,) in tables:
                    if table_name == 'sqlite_sequence':
                        continue
                    
                    # Get table schema
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    
                    schema["tables"][table_name] = {
                        "columns": {
                            col[1]: {  # col[1] is column name
                                "type": col[2],
                                "not_null": bool(col[3]),
                                "default": col[4],
                                "primary_key": bool(col[5])
                            } for col in columns
                        }
                    }
                    
                    # Get indexes
                    cursor.execute(f"PRAGMA index_list({table_name})")
                    indexes = cursor.fetchall()
                    schema["tables"][table_name]["indexes"] = [idx[1] for idx in indexes]
        
        except Exception as e:
            logger.error(f"Error reading schema: {e}")
            schema["error"] = str(e)
        
        return schema
    
    def check_migration_needed(self) -> List[str]:
        """Check what migrations are needed.
        
        Returns:
            List of migration descriptions.
        """
        schema = self.get_current_schema()
        needed_migrations = []
        
        # Check if assets table has new columns
        if "assets" in schema["tables"]:
            assets_columns = schema["tables"]["assets"]["columns"]
            
            required_new_columns = [
                ("file_id", "VARCHAR(100)"),
                ("thumbnail_path", "VARCHAR(500)"),
                ("file_size", "INTEGER"),
                ("content_type", "VARCHAR(100)"),
                ("checksum", "VARCHAR(64)"),
                ("generation_mode", "VARCHAR(20)"),
                ("generation_time", "INTEGER"),
                ("api_provider", "VARCHAR(50)")
            ]
            
            for column_name, column_type in required_new_columns:
                if column_name not in assets_columns:
                    needed_migrations.append(f"Add column {column_name} to assets table")
        
        else:
            needed_migrations.append("Create assets table with enhanced schema")
        
        return needed_migrations
    
    def run_migrations(self) -> bool:
        """Run all needed migrations.
        
        Returns:
            True if successful, False otherwise.
        """
        migrations_needed = self.check_migration_needed()
        
        if not migrations_needed:
            logger.info("✅ No migrations needed")
            return True
        
        logger.info(f"🔄 Running {len(migrations_needed)} migrations...")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Backup existing data if table exists
                schema = self.get_current_schema()
                if "assets" in schema["tables"]:
                    logger.info("📦 Backing up existing assets...")
                    cursor.execute("CREATE TABLE assets_backup AS SELECT * FROM assets")
                
                # Add new columns to assets table
                new_columns = [
                    "ALTER TABLE assets ADD COLUMN file_id VARCHAR(100)",
                    "ALTER TABLE assets ADD COLUMN thumbnail_path VARCHAR(500)",
                    "ALTER TABLE assets ADD COLUMN file_size INTEGER",
                    "ALTER TABLE assets ADD COLUMN content_type VARCHAR(100)",
                    "ALTER TABLE assets ADD COLUMN checksum VARCHAR(64)",
                    "ALTER TABLE assets ADD COLUMN generation_mode VARCHAR(20)",
                    "ALTER TABLE assets ADD COLUMN generation_time INTEGER",
                    "ALTER TABLE assets ADD COLUMN api_provider VARCHAR(50)"
                ]
                
                for column_sql in new_columns:
                    try:
                        cursor.execute(column_sql)
                        logger.debug(f"✅ {column_sql}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" in str(e):
                            logger.debug(f"⏭️  Column already exists: {column_sql}")
                        else:
                            raise
                
                # Create index on file_id for faster lookups
                try:
                    cursor.execute("CREATE INDEX idx_assets_file_id ON assets(file_id)")
                    logger.info("✅ Created index on file_id")
                except sqlite3.OperationalError as e:
                    if "already exists" in str(e):
                        logger.debug("⏭️  Index already exists")
                    else:
                        raise
                
                conn.commit()
                
                # Clean up backup table
                if "assets" in schema["tables"]:
                    cursor.execute("DROP TABLE assets_backup")
                    logger.info("🧹 Cleaned up backup table")
                
                logger.info("✅ All migrations completed successfully")
                return True
                
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
    
    def reset_database(self) -> bool:
        """Reset database by recreating from scratch.
        
        Returns:
            True if successful.
        """
        try:
            if self.db_path.exists():
                self.db_path.unlink()
                logger.info(f"🗑️  Deleted existing database: {self.db_path}")
            
            # Recreate using SQLAlchemy models
            from app.models.database import init_db
            init_db()
            
            logger.info("✅ Database recreated successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database reset failed: {e}")
            return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get migration status report.
        
        Returns:
            Status report dictionary.
        """
        schema = self.get_current_schema()
        migrations_needed = self.check_migration_needed()
        
        return {
            "database_exists": self.db_path.exists(),
            "database_path": str(self.db_path),
            "tables_count": len(schema["tables"]),
            "migrations_needed": migrations_needed,
            "needs_migration": len(migrations_needed) > 0,
            "current_schema_version": schema.get("version", 0),
            "tables": list(schema["tables"].keys())
        }


def main():
    """Run database migration."""
    print("🗃️  FIBO Database Migration Tool")
    print("=" * 40)
    
    migrator = DatabaseMigrator()
    
    # Get current status
    status = migrator.get_migration_status()
    
    print(f"Database: {status['database_path']}")
    print(f"Exists: {status['database_exists']}")
    print(f"Tables: {status['tables_count']} ({', '.join(status['tables'])})")
    print()
    
    if status['needs_migration']:
        print("🔄 Migrations needed:")
        for migration in status['migrations_needed']:
            print(f"  - {migration}")
        print()
        
        # Run migrations
        success = migrator.run_migrations()
        
        if success:
            print("✅ Migration completed successfully!")
        else:
            print("❌ Migration failed!")
            return 1
    else:
        print("✅ Database is up to date!")
    
    # Show final status
    final_status = migrator.get_migration_status()
    print(f"\nFinal state: {final_status['tables_count']} tables")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())