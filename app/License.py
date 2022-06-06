# fetch databaseID for is_validated = false and check for license key, post query to Gumroad, if matches, is_validated == true.
import sqlite3
from sqlite3 import connect
from decouple import config
import requests

databaseFile = config("DATABASE_FILE_PATH")

conn = sqlite3.connect(databaseFile)

def fetchToken():
    cursor = conn.cursor()
    data = """SELECT access_token FROM USERS WHERE is_validated = 0"""
    cursor.execute(data)
    records = cursor.fetchall()
    listTokens = []
    for item in records:
        listTokens.append(item[0])
    return listTokens    

def fetchDatabaseID(token):
    databaseIDurl = " https://api.notion.com/v1/search"
    params = {"filter" : {"value" : "database","property" : "object"}, "query" : "License Key"}
    response = requests.post(databaseIDurl, headers= {"Notion-Version": "2022-02-22", "Authorization": "Bearer " + token},  data=params)
    parsedResponse = response.json()
    database = parsedResponse[0]
    databaseID = database.get("id", "")
    return databaseID

def fetchLicenseKey(databaseID, lastCheckedTime):
    url = f"https://api.notion.com/v1/databases/{databaseID}/query"    
    params = 