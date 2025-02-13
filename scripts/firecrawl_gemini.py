FIRECRAWL_API_KEY = "fc-5a60c462fef743c59048f5ecc8bc1455"
GOOGLE_API_KEY="AIzaSyD6UbqgGutm-zCKy1Vrt3J5bl4w5gvAmmQ"


from firecrawl import FirecrawlApp
from pydantic import BaseModel
from typing import List
import google.generativeai as genai
from dotenv import load_dotenv
import pandas as pd
import json
import os

load_dotenv()

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# scrape data from pages 1 to 5
pages = range(1,5)
items = []

for page in pages:
    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
    url = "https://www.python-unlimited.com/webscraping/hotels.php?page="+str(page)

    # store the page content in the variable page_content
    page_content = app.scrape_url(url=url,  
        params={
            "pageOptions":{
                "onlyMainContent": True 
            }
        })

    # Define the fields to extract
    fields = ["hotel_name", "hotel_location", "hotel_rating"]

    # Prepare the prompt for Gemini
    prompt = f"""
    Extract the following information from this webpage content into JSON format:
    Fields to extract: {fields}
    
    Webpage content: {page_content}
    
    Return the data as a valid JSON array of objects, where each object contains the specified fields.
    """

    # Get response from Gemini
    response = model.generate_content(prompt)
    
    try:
        # Parse the response text to get JSON
        # Gemini might wrap the JSON in markdown code blocks, so we need to handle that
        response_text = response.text
        if "```json" in response_text:
            # Extract JSON from markdown code block
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()
        
        data = json.loads(json_str)
        
        # Handle case where data might be wrapped in an extra dictionary
        if isinstance(data, dict):
            keys = list(data.keys())
            if len(keys) == 1:
                data = data[keys[0]]
        
        # Add all items
        if isinstance(data, list):
            items.extend(data)
        
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from page {page}: {e}")
        continue
    
    break

# Create DataFrame and save to files
df = pd.DataFrame(items)
df.to_excel("hotels.xlsx", index=False)
df.to_csv("hotels.csv", index=False)