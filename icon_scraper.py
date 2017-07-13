import requests
import urllib.request
from bs4 import BeautifulSoup as BS

r = requests.get("http://dota2.gamepedia.com/Heroes")

if r.status_code == 200:
    try:
        heroDocument = BS(r.text, 'html.parser')
        #icons are stored in classed tables within the main page content
        for table in heroDocument.find(id='mw-content-text').find_all(class_='wikitable'):
            for img in table.find_all('img'):
                url = img['src']
                heroname = url.split('_icon.png')[0].split('/')[-1].replace('%27', '\'').lower()
                print('Processing {}'.format(heroname))
                urllib.request.urlretrieve(url, 'icons\\{}.png'.format(heroname))
        print('All hero images saved successfully')
    except:
        print('Unable to parse document, please try again')
else:
    print('Unable to obtain document from {}'.format(r.url))