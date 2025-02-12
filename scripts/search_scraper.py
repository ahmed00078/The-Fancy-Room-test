import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random

# Configuration du User-Agent pour éviter les blocages
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.google.com/",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"
}

# URL de recherche avec un mot-clé (à modifier selon le site cible)
BASE_URL = "https://data.inpi.fr/entreprises/430653709?q=SCI%20#430653709"

# Fonction pour récupérer les résultats d'une recherche
def scrape_search_results(query, max_pages=1):
    results = []
    
    for page in range(1, max_pages + 1):
        url = BASE_URL.format(query=query.replace(" ", "+"), page=page)
        print(f"📡 Scraping page {page}: {url}")

        session = requests.Session()
        session.headers.update(HEADERS)
        response = session.get(url)

        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"❌ Erreur {response.status_code} lors du scraping")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        # Trouver tous les blocs d'entreprises (adapté au site cible)
        company_blocks = soup.find_all("div", class_="company-list-item")

        for company in company_blocks:
            try:
                name = company.find("h2").text.strip()
                link = company.find("a")["href"]
                description = company.find("p", class_="desc").text.strip() if company.find("p", class_="desc") else ""
                
                results.append({
                    "name": name,
                    "link": link,
                    "description": description
                })
            except Exception as e:
                print(f"⚠️ Erreur d'extraction: {e}")

        # Pause pour éviter d’être bloqué (anti-bot)
        time.sleep(random.uniform(2, 5))

    print(f"✅ Scraping terminé: {len(results)} résultats collectés")
    return results

# Sauvegarde des résultats dans un fichier CSV
def save_to_csv(results, filename="search_results.csv"):
    df = pd.DataFrame(results)
    df.to_csv(filename, index=False, encoding="utf-8")
    print(f"✅ Résultats enregistrés dans {filename}")

# Exécution du scraper
if __name__ == "__main__":
    query = "nom entreprise"
    search_results = scrape_search_results(query, max_pages=1)
    save_to_csv(search_results)