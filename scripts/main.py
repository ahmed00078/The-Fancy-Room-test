import requests

api_key = "db4c3631da8cde1fc990a336492aff94f487bd2fc37bc943"
siren = "813257300"
url = f"https://api.pappers.fr/v2/entreprise?siren={siren}&api_token={api_key}"
response = requests.get(url)
data = response.json()
print(data)