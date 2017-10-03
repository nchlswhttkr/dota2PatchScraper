import os, sys, shutil
import re
from datetime import datetime
import requests
import urllib.request
from lxml import html
import webbrowser
import json


# TODO: documentation for localised name
# TODO: consider items with multiple levels - dagon, necrobook, BoTs
# TODO: compatability with updates via steamcomunity.com
# TODO: disable writing for unprepared/failed patches
# TODO: provide README documentation


class DOTAPatch:

    def __init__(self, post_url, steam_api_key=None, write_patches_to='patches'):

        self.success = True
        self.url = post_url
        self.api_key = steam_api_key
        self.id = None
        self.release_date = None
        self.all_heroes = []
        self.all_items = []
        self.changed_heroes = []
        self.changed_items = []
        self._changes = {}
        self._general_changes = []

        self.media_directory = 'media'
        self.patch_directory = write_patches_to
        self._icon_url_path = 'http://cdn.dota2.com/apps/dota2/images'

        # verify the directory to save patches to is valid and has write permissions
        if not os.path.exists(self.patch_directory):
            raise FileNotFoundError('The directory to save patches to does not exist')
        if not os.access(self.patch_directory, os.W_OK):
            raise PermissionError('The directory to save patches to does not have write permissions')

        # maintain a list of all heroes and items, try and update using Steam API
        if self.api_key is not None:
            self._get_hero_records()
            self._get_item_records()
        with open('heroes.json', 'r') as herofile:
            heroes = json.load(herofile)
            for hero in heroes:
                self.all_heroes.append(hero['sanitised_name'])
        with open('items.json', 'r') as itemfile:
            items = json.load(itemfile)
            for item in items:
                self.all_items.append(item['sanitised_name'])

        # read patch post and fetch details
        self._get_patch_details(post_url)

    def _get_patch_details(self, post_url):
        """
        requests patch details from url and searches for the target sections (date, contents)
        :param post_url: URL of post, including protocol
        :return: none
        :raises IndexError: the target section/s could not be found
        :raises Exception: if a connection could not be established with the given url (http status =/= 200)
        """

        # get post document and parse into lxml
        r = requests.get(post_url)
        if r.status_code != 200:
            raise Exception('Received response {} when trying to access post at "{}"'.format(r.status_code, post_url))
        document = html.fromstring(r.content)

        # find target sections (date and contents)
        try:
            raw_post_date = document.find_class('entry-meta')[0].text_content().strip()
            raw_post_content = document.find_class('entry-content')[0].text_content().strip()
        except IndexError:
            self.success = False
            return None

        # determine the post date as a datetime object
        self.release_date = self._extract_date(raw_post_date)

        # split the post contents by a line separator to get ID and changelog
        # this line separator is usually a series of equal '=' signs
        """
        patch_details ID
        ======
        * HERO: CHANGE
        * HERO2: CHANGE
        """
        line_separator = re.findall(':=+', raw_post_content)[0]
        raw_id, raw_changelog = raw_post_content.split(line_separator)

        # set the post id
        self.id = raw_id.upper()

        self.parse_changelog(raw_changelog)

    def _extract_date(self, raw_date):
        """
        extracts a datetime object from a string, or returns the current time if no date can be found
        :param raw_date: the string containing the date
        :return: a datetime object
        """
        #TODO: edge cases - american date format and numeric months
        m = re.match(r"([0-9]+)[ .,/-]*([A-Za-z]+)[ .,/-]*([0-9]+)", raw_date)
        if m:
            # handles shortened months ('Dec' V 'December')
            if len(m[2]) == 3:
                return datetime.strptime('{}-{}-{}'.format(m[1], m[2], m[3]), '%d-%b-%Y')
            else:
                return datetime.strptime('{}-{}-{}'.format(m[1], m[2], m[3]), '%d-%B-%Y')
        else:
            return datetime.today()

    def _get_hero_records(self):
        """
        attempts to get updated hero data from the Steam API, otherwise default to the local files
        :return: none
        """
        if self.api_key is None:
            return None

        try:
            r = requests.get(url='http://api.steampowered.com/IEconDOTA2_570/GetHeroes/v1/',
                             params={'key': self.api_key, 'language':'en'})
            r.raise_for_status()
            hero_list = []
            for hero in r.json()['result']['heroes']:
                hero['sanitised_name'] = self._sanitise_name(hero['localized_name'])
                hero_list.append(hero)
            with open('heroes.json', 'w') as outfile:
                json.dump(hero_list, outfile, indent=2)
        except requests.HTTPError as err:
            pass

    def _get_item_records(self):
        """
        attempts to get updated item data from the Steam API, otherwise default to the local files
        :return: none
        """
        if self.api_key is None:
            return None

        try:
            r = requests.get(url='http://api.steampowered.com/IEconDOTA2_570/GetGameItems/V001/',
                             params={'key':self.api_key, 'language':'en'})
            r.raise_for_status()
            item_list = []
            for item in r.json()['result']['items']:
                item['sanitised_name'] = self._sanitise_name(item['localized_name'])
                item_list.append(item)
            with open('items.json', 'w') as outfile:
                json.dump(item_list, outfile, indent=2)
        except requests.HTTPError as err:
            pass

    def generate_patch(self, check_for_icons=False, open_on_completion=False, generate_json=False):
        """
        writes the patch notes to a new folder within the specified directory
        :param check_for_icons: determines whether missing icons should be downloaded
        :param open_on_completion: open the HTML file when the page is generated, useful for testing
        :return: none
        """

        # cannot generate changelog if it was unable to be parsed
        if not self.success:
            raise Exception('Could not generate page, patch is not ready to write')

        # download hero icons, unless the user preferences otherwise
        if check_for_icons:
            self._get_icons()

        # initialise a NEW directory that does not overwrite existing folders
        if self.id not in os.listdir(self.patch_directory):
            patch_name = self.id
        else:
            # 7.01B [1], 7.01B[2], 7.01B[3]...
            n = 1
            patch_name = '{} [{}]'.format(self.id, n)
            while patch_name in os.listdir(self.patch_directory):
                n += 1
                patch_name = self.id + ' [{}]'.format(n)

        write_patch_to = '{}/{}'.format(self.patch_directory, patch_name)

        # generate directory for patch and copy default images files
        os.mkdir(write_patch_to)
        os.mkdir('{}/img'.format(write_patch_to))
        shutil.copyfile('patch.css', '{}/patch.css'.format(write_patch_to))
        shutil.copyfile('{}/backdrop.jpg'.format(self.media_directory), '{}/img/backdrop.jpg'.format(write_patch_to))

        # generate the HTML document
        with open('{}/index.html'.format(write_patch_to), 'w') as patchfile:

            # page metadata
            patchfile.write('<!DOCTYPE html>\n' +
                            '<head>\n' +
                            '<title>{}</title>\n'.format(self.id) +
                            '<link rel="stylesheet" type="text/css" href="patch.css">\n' +
                            '</head>\n' +
                            '<body>\n' +
                            '<img src="http://cdn.dota2.com/apps/dota2/images/blogfiles/bg_five_heroes.jpg" id="banner"></img>\n' +
                            '<h1>DOTA2  {}  ({})</h1>\n'.format(self.id, datetime.strftime(self.release_date, '%d/%m/%y')))

            # if there are any general notes in the patch
            if self._check_general_changes():
                patchfile.write('<div id="general" class="section">\n' +
                                '<h2>GENERAL</h2>\n')
                for general_change in self._general_changes:
                    patchfile.write('<p>{}</p>\n'.format(general_change))
                patchfile.write('</div>\n')

            # changes to items
            if self._check_item_changes():
                patchfile.write('<div id="items" class="section">\n' +
                                '<h2>ITEMS</h2>\n')

                # list buffs to target item
                for item in self.changed_items:
                    patchfile.write('<div class="entity">\n' +
                                    '<img src="img/{}.png">\n'.format(self._sanitise_name(item)) +
                                    '<h3>{}</h3>\n'.format(item))
                    for change in self.get_changes(item):
                        patchfile.write('<p>{}</p>\n'.format(change))
                    patchfile.write('</div>\n')
                patchfile.write("</div>\n")

            # changes to heroes
            if self._check_hero_changes():
                patchfile.write('<div id="heroes" class="section">\n' +
                                '<h2>HEROES</h2>\n')

                # list buffs to target hero
                for hero in self.changed_heroes:
                    patchfile.write('<div class="entity">\n' +
                                    '<img src="img/{}.png">\n'.format(self._sanitise_name(hero)) +
                                    '<h3>{}</h3>\n'.format(hero))
                    for change in self.get_changes(hero):
                        patchfile.write('<p>{}</p>\n'.format(change))
                    patchfile.write('</div>\n')
                patchfile.write("</div>\n")
            patchfile.write('</body>\n')

        # shift icons for every hero and item from the main folder, or use placeholders
        local_icons = os.listdir('{}/icons'.format(self.media_directory))
        for entity in (self.changed_heroes + self.changed_items):
            entity_filename = self._sanitise_name(entity) + ".png"
            if entity_filename in local_icons:
                shutil.copyfile('{}/icons/{}'.format(self.media_directory, entity_filename), '{}/img/{}'.format(write_patch_to, entity_filename))
            else:
                shutil.copyfile('{}/default.png'.format(self.media_directory), '{}/img/{}'.format(self.media_directory, entity_filename))

        # generate and write a json with the patches details if requests
        if generate_json:
            jsoncontents = {
                'url': self.url,
                'id': self.id,
                'date': self.release_date.strftime('%d-%m-%Y'),
                'changed_heroes': self.changed_heroes,
                'changed_items': self.changed_items,
                'general_changes': self._general_changes,
                'hero_changes': self.get_hero_changes(),
                'item_changes': self.get_item_changes()
            }

            jsonfile = open('{}/{}.json'.format(write_patch_to, self.id), 'w')
            json.dump(jsoncontents, jsonfile, indent=2)
            jsonfile.close()

        if open_on_completion:
            webbrowser.open(os.getcwd() + '{}/index.html'.format(write_patch_to))

    def _get_icons(self):
        """
        determines whether any icons need to be downloaded by reading and comparing the current icon list with the lists
        in heroes.json and items.json
        :return: none
        """

        # set a default save location
        save_icons_to = '{}/icons'.format(self.media_directory)

        # read items and heroes locally
        hero_list = json.load(open('heroes.json', 'r'))
        item_list = json.load(open('items.json', 'r'))
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

    def _sanitise_name(self, raw_name):
        # converts names into a more general form to make comparison easier
        name = ""
        illegal_chars = [' ', '\'', ':', '-']

        for char in raw_name.lower():
            if char not in illegal_chars:
                name += char

        return name

    def get_changes(self, raw_entity_name):
        entity_name = self._sanitise_name(raw_entity_name)
        return self._changes[entity_name]

    def parse_changelog(self, raw_changelog):

        # divide patch notes into individual changes
        changes = raw_changelog.split('* ')[1:]

        for change in changes:

            # if the change is target at a hero/item
            """
            * HERO_NAME: CHANGE MADE
            """
            if ':' in change:
                target, change_details = change.split(':')
                change_details = change_details.strip()
                if self._sanitise_name(target) in self.all_heroes:
                    self.changed_heroes.append(target)
                    self._add_change(target, change_details)
                elif self._sanitise_name(target) in self.all_items:
                    self.changed_items.append(target)
                    self._add_change(target, change_details)
                else:
                    self._general_changes.append(change)
            # general changelog to catch any other changes
            else:
                self._general_changes.append(change)

        # sort the lists of changed heroes and items, as well as removing duplicates
        # this ensures that the patch notes are ordered alphabetically when iterated over
        self._sort(self.changed_heroes)
        i = len(self.changed_heroes) - 1
        while i >= 1:
            if self.changed_heroes[i] == self.changed_heroes[i - 1]:
                self.changed_heroes.remove(self.changed_heroes[i])
            i -= 1
        self._sort(self.changed_items)
        i = len(self.changed_items) - 1
        while i >= 1:
            if self.changed_items[i] == self.changed_items[i - 1]:
                self.changed_items.remove(self.changed_items[i])
            i -= 1

    def _add_change(self, target, change_details):
        try:
            self._changes[self._sanitise_name(target)].append(change_details)
        except KeyError:
            self._changes[self._sanitise_name(target)] = [change_details]

    def _sort(self, L, start=0, end=None):
        # in place quicksort
        if end is None:
            end = len(L) - 1

        if end < start:
            return None

        pivot = L[start]
        low = start + 1
        high = end
        while high >= low:
            if pivot >= L[low]:
                low += 1
            else:
                L[low], L[high] = L[high], L[low]
                high -= 1
        L[start], L[high] = L[high], L[start]
        self._sort(L, start, high - 1)
        self._sort(L, high + 1, end)

    def _check_general_changes(self):
        return len(self._general_changes) != 0

    def _check_hero_changes(self):
        return len(self.changed_heroes) != 0

    def _check_item_changes(self):
        return len(self.changed_items) != 0

    def get_hero_changes(self):
        """
        generates a dictionary of changed heroes, listing all of their changes
        """
        hero_changes = {}
        for hero in self.changed_heroes:
            hero_changes[hero] = self._changes[self._sanitise_name(hero)]
        return hero_changes

    def get_item_changes(self):
        """
        generates a dictionary of changed items, listing all of their changes
        """
        item_changes = {}
        for item in self.changed_items:
            item_changes[item] = self._changes[self._sanitise_name(item)]
        return item_changes


def main(arguments):
    if arguments:
        patch_url = arguments[0]
    else:
        patch_url = input("Enter patch post URL > ")
    mypatch = DOTAPatch(patch_url)
    mypatch.generate_patch(generate_json=True)


if __name__ == '__main__':
    main(sys.argv[1:])
