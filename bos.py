
class Piece:
	def __init__(self):
		self.numero = ""
		self.nom = ""
		self.prix = ""

	def __str__(self):
		return "{} {} {}".format(self.numero, self.nom, self.prix)


