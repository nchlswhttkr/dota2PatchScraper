import requests
from datetime import datetime
import urllib.request
from bs4 import BeautifulSoup  # https://www.crummy.com/software/BeautifulSoup/bs4/doc/
import os
import re
import collections


class D2Patch:
    def __init__(self):
        self.ready = False
        self.url = ''
        self.id = ''
        self.date = datetime.now()
        self.changelog = {'heroes/items': collections.OrderedDict([]),
                          'other': []}

    def fetch_new_post(self, post_url):
        r = requests.get(post_url)
        if r.status_code == 200:
            self.url = post_url
            self.parse_post_document(BeautifulSoup(r.text, 'html.parser'))
            self.generate_page()
        else:
            print('There was an error in retreiving the blog post, please try again.')
        return None

    def parse_post_document(self, document):
        post = document.find('div', id='mainLoop').find_all('div')[0]
        post_date, post_content = post.find_all('div')
        patch_id, patch_date, raw_changelog = self.parse_post_details(post_date, post_content)
        patch_changelog = self.parse_changelog(raw_changelog)
        self.id = patch_id
        self.date = patch_date
        self.changelog = patch_changelog
        return None

    def parse_post_details(self, raw_date, raw_contents):
        post_date = datetime.strptime(raw_date.string.strip(), '%B %d, %Y - Valve')
        print('REMOVE' + raw_date.string)
        post_content = list(raw_contents.stripped_strings)
        post_id = post_content[0][:-1]  # remove trailing colon
        post_changelog = post_content[2:]
        return post_id, post_date, post_changelog

    def parse_changelog(self, raw_changelog):
        changelog = {'heroes/items': collections.OrderedDict([]),
                     'other': []}
        for change in raw_changelog:
            change = change.lstrip('* ').split(': ')
            if len(change) == 2:
                hero = change[0]
                if hero in changelog['heroes/items'].keys():
                    changelog['heroes/items'][hero].append(change[1])
                else:
                    changelog['heroes/items'][hero] = [change[1]]
            else:
                changelog['other'].append(change)
        return changelog

    def generate_page(self):
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
