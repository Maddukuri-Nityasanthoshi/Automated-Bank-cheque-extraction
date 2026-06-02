import os
import psycopg2
import pandas as pd
from datetime import datetime


DB_CONFIG = {
    "host": "localhost",
    "dbname": "cheque",
    "user": "postgres",
    "password": "root",  # Ensure it's a string
    "port": 5432
}

# Connect to PostgreSQL Database
def connect_db():
    return psycopg2.connect(**DB_CONFIG)

def save_to_database(cheque_details):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        print("📝 Attempting to Save Cheque:", cheque_details)  # Debugging

        cheque_date = cheque_details.get("date", None)
        if cheque_date:
            try:
                cheque_date = datetime.strptime(cheque_date, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                cheque_date = None
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cheques (
                id SERIAL PRIMARY KEY,
                account_no VARCHAR(50),  
                bank_name VARCHAR(255),  
                payee_name VARCHAR(255),
                amount NUMERIC(12,2)  
            )
        """)
        cursor.execute("""
    INSERT INTO cheques (account_no, bank_name, payee_name, amount)
    VALUES (%s, %s, %s, %s)
""", (cheque_details["structured_data"]["account_no"], 
      cheque_details["structured_data"]["bank_name"], 
      cheque_details["structured_data"]["payee_name"], 
      cheque_details["structured_data"]["amount"]))


        conn.commit()
        cursor.close()
        conn.close()

        print("✅ Cheque Saved Successfully!")  # Debugging

    except Exception as e:
        print("❌ Database Error:", e)  # Catch errors

# Function to fetch cheque details
def fetch_cheque_data():
    try:
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM cheques")
        data = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]

        cursor.close()
        conn.close()

        return pd.DataFrame(data, columns=column_names) if data else pd.DataFrame()  # Return empty DataFrame if no records
    except Exception as e:
        print(f"Database Error: {e}")
        return None  # Return empty DataFrame on failure

