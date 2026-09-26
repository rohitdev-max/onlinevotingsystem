"""
Test script to verify MySQL database connection.
Run this before starting the application to ensure database is accessible.
"""
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

def test_connection():
    """Test MySQL database connection."""
    try:
        print("Testing MySQL connection...")
        print(f"Host: {os.getenv('DATABASE_HOST')}")
        print(f"Port: {os.getenv('DATABASE_PORT')}")
        print(f"Database: {os.getenv('DATABASE_NAME')}")
        print(f"User: {os.getenv('DATABASE_USER')}")
        
        connection = pymysql.connect(
            host=os.getenv('DATABASE_HOST'),
            port=int(os.getenv('DATABASE_PORT', 3306)),
            user=os.getenv('DATABASE_USER'),
            password=os.getenv('DATABASE_PASSWORD'),
            database=os.getenv('DATABASE_NAME'),
            connect_timeout=10
        )
        
        print("✓ Successfully connected to MySQL database!")
        
        cursor = connection.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"✓ MySQL version: {version[0]}")
        
        cursor.close()
        connection.close()
        print("✓ Connection test completed successfully!")
        return True
        
    except pymysql.Error as e:
        print(f"✗ MySQL connection failed: {e}")
        print("\nPlease ensure:")
        print("1. MySQL server is running")
        print("2. Database 'rohit_voting_system' exists")
        print("3. Credentials in .env file are correct")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == '__main__':
    test_connection()
