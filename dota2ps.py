import os
import re
import collections
from datetime import datetime
import requests
import urllib.request
from bs4 import BeautifulSoup  # https://www.crummy.com/software/BeautifulSoup/bs4/doc/


class D2Patch:
    def __init__(self):
        self.ready = False
        self.url = ''
        self.id = ''
        self.date = datetime.now()
        self.changelog = {'heroes/items': collections.OrderedDict([]),
                          'other': []}

    def fetch_new_post(self, post_url):
        """
        attempts to request document and sends it off to be parsed
        :param post_url: blog post url in form "www.dota2.com/news/updates/....."
        :return:
        """
        r = requests.get(post_url)
        if r.status_code == 200:
            self.url = post_url
            self.parse_post_document(BeautifulSoup(r.text, 'html.parser'))
            self.generate_page()
        else:
            print('There was an error in retreiving the blog post, please try again.')
        return None

    @staticmethod
    def fetch_hero_icons():
        """
        reads hero page of dota2.gamepedia.com for hero icons and downloads any new icons
        hero names are also kept up to date ("Necrolyte" --> "Necrophos")
        :return:
        """
        if 'icons' not in os.listdir(os.getcwd()):
            os.mkdir('icons')

        r = requests.get('https://dota2.gamepedia.com/Heroes')
        if r.status_code == 200:
            try:
                hero_document = BeautifulSoup(r.text, 'html.parser')
                # icons are stored in classed tables within the main page content
                print('Processing hero icons...')
                for table in hero_document.find(id='mw-content-text').find_all(class_='wikitable'):
                    for img in table.find_all('img'):
                        hero_url = img['src']
                        hero_name = re.search('/[^/]*\?', hero_url).group()[7:-10]
                        hero_name = hero_name.replace('%27', '\'').lower()
                        if '{}.png'.format(hero_name) not in os.listdir('icons'):
                            print(hero_name, end=', ', flush=True)
                            urllib.request.urlretrieve(hero_url, 'icons\\{}.png'.format(hero_url))
                print('DONE!')
            except:
                print('Unable to parse document, please try again')
        else:
            print('Unable to obtain document from {}, status code'.format(r.url, r.status_code))
        return None

    @staticmethod
    def fetch_item_icons():
        """
        reads icon page of dota2.com for item icons and downloads any new icons
        some names are outdated, this will need to be rectified
        :return:
        """
        if 'icons' not in os.listdir(os.getcwd()):
            os.mkdir('icons')

        r = requests.get('https://www.dota2.com/items/')
        if r.status_code == 200:
            try:
                item_document = BeautifulSoup(r.text, 'html.parser')
                print('Processing item icons...')
                for column in item_document.find_all(class_='shopColumn'):
                    # nested loop to avoid header image, which is not encapsulated within a div
                    for item_container in column.find_all(name='div'):
                        item_url = item_container.find(name='img')['src']
                        item_name = re.search('/[^/]*\.png', item_url).group()[1:-7]
                        if '{}.png'.format(item_name) not in os.listdir('icons'):
                            print(item_name, end=', ', flush=True)
                            urllib.request.urlretrieve(item_url, 'icons\\{}.png'.format(item_url))
                print('DONE!')
            except:
                print('Unable to parse document, please try again')
        else:
            print('Unable to obtain document from {}, status code'.format(r.url, r.status_code))
        return None

    def parse_post_document(self, document):
        """
        strips the title and body from a blog post
        :param document: the HTML documents as a beautifulsoup object
        :return:
        """
        post = document.find('div', id='mainLoop').find_all('div')[0]
        raw_date, raw_content = post.find_all('div')
        self.date = datetime.strptime(raw_date.string.strip(), '%B %d, %Y - Valve')
        raw_content = list(raw_content.stripped_strings)
        self.id = raw_content[0][:-1]  # remove trailing colon
        self.parse_changelog(raw_content[2:])
        return None

    def parse_changelog(self, raw_changelog):
        self.changelog = {'heroes/items': collections.OrderedDict([]),
                          'other': []}
        for change in raw_changelog:
            change = change.lstrip('* ').split(': ')
            if len(change) == 2:
                hero = change[0]
                if hero in self.changelog['heroes/items'].keys():
                    self.changelog['heroes/items'][hero].append(change[1])
                else:
                    self.changelog['heroes/items'][hero] = [change[1]]
            else:
                self.changelog['other'].append(change)
        return None

    def generate_page(self):
        """
        writes the contents of changelog to an HTML file
        :return:
        """
        with open('patches/{}.html'.format(self.id.upper()), 'w') as patchfile:
            patchfile.write('<!DOCTYPE html>\n' +
                            '<head>\n' +
                            '    <title>{}</title>\n'.format(self.id.upper()) +
                            '    <link rel="stylesheet" href="patch.css"\n' +
                            '</head>\n' +
                            '<body>\n' +
                            '    <h1>{}</h1>'.format(self.id.upper()) +
                            '    <h2>GENERAL</h2>\n' +
                            '    <div id="general">\n')

            for change in self.changelog['other']:
                patchfile.write('            <p>{}</p>\n'.format(change))

            patchfile.write('    </div>\n' +
                            '    <h2>HEROES/ITEMS</h2>\n' +
                            '    <div id="heroes">\n')
            for _ in range(len(self.changelog['heroes/items'])):
                hero, change = self.changelog['heroes/items'].popitem(last=False)
                patchfile.write('        <div class="hero">\n' +
                                '            <img src="../icons/{}.png">\n'.format(hero.replace(' ', '_')) +
                                '            <h3>{}</h3>\n'.format(hero) +
                                '            <ul>\n' +
                                '                <li>' +
                                '\n                <li>'.join([c for c in change]) +
                                '\n            </ul>\n' +
                                '        </div>\n')
            patchfile.write('    </div>\n' +
                            '</body>')
        return None

if __name__ == '__main__':
    patch = D2Patch()
    patch.fetch_new_post(input('Enter URL of blog post\n>>> '))
    patch.fetch_hero_icons()
    patch.fetch_item_icons()
