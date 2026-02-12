"""
Database utilities with retry logic for concurrent access
Handles SQLite database locks gracefully with exponential backoff
"""

import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager
from functools import wraps

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def get_db():
    """
    Get database connection with optimized settings for concurrent access
    """
    conn = sqlite3.connect(
        DATABASE_PATH,
        timeout=30.0,
        isolation_level='DEFERRED',  # Better for read-heavy workloads
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    
    # Ensure WAL mode and optimizations are set
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA busy_timeout=30000')  # 30 seconds in milliseconds
    
    return conn

@contextmanager
def get_db_connection():
    """
    Context manager for database connections
    Ensures proper cleanup even on errors
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
            conn.commit()
    """
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()

def retry_on_lock(max_retries=5, initial_delay=0.1, backoff_factor=2):
    """
    Decorator to retry database operations on lock errors
    Uses exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay on each retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if 'database is locked' in str(e) or 'locked' in str(e).lower():
                        last_error = e
                        if attempt < max_retries:
                            time.sleep(delay)
                            delay *= backoff_factor
                            continue
                    raise
                except Exception:
                    raise
            
            # If we exhausted all retries, raise the last error
            if last_error:
                raise last_error
        
        return wrapper
    return decorator

@retry_on_lock(max_retries=5)
def execute_with_retry(query, params=None, fetch='none', commit=True):
    """
    Execute a query with automatic retry on lock
    
    Args:
        query: SQL query string
        params: Query parameters (tuple or dict)
        fetch: 'none', 'one', 'all', or 'lastrowid'
        commit: Whether to commit the transaction
    
    Returns:
        Query result based on fetch parameter
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        result = None
        if fetch == 'one':
            row = cursor.fetchone()
            result = dict(row) if row else None
        elif fetch == 'all':
            result = [dict(row) for row in cursor.fetchall()]
        elif fetch == 'lastrowid':
            result = cursor.lastrowid
        
        if commit:
            conn.commit()
        
        return result

@retry_on_lock(max_retries=5)
def execute_many_with_retry(query, params_list, commit=True):
    """
    Execute the same query multiple times with different parameters
    Useful for batch inserts
    
    Args:
        query: SQL query string
        params_list: List of parameter tuples
        commit: Whether to commit the transaction
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        
        if commit:
            conn.commit()

@retry_on_lock(max_retries=5)
def transaction(func):
    """
    Decorator to wrap a function in a database transaction
    The function should accept a cursor as its first argument
    
    Usage:
        @transaction
        def my_operation(cursor, arg1, arg2):
            cursor.execute(...)
            cursor.execute(...)
            return cursor.lastrowid
        
        result = my_operation(arg1, arg2)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                result = func(cursor, *args, **kwargs)
                conn.commit()
                return result
            except Exception:
                conn.rollback()
                raise
    
    return wrapper

# Convenience function for logging with retry
@retry_on_lock(max_retries=3)
def log_to_audit(user_id, table_name, record_id, action, changes=None, 
                 organization_id=None, division_id=None, ip_address=None):
    """
    Log an action to the audit trail with retry logic
    Separate connection to avoid blocking main operations
    """
    import json
    
    changes_json = json.dumps(changes) if changes else None
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (
                organization_id, division_id, user_id, table_name, 
                record_id, action, changes, ip_address
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (organization_id, division_id, user_id, table_name, 
              record_id, action, changes_json, ip_address))
        conn.commit()
