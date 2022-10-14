import requests
import logging
import random
from bs4 import BeautifulSoup
import time

logging.basicConfig(
    filename="goodreads.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    level = logging.DEBUG
)

def user_agent():
    user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7"    
    ]
    return random.choice(user_agents)

base_url = "https://www.goodreads.com/book/show/"

def get_book_details(goodreads_id, user_agent):
    url = f"{base_url}{goodreads_id}"
    headers = {"User-Agent": user_agent}
    img_deets = None
    count = 0
    while img_deets is None or len(img_deets) == 0 and count < 10:
        try:
            r = requests.get(url, headers=headers)
            html_doc = r.content
            soup = BeautifulSoup(html_doc, "html.parser") 
            img_deets = soup.find_all("img", id="coverImage")[0]["src"]
            count += 1
            time.sleep(1)
        except Exception as e:
            count += 1     
    summary_deets = soup.find_all("div", id="descriptionContainer")
    summary = ""
    if summary_deets is not None and len(summary_deets) != 0: 
        get_summary = summary_deets[0].find_all("span", style="display:none")
        if get_summary is not None and len(get_summary) != 0:
            final_summary = get_summary[0]
            for string in final_summary.strings:
                summary = summary + string        
    categories = []
    category_deets = soup.find_all("div", class_="bigBoxBody")
    if category_deets is not None and len(category_deets) != 0:
        for item in category_deets:
            category_list = item.find_all("div", class_="elementList")
            if len(category_list) != 0 and category_list is not None:
                for c in category_list:
                    category = c.find("div", class_="left")
                    if category is not None:
                        dic_final_category = {}
                        final_category = category.find("a").string
                        if final_category is not None:    
                            dic_final_category["name"] = final_category 
                            categories.append(dic_final_category)                     
    return img_deets, summary, categories


       
def add_to_dic(myDic):
    image_link, summary, categories = get_book_details(myDic["goodreadsID"], user_agent())
    myDic["Image_url"] = image_link
    if len(summary)> 2000:
        summary = summary[:1997] + "..."
        summaryExtd = summary[1998:]
        myDic["SummaryExtd"] = summaryExtd
    else:
        myDic["SummaryExtd"] = ""    
    myDic["Summary"] = summary
    myDic["Categories"] = categories
    return myDic