"""Database initialization script.
Run this script to create the database schema and seed data.
"""
import os
import sys

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
        "charset": "utf8mb4",
    }


def execute_sql_file(filename):
    """Execute SQL file."""
    try:
        print(f"Executing {filename}...")
        connection = pymysql.connect(**get_db_config())

        with open(filename, "r", encoding="utf-8") as file_handle:
            sql = file_handle.read()

        cursor = connection.cursor()
        statements = [statement.strip() for statement in sql.split(";") if statement.strip()]

        for statement in statements:
            cursor.execute(statement)

        connection.commit()
        cursor.close()
        connection.close()

        print(f"✓ Successfully executed {filename}")
        return True
    except ValueError as exc:
        print(f"✗ Missing MySQL environment configuration: {exc}")
        return False
    except Exception as exc:
        print(f"✗ Error executing {filename}: {exc}")
        return False


def main():
    """Main initialization function."""
    print("=" * 60)
    print("ROHIT VOTING SYSTEM - Database Initialization")
    print("=" * 60)
    print()

    try:
        print("Checking database connection...")
        config = get_db_config()
        connection = pymysql.connect(**config)
        cursor = connection.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.close()
        connection.close()
        print(f"✓ Database '{config['database']}' is ready")
        print()
    except ValueError as exc:
        print(f"✗ Missing MySQL environment configuration: {exc}")
        print("Please set DATABASE_HOST, DATABASE_PORT, DATABASE_NAME, DATABASE_USER, and DATABASE_PASSWORD in your .env file.")
        sys.exit(1)
    except Exception as exc:
        print(f"✗ Error creating database: {exc}")
        print("Please check your .env file and MySQL server.")
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    schema_file = os.path.join(script_dir, "schema.sql")
    seed_file = os.path.join(script_dir, "seed.sql")

    if not execute_sql_file(schema_file):
        sys.exit(1)

    print()

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
