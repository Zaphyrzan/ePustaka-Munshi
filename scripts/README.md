# Scripts Folder

Maintenance, testing, and database administration scripts.

## Database Migration

### 01_drop_all_tables.py
Drops all tables from Supabase database for a clean reset.
```bash
python scripts/01_drop_all_tables.py
```

### 02_migrate_v2.py (Recommended)
Primary migration script that:
- Creates tables using SQLAlchemy models (via init_db.py)
- Copies data from SQLite epustaka.db to Supabase
- Handles type conversions (boolean, datetime, etc.)
- Respects foreign key constraints
```bash
python scripts/02_migrate_v2.py
```

### 03_verify_migration.py
Verifies migration by comparing row counts between SQLite and Supabase.
```bash
python scripts/03_verify_migration.py
```

## Complete Migration Workflow

To reset and migrate from scratch:
```bash
# 1. Drop all Supabase tables
python scripts/01_drop_all_tables.py

# 2. Initialize database schema (creates all tables)
python init_db.py

# 3. Copy data from SQLite
python scripts/02_migrate_v2.py

# 4. Verify migration succeeded
python scripts/03_verify_migration.py
```

## Other Utilities

- `check_database.py` - Check current database state
- `test_connection.py` - Test database connectivity
- `migrate.py` - Old simple migration (deprecated)
- `migrate_ordered.py` - Old ordered migration (deprecated)
