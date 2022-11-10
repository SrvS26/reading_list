import random
import requests as requests

def random_proxy():
    ips = requests.get("http://localhost:8000").json()
    return random.choice(ips['ips'])

    