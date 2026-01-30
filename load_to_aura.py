#!/usr/bin/env python3

from neo4j import GraphDatabase
import pandas as pd
import sys
import os
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv('NEO4J_URI')
USERNAME = os.getenv('NEO4J_USER', 'neo4j')
PASSWORD = os.getenv('NEO4J_PASSWORD')

CSV_FILE = "itcont.csv"
BATCH_SIZE = 10000

FEC_COLUMNS = [
    'CMTE_ID',
    'AMNDT_IND',
    'RPT_TP',
    'TRANSACTION_PGI',
    'IMAGE_NUM',
    'TRANSACTION_TP',
    'ENTITY_TP',
    'NAME',
    'CITY',
    'STATE',
    'ZIP_CODE',
    'EMPLOYER',
    'OCCUPATION',
    'TRANSACTION_DT',
    'TRANSACTION_AMT',
    'OTHER_ID',
    'TRAN_ID',
    'FILE_NUM',
    'MEMO_CD',
    'MEMO_TEXT',
    'SUB_ID'
]

def load_to_aura():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

    try:
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            print("Connected to Neo4j")
        with driver.session() as session:
            session.run("CREATE INDEX donor_name IF NOT EXISTS FOR (d:Donor) ON (d.name)")
            session.run("CREATE INDEX committee_id IF NOT EXISTS FOR (c:Committee) ON (c.cmte_id)")
            session.run("CREATE INDEX donation_id IF NOT EXISTS FOR ()-[d:DONATED]-() ON (d.tran_id)")

        print(f"Loading data from {CSV_FILE}")

        chunk_count = 0
        total_loaded = 0
        for chunk in pd.read_csv(CSV_FILE, names=FEC_COLUMNS, chunksize=BATCH_SIZE, low_memory=False):
            chunk_count += 1
            chunk = chunk[chunk['NAME'].notna() & 
                         chunk['CMTE_ID'].notna() & 
                         chunk['TRANSACTION_AMT'].notna()]
            chunk = chunk[chunk['TRANSACTION_AMT'] != 0]

            batch_data = []
            for _, row in chunk.iterrows():
                try:
                    amount = float(row['TRANSACTION_AMT'])
                    if amount != 0:
                        donor_props = {
                            'name': str(row['NAME']).strip()
                        }
                        if pd.notna(row['CITY']):
                            donor_props['city'] = str(row['CITY']).strip()
                        if pd.notna(row['STATE']):
                            donor_props['state'] = str(row['STATE']).strip()
                        if pd.notna(row['ZIP_CODE']):
                            donor_props['zip_code'] = str(row['ZIP_CODE']).strip()
                        if pd.notna(row['EMPLOYER']):
                            donor_props['employer'] = str(row['EMPLOYER']).strip()
                        if pd.notna(row['OCCUPATION']):
                            donor_props['occupation'] = str(row['OCCUPATION']).strip()
                        committee_props = {
                            'cmte_id': str(row['CMTE_ID']).strip()
                        }
                        donation_props = {
                            'amount': amount
                        }
                        if pd.notna(row['AMNDT_IND']):
                            donation_props['amendment_ind'] = str(row['AMNDT_IND']).strip()
                        if pd.notna(row['RPT_TP']):
                            donation_props['report_type'] = str(row['RPT_TP']).strip()
                        if pd.notna(row['TRANSACTION_PGI']):
                            donation_props['primary_general'] = str(row['TRANSACTION_PGI']).strip()
                        if pd.notna(row['IMAGE_NUM']):
                            donation_props['image_num'] = str(row['IMAGE_NUM']).strip()
                        if pd.notna(row['TRANSACTION_TP']):
                            donation_props['transaction_type'] = str(row['TRANSACTION_TP']).strip()
                        if pd.notna(row['ENTITY_TP']):
                            donation_props['entity_type'] = str(row['ENTITY_TP']).strip()
                        if pd.notna(row['TRANSACTION_DT']):
                            donation_props['transaction_date'] = str(row['TRANSACTION_DT']).strip()
                        if pd.notna(row['OTHER_ID']):
                            donation_props['other_id'] = str(row['OTHER_ID']).strip()
                        if pd.notna(row['TRAN_ID']):
                            donation_props['tran_id'] = str(row['TRAN_ID']).strip()
                        if pd.notna(row['FILE_NUM']):
                            donation_props['file_num'] = str(row['FILE_NUM']).strip()
                        if pd.notna(row['MEMO_CD']):
                            donation_props['memo_code'] = str(row['MEMO_CD']).strip()
                        if pd.notna(row['MEMO_TEXT']):
                            donation_props['memo_text'] = str(row['MEMO_TEXT']).strip()
                        if pd.notna(row['SUB_ID']):
                            donation_props['sub_id'] = str(row['SUB_ID']).strip()
                        
                        batch_data.append({
                            'donor_props': donor_props,
                            'committee_props': committee_props,
                            'donation_props': donation_props
                        })
                except Exception as e:
                    continue

            if batch_data:
                with driver.session() as session:
                    result = session.run("""
                        UNWIND $batch AS row
                        MERGE (donor:Donor {name: row.donor_props.name})
                        SET donor += row.donor_props
                        MERGE (committee:Committee {cmte_id: row.committee_props.cmte_id})
                        SET committee += row.committee_props
                        CREATE (donor)-[d:DONATED]->(committee)
                        SET d += row.donation_props
                        RETURN count(*) as processed
                    """, batch=batch_data)
                    processed = result.single()['processed']
                    total_loaded += processed
                    print(f"Batch {chunk_count}: Loaded {processed:,} records")
                    if chunk_count % 10 == 0:
                        import time
                        time.sleep(1)

        print(f"Total records loaded: {total_loaded:,}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        driver.close()

if __name__ == "__main__":
    if not PASSWORD:
        print("ERROR: NEO4J_PASSWORD not found in .env file")
        print("Please add NEO4J_PASSWORD to your .env file")
        sys.exit(1)

    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "neo4j", "pandas", "python-dotenv"])

    load_to_aura()