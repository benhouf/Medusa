# coding=utf-8
# Author: Nick Sologoub
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re
import traceback

from requests.compat import urljoin
from requests.compat import quote
from requests.utils import dict_from_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class PretomeProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """Pretome Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'Pretome')

        # Credentials
        self.username = None
        self.password = None
        self.pin = None

        # URLs
        self.url = 'https://pretome.info'
        self.urls = {
            'base_url': self.url,
            'login': urljoin(self.url, 'takelogin.php'),
            'search': urljoin(self.url, 'browse.php?search=%s%s'),
            'download': urljoin(self.url, 'download.php/%s/%s.torrent'),
            'detail': urljoin(self.url, 'details.php?id=%s'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Miscellaneous Options
        self.categories = '&st=1&cat%5B%5D=7'

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        Search a provider and parse the results

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_url = self.urls['search'] % (quote(search_string), self.categories)
                response = self.get_url(search_url, returns='response')
                if not response or not response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                results += self.parse(response.text, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """

        items = []

        with BS4Parser(data, 'html5lib') as html:
            # Continue only if one Release is found
            empty = html.find('h2', text='No .torrents fit this filter criteria')
            if empty:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            torrent_table = html.find('table', attrs={'style': 'border: none; width: 100%;'})
            if not torrent_table:
                logger.log('Could not find table of torrents', logger.ERROR)
                return items

            torrent_rows = torrent_table('tr', attrs={'class': 'browse'})

            for row in torrent_rows:
                cells = row('td')
                try:
                    size = None
                    link = cells[1].find('a', attrs={'style': 'font-size: 1.25em; font-weight: bold;'})

                    torrent_id = link['href'].replace('details.php?id=', '')

                    if link.get('title', ''):
                        title = link['title']
                    else:
                        title = link.contents[0]

                    download_url = self.urls['download'] % (torrent_id, link.contents[0])
                    if not all([title, download_url]):
                        continue

                    seeders = int(cells[9].contents[0])
                    leechers = int(cells[10].contents[0])

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    # Need size for failed downloads handling
                    if size is None:
                        torrent_size = cells[7].text
                        size = convert_size(torrent_size) or -1

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': None,
                        'hash': None,
                    }
                    if mode != 'RSS':
                        logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                   (title, seeders, leechers), logger.DEBUG)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    logger.log('Failed parsing provider. Traceback: {0!r}'.format
                               (traceback.format_exc()), logger.ERROR)

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'login_pin': self.pin,
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Username or password incorrect', response.text):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password or not self.pin:
            logger.log('Invalid username or password or pin. Check your settings', logger.WARNING)

        return True


provider = PretomeProvider()