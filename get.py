import requests
import bs4
import bos
import re
import configparser

class PiecesGetter:
	LOGIN_POST_URL = 'http://cyclebabac.com/members/component/users/'
	USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:28.0) Gecko/20100101 Firefox/28.0'
	SEARCH_FORMAT = 'http://www.cyclebabac.com/members/component/search/?searchword={}'
	BASE_URL = 'http://cyclebabac.com'

	def __init__(self, username, password):
		self._username = username
		self._password = password

		self._init()
		self._login()

	def _init(self):
		self._session = requests.Session()
		self._session.headers.update({
			'User-Agent': PiecesGetter.USER_AGENT,
		})

	def _login(self):
		r = self._session.get(PiecesGetter.LOGIN_POST_URL)
		soup = bs4.BeautifulSoup(r.text)
		form = soup.find('form', id='login-form')
		super_secret_stuff = form.find('input', value='1')['name']

		login_data = {
			'username': self._username,
			'password': self._password,
			'Submit': 'Log+in',
			'option': 'com_users',
			'task': 'user.login',
			'return': 'aW5kZXgucGhwP0l0ZW1pZD01NzI=',
			super_secret_stuff: '1',
		}

		r = self._session.post(PiecesGetter.LOGIN_POST_URL, data = login_data)

	def _make_search(self, numero_piece):
		url = PiecesGetter.SEARCH_FORMAT.format(numero_piece)
		r = self._session.get(url)
		soup = bs4.BeautifulSoup(r.text)
		dts = soup.find_all('dt', attrs = {'class': 'result-title'})
		res = []
		for dt in dts:
			href = dt.find('a')['href']

			res.append(PiecesGetter.BASE_URL + href)
		return res

	def _get_piece(self, url):
		piece = bos.Piece()

		r = self._session.get(url)
		soup = bs4.BeautifulSoup(r.text)

		details_div = soup.find('div', attrs = {'class': 'productdetails-view'})

		piece.nom = details_div.find('h1').text

		prix = details_div.find('span', attrs = {'class': 'PricesalesPrice'}).text.strip()
		match = re.match(r'\$([0-9]+)\.([0-9]{2})', prix)
		if not match:
			raise Exception('Price not found/wrong price format: {}'.format(prix))
		piasses = int(match.group(1))
		cennes = int(match.group(2))

		piece.prix = 100 * piasses + cennes

		return piece


	def get_piece(self, numero_piece):
		hrefs = self._make_search(numero_piece)
		if len(hrefs) == 0:
			raise Exception("0 result for numero piece {}".format(numero_piece))
		elif len(hrefs) > 1:
			raise Exception("More than 1 result for numero piece {}".format(numero_piece))

		url = hrefs[0]

		piece = self._get_piece(url)
		piece.numero = numero_piece

		return piece

if __name__ == '__main__':
	parser = configparser.ConfigParser()
	parser.read('babac.conf')

	g = PiecesGetter(parser['babac']['username'], parser['babac']['password'])
	print(g.get_piece('60-036'))
