"""
Database initialization script.
Run this script to create the database schema and seed data.
"""
import pymysql
from dotenv import load_dotenv
import os
import sys

load_dotenv()

def execute_sql_file(filename):
    """Execute SQL file."""
    try:
        print(f"Executing {filename}...")
        
        connection = pymysql.connect(
            host=os.getenv('DATABASE_HOST'),
            port=int(os.getenv('DATABASE_PORT', 3306)),
            user=os.getenv('DATABASE_USER'),
            password=os.getenv('DATABASE_PASSWORD'),
            database=os.getenv('DATABASE_NAME'),
            charset='utf8mb4'
        )
        
        with open(filename, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        cursor = connection.cursor()
        
        # Split SQL by semicolon and execute each statement
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        
        for statement in statements:
            if statement:
                cursor.execute(statement)
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"✓ Successfully executed {filename}")
        return True
        
    except Exception as e:
        print(f"✗ Error executing {filename}: {e}")
        return False

def main():
    """Main initialization function."""
    print("=" * 60)
    print("ROHIT VOTING SYSTEM - Database Initialization")
    print("=" * 60)
    print()
    
    # Check if database exists
    try:
        print("Checking database connection...")
        connection = pymysql.connect(
            host=os.getenv('DATABASE_HOST'),
            port=int(os.getenv('DATABASE_PORT', 3306)),
            user=os.getenv('DATABASE_USER'),
            password=os.getenv('DATABASE_PASSWORD')
        )
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {os.getenv('DATABASE_NAME')} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        connection.close()
        print(f"✓ Database '{os.getenv('DATABASE_NAME')}' is ready")
        print()
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        print("Please check your .env file and MySQL server.")
        sys.exit(1)
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    schema_file = os.path.join(script_dir, 'schema.sql')
    seed_file = os.path.join(script_dir, 'seed.sql')
    
    # Execute schema
    if not execute_sql_file(schema_file):
        sys.exit(1)
    
    print()
    
    # Execute seed data
    if not execute_sql_file(seed_file):
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✓ Database initialization completed successfully!")
    print("=" * 60)
    print()
    print("Default admin credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print()
    print("IMPORTANT: Change the default admin password immediately!")
    print()

if __name__ == '__main__':
    main()
