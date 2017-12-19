import os
import sys
import shutil
import re
from datetime import date
import json
import urllib.request
import webbrowser
import requests
from lxml import html

"""
TODO:
 - documentation RE localised names
 - handle items with multiple levels (dagon, necrobook)
 - improve compatability with updates hosted on steamcommunity.com
   - posts on dota2.com are only temporararily available (last ~20-50 posts)
 - disable writing for unprepared/failed patches
 - provide README documentation of available commands
 - handle edge cases with dates (american format / month as a number / missing year)
 - accepted patch url in multiple formats (id, url sans protocol, etc...)
 - try/except catches for all API requests (inc. requests.raise_for_status())
 - include warnings about when to use reference/sanitised/display names
"""

class DOTAPatch:

    def __init__(self, patch_url, steam_api_key='', patch_directory='patches', media_directory='media'):
        """
        :param patch_url: the URL (including protocol) where the patch is hosted
        :param steam_api_key: a key to the Steam API, used for keep game data up-to-date
        :param write_directory: the location to write patches to
        :param media_directory: the location to read icons and other misc images from
        """

        #
        self.OK = True
        self.api_key = steam_api_key
        self.patch_directory = patch_directory
        self.media_directory = media_directory

        # patch details
        self.patch_url = patch_url
        self.patch_id = ''
        self.patch_release_date = ''
        self.patch_heroes_changed = []
        self.patch_items_changed = []
        self.patch_hero_changes = {}
        self.patch_item_changes = {}
        self.patch_general_changes = []

        # general game data
        self.dota_heroes = []
        self.dota_items = []
        self._icon_url_path = 'http://cdn.dota2.com/apps/dota2/images'

        # verify that the patch and media and media directories exist and have read/write permissions
        if not os.path.exists(self.patch_directory):
            raise FileNotFoundError('The directory to save patches to could not be found')
        if not os.path.exists(self.media_directory):
            raise FileNotFoundError('The directory to read icons from could not be found')
        if not os.access(self.patch_directory, os.W_OK):
            raise PermissionError('The directory to save patches to does not have write permissions')
        if not os.access(self.media_directory, os.W_OK):
            raise PermissionError('The directory to read and write icons from and to does not have write permissions')

        # attempt to update the hero and item data using the Steam API if a key is provided
        if self.api_key != '':
            self._update_hero_data()
            self._update_item_data()
        # generate a list of all heroes/items for faster referencing
        with open('heroes.json', 'r') as herofile:
            heroes = json.load(herofile)
            for hero in heroes:
                self.dota_heroes.append(hero['sanitised_name'])
        with open('items.json', 'r') as itemfile:
            items = json.load(itemfile)
            for item in items:
                self.dota_items.append(item['sanitised_name'])

        # generate patch details
        self._get_patch_details()

    def generate_patch(self, generate_json=True, check_for_icons=False, open_on_completion=False):
        """
        creates a basic webpage for the patch notes
        :param generate_json: will produce an accompanying json file with patch details
        :param check_for_icons: will run an additional function to check for missing icons to download
        :param open_on_completion: opens the resulting HTML file once the page is generated, useful for debugging
        :return: none
        """

        # prevent writing an erroneous/failed patch
        if not self.OK:
            raise Exception()

        # download any missing icons
        if check_for_icons:
            self._get_icons()

        # initialise a NEW directory that does not overwrite existing folders and copy over essential files
        if self.patch_id not in os.listdir(self.patch_directory):
            patch_name = self.patch_id
        else:
            # 7.01B [1], 7.01B[2], 7.01B[3]...
            n = 1
            patch_name = '{} [{}]'.format(self.patch_id, n)
            while patch_name in os.listdir(self.patch_directory):
                n += 1
                patch_name = self.patch_id + ' [{}]'.format(n)
        write_patch_to = '{}/{}'.format(self.patch_directory, patch_name)
        os.mkdir(write_patch_to)
        os.mkdir('{}/img'.format(write_patch_to))
        shutil.copyfile('patch.css', '{}/patch.css'.format(write_patch_to))
        shutil.copyfile('{}/backdrop.jpg'.format(self.media_directory), '{}/img/backdrop.jpg'.format(write_patch_to))

        # generate the HTML document
        with open('{}/index.html'.format(write_patch_to), 'w') as patchfile:

            # static data
            patchfile.write('<!DOCTYPE html>' +
                            '<head>' +
                            '<title>{}</title>'.format(self.patch_id) +
                            '<link rel="stylesheet" type="text/css" href="patch.css">' +
                            '</head>' +
                            '<body>' +
                            '<img src="http://cdn.dota2.com/apps/dota2/images/blogfiles/bg_five_heroes.jpg" id="banner"></img>' +
                            '<h1>DOTA2 {}<br>({})</h1>'.format(self.patch_id,
                                                                date.strftime(self.patch_release_date, '%d/%m/%y')))

            # general changes
            if len(self.patch_general_changes) != 0:
                patchfile.write('<div id="general" class="section">' +
                                '<h2>GENERAL</h2>')
                for general_change in self.patch_general_changes:
                    patchfile.write('<p>{}</p>'.format(general_change))
                patchfile.write('</div>')

            # item changes
            if len(self.patch_items_changed) != 0:
                patchfile.write('<div id="items" class="section">' +
                                '<h2>ITEMS</h2>')
                for item in self.patch_items_changed:
                    patchfile.write('<div class="entity">' +
                                    '<img src="img/{}.png">'.format(self._sanitise_name(item)) +
                                    '<h3>{}</h3>'.format(item))
                    for change in self.patch_item_changes[item]:
                        patchfile.write('<p>{}</p>'.format(change))
                    patchfile.write('</div>')
                patchfile.write('</div>')

            # hero changes
            if len(self.patch_heroes_changed) != 0:
                patchfile.write('<div id="heroes" class="section">' +
                                '<h2>HEROES</h2>')
                for hero in self.patch_heroes_changed:
                    patchfile.write('<div class="entity">' +
                                    '<img src="img/{}.png">'.format(self._sanitise_name(hero)) +
                                    '<h3>{}</h3>'.format(hero))
                    for change in self.patch_hero_changes[hero]:
                        patchfile.write('<p>{}</p>'.format(change))
                    patchfile.write('</div>')
                patchfile.write('</div>')

            patchfile.write('<footer>' +
                            '<p>Generated using the <a href="https://github.com/NickelOz/dota2PatchScraper">DOTA2 PATCH SCRAPER</a></p>' +
                            '</footer' +
                            '</body>')

        # shift icons for every hero and item from the main folder, or use placeholders if the icon is not available
        try:
            local_icons = os.listdir('{}/icons'.format(self.media_directory))
        except FileNotFoundError:
            local_icons = []
        for entity in (self.patch_heroes_changed + self.patch_items_changed):
            entity_filename = self._sanitise_name(entity) + ".png"
            if entity_filename in local_icons:
                shutil.copyfile('{}/icons/{}'.format(self.media_directory, entity_filename),
                                '{}/img/{}'.format(write_patch_to, entity_filename))
            else:
                shutil.copyfile('{}/default.png'.format(self.media_directory),
                                '{}/img/{}'.format(write_patch_to, entity_filename))

        # generate json with the patch details
        if generate_json:
            jsoncontents = {
                'url': self.patch_url,
                'id': self.patch_id,
                'date': self.patch_release_date.strftime('%d-%m-%Y'),
                'heroes_changed': self.patch_heroes_changed,
                'items_changed': self.patch_items_changed,
                'hero_changes': self.patch_hero_changes,
                'item_changes': self.patch_item_changes,
                'general_changes': self.patch_general_changes
            }
            jsonfile = open('{}/{}.json'.format(write_patch_to, self.patch_id), 'w')
            json.dump(jsoncontents, jsonfile, indent=2)
            jsonfile.close()

        if open_on_completion:
            webbrowser.open(os.getcwd() + '{}/index.html'.format(write_patch_to))

    def _get_patch_details(self):
        """
        requests patch details and writes these to the instance
        :return:
        """

        # get patch document and parse using lxml
        r = requests.get(self.patch_url)
        r.raise_for_status()
        document = html.fromstring(r.content)
        domain = re.findall(r"[A-z0-9\.]*\.com", self.patch_url)[0]

        # identify and read target sections (date / patch contents)
        try:
            if domain == 'www.dota2.com':
                raw_patch_date = document.find_class('entry-meta')[0].text_content().strip()
                raw_patch_contents = document.find_class('entry-content')[0].text_content().strip()
            elif domain == 'store.steampowered.com':
                raw_patch_date = document.find_class('headline')[0].find_class('date')[0].text_content().strip()
                raw_patch_contents = document.find_class('body')[0].text_content().strip()
            else:
                raise IndexError
        except IndexError:
            self.OK = False
            return None

        # identify the patch release date
        self.patch_release_date = self._extract_date(raw_patch_date)

        # split the patch contents into a title (the ID) and a changelog
        # this is usually identified by a group of '=' signs
        # regex ignores newlines, so we can also include the colon from the preceding line
        """
        PATCH ID:
        ====
        PATCH CHANGELOG
        ...
        ...
        """
        line_separator = re.findall(r":=", raw_patch_contents)[0]
        raw_id, raw_changelog = raw_patch_contents.split(line_separator)

        # set the date and parse the changelog
        self.patch_id = raw_id.upper()
        self._parse_changelog(raw_changelog)

    def _parse_changelog(self, raw_changelog):
        """
        identifies the individual changes within a patch from the changelog
        :param raw_changelog:
        :return: none
        """

        changes = raw_changelog.split('* ')[1:]

        for change in changes:

            # changes to heroes and items will have this form
            """
            ...
            HERO: CHANGE
            HERO: CHANGE 2
            ITEM: CHANGE
            ...
            """
            if ': ' in change:
                target, change_details = change.split(': ')
                change_details = change_details.strip()

                # change was applied to a hero
                if self._sanitise_name(target) in self.dota_heroes:
                    try:
                        self.patch_hero_changes[target].append(change_details)
                    except KeyError:
                        self.patch_hero_changes[target] = [change_details]
                    if len(self.patch_heroes_changed) == 0 or self.patch_heroes_changed[-1] != target:
                        self.patch_heroes_changed.append(target)

                # change was applied to an item
                elif self._sanitise_name(target) in self.dota_items:
                    try:
                        self.patch_item_changes[target].append(change_details)
                    except KeyError:
                        self.patch_item_changes[target] = [change_details]
                    if len(self.patch_items_changed) == 0 or self.patch_items_changed[-1] != target:
                        self.patch_items_changed.append(target)

                # catches any other changes
                else:
                    self.patch_general_changes.append(change)

            else:
                # general change
                self.patch_general_changes.append(change)

    def _get_missing_icons(self):
        """
        checks for missing icons in the media directory and downloads said icons
        :return: none
        """
        # set a default save location
        save_icons_to = '{}/icons'.format(self.media_directory)
        if not os.path.exists(save_icons_to):
            os.mkdir(save_icons_to)

        # read items and heroes locally
        with open('heroes.json', 'r') as herofile:
            hero_list = json.load(herofile)
        with open('items.json', 'r') as itemfile:
            item_list = json.load(itemfile)
        local_icons = os.listdir(save_icons_to)

        # some icons should be excluded, as a tuple to use an argument for inbuilt string methods
        exclude_item_prefixes = ('recipe', 'rivervial')

        # check that icons for every hero have been downloaded
        for hero in hero_list:
            hero_filename = '{}.png'.format(self._sanitise_name(hero['localized_name']))
            if hero_filename not in local_icons:
                # some heroes have a different name within the games files, we must reference by this
                # 'Necrophos' is 'Necrolyte' in the source files
                hero_ref_name = hero['name'][14:]  # strip 'npc_dota_hero_'

                # fetch item from the CDN
                download_url = '{}/heroes/{}_lg.png'.format(self._icon_url_path, hero_ref_name)
                write_file_location = '{}/{}'.format(save_icons_to, hero_filename)
                try:
                    urllib.request.urlretrieve(download_url, write_file_location)
                except urllib.request.HTTPError:
                    pass

        # check that icons for every item have been downloaded, excluding some specific icons
        for item in item_list:
            item_filename = '{}.png'.format(self._sanitise_name(item['localized_name']))
            if item_filename not in local_icons and not item_filename.startswith(exclude_item_prefixes):
                item_ref_name = item['name'][5:]  # strip 'item_'

                # fetch item from the CDN
                download_url = '{}/items/{}_lg.png'.format(self._icon_url_path, item_ref_name)
                write_file_location = '{}/{}'.format(save_icons_to, item_filename)
                try:
                    urllib.request.urlretrieve(download_url, write_file_location)
                except urllib.request.HTTPError:
                    pass

    def _update_hero_data(self):
        """
        attempts to get updated hero data from the Steam API, otherwise default to the local files
        :return: none
        """
        assert self.api_key != ''
        try:
            r = requests.get(url='http://api.steampowered.com/IEconDOTA2_570/GetHeroes/v1/',
                             params={'key': self.api_key, 'language': 'en'})
            r.raise_for_status()
            heroes = []
            for hero in r.json()['result']['heroes']:
                hero['sanitised_name'] = self._sanitise_name(hero['localized_name'])
                heroes.append(hero)
            with open('heroes.json', 'w') as herofile:
                json.dump(heroes, herofile, indent=2)
        except requests.HTTPError:
            pass

    def _update_item_data(self):
        """
        attempts to get updated item data from the Steam API, otherwise default to the local files
        :return: none
        """
        assert self.api_key != ''
        try:
            r = requests.get(url='http://api.steampowered.com/IEconDOTA2_570/GetGameItems/V001/',
                             params={'key': self.api_key, 'language': 'en'})
            r.raise_for_status()
            items = []
            for item in r.json()['result']['items']:
                item['sanitised_name'] = self._sanitise_name(item['localized_name'])
                items.append(item)
            with open('items.json', 'w') as itemfile:
                json.dump(items, itemfile, indent=2)
        except requests.HTTPError:
            pass

    def _extract_date(self, raw_date):
        """
        identifies a date within a string and returns it as a date object
        NOTE - currently defaults to the present date if no date can be identifed
        :param raw_date: a string believed to contain a date
        :return: a date object
        """
        # m = re.match(r"([0-9]+)[ .,/-]*([A-Za-z]+)[ .,/-]*([0-9]+)", raw_date)
        # if m:
        #     # month may be in long or shortened form ('Dec' V 'December')
        #     if len(m[2]) == 3:
        #         return date.strptime('{}-{}-{}'.format(m[1], m[2], m[3]), '%d-%b-%Y')
        #     else:
        #         return date.strptime('{}-{}-{}'.format(m[1], m[2], m[3]), '%d-%B-%Y')
        # else:
        #     return date.today()
        return date.today()

    def _sanitise_name(self, raw_name):
        """
        converts a name into a more general form to make comparision easier by removing illegal characters
        :param raw_name: the original name
        :return: the name with offending characters removed
        """
        name = ''
        illegal_chars = [' ', '\'', ':', '-']
        for char in raw_name.lower():
            if char not in illegal_chars:
                name += char
        return name

def main(arguments):
    if arguments:
        patch_url = arguments[0]
    else:
        patch_url = input("Enter patch post URL > ")
    mypatch = DOTAPatch(patch_url)
    mypatch.generate_patch()

if __name__ == '__main__':
    main(sys.argv[1:])