import requests
import logging
import random
from bs4 import BeautifulSoup
import proxies
import time

proxies = {"http": proxies.random_proxy(), "https": proxies.random_proxy()}

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

def get_book_details_users(goodreads_id, user_agent):
    scraped_details = {}
    url = f"{base_url}{goodreads_id}"
    headers = {"User-Agent": user_agent}
    try:
        r = requests.get(url, headers=headers, proxies=proxies)
        html_doc = r.content
        soup = BeautifulSoup(html_doc, "html.parser")
    except Exception as E:
        logging.error("Scraping request failed")
        return    
    try:
        scraped_details["img_deets"] = (soup.find_all("div", id="imagecol")[0].find("img", id="coverImage")["src"])
        summary = ''
        almost_summary = soup.find_all("div", id="descriptionContainer")[0].find_all("span", style="display:none")[0]
        for string in almost_summary.strings:
            summary = summary + string
        scraped_details["summary"] = summary
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
        scraped_details["categories"] = categories
        with open("output.html", "w") as file:
            file.write(str(soup))                       
    except IndexError:
        try:
            scraped_details["img_deets"] = soup.find_all("div", class_="BookCover__image")[0].find("img", class_="ResponsiveImage")["src"]
            summary = ''
            almost_summary = (soup.find_all("div", class_="BookPageMetadataSection__description")[0].find("span", class_="Formatted"))
            for string in almost_summary.strings:
                summary = summary + string
            scraped_details["summary"] = summary    
            categories = []
            all_categories = soup.find("div", class_="BookPageMetadataSection__genres").find_all("span", class_="BookPageMetadataSection__genreButton")
            for item in all_categories:
                dic = {}
                category = item.find("span", class_="Button__labelItem").string
                dic["name"] = category
                categories.append(dic)
            scraped_details["categories"] = categories 
            with open("output1.html", "w") as file:
                file.write(str(soup))   
        except IndexError:
            logging.error(f"Failed to extract data from soup ?different html result")
            with open("output2.html", "w") as file:
                file.write(str(soup))
            print (soup)        
            return None
    except Exception as e:
        logging.error (f"Failed to extract data from soup: {e}")
        return None                        
    return scraped_details


       
def add_to_dic(myDic):
    count = 0
    while count <3: 
        scraped_details = get_book_details_users(myDic["goodreadsID"], user_agent())
        if scraped_details is not None:
            break
        count+=1
        time.sleep(1)
    if scraped_details is not None:  
        myDic["Image_url"] = scraped_details["img_deets"]
        summary = scraped_details["summary"]
        if len(summary)> 2000:
            summary = summary[:1997] + "..."
            summaryExtd = summary[1998:]
            myDic["SummaryExtd"] = summaryExtd
        else:
            myDic["SummaryExtd"] = ""    
            myDic["Summary"] = summary
        myDic["Categories"] = scraped_details["categories"]
        return myDic
    else:
        return

