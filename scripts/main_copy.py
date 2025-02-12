import requests
from bs4 import BeautifulSoup
import re

def get_company_contacts(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", soup.text))
        phones = set(re.findall(r"\+?\d[\d\s.-]{8,}\d", soup.text))

        return {"emails": list(emails), "phones": list(phones)}
    else:
        print("❌ Erreur de requête")
        return None

# Exemple d'utilisation
url = "https://ahmed78.me/"
print(get_company_contacts(url))
