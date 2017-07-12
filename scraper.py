import requests
from datetime import datetime
import collections
from bs4 import BeautifulSoup as BS #https://www.crummy.com/software/BeautifulSoup/bs4/doc/


def parseDocument(document):
    """
    isolate patch content from document, break down content into objects
    :param document: html document as a BS OBJ
    :return: DICT of key information
    """
    post = document.find_all('div', id='mainLoop')[0].find_all('div')[0]
    postDate, postContents = post.find_all('div')
    patchDate, patchID, patchChangelog = parsePatchDetails(postDate, postContents)
    patchBuffs = parseBuffs(patchChangelog)
    return {'date': patchDate, 'id': patchID, 'buffs': patchBuffs}


def parsePatchDetails(rawdate, rawcontents):
    """
    parse page content (release date, patch ID, changelog)
    :param rawdate: date of post as a BS OBJ
    :param rawcontents: patch ID and changelog within a BS OBJ
    :return: DATE, ID as STR, changelog as LIST
    """
    patchdate = datetime.strptime(rawdate.string.strip(), '%B %d, %Y - Valve')
    contents = list(rawcontents.stripped_strings)
    patchid, patchchangelog = contents[0][:-1], contents[2:]
    return patchdate, patchid, patchchangelog


def parseBuffs(changelog):
    """
    catalogue buffs/nerfs as well as general changes
    :param changelog: a LIST of buffs and nerfs
    :return: described below
    """
    buffs = {'heroes/items': collections.OrderedDict([]),
             'other': []}
    for change in changelog:
        change = change.split(': ')
        if len(change) == 2: #buffs targeted at heroes and items will be in the form "hero: buff"
            hero, buff = change
            hero = hero.lstrip('* ')
            if hero in buffs['heroes/items'].keys():
                buffs['heroes/items'][hero].append(buff)
            else:
                buffs['heroes/items'][hero] = [buff]
        else: #general changes
            buffs['other'].append(change)
    return buffs

def generatePage(patchNotes):
    with open('patches/{}.html'.format(patchNotes['id'].upper()), 'w') as patchfile:
        patchfile.write('<!DOCTYPE html>\n' +
                        '<head>\n' +
                        '    <title>{}</title>\n'.format(patchNotes['id'].upper()) +
                        '    <link rel="stylesheet" href="patch.css"\n' +
                        '</head>\n' +
                        '<body>\n' +
                        '    <h1>{}</h1>'.format(patchNotes['id'].upper()) +
                        '    <h2>GENERAL</h2>\n' +
                        '    <div id="general">\n')

        for change in patchNotes['buffs']['other']:
            patchfile.write('            <p>{}</p>\n'.format(change))

        patchfile.write('    </div>\n' +
                        '    <h2>HEROES/ITEMS</h2>\n' +
                        '    <div id="heroes">\n')
        for _ in range(len(patchNotes['buffs']['heroes/items'])):
            hero, buffs = patch['buffs']['heroes/items'].popitem(last=False)
            patchfile.write('        <div class="hero">\n' +
                            '            <img src="../icons/{}.png">\n'.format(hero.replace(' ', '_')) +
                            '            <h3>{}</h3>\n'.format(hero) +
                            '            <ul>\n' +
                            '                <li>' +
                            '\n                <li>'.join([buff for buff in buffs]) +
                            '\n            </ul>\n' +
                            '        </div>\n')
        patchfile.write('    </div>\n' +
                        '</body>')
        print('Patch notes written successfully')
    return None


#request the page contents, for example "http://www.dota2.com/news/updates/29717/"
patchURL = input('PATCH URL\n>>> ')

print('Accessing patch notes')
r = requests.get(patchURL)


if r.status_code == 200:
    print('Parsing patch notes')
    patch = parseDocument(BS(r.text, 'html.parser'))
    generatePage(patch)

else:
    print('Error: Could not access document')

