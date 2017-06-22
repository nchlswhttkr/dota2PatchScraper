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


#request the page contents, for example "http://www.dota2.com/news/updates/29717/"
patchURL = input('PATCH URL\n>>> ')

print('Accessing patch notes')
r = requests.get(patchURL)

if r.status_code == 200:
    print('Parsing patch notes')
    patch = parseDocument(BS(r.text, 'html.parser'))

    with open('{}.txt'.format(patch['id']),'w') as patchfile:
        print('Writing patch notes')
        patchfile.write('{}'
                        '\n\n'
                        '{}'
                        '\n\n'
                        '===='
                        '\n\n'
                        'GENERAL\n'.format(patch['id'].upper(),
                                           datetime.strftime(patch['date'], '%d/%m/%Y'))
                        )

        for buff in patch['buffs']['other']:
            patchfile.write('\t{}\n'.format(buff))

        patchfile.write('\n\nHEROES/ITEMS\n')
        for _ in range(len(patch['buffs']['heroes/items'])):
            hero, buffs = patch['buffs']['heroes/items'].popitem(last=False)
            patchfile.write('\t{}\n'.format(hero.upper()))
            for buff in buffs:
                patchfile.write('\t\t{}\n'.format(buff))
        print('Patch results written successfully')

else:
    print('Error: Could not access document')

