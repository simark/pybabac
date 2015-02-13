import mechanicalsoup as ms
import bos
import sys
import re
import configparser
import time
import shelve

PYBABAC_CONF = '/home/biciklo/.pybabac'
CACHE_FILENAME = '/home/biciklo/.pybabac-cache'


class PieceNotFoundException(Exception):

    def __init__(self, numero):
        self._numero = numero


class CantLoginException(Exception):

    def __str__(self):
        return 'Impossible de se connecter au site de Babac.'


class PieceCacheEntry:

    def __init__(self, piece):
        self._piece = piece

        two_weeks_in_seconds = 24 * 3600 * 14

        self._stale_time = time.time() + two_weeks_in_seconds

    @property
    def piece(self):
        return self._piece

    @property
    def expired(self):
        now = time.time()
        return now > self._stale_time


class PiecesGetter:
    LOGIN_POST_URL = 'http://cyclebabac.com/members/component/users/'
    USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:28.0) ' + \
        'Gecko/20100101 Firefox/28.0'
    SEARCH_FORMAT = 'http://www.cyclebabac.com/component/search/?searchword={}'
    BASE_URL = 'http://www.cyclebabac.com'
    LOGIN_URL = 'http://www.cyclebabac.com/log-in.html'

    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._logged_in = False

        self._browser = ms.Browser()
        self._browser.session.headers.update(
            {'User-Agent': PiecesGetter.USER_AGENT})

    def _login_if_necessary(self):
        if self._logged_in:
            return

        # Instantiate browser and log in
        login_page = self._browser.get(PiecesGetter.LOGIN_URL)
        login_form = login_page.soup.find('form', attrs={'name': 'ialLogin'})
        login_form.select('#userTxt')[0]['value'] = self._username
        login_form.select('#passTxt')[0]['value'] = self._password
        login_response = self._browser.submit(
            login_form, url=PiecesGetter.BASE_URL)

        profile = login_response.soup.find(id='users-profile-core')
        if not profile:
            raise CantLoginException()

        self._logged_in = True

    def _make_search(self, numero_piece):
        numero_piece = str(numero_piece)

        url = PiecesGetter.SEARCH_FORMAT.format(numero_piece)
        search_results = self._browser.get(url)
        links = search_results.soup.select('dl.search-results a')

        found = False
        for link in links:
            if numero_piece in link.text:
                found = True
                break
        if not found:
            raise PieceNotFoundException(numero_piece)

        return PiecesGetter.BASE_URL + link['href']

    def _get_piece(self, url):
        self._login_if_necessary()

        page_piece = self._browser.get(url)
        piece = bos.Piece()

        details_div = page_piece.soup.find(
            'div', attrs={'class': 'productdetails-view'})

        piece.nom = details_div.find('h1').text
        prix = details_div.find('span', attrs={'class': 'PricesalesPrice'})

        if not prix:
            raise Exception('Price not found on {}'.format(url))

        prix = prix.text.strip()
        match = re.match(r'\$([0-9]+)\.([0-9]{2})', prix)

        if not match:
            raise Exception(
                'Price not found/wrong price format: {}'.format(prix))

        piasses = int(match.group(1))
        cennes = int(match.group(2))

        piece.prix = 100 * piasses + cennes

        return piece

    def get_piece(self, numero_piece):
        href = self._make_search(numero_piece)
        piece = self._get_piece(href)
        piece.numero = numero_piece

        return piece

    def get_piece_with_cache(self, numero_piece):
        with shelve.open(CACHE_FILENAME, flag='c') as cache:
            if numero_piece in cache and cache[numero_piece].expired:
                del cache[numero_piece]

            if numero_piece not in cache:
                try:
                    piece = self.get_piece(numero_piece)
                    cache[numero_piece] = PieceCacheEntry(piece)
                except PieceNotFoundException:
                    cache[numero_piece] = PieceCacheEntry(None)
                    raise

            piece = cache[numero_piece].piece

            if not piece:
                raise PieceNotFoundException(numero_piece)

            return piece

if __name__ == '__main__':
    parser = configparser.ConfigParser()
    files_read = parser.read(PYBABAC_CONF)
    if PYBABAC_CONF not in files_read:
        print('Impossible de lire le fichier de configuration {}.'.format(
            PYBABAC_CONF))
        sys.exit(1)

    if 'babac' not in parser:
        print('Section babac manquante dans le fichier de configuration.')
        sys.exit(1)

    if 'username' not in parser['babac']:
        print('Entrée username manquante dans le fichier de configuration.')
        sys.exit(1)

    if 'password' not in parser['babac']:
        print('Entrée password manquante dans le fichier de configuration.')
        sys.exit(1)

    g = PiecesGetter(parser['babac']['username'], parser['babac']['password'])

    for num in sys.argv[1:]:
        try:
            print(g.get_piece_with_cache(num))
        except PieceNotFoundException:
            print('Pièce {} introuvable.'.format(num))
        except CantLoginException as e:
            print(e)
            sys.exit(1)
