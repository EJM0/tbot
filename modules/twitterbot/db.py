from mysql.connector import connect, Error
import json
from dotenv import load_dotenv
load_dotenv()
import os

config = os.environ.get("channel-config")

class database:
    def __init__(self):
        try:
            self.connection = connect(
            host=os.environ.get("db-host"),
            user=os.environ.get("db-user"),
            password=os.environ.get("db-password"),
            database=os.environ.get("db-database")
            )
            self.cursor = self.connection.cursor()
        except Exception as e:
            print(e)
            
        
    def send_command(self, command, margs=()):
        try:
            self.cursor.execute(command, margs)
            return self.cursor
        except Exception as e:
            print(e)

    def commit(self):
        try:
            self.connection.commit()
        except Exception as e:
            print(e)
            
    def get_data_by_id(self, id):
        select_query = "SELECT * FROM streams WHERE id = %s"
        self.cursor.execute(select_query, (id,))
        return self.cursor.fetchone()

    def get_data_by_datetime(self, datetime):
        select_query = "SELECT * FROM streams WHERE date = %s"
        self.cursor.execute(select_query, (datetime,))
        return self.cursor.fetchone()

    def update_by_id(self, id, column_name, new_value):
        update_query = f"UPDATE streams SET {column_name} = %s WHERE id = %s"
        self.cursor.execute(update_query, (new_value, id))
        
    def dump_array_via_id(self, id, column_name, array):
            update_query = f"UPDATE streams SET {column_name} = %s WHERE id = %s"
            array_json = json.dumps(array, indent=4, sort_keys=True, default=str)
            self.cursor.execute(update_query, (array_json, id))

    def update_by_datetime(self, datetime, column_name, new_value):
        update_query = f"UPDATE streams SET {column_name} = %s WHERE date = %s"
        self.cursor.execute(update_query, (new_value, datetime))
    
    def get_id_last_insert(self):
        self.cursor.execute("SELECT LAST_INSERT_ID()")
        lastid = self.cursor.fetchone()[0]
        return lastid

    def close(self):
        try:
            self.cursor.close()
            self.connection.close()
        except Exception as e:
            print(e)
            
    def cd(self):
        self.commit()
        self.close()
        
    def create_frame(self, streamer, dt):
        try:
            insert_query = """
            INSERT INTO streams (streamer, date)
            VALUES (%s, %s)
            """
            self.send_command(insert_query, margs=(streamer, dt,))
            return self.get_id_last_insert()
        except Exception as e:
            print(e)
