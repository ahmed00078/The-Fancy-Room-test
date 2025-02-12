import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from linkedin_api import Linkedin
import logging
from typing import List, Dict
import concurrent.futures

class DataEnrichmentPipeline:
    def __init__(self, max_workers: int = 3):
        self.data = pd.DataFrame()
        self.max_workers = max_workers
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='scraping.log'
        )
        
    def search_results_scraper(self, base_url: str, search_params: Dict) -> List[Dict]:
        """Scrape les pages de résultats de recherche"""
        try:
            results = []
            with requests.Session() as session:
                response = session.get(base_url, params=search_params)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Adapter le sélecteur selon la structure du site
                results_elements = soup.select('.result-item')  
                
                for element in results_elements:
                    result = {
                        'company_name': element.get('company', ''),
                        'website': element.get('website', ''),
                        'address': element.get('address', ''),
                        'siret': element.get('siret', '')
                    }
                    results.append(result)
                    
            return results
        except Exception as e:
            logging.error(f"Erreur lors du scraping des résultats: {str(e)}")
            return []

    def website_contact_scraper(self, url: str) -> Dict:
        """Extrait les informations de contact depuis un site web"""
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Patterns pour emails et téléphones
            email_pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}'
            phone_pattern = r'(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}'
            
            emails = list(set(re.findall(email_pattern, response.text)))
            phones = list(set(re.findall(phone_pattern, response.text)))

            print(f"Contact info found: {emails}, {phones}")
            
            return {
                'emails': emails,
                'phones': phones
            }
        except Exception as e:
            logging.error(f"Erreur lors du scraping du site {url}: {str(e)}")
            return {'emails': [], 'phones': []}

    def linkedin_profile_finder(self, company_name: str, api_client: Linkedin) -> List[Dict]:
        """Recherche les profils LinkedIn correspondants"""
        try:
            # Recherche de l'entreprise
            company = api_client.search_companies(company_name)[0]
            company_id = company['id']
            
            # Recherche des employés
            employees = api_client.search_people(
                f'company:"{company_id}" AND (CEO OR Founder OR Director OR Manager)'
            )
            
            return [{
                'name': emp['name'],
                'title': emp['title'],
                'profile_url': f"https://www.linkedin.com/in/{emp['public_id']}"
            } for emp in employees[:5]]  # Limite aux 5 premiers résultats
            
        except Exception as e:
            logging.error(f"Erreur lors de la recherche LinkedIn pour {company_name}: {str(e)}")
            return []

    def enrich_with_external_services(self, company_data: Dict) -> Dict:
        """Enrichit les données avec des services externes"""
        # Exemple avec un service fictif d'enrichissement
        try:
            # Ici vous pourriez intégrer des services comme Hunter.io, Clearbit, etc.
            enriched_data = {
                'additional_emails': [],
                'social_profiles': [],
                'company_info': {}
            }

            print(f"Enriching data for: {company_data['company_name']}")
            return enriched_data
        except Exception as e:
            logging.error(f"Erreur lors de l'enrichissement des données: {str(e)}")
            return {}

    def process_company(self, company_data: Dict) -> Dict:
        """Traite une entreprise à travers tout le pipeline"""
        results = company_data.copy()

        # 1. Scraping du site web
        if results.get('website'):
            logging.info(f"Scraping website: {results['website']}")
            contact_info = self.website_contact_scraper(results['website'])
            logging.info(f"Contact info found: {contact_info}")
            results.update(contact_info)

        # 2. Recherche LinkedIn
        linkedin_profiles = self.linkedin_profile_finder(results['company_name'], self.linkedin_client)
        results['linkedin_profiles'] = linkedin_profiles

        # 3. Enrichissement externe
        enriched_data = self.enrich_with_external_services(results)
        results.update(enriched_data)

        print(f"Processed company: {results['company_name']}")

        return results

    def run_pipeline(self, search_urls: List[str], search_params: Dict) -> pd.DataFrame:
        """Exécute le pipeline complet"""
        all_results = []
        
        # 1. Collecte initiale des données
        for url in search_urls:
            results = self.search_results_scraper(url, search_params)
            all_results.extend(results)
        
        # 2. Traitement parallèle des entreprises
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            processed_results = list(executor.map(self.process_company, all_results))
        
        # 3. Création du DataFrame final
        self.data = pd.DataFrame(processed_results)
        
        # 4. Sauvegarde des résultats
        self.data.to_csv('resultats_enrichis.csv', index=False)

        print("Pipeline completed: ", self.data)
        
        return self.data

    def validate_data(self) -> pd.DataFrame:
        """Valide et nettoie les données collectées"""
        # Suppression des doublons
        self.data.drop_duplicates(subset=['siret'], inplace=True)
        
    def validate_data(self) -> pd.DataFrame:
        """Validate and clean collected data"""
        if self.data.empty:
            return self.data
            
        # Remove duplicates if siret column exists
        if 'siret' in self.data.columns:
            self.data.drop_duplicates(subset=['siret'], inplace=True)
        
        # Validate emails if column exists
        if 'emails' in self.data.columns:
            self.data['emails'] = self.data['emails'].apply(
                lambda x: [email for email in x if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)]
            )
        
        # Validate phone numbers if column exists
        if 'phones' in self.data.columns:
            self.data['phones'] = self.data['phones'].apply(
                lambda x: [phone for phone in x if re.match(r'^(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}$', phone)]
            )

        print("Data validation completed: ", self.data)
        
        return self.data

if __name__ == "__main__":
    search_urls = [
        'https://www.pappers.fr/recherche'
    ]
    
    search_params = {
        'q': 'SCI'
    }

    pipeline = DataEnrichmentPipeline(max_workers=3)
    
    pipeline.run_pipeline(search_urls, search_params)
    print("pipeline.data.columns: ", pipeline.data.columns)
    pipeline.validate_data()
    print(pipeline.data)