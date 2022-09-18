import datetime, time
from decouple import config
import logging
import googlebooks
import usersDatabase
import image
import notion

ourList = ["Title", "Publisher", "Authors", "Summary", "Category", "Published", "ISBN_10", "Pages", "ISBN_13", "Summary_extd"]

ourDic = {"Title": "", "Subtitle": "", "Publisher": "", "Authors": "", "Summary": "", "Summary_extd": "", "Category":"", "Published": "", "ISBN_10": "", "Pages": None, "ISBN_13":"", "Image_url": ""}

databaseFile = config("DATABASE_FILE_PATH")

imageFolder = config("IMAGE_PATH")

google_api_key = config("GOOGLE_API_KEY")

url = config("BASE_URL")

# logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
logging.basicConfig(filename='app.log', format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

conn = usersDatabase.connectDatabase(databaseFile)

while True:
    print (datetime.datetime.now())
    newRecords = usersDatabase.getRecords(conn)
    listAccessTokens = usersDatabase.getValidatedTokens(newRecords)
    for i in range (5):  #loop through Notion 5 times before looking for new access tokens
        for index in range(len(listAccessTokens)):
            listRevoked = []
            databaseID = listAccessTokens[index]["database_id"]
            token = listAccessTokens[index]["access_token"]
            userID = listAccessTokens[index]["user_id"]
            try:
                results = notion.requiredPageDetails(databaseID, userID, token)  
                if results == 401 or results == 404:
                    listAccessTokens[index]["is_revoked"] = True
                elif results is not None: 
                    newTitlesOrISBN = notion.getNewTitlesOrISBN(results)
                    availableFields = notion.getAllFields(results)
                    missingProperties = notion.compareLists(availableFields)
                    for item in newTitlesOrISBN:    
                        newGoogleBookDetails = googlebooks.getBookDetails(item, token, userID)
                        if newGoogleBookDetails is not None:
                            mappedDic = googlebooks.mapOneDicToAnother(ourDic, newGoogleBookDetails)
                            filePath = image.uploadImage(mappedDic)
                            notion.updateDatabase(mappedDic, item, filePath, missingProperties, userID, token)               
            except Exception as e:
                logging.error(e) 
        listRevoked = list(filter(lambda x: x["is_revoked"], listAccessTokens))
        usersDatabase.removeFromUsers(listRevoked, conn)
        time.sleep(5)
    print (datetime.datetime.now())    

conn.close()