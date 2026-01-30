from neo4j import GraphDatabase
import sys
import time
import os
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv('NEO4J_URI')
USERNAME = os.getenv('NEO4J_USER', 'neo4j')
PASSWORD = os.getenv('NEO4J_PASSWORD')

def delete_in_batches(driver, batch_size=10000):
    total_deleted = 0
    batch_num = 0

    while True:
        batch_num += 1

        with driver.session() as session:
            result = session.run(f"""
                MATCH (n)
                WITH n LIMIT {batch_size}
                DETACH DELETE n
                RETURN count(n) as deleted
            """)

            deleted = result.single()['deleted']
            total_deleted += deleted

            if deleted == 0:
                break

            print(f"Batch {batch_num}: Deleted {deleted:,} nodes")

            if batch_num % 5 == 0:
                time.sleep(1)

    print(f"Total nodes deleted: {total_deleted:,}")
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) as remaining")
        remaining = result.single()['remaining']
        if remaining == 0:
            print("Database is now empty")
        else:
            print(f"Warning: {remaining} nodes still remain")

def main():
    if not PASSWORD:
        print("ERROR: NEO4J_PASSWORD not found in .env file")
        print("Please add NEO4J_PASSWORD to your .env file")
        sys.exit(1)

    print(f"Connecting to {URI}...")
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

    try:
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as total")
            total = result.single()['total']
            print(f"Found {total:,} nodes to delete")

        if total == 0:
            print("Database is already empty!")
            return

        response = input("This will DELETE ALL DATA. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Deletion cancelled.")
            return

        delete_in_batches(driver)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        driver.close()

if __name__ == "__main__":
    main()
