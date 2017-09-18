import os, sys, shutil
import re
from collections import OrderedDict
from datetime import datetime
import requests
import urllib.request
from lxml import html
import webbrowser


# TODO: differentiate between hero and item nerfs
# TODO: add sys arg capability
# TODO: error handling
# TODO: documentation for localised name
# TODO: error in reading page (indexerrror)
# TODO: can sometimes throw an error if the blog post is not served with the page
# TODO: empty lines in patch
# TODO: consider items with multiple levels - dagon, necrobook, BoTs
# TODO: output as json
# TODO: compatability with updates via steamcomunity.com
# TODO: check directories


class D2Patch:


    def __init__(self, post_url, steam_api_key=None):

        # tied to state
        self.url = post_url
        self.api_key = steam_api_key

        # # uninitialised
        self.id = None
        self.date = None
        self.changelog = {'general': [],
                          'heroes/items': OrderedDict()}

        # private
        self._icon_url_path = 'http://cdn.dota2.com/apps/dota2/images'

        # read blog post and fetch details
        patch = self._get_patch_details(post_url)
        self.release_date = patch['date']
        self.id = patch['id']
        self.changelog = patch['changelog']


    def _get_patch_details(self, post_url):

        # get post document and parse into lxml
        r = requests.Session().get(post_url)
        if r.status_code != 200:
            raise Exception('Received response {} when trying to access post at "{}"'.format(r.status_code, post_url))
        document = html.fromstring(r.content)

        # parse post content
        raw_post_date = document.find_class('entry-meta')[0].text_content().strip()
        raw_post_content = document.find_class('entry-content')[0].text_content().strip()

        # generate the response object
        patch_details = {'date': None, 'id': None, 'changelog': None}

        # set the post date
        patch_details['date'] = datetime.strptime(raw_post_date, '%B %d, %Y - Valve')

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
        patch_details['id'] = raw_id.upper()

        # pass the raw_changelog off to a handler function
        patch_details['changelog'] = self._parse_changelog(raw_changelog)

        return patch_details


    def _parse_changelog(self, raw_changelog):
        changelog = {'general': [],
                     'heroes/items': OrderedDict()}
        changes = raw_changelog.split('* ')[1:]
        for change in changes:
            if ': ' in change:
                hero, buff = change.split(': ')

                # hero has had previous buffs
                if hero in changelog['heroes/items'].keys():
                    changelog['heroes/items'][hero].append(buff)

                # new hero
                else:
                    changelog['heroes/items'][hero] = [buff]

            else:
                changelog['general'].append(change)
        return changelog


    def generate_page(self, write_directory='patches', open_on_completion=False):

        # initialise a directory for the patch
        if self.id not in os.listdir(write_directory):
            directory_name = self.id
        else:
            n = 1
            directory_name = self.id + ' [{}]'.format(n)
            while directory_name in os.listdir(write_directory):
                n += 1
                directory_name = self.id + ' [{}]'.format(n)

        write_to = '{}/{}'.format(write_directory, directory_name)

        # generate directory for patch
        os.mkdir(write_to)
        os.mkdir('{}/img'.format(write_to))

        # copy the CSS file and default image files
        shutil.copyfile('patch.css', '{}/patch.css'.format(write_to))
        shutil.copyfile('media/backdrop.jpg', '{}/img/backdrop.jpg'.format(write_to))

        # generate the HTML document
        with open('{}/index.html'.format(write_to), 'w') as patchfile:
            patchfile.write('<!DOCTYPE html>\n' +
                            '<head>\n' +
                            '<title>{}</title>\n'.format(self.id) +
                            '<link rel="stylesheet" type="text/css" href="patch.css">\n' +
                            '</head>\n' +
                            '<body>\n' +
                            '<img src="http://cdn.dota2.com/apps/dota2/images/blogfiles/bg_five_heroes.jpg" id="banner"></img>\n' +
                            '<h1>PATCH {}</h1>\n'.format(self.id))

            # if there are general notes in the patch
            if len(self.changelog['general']) > 0:
                patchfile.write('<div id="general" class="section">\n' +
                                '<h2>GENERAL</h2>\n')
                for general_change in self.changelog['general']:
                    patchfile.write('<p>{}</p>\n'.format(general_change))
                patchfile.write('</div>\n')

            # individual hero buffs and nerfs
            if len(self.changelog['heroes/items']) > 0:
                patchfile.write('<div id="heroes" class="section">\n' +
                                '<h2>HEROES / ITEMS</h2>\n')

                # list buffs to target hero
                for hero in self.changelog['heroes/items']:
                    hero_base_name = hero.lower()
                    hero_base_name = hero_base_name.replace('\'', '')
                    hero_base_name = hero_base_name.replace(' ', '')
                    patchfile.write('<div class="hero">\n' +
                                    '<img src="img/{}.png">\n'.format(hero_base_name) +
                                    '<h3>{}</h3>\n'.format(hero))
                    for change in self.changelog['heroes/items'][hero]:
                        patchfile.write('<p>{}</p>\n'.format(change))
                    patchfile.write('</div>\n')

                    # transfer icons from main folder, or use a placeholder
                    if '{}.png'.format(hero_base_name) in os.listdir('media/icons'):
                        shutil.copyfile('media/icons/{}.png'.format(hero_base_name), '{}/img/{}.png'.format(write_to, hero_base_name))
                    else:
                        shutil.copyfile('media/default.png', '{}/img/{}.png'.format(write_to, hero_base_name))

            patchfile.write('</body>\n')

        if open_on_completion:
            webbrowser.open(os.getcwd() + '/{}/index.html'.format(write_to))


    def get_hero_icons(self, write_to='media/icons'):

        if self.api_key is None:
            raise Exception("No Steam API Key has been provided")

        # get a list of heroes from the Steam API, including the localised (current in-game) name
        r = requests.get('http://api.steampowered.com/IEconDOTA2_570/GetHeroes/v1/',
                         params={'key': self.api_key, 'language': 'en'})

        if r.status_code == 200:
            hero_list = r.json()['result']['heroes']
            failed = []

            for hero in hero_list:
                hero_ref_name = hero['name'][14:]
                hero_local_name = hero['localized_name']
                hero_local_name = hero_local_name.lower()
                hero_local_name = hero_local_name.replace('\'', '')
                hero_local_name = hero_local_name.replace(':', '')
                hero_local_name = hero_local_name.replace(' ', '')

                download_url = '{}/heroes/{}_lg.png'.format(self._icon_url_path, hero_ref_name)
                write_file_location = '{}/{}.png'.format(write_to, hero_local_name)
                try:
                    if '{}.png'.format(hero_local_name) not in os.listdir(write_to):
                        print('dl', hero_ref_name)
                        urllib.request.urlretrieve(download_url, write_file_location)
                except urllib.request.HTTPError:
                    failed.append((hero['localized_name'], hero['name']))

            return failed
        elif r.status_code == 403:
            raise Exception("Could not access the Steam API: API Key was not accepted")
        else:
            raise Exception("Could not access the Steam API")


    def get_item_icons(self, write_to='media/icons'):
        """
        pings the Steam API for a list of items
        :return:
        """

        if self.api_key is None:
            raise Exception("No Steam API Key has been provided")

        r = requests.get('http://api.steampowered.com/IEconDOTA2_570/GetGameItems/V001/',
                         params={'key': self.api_key, 'language': 'en'})

        if r.status_code == 200:
            items = r.json()['result']['items']
            failed = []
            ignore_flags = ['recipe', 'river']
            for item in items:
                item_ref_name = item['name'][5:]
                item_ref_name = item_ref_name.replace(':', '_')
                flagged = (item_ref_name.split('_')[0] in ignore_flags)
                item_local_name = item['localized_name']
                item_local_name = item_local_name.lower()
                item_local_name = item_local_name.replace('\'', '')
                item_local_name = item_local_name.replace(' ', '')

                download_url = '{}/items/{}_lg.png'.format(self._icon_url_path, item_ref_name)
                write_file_location = '{}/{}.png'.format(write_to, item_local_name)

                try:
                    if '{}.png'.format(item_local_name) not in os.listdir(write_to) and not flagged:
                        print('dl', item_ref_name)
                        urllib.request.urlretrieve(download_url, write_file_location)
                except urllib.request.HTTPError:
                    failed.append(item_local_name)

            return failed
        elif r.status_code == 403:
            raise Exception("Could not access the Steam API: API Key not accepted")
        else:
            raise Exception("Could not access the Steam API: Invalid")


    def _log_error(self, err):
        if 'errors.txt' not in os.listdir():
            error_log_file = open('errors.txt', 'w')
        else:
            error_log_file = open('errors.txt', 'a')
        error_log_file.write('[{}] {}\n'.format(datetime.now().strftime('%d %b %Y %H:%I'), err))
        error_log_file.close()


if __name__ == '__main__':
    mypatch = D2Patch(input("Enter patch post URL > "), steam_api_key=input("Enter Steam API Key > "))
    mypatch.get_item_icons()
    mypatch.get_hero_icons()
    mypatch.generate_page(open_on_completion=True)
