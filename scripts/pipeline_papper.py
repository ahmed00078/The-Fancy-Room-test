import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import logging
from typing import Dict, Optional
from datetime import datetime
import time
import random
from fake_useragent import UserAgent
import cloudscraper

class PappersScraper:
    def __init__(self):
        self.setup_logging()
        # Utiliser cloudscraper pour contourner la protection Cloudflare
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        self.setup_session()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='pappers_scraping.log'
        )

    def setup_session(self):
        """Configure la session avec des headers appropriés"""
        ua = UserAgent()
        self.headers = {
            'User-Agent': ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        self.scraper.headers.update(self.headers)

    def random_delay(self):
        """Ajoute un délai aléatoire entre les requêtes"""
        time.sleep(random.uniform(2, 5))

    def get_with_retry(self, url: str, max_retries: int = 3) -> Optional[str]:
        """Effectue une requête avec retry et rotation des User-Agents"""
        for attempt in range(max_retries):
            try:
                # Mettre à jour le User-Agent à chaque tentative
                self.headers['User-Agent'] = UserAgent().random
                self.scraper.headers.update(self.headers)
                
                # Effectuer la requête
                response = self.scraper.get(url)
                
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 403:
                    logging.warning(f"Tentative {attempt + 1}/{max_retries}: Access denied (403)")
                    self.random_delay()
                    continue
                else:
                    logging.error(f"Erreur HTTP {response.status_code}")
                    return None
                    
            except Exception as e:
                logging.error(f"Erreur lors de la tentative {attempt + 1}: {str(e)}")
                self.random_delay()
                
        return None

    def extract_company_data(self, html_content: str) -> Dict:
        """Extrait toutes les informations pertinentes de la page Pappers"""
        soup = BeautifulSoup(html_content, 'html.parser')
        print("soup", soup)
        data = {}

        try:
            # Informations de base
            title_elem = soup.select_one('h1')
            if title_elem:
                data['nom'] = self.clean_text(title_elem.text)

            # Extraction systématique des informations clés
            info_labels = {
                'siren': r'SIREN\s*:',
                'siret': r'SIRET.*:',
                'forme_juridique': r'Forme juridique\s*:',
                'capital_social': r'Capital social\s*:',
                'date_creation': r'Création\s*:',
                'activite': r'Activité principale déclarée\s*:',
                'code_naf': r'Code NAF ou APE\s*:',
            }

            for key, pattern in info_labels.items():
                elem = soup.find(string=re.compile(pattern))
                if elem:
                    next_elem = elem.find_next(text=True)
                    if next_elem:
                        data[key] = self.clean_text(next_elem)

            # Extraction de l'adresse
            address_elem = soup.find('div', {'class': 'company-address'})
            if address_elem:
                data['adresse'] = self.clean_text(address_elem.text)

            # Extraction des dirigeants
            dirigeants = []
            dirigeants_section = soup.find(string=re.compile(r'Dirigeants'))
            if dirigeants_section:
                dirigeants_cards = soup.find_all('div', {'class': 'dirigeant-card'})
                for card in dirigeants_cards:
                    nom = card.find('h3')
                    role = card.find('div', {'class': 'role'})
                    if nom and role:
                        dirigeants.append({
                            'nom': self.clean_text(nom.text),
                            'role': self.clean_text(role.text)
                        })
            data['dirigeants'] = dirigeants

            # Extraction des établissements
            etablissements = []
            etab_section = soup.find(string=re.compile(r'Etablissements'))
            if etab_section:
                etab_cards = soup.find_all('div', {'class': 'etablissement-card'})
                for card in etab_cards:
                    siret = card.find('div', {'class': 'siret'})
                    adresse = card.find('div', {'class': 'adresse'})
                    if siret or adresse:
                        etablissements.append({
                            'siret': self.clean_text(siret.text) if siret else '',
                            'adresse': self.clean_text(adresse.text) if adresse else ''
                        })
            data['etablissements'] = etablissements

        except Exception as e:
            logging.error(f"Erreur lors de l'extraction des données: {str(e)}")
            data['error'] = str(e)

        return data

    def clean_text(self, text: Optional[str]) -> str:
        """Nettoie le texte des caractères non désirés"""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    def scrape_company(self, siren: str) -> Dict:
        """Scrape une entreprise à partir de son SIREN"""
        url = f'https://www.pappers.fr/entreprise/sci-baba-and-co-{siren}'
        self.random_delay()
        
        html_content = self.get_with_retry(url)
        if html_content:
            return self.extract_company_data(html_content)
        else:
            return {'error': 'Impossible d\'accéder à la page'}

    def save_to_csv(self, data: Dict, filename: str = None):
        """Sauvegarde les données dans un fichier CSV"""
        if not filename:
            filename = f"pappers_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Aplatir les données pour le CSV
        flat_data = {
            'nom': data.get('nom', ''),
            'siren': data.get('siren', ''),
            'siret': data.get('siret', ''),
            'forme_juridique': data.get('forme_juridique', ''),
            'adresse': data.get('adresse', ''),
            'activite': data.get('activite', ''),
            'code_naf': data.get('code_naf', ''),
            'capital_social': data.get('capital_social', ''),
            'date_creation': data.get('date_creation', ''),
            'dirigeants': '; '.join([f"{d['nom']} ({d['role']})" for d in data.get('dirigeants', [])]),
            'etablissements': '; '.join([f"{e['siret']} - {e['adresse']}" for e in data.get('etablissements', [])])
        }
        
        df = pd.DataFrame([flat_data])
        df.to_csv(filename, index=False, encoding='utf-8')
        logging.info(f"Données sauvegardées dans {filename}")
        return filename

def main():
    scraper = PappersScraper()
    
    # Example usage
    siren = "813257300"  # SCI BABA AND CO
    print(f"Scraping data for SIREN: {siren}")
    
    data = scraper.scrape_company(siren)
    print("\nExtracted Data:")
    for key, value in data.items():
        print(f"{key}: {value}")
    
    # Save to CSV
    filename = scraper.save_to_csv(data)
    print(f"\nData saved to {filename}")

if __name__ == "__main__":
    main()