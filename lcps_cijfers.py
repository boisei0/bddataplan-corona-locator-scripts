import requests
import re

res = requests.get('https://s3.eu-de.cloud-object-storage.appdomain.cloud/cloud-object-storage-lcps/news.json')
data = res.json()

title_pattern = re.compile(r'^\d.+ COVID-patiënten op IC')

for item in data['updates']:
    if title_pattern.search(item['title']):
        content_parts = item['content'].split('.')
        print(content_parts[0][content_parts[0].find('bedraagt') + len('bedraagt '):])
        # ugh, toch maar regex doen dan?