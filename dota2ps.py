import requests
from datetime import datetime
import urllib.request
from bs4 import BeautifulSoup #https://www.crummy.com/software/BeautifulSoup/bs4/doc/
import os
import re
import collections

class D2Patch:
    def __init__(self, id_code, release_date, changelog, url):
        self.id = id_code
        self.date = release_date
        self.changelog = changelog
        self.url = url

def parse_document(document, url):
    """
    isolate patch content from document, break down content into objects
    :param document: html document as a BS OBJ
    :return: DICT of key information
    """
    post = document.find('div', id='mainLoop').find('div')
    post_title, post_content = post.find_all('div')
    patch_date, patch_id, raw_changelog = parse_post_details(post_title, post_content)
    patch_changelog = parse_changelog(raw_changelog)
    patch = D2Patch(patch_id, patch_date, patch_changelog, url)
    return patch

def parse_post_details(raw_date, raw_contents):
    """
    read post content and strip the date, id and contents of the patch
    :param raw_date: date of post as a string
    :param raw_contents: list of strings, representing each line of the post
    :return: date, id and a list of changes
    """
    post_date = datetime.strptime(raw_date.string.strip(), '%B %d, %Y - Valve')
    post_content = list(raw_contents.stripped_strings)
    post_id = post_content[0][:-1] #first line of post, exclude trailing colon
    post_changelog = post_content[2:] #changelog follows a break
    return post_date, post_id, post_changelog

def parse_changelog(raw_changelog):
    """
    catalogue buffs/nerfs as well as general changes
    :param changelog: a LIST of buffs and nerfs
    :return: described below
    """
    changelog = {'heroes/items': collections.OrderedDict([]),
             'other': []}
    for change in raw_changelog:
        change = change.split(': ')
        # buffs targeted at heroes and items will be in the form "hero: buff"
        if len(change) == 2:
            hero, buff = change
            hero = hero.lstrip('* ') # leading dot point
            if hero in changelog['heroes/items'].keys():
                changelog['heroes/items'][hero].append(buff)
            else:
                changelog['heroes/items'][hero] = [buff]
        else: #general changes
            changelog['other'].append(change)
    return changelog

def generate_page(patch):
    with open('patches/{}.html'.format(patch.id.upper()), 'w') as patchfile:
        patchfile.write('<!DOCTYPE html>\n' +
                        '<head>\n' +
                        '    <title>{}</title>\n'.format(patch.id.upper()) +
                        '    <link rel="stylesheet" href="patch.css"\n' +
                        '</head>\n' +
                        '<body>\n' +
                        '    <h1>{}</h1>'.format(patch.id.upper()) +
                        '    <h2>GENERAL</h2>\n' +
                        '    <div id="general">\n')

        for change in patch.changelog['other']:
            patchfile.write('            <p>{}</p>\n'.format(change))

        patchfile.write('    </div>\n' +
                        '    <h2>HEROES/ITEMS</h2>\n' +
                        '    <div id="heroes">\n')
        for _ in range(len(patch.changelog['heroes/items'])):
            hero, change = patch.changelog['heroes/items'].popitem(last=False)
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

def fetch_post(post_url):
    r = requests.get(post_url)
    if r.status_code == 200:
        patchDocument = parse_document(BeautifulSoup(r.text, 'html.parser'), r.url)
        generate_page(patchDocument)

if __name__ == "__main__":
    post_url = input('Please enter the URL to the patch\'s blog post\n>>> ')
    fetch_post(post_url)