from cmath import e
import requests
import random
from bs4 import BeautifulSoup
import time



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
    while img_deets is None or len(img_deets) == 0:
        try:
            r = requests.get(url, headers=headers)
            status = r.status_code
            print (status)
            html_doc = r.content
            soup = BeautifulSoup(html_doc, "html.parser") 
            img_deets = soup.find_all("img", id="coverImage")[0]["src"]
            time.sleep(1)
        except Exception as e:
            print (e)                   
    return img_deets


get_book_details(555, user_agent())
