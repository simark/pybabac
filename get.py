import mechanicalsoup as ms
import bos
import re
import configparser


class PieceNotFoundException(Exception):

    def __init__(self, numero, nb_resultats):
        self._numero = numero
        self._nb_resultats = nb_resultats

    def __str__(self):
        return 'Aucun candidat valide trouvé dans les résultats de recherche pour {} (sur {} candidats).'.format(self._numero, self._nb_resultats)


class PiecesGetter:
    LOGIN_POST_URL = 'http://cyclebabac.com/members/component/users/'
    USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:28.0) Gecko/20100101 Firefox/28.0'
    SEARCH_FORMAT = 'http://www.cyclebabac.com/component/search/?searchword={}'
    BASE_URL = 'http://www.cyclebabac.com'
    LOGIN_URL = 'http://www.cyclebabac.com/log-in.html'

    def __init__(self, username, password):
        self._username = username
        self._password = password

        self._init()

    def _init(self):
        # Instantiate browser and log in
        self._browser = ms.Browser()
        self._browser.session.headers.update(
            {'User-Agent': PiecesGetter.USER_AGENT})
        login_page = self._browser.get(PiecesGetter.LOGIN_URL)
        login_form = login_page.soup.find('form', attrs={'name': 'ialLogin'})
        login_form.select('#userTxt')[0]['value'] = self._username
        login_form.select('#passTxt')[0]['value'] = self._password
        login_response = self._browser.submit(
            login_form, url=PiecesGetter.BASE_URL)

        profile = login_response.soup.find(id='#users-profile-core')
        if not profile:
			raise Exception('Could not log in.')

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
            raise PieceNotFoundException(numero_piece, len(links))

        return PiecesGetter.BASE_URL + link['href']

    def _get_piece(self, url):
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

if __name__ == '__main__':
    parser = configparser.ConfigParser()
    parser.read('babac.conf')

    g = PiecesGetter(parser['babac']['username'], parser['babac']['password'])
    print(g.get_piece('60-036'))
