import requests
from decouple import config
import sqlite3

gumroad_token = config("GUMROAD_TOKEN")

database_file_path = config("DATABASE_FILE_PATH")

conn = sqlite3.connect(database_file_path)

#Query Gumroad, get all sales details
    # Since it returns only 10 per page, this needs to be a loop to get all sales until no more
    # Get out the relevant data from everything that is returned and add to a list
#Query table, get already existing entries
    # Get the existing entries and remove those from list
#Insert rest of the queries into the table

headers = {"Content-Type": "application/json",
           "Authorization": f"Bearer {gumroad_token}"}


def get_sales_info(params = ''):
    url = "https://api.gumroad.com/v2/sales"
    try:
        response = requests.get(url, headers=headers, data=params)
        status_code = response.status_code
        if status_code == 200:
            parsed_response = response.json()
            return parsed_response.get("sales"), parsed_response.get("next_page_key")
        else:
            return None, None
    except Exception:
        return None, None


def match_sales_info(sales_info):
    list_of_sales = []
    for sale in sales_info:
        one_sale = {sales_info.get("id"): {
                "sale_id": sales_info.get("id", ''),
                "sale_timestamp": sales_info.get("timestamp", ''),
                "order_number": sales_info.get("order_id", ''),
                "product_id": sales_info.get("product_id", ''),
                "permalink": sales_info.get("product_permalink", ''),
                "product_permalink": "https://se7enforward.gumroad.com/l/" + sales_info.get("product_permalink", ''),
                "product_name": sales_info.get("product_name", ''),
                "short_product_id": sales_info.get("product_permalink", ''),
                "email": sales_info.get("email", ''),
                "full_name":sales_info.get("full_name", ''),
                "subscription_id":sales_info.get("subscription_id", ''),
                "ip_country": sales_info.get("country", ''),
                "referrer": sales_info.get("referrer", ''),
                "price": sales_info.get("price", ''),
                "variants": sales_info.get("variants", {}).get("Tier", ''),
                "is_recurring_charge": sales_info.get("is_recurring_billing", None),
                "license_key": sales_info.get("license_key", ''),
                "affiliate": sales_info.get("affiliate", {}).get("email", ''),
                "affiliate_credit": sales_info.get("affilate", {}).get("amount", ''),
                "refunded": sales_info.get("refunded", None),
                "discover_fee_charged": sales_info.get("discover_fee_charged", None),
                "gumroad_fee": sales_info.get("gumroad_fee", '')
            }}
        list_of_sales.append(one_sale)
    return list_of_sales





