"""Test script to verify MySQL database connection.
Run this before starting the application to ensure database is accessible.
"""
import os

import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_db_config():
    """Build a MySQL connection config from environment variables."""
    required = {
        "host": os.getenv("DATABASE_HOST"),
        "user": os.getenv("DATABASE_USER"),
        "password": os.getenv("DATABASE_PASSWORD"),
        "database": os.getenv("DATABASE_NAME"),
    }

    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(
            "Missing MySQL environment values: " + ", ".join(missing)
        )

    return {
        "host": required["host"],
        "port": int(os.getenv("DATABASE_PORT", 3306)),
        "user": required["user"],
        "password": required["password"],
        "database": required["database"],
        "connect_timeout": 10,
        "charset": "utf8mb4",
    }


def test_connection():
    """Test MySQL database connection."""
    try:
        print("Testing MySQL connection...")
        config = get_db_config()
        print(f"Host: {config['host']}")
        print(f"Port: {config['port']}")
        print(f"Database: {config['database']}")
        print(f"User: {config['user']}")

        connection = pymysql.connect(**config)

        print("✓ Successfully connected to MySQL database!")

        cursor = connection.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"✓ MySQL version: {version[0]}")

        cursor.close()
        connection.close()
        print("✓ Connection test completed successfully!")
        return True

    except ValueError as exc:
        print(f"✗ Missing MySQL environment configuration: {exc}")
        print("Please set DATABASE_HOST, DATABASE_PORT, DATABASE_NAME, DATABASE_USER, and DATABASE_PASSWORD in your .env file.")
        return False
    except pymysql.Error as exc:
        print(f"✗ MySQL connection failed: {exc}")
        print("\nPlease ensure:")
        print("1. MySQL server is running")
        print("2. Database 'rohit_voting_system' exists")
        print("3. Credentials in .env file are correct")
        return False
    except Exception as exc:
        print(f"✗ Unexpected error: {exc}")
        return False


if __name__ == '__main__':
    test_connection()
