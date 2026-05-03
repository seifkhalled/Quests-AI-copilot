import os
import psycopg2
from dotenv import load_dotenv

def setup_database():
    # Load environment variables from .env
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not found in .env file")
        return

    print("Connecting to Supabase...")
    try:
        # Connect to the database
        conn = psycopg2.connect(database_url, sslmode='require')
        conn.autocommit = True
        cur = conn.cursor()

        # Read the schema file
        schema_path = os.path.join("supabase", "schema.sql")
        print(f"Reading schema from {schema_path}...")
        with open(schema_path, "r") as f:
            schema_sql = f.read()

        # Execute the SQL
        print("Executing schema migration...")
        cur.execute(schema_sql)
        
        print("Successfully created all tables, triggers, and indexes!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error during database setup: {e}")

if __name__ == "__main__":
    setup_database()