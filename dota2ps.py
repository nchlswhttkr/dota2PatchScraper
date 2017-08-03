import os
import re
import collections
from datetime import datetime
import requests
import urllib.request
from lxml import html


class D2Patch:
    def __init__(self, key):
        self.ready = False
        self.url = ''
        self.id = ''
        self.date = datetime.now()
        self.changelog = {'heroes/items': collections.OrderedDict([]),
                          'other': []}
        self.icon_url = 'http://cdn.dota2.com/apps/dota2/images/'
        self.api_key = key

    def fetch_new_post(self, post_url):
        """
        attempts to request document and sends it off to be parsed
        :param post_url: blog post url in form "www.dota2.com/news/updates/....."
        :return:
        """
        r = requests.get(post_url)
        if r.status_code == 200:
            self.url = post_url
            self.parse_post_document(r)
            self.generate_page()
        else:
            print('There was an error in retreiving the blog post, please try again.')
        return None

    def fetch_hero_icons(self):
        """
        pings the Steam API for a list of heroes
        :return:
        """
        r = requests.get('http://api.steampowered.com/IEconDOTA2_570/GetHeroes/v1/', params={'key': self.api_key,
                                                                                                  'language': 'en'})
        if r.status_code == 200:
            try:
                print('\nDownloading hero icons\nProcessing ', end=' ')
                heroes = r.json()['result']['heroes']
                failed = []
                for hero in heroes:
                    hero_id = hero['name'] #may be old or outdated, used purely to retrieve icon
                    hero_id = hero_id[14:]
                    hero_name = hero['localized_name']
                    print(hero_name, end=', ', flush=True)
                    self.download_icon('heroes/{}_lg.png'.format(hero_id), hero_name)
                print('DONE!\nThe following icons could not be downloaded:\n' +
                      'NOTE: Some of these may just be the result of Valve not keeping their API up-to-date\n' +
                      ', '.join(failed))
            except Exception as err:
                print(err)
        else:
            print('There was an error in accessing the Steam API')

    def fetch_item_icons(self):
        """
        pings the Steam API for a list of items
        :return:
        """
        r = requests.get('http://api.steampowered.com/IEconDOTA2_570/GetGameItems/V001/', params={'key': self.api_key,
                                                                                                  'language': 'en'})
        if r.status_code == 200:
            try:
                print('\nDownloading item icons\nProcessing ', end=' ')
                items = r.json()['result']['items']
                failed = []
                for item in items:
                    item_id = item['name'] #may be old or outdated, used purely to retrive icon
                    item_id = item_id[5:]
                    item_name = item['localized_name']
                    print(item_name, end=', ', flush=True)
                    download_result = self.download_icon('items/{}_lg.png'.format(item_id), item_name)
                    if download_result != 0:
                        failed.append(download_result)
                print('DONE!\nThe following icons could not be downloaded:\n' +
                      'NOTE: Some of these may just be the result of Valve not keeping their API up-to-date\n' +
                      ', '.join(failed))
            except Exception as err:
                print(err)
        else:
            print('There was an error in accessing the Steam API')

    def download_icon(self, slug, name):
        if '{}.png'.format(name) not in os.listdir('icons'):
            try:
                urllib.request.urlretrieve(self.icon_url + slug, 'icons\\{}.png'.format(name))
            except:
                return name
        return 0

    def parse_post_document(self, response):
        """
        strips the title and body from a blog post
        :param response: the requests response object
        :return:
        """
        document = html.fromstring(response.content)
        raw_date = document.find_class('entry-meta')[0].text_content().strip()
        raw_content = document.find_class('entry-content')[0].text_content().strip()
        self.date = datetime.strptime(raw_date, '%B %d, %Y - Valve')
        line_seperator = re.findall(':=+', raw_content)[0]
        self.id, raw_changelog = raw_content.split(line_seperator)
        self.parse_changelog(raw_changelog)
        return None

    def parse_changelog(self, raw_changelog):
        self.changelog = {'heroes/items': collections.OrderedDict([]),
                          'other': []}
        raw_changelog = raw_changelog.lstrip('* ').split('* ')
        for change in raw_changelog:
            change = change.split(': ')
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
                            '    <h1>{}</h1>\n'.format(self.id.upper()) +
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
                                '            <img src="../icons/{}.png">\n'.format(hero) +
                                '            <h3>{}</h3>\n'.format(hero) +
                                '            <ul>\n' +
                                '                <li>' +
                                '</li>\n                <li>'.join([c for c in change]) +
                                '</li>\n            </ul>\n' +
                                '        </div>\n')
            patchfile.write('    </div>\n' +
                            '</body>')
        return None


if 'icons' not in os.listdir():
    os.mkdir('icons')

if __name__ == '__main__':
    patch = D2Patch(input('Please enter your Steam API Key\n>>> '))
    patch.fetch_hero_icons()
    patch.fetch_item_icons()
    patch.fetch_new_post(input('Enter URL of blog post\n>>> '))