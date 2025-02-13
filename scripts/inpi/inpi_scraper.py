import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import logging
import re
from typing import List, Dict, Optional


class INPIScraper:
    def __init__(self):
        self.base_url = "https://data.inpi.fr"
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='inpi_scraper.log'
        )

    def setup_session(self):
        """Setup session headers and cookies"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',  # Added French language preference
            'Referer': 'https://data.inpi.fr/',
        })

    def get_company_by_siren(self, siren: str) -> Optional[Dict]:
        """Fetch company data directly using SIREN number"""
        url = f"{self.base_url}/entreprises/{siren}"
        
        # First request to get cookies and tokens
        initial_response = self._make_request(url)
        print("\n\n\nInitial Response: ", initial_response)
        if not initial_response:
            return None
            
        # Make the actual request with proper parameters
        final_url = f"{url}?q=SCI%20#{siren}"
        response = self._make_request(final_url)
        
        if response:
            return self.extract_company_data(response.text)
        return None

    def extract_company_data(self, html_content: str) -> Dict:
        """Extract company information from INPI HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        company_data = {}
    
        try:
            # Extract company name and SIREN from the header
            header = soup.find('h1', class_='truncate-long-title')
            if header:
                name_span = header.find('span', class_='inpi-bold')
                if name_span:
                    company_data['company_name'] = name_span.text.strip()
                siren_match = re.search(r'SIREN\s+(\d{3}\s*\d{3}\s*\d{3})', header.text)
                if siren_match:
                    company_data['siren'] = siren_match.group(1).replace(' ', '')
    
            # Find all detail blocks within the first container
            identity_section = soup.find('h3', string='Identité')
            if identity_section:
                detail_blocks = identity_section.find_parent('div', class_='row').find_all('div', class_='bloc-detail-notice')
                
                for block in detail_blocks:
                    # Find the label (first p element in the block)
                    label = block.find('p', class_='font-weight-300')

                    # Find the value (second p element in the block)
                    # First, get all p elements in the block
                    all_p_elements = block.find_all('p')
                    # The value should be the second p element (index 1)
                    value = all_p_elements[1] if len(all_p_elements) > 1 else None

                    if not label or not value:
                        continue
                
                    label_text = label.text.strip()
                    value_text = value.text.strip()

                    print("Label: ", label_text)
                    print("Value: ", value_text)
                    if not label or not value:
                        continue
                    
                    label_text = label.text.strip()
                    value_text = value.text.strip()
    
                    # Map specific fields
                    if "SIREN (siège)" in label_text:
                        company_data['siren_hq'] = value_text
                    elif "Date d'immatriculation au RNE" in label_text:
                        company_data['registration_date'] = value_text
                    elif "Nature de l'entreprise" in label_text:
                        company_data['company_nature'] = value_text
                    elif "Forme juridique" in label_text:
                        company_data['legal_form'] = value_text
                    elif "Activité principale" in label_text:
                        company_data['main_activity'] = value_text
                    elif "Code APE" in label_text:
                        # Extract just the code portion if there's a hyphen
                        company_data['ape_code'] = value_text.split('-')[0].strip() if '-' in value_text else value_text
                    elif "Adresse du siège" in label_text:
                        # Split address into components and clean up
                        address_parts = value_text.split()
                        if len(address_parts) >= 4:  # Make sure we have enough parts
                            company_data['address'] = {
                                'street_number': address_parts[0],
                                'street_type': address_parts[1],
                                'street_name': ' '.join(address_parts[2:-3]),
                                'postal_code': address_parts[-3],
                                'city': address_parts[-2],
                                'country': address_parts[-1]
                            }
                    elif "Début d'activité" in label_text:
                        company_data['activity_start_date'] = value_text
    
            # Extract establishments
            establishments = []
            establishments_title = soup.find('h3', string='Établissements')
            if establishments_title:
                establishment_section = establishments_title.find_next('div', class_='row')
                if establishment_section:
                    current_establishment = {}
                    for block in establishment_section.find_all('div', class_='bloc-detail-notice'):
                        label = block.find('p', class_='font-weight-300')
                        value = block.find('p', class_='font-size-0-9-rem')
                        
                        if label and value:
                            label_text = label.text.strip()
                            value_text = value.text.strip()
                            
                            if "Siret" in label_text:
                                if current_establishment:
                                    establishments.append(current_establishment.copy())
                                current_establishment = {'siret': value_text}
                            elif "Type d'établissement" in label_text:
                                current_establishment['type'] = value_text
                            elif "Date début d'activité" in label_text:
                                current_establishment['start_date'] = value_text
                            elif "Code APE" in label_text:
                                current_establishment['ape_code'] = value_text.split('-')[0].strip() if '-' in value_text else value_text
                            elif "Adresse" in label_text:
                                address_text = value_text.replace('\n', ' ').strip()
                                current_establishment['address'] = address_text
    
                    if current_establishment:
                        establishments.append(current_establishment)
                        
            if establishments:
                company_data['establishments'] = establishments
    
        except Exception as e:
            self.logger.error(f"Error extracting company data: {str(e)}")
            raise
        
        return company_data

    def _make_request(self, url: str, method: str = 'get', data: Dict = None) -> Optional[requests.Response]:
        """Make HTTP request with retry logic and rate limiting"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                time.sleep(1)  # Basic rate limiting
                if method.lower() == 'post':
                    response = self.session.post(url, data=data)
                else:
                    response = self.session.get(url)
                    
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    self.logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None

    def _extract_company_links(self, soup: BeautifulSoup) -> List[str]:
        """Extract company profile links from search results"""
        company_links = []
        # Adjust the selector based on the actual HTML structure of the search results
        for link in soup.select('a[href*="/entreprises/"]'):  # Example selector
            company_links.append(self.base_url + link['href'])
        return company_links

    def search_companies(self, criteria: Dict) -> List[Dict]:
        """Search for companies based on criteria"""
        search_url = f"{self.base_url}/search"  # Adjust URL as needed
        
        try:
            response = self._make_request(search_url, 'post', data=criteria)
            if not response:
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            company_links = self._extract_company_links(soup)
            
            companies = []
            for link in company_links:
                company_response = self._make_request(link)
                if company_response:
                    company_data = self.extract_company_data(company_response.text)
                    companies.append(company_data)
                    
            return companies
            
        except Exception as e:
            self.logger.error(f"Error in company search: {str(e)}")
            return []

    def save_to_csv(self, companies: List[Dict], filename: str = None):
        """Save extracted data to CSV file"""
        if not filename:
            filename = f'inpi_companies_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            
        try:
            df = pd.DataFrame(companies)
            df.to_csv(filename, index=False, encoding='utf-8')
            self.logger.info(f"Data saved to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving to CSV: {str(e)}")

# Usage example:
scraper = INPIScraper()
scraper.setup_session()
company_data = scraper.get_company_by_siren("430653709")
print(company_data)
if company_data:
    scraper.save_to_csv([company_data])