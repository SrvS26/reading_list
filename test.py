import concurrent.futures
import requests
import string
import datetime
import asyncio
import os
from aiohttp import ClientSession

ourDic = {"Title": "", "Subtitle": "", "Publisher": "", "Authors": "", "Summary": "", "Summary_extd": "", "Category":"", "Published": "", "ISBN_10": "", "Pages": None, "ISBN_13":"", "Image_url": ""}

listDicIdentifier = ['9780241953242', '9781781100264', '9781566895828', '9780849938719', '9780143135197', '9781982122355', '9781646140145', '9780062060891', '9780593429723', '9780375708275', '9781250219381', '9781984818423', '9780553901023', '9780749474713', '9780062422668']

async def getBookdetails(ISBN, session):
    url = f"https://www.googleapis.com/books/v1/volumes?q={ISBN}"
    response = await session.request(method= "GET", url=url, ssl=False)
    parsedResponse = await response.json()
    if parsedResponse.get("totalItems", 0) > 0:
        listOfBookResults = parsedResponse["items"]
        firstBookResult = listOfBookResults[0]                              
        bookDetails = firstBookResult.get("volumeInfo")
        requiredBookDetails = ["title", "subtitle", "authors", "publisher", "publishedDate", "description", "industryIdentifiers", "pageCount", "categories", "imageLinks"]
        dicOfRequiredBookDetails = {}
        for item in requiredBookDetails:                                   
            if item in bookDetails.keys():                                   
                dicOfRequiredBookDetails[item] = bookDetails[item]
            else:
                continue  
        return dicOfRequiredBookDetails        


def mapOneDicToAnother(ourDic, GoogleBookInfo):
    ourDic["Publisher"] = GoogleBookInfo.get("publisher", "")
    listauthors = []
    if GoogleBookInfo.get("authors") != None and len(GoogleBookInfo["authors"]) > 0:
        for item in GoogleBookInfo["authors"]:
            authors = {}
            authors["name"] = string.capwords(item).replace(",", "")
            listauthors.append(authors)           
    ourDic["Authors"] = listauthors  
    summary = GoogleBookInfo.get("description", "")
    if len(summary) > 2000:
        summary = summary[:1997] + "..."
        summary_extd = summary[1998:]    
        ourDic["Summary_extd"] = summary_extd
    ourDic["Summary"] = summary
    ourDic["Published"] = GoogleBookInfo.get("publishedDate", "")
    if GoogleBookInfo.get("industryIdentifiers") != None:
        for element in GoogleBookInfo["industryIdentifiers"]:
            if element["type"] in ["ISBN_10", "ISBN_13"]:
                if element["type"] == "ISBN_10":
                    ourDic["ISBN_10"] = element["identifier"]
                if element["type"] == "ISBN_13":       
                    ourDic["ISBN_13"] = element["identifier"]
            else:
                ourDic["ISBN_10"] = ""      
                ourDic["ISBN_13"] = ""
    else:
        ourDic["ISBN_10"] = ""      
        ourDic["ISBN_13"] = ""
    ourDic["Pages"] = GoogleBookInfo.get("pageCount", 0)
    ourDic["Title"] = GoogleBookInfo.get("title", "")
    subTitle = GoogleBookInfo.get("subtitle", "")
    if subTitle != "":
        ourDic["Subtitle"] = f": {subTitle}"
    listcategory = []
    if GoogleBookInfo.get("categories") != None and len(GoogleBookInfo["categories"]) > 0:   
        for item in GoogleBookInfo["categories"]: 
            category = {}
            category["name"] = string.capwords(item.replace(","," "))
            listcategory.append(category)
    ourDic["Category"] = listcategory
    if GoogleBookInfo.get("imageLinks") != None:
        imageLink = GoogleBookInfo["imageLinks"]["thumbnail"]
        ourDic["Image_url"] = imageLink
    return ourDic                                     


async def run_program(isbn, session):
    response = await getBookdetails(isbn, session)
    relevantDeets = mapOneDicToAnother(ourDic, response)
    return    

with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    print (datetime.datetime.now())
    print ("----------------------------------------------------------------------------------")
    future_to_url = {executor.submit(getBookdetails, ISBN): ISBN for ISBN in listDicIdentifier}
    list = []
    for future in concurrent.futures.as_completed(future_to_url):
        url = future_to_url[future]
        data = (future.result())
        list.append(data)
    listFinal = []
    for item in list:
        oneDic = mapOneDicToAnother(ourDic, item)
        listFinal.append(oneDic)
    print ("----------------------------------------------------------------------------------")
    print (datetime.datetime.now())
