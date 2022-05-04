import sqlite3
from sqlite3 import Error


def connect(notionReadingList):
    conn = None
    try:
        conn = sqlite3.connect(notionReadingList)
    except Error as e:
        print (e)
    return conn    

connect("/Users/sravanthis/Documents/ReadingList/notionReadingList.db")   


# def DropTable(db_filemain):
#     conn = sqlite3.connect(db_filemain)
#     cursor_object = conn.cursor()
#     table = """DROP TABLE USERS"""
#     try:
#         cursor_object.execute(table)
#         conn.commit()
#         print ("table USERS dropped")
#     except:
#         print ("Could not drop")    
#     cursor_object.close()
#     conn.close()

# DropTable("/Users/sravanthis/Documents/ReadingList/database/sqlite/db_filemain")



def createTable():
    conn = connect("/Users/sravanthis/Documents/ReadingList/notionReadingList.db")
    cursor_object = conn.cursor()
    table = """CREATE TABLE IF NOT EXISTS USERS (
            access_token VARCHAR(255) NOT NULL,
            database_id VARCHAR(255) NOT NULL,
            bot_id VARCHAR(255) NOT NULL,
            workspace_name VARCHAR(255) NOT NULL,
            workspace_id VARCHAR(255) NOT NULL,
            owner_type VARCHAR(255) NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            user_name VARCHAR(255) NOT NULL,
            time_added FLOAT NOT NULL
            )"""
    try:        
        cursor_object.execute(table)
        conn.commit()
        print ("Table USERS created")
    except:
        print ("Could not create table USERS")
    cursor_object.close()
    conn.close()
    return

createTable()
