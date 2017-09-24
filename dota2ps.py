import os, sys, shutil
import re
from datetime import datetime
import requests
import urllib.request
from lxml import html
import webbrowser
import json


# TODO: add sys arg capability
# TODO: documentation for localised name
# TODO: can sometimes throw an error if the blog post is not served with the page
# TODO: empty lines in patch
# TODO: consider items with multiple levels - dagon, necrobook, BoTs
# TODO: output patch as json
# TODO: compatability with updates via steamcomunity.com
# TODO: regex for date recognition
# TODO: disable writing for unprepared patches
# TODO: general notes on naming conventions
# TODO: better control of public/private  methods
# TODO: provide README documentation
# TODO: limit item downloads for recipes/river vials


class DOTAPatch:

    def __init__(self, post_url, steam_api_key=None, save_media_to = 'media', write_patches_to='patches'):

        self.url = post_url
        self.api_key = steam_api_key
        self.id = None
        self.release_date = None
        self.changelog = None
        self.media_directory = save_media_to
        self.patch_directory = write_patches_to
        self._icon_url_path = 'http://cdn.dota2.com/apps/dota2/images'

        # verify the icons save directory, or use a default
        if os.access(self.media_directory, os.W_OK) != True:
            self._log_error(Exception("The directory to save media to, '{}', does not have write permissions or does not exist"))
            self.media_directory = 'media'
        if 'icons' not in os.listdir(self.media_directory):
            os.mkdir('{}/{}'.format(self.media_directory, 'icons'))

        # verify the patch writing directory
        if os.access(self.patch_directory, os.W_OK) != True:
            self._log_error(Exception("The directory to write patches to, '{}', does not have write permissions or does not exist"))
            self.patch_directory = 'patches'
            if 'patches' not in os.listdir():
                os.mkdir('patches')

        # read blog post and fetch details
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

        # find target sections (date and contents
        try:
            raw_post_date = document.find_class('entry-meta')[0].text_content().strip()
        except IndexError:
            self._log_error(IndexError("Could not access date within post document"))
            return None

        try:
            raw_post_content = document.find_class('entry-content')[0].text_content().strip()
        except IndexError:
            self._log_error(IndexError("Could not access patch details within post document"))
            return None

        # determine the post date as a datetime object
        self.release_date = datetime.strptime(raw_post_date, '%B %d, %Y - Valve')

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

        # update the list of heroes and items if a Steam API key is given, and generate the changelog object
        if self.api_key is not None:
            self._get_hero_and_item_records()
        self.changelog = DOTAChangelog(raw_changelog, self._sanitise_name)

    def _get_hero_and_item_records(self):
        """
        attempts to get updated hero and item data from the Steam API, otherwise default to the local files
        :return: none
        """
        if self.api_key is None:
            return None

        # get heroes
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
            self._log_error(err)

        # get items
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
            self._log_error(err)

    def generate_page(self, check_for_icons=False, open_on_completion=False):
        """
        writes the patch notes to a new folder within the specified directory
        :param write_destination: local destination to write patch contents to
        :param open_on_completion: open the HTML file when the page is generated, useful for testing
        :return: none
        """

        # cannot generate changelog if it was unable to be parsed
        if self.changelog is None:
            self._log_error(Exception("Cannot write patch, scrape failed"))
            return None

        # download hero icons, unless the user preferences otherwise
        if check_for_icons:
            self.get_icons()

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
        shutil.copyfile('media/backdrop.jpg', '{}/img/backdrop.jpg'.format(write_patch_to))

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
                            '<h1>DOTA2 {}</h1>\n'.format(self.id))

            # if there are any general notes in the patch
            if self.changelog.check_general_changes():
                patchfile.write('<div id="general" class="section">\n' +
                                '<h2>GENERAL</h2>\n')
                for general_change in self.changelog['general']:
                    patchfile.write('<p>{}</p>\n'.format(general_change))
                patchfile.write('</div>\n')

            # changes to items
            if self.changelog.check_item_changes():
                patchfile.write('<div id="items" class="section">\n' +
                                '<h2>ITEMS</h2>\n')

                # list buffs to target item
                for item in self.changelog.items_changed:
                    patchfile.write('<div class="entity">\n' +
                                    '<img src="img/{}.png">\n'.format(self._sanitise_name(item)) +
                                    '<h3>{}</h3>\n'.format(item))
                    for change in self.changelog[item]:
                        patchfile.write('<p>{}</p>\n'.format(change))
                    patchfile.write('</div>\n')
                patchfile.write("</div>\n")

            # changes to heroes
            if self.changelog.check_hero_changes():
                patchfile.write('<div id="heroes" class="section">\n' +
                                '<h2>HEROES</h2>\n')

                # list buffs to target hero
                for hero in self.changelog.heroes_changed:
                    patchfile.write('<div class="entity">\n' +
                                    '<img src="img/{}.png">\n'.format(self._sanitise_name(hero)) +
                                    '<h3>{}</h3>\n'.format(hero))
                    for change in self.changelog[hero]:
                        patchfile.write('<p>{}</p>\n'.format(change))
                    patchfile.write('</div>\n')
                patchfile.write("</div>\n")
            patchfile.write('</body>\n')

        # shift icons for every hero and item from the main folder, or use placeholders
        local_icons = os.listdir('{}/icons'.format(self.media_directory))
        for entity in (self.changelog.heroes_changed + self.changelog.items_changed):
            entity_filename = self._sanitise_name(entity) + ".png"
            if entity_filename in local_icons:
                shutil.copyfile('{}/icons/{}'.format(self.media_directory, entity_filename), '{}/img/{}'.format(write_patch_to, entity_filename))
            else:
                shutil.copyfile('{}/default.png'.format(self.media_directory), '{}/img/{}'.format(self.media_directory, entity_filename))

        if open_on_completion:
            webbrowser.open(os.getcwd() + '/{}/index.html'.format(write_patch_to))

    def get_icons(self, save_icons_to=None):
        """
        determines whether any icons need to be downloaded by reading and comparing the current icon list with the lists
        in heroes.json and items.json
        :param save_icons_to: The parent directory for icons
        :return: none
        """

        # set a default save location
        if save_icons_to is None:
            save_icons_to = '{}/icons'.format(self.media_directory)

        # read items and heroes locally
        hero_list = json.load(open('heroes.json', 'r'))
        item_list = json.load(open('items.json', 'r'))
        local_icons = os.listdir(save_icons_to)

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
                    self._log_error(Exception('Could not save icon of {} / {}'.format(hero['localized_name'], hero['name'])))

        for item in item_list:
            item_filename = '{}.png'.format(self._sanitise_name(item['localized_name']))

            if item_filename not in local_icons:
                item_ref_name = item['name'][5:]  # strip 'item_'

                # fetch item from the CDN
                download_url = '{}/items/{}_lg.png'.format(self._icon_url_path, item_ref_name)
                write_file_location = '{}/{}'.format(save_icons_to, item_filename)
                try:
                    urllib.request.urlretrieve(download_url, write_file_location)
                except urllib.request.HTTPError:
                    self._log_error(Exception('Could not save icon of {} / {}'.format(item['localized_name'], item['name'])))

    def _log_error(self, err):
        # logs internal errors
        if 'errors.txt' not in os.listdir():
            error_log_file = open('errors.txt', 'w')
        else:
            error_log_file = open('errors.txt', 'a')
        error_log_file.write('[{}] {}\n'.format(datetime.now().strftime('%d %b %Y %H:%I'), err))
        error_log_file.close()

    def _sanitise_name(self, raw_name):
        # converts names into a more general form to make comparison easier
        name = ""
        illegal_chars = [' ', '\'', ':', '-']

        for char in raw_name.lower():
            if char not in illegal_chars:
                name += char

        return name


class DOTAChangelog:

    def __init__(self, changelog_raw, sanitise_name_FN):
        self.heroes_changed = []
        self.items_changed = []
        self.targeted_changes = {}
        self._sanitise_name = sanitise_name_FN

        self.hero_list = []
        with open('heroes.json', 'r') as herofile:
            heroes = json.load(herofile)
            for hero in heroes:
                self.hero_list.append(hero['sanitised_name'])

        self.item_list = []
        with open('items.json', 'r') as itemfile:
            items = json.load(itemfile)
            for item in items:
                self.item_list.append(item['sanitised_name'])

        self.parse_changelog(changelog_raw)

        # sort the lists of changed heroes and items, as well as removing duplicates
        # this ensures that the patch notes are ordered alphabetically when iterated over
        self._sort(self.heroes_changed)
        i = len(self.heroes_changed) - 1
        while i >= 1:
            if self.heroes_changed[i] == self.heroes_changed[i - 1]:
                self.heroes_changed.remove(self.heroes_changed[i])
            i -= 1
        self._sort(self.items_changed)
        i = len(self.items_changed) - 1
        while i >= 1:
            if self.items_changed[i] == self.items_changed[i - 1]:

                self.items_changed.remove(self.items_changed[i])
            i -= 1

    def __getitem__(self, item):
        return self.targeted_changes[self._sanitise_name(item)]

    def parse_changelog(self, changelog_raw):

        #divide patch notes into individual changes
        changes = changelog_raw.split('* ')[1:]
        for change in changes:

            # if the change is target at a hero/item
            """
            * HERO_NAME: CHANGE MADE
            """
            if ':' in change:
                target, change_details = change.split(':')
                change_details = change_details.strip()
                if self._sanitise_name(target) in self.hero_list:
                    self.heroes_changed.append(target)
                    self._add_change(target, change_details)
                elif self._sanitise_name(target) in self.item_list:
                    self.items_changed.append(target)
                    self._add_change(target, change_details)
                else:
                    self._add_change('general', change)

            # general changelog to catch any other changes
            else:
                self._add_change('general', change)

    def _add_change(self, target, change_details):
        try:
            self.targeted_changes[self._sanitise_name(target)].append(change_details)
        except KeyError:
            self.targeted_changes[self._sanitise_name(target)] = [change_details]

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

    def check_general_changes(self):
        return 'general' in self.targeted_changes.keys()

    def check_hero_changes(self):
        return len(self.heroes_changed) > 0

    def check_item_changes(self):
        return len(self.items_changed) > 0


if __name__ == '__main__':
    mypatch = DOTAPatch(input("Enter patch post URL > "))
    mypatch.generate_page(check_for_icons=True, open_on_completion=True)
