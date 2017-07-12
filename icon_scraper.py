import requests
import urllib.request
from bs4 import BeautifulSoup as BS

document = requests.get("http://dota2.gamepedia.com/Heroes")
heroTable = BS(document.text, 'html.parser')

for table in heroTable.find_all('div', id='mw-content-text')[0].find_all(class_='wikitable'):
    for img in table.find_all('img'):
        url = img['src']
        heroname = url.split('_icon.png')[0].split('/')[-1].replace('%27', '\'').lower()
        print('Processing {}'.format(heroname))
        urllib.request.urlretrieve(url, 'icons\\{}.png'.format(heroname))