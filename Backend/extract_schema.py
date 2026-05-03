import asyncio
from src.db.supabase import supabase_client

async def extract_schema():
    # Query to get all tables and their columns in the public schema
    query = """
        SELECT table_name, column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """
    res = await supabase_client.fetch(query)
    
    schema = {}
    for row in res:
        t = row['table_name']
        if t not in schema:
            schema[t] = []
        schema[t].append({
            'column': row['column_name'],
            'type': row['data_type'],
            'nullable': row['is_nullable'],
            'default': row['column_default']
        })
    
    with open('current_schema.txt', 'w') as f:
        for t, cols in schema.items():
            f.write(f"TABLE: {t}\n")
            for c in cols:
                f.write(f"  - {c['column']}: {c['type']} (nullable: {c['nullable']}, default: {c['default']})\n")
            f.write("\n")
    print("Schema written to current_schema.txt")

asyncio.run(extract_schema())
