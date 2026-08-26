import requests as rec
from bs4 import BeautifulSoup
import time

link = "https://en.wikipedia.org/wiki/Lifestyle"

headers = {
    "User-Agent": ""
}

while True:
    try:
        res = rec.get(link, headers=headers, timeout=10)

        print(res.status_code)

        if res.status_code == 200:
            break

    except rec.RequestException:
        print("Request failed")


soup = BeautifulSoup(res.text, "html.parser")
print(soup.text)