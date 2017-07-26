import requests
import urllib.request
from bs4 import BeautifulSoup as BS
import os

#create icon file if one does not already exist
if 'icons' not in os.listdir(os.getcwd()):
    os.mkdir('icons')

#dota2.gamepedia is used here because of it keeps hero names updated
#for example "Necrolyte" --> "Necrophos"
heroRequest = requests.get('http://dota2.gamepedia.com/Heroes')
if heroRequest.status_code == 200:
    try:
        heroDocument = BS(heroRequest.text, 'html.parser')
        #icons are stored in classed tables within the main page content
        for table in heroDocument.find(id='mw-content-text').find_all(class_='wikitable'):
            for img in table.find_all('img'):
                heroURL = img['src']
                heroName = heroURL.split('_icon.png')[0].split('/')[-1].replace('%27', '\'').lower()
                print('Processing {}'.format(heroName))
                urllib.request.urlretrieve(heroURL, 'icons\\{}.png'.format(heroName))
        print('All hero images downloaded successfully')
    except:
        print('Unable to parse document, please try again')
else:
    print('Unable to obtain document from {}, status code'.format(heroRequest.url, heroRequest.status_code))

#the official dota2 page is used here, as dota2.gamepedia generates
#   the item page at execution instead of rendering it client-side
#some items also have outdated names, this will be fixed in future
itemRequest = requests.get('https://www.dota2.com/items/')
if itemRequest.status_code == 200:
    try:
        itemDocument = BS(itemRequest.text, 'html.parser')
        for column in itemDocument.find_all(class_='shopColumn'):
            # this additional loop ignores the column's header icon, which is the only image not encapsulated within a div
            for itemContainer in column.find_all(name='div'):
                itemURL = itemContainer.find(name='img')['src']
                itemName = itemURL.split('_lg.png')[0].split('/')[-1]
                print('Processing {}'.format(itemName))
                urllib.request.urlretrieve(itemURL, 'icons\\{}.png'.format(itemName))
        print('All item images downloaded successfully')
    except:
        print('Unable to parse document, please try again')
else:
    print('Unable to obtain document from {}, status code'.format(itemRequest.url, itemRequest.status_code))