import random
from SVGVideoMaker import SVG, Polygon, Point2D, EllipseArc

class Truchet:

	def __init__(self, width, height, s, rule):
		"""Initialize the class with image size and tile size and split."""
		self.width, self.height = width, height
		self.s = s
		self.nx, self.ny = int(width // s), int(height // s)
		self.rule = rule
		self.elements = []

	def svg_shape(self):
		""" Need implementation in child class """

	def make_svg(self, filename):
		SVG(self.elements, self.width, self.height).save("./", filename)

class Triangle(Polygon):
	def __init__(self, a, b, c):
		super().__init__([a, b, c])


class TruchetTriangles(Truchet):
	"""A class for creating a Truchet tiling of triangles."""

	def __init__(self, width, height, s, color, rule=None):
		super(TruchetTriangles, self).__init__(width, height, s, rule)
		self.color = color
		self.svg_shape()

	def svg_shape(self, rule=None):
		"""A Truchet figure based on triangles.

		The four triangle orientations to choose from in each square are:
								xx x. xx .x
								.x xx x. xx

		"""

		if rule is None:
			rule = lambda ix, iy: random.randint(0,4)

		def triangle_path(A, B, C):
			"""Output a triangular path with vertices at A, B, C."""
			t = Triangle(A, B , C)
			t.set_style(fill_color=self.color)
			self.elements.append(t)

		for ix in range(self.nx):
			for iy in range(self.ny):
				x0, y0 = ix * self.s, iy * self.s
				x1, y1 = (ix + 1) * self.s, (iy + 1) * self.s
				p = rule(ix, iy)
				if p == 0:
					triangle_path(Point2D(x0, y0), Point2D(x1, y0), Point2D(x1, y1))
				elif p == 1:
					triangle_path(Point2D(x0, y0), Point2D(x0, y1), Point2D(x1, y1))
				elif p == 2:
					triangle_path(Point2D(x0, y0), Point2D(x1, y0), Point2D(x0, y1))
				else:
					triangle_path(Point2D(x1, y0), Point2D(x1, y1), Point2D(x0, y1))

class TruchetArcs(Truchet):
	"""A class for creating a Truchet tiling of arcs."""

	def __init__(self, width, height, s, color, rx=None, ry=None, rule=None):
		super(TruchetArcs, self).__init__(width, height, s, rule)
		self.color = color
		self.rx = rx
		self.ry = ry
		self.svg_shape()

	def svg_shape(self):
		"""A Truchet figure based on interlinking circular arcs."""

		def arc_path(center, radius, start_angle, end_angle):
			"""Semicircular arc path from A=(x0,y0) to B=(x1,y1), radius r."""
			a = EllipseArc(center, radius, start_angle, end_angle)
			a.set_style(stroke_color=self.color, stroke_width=5, fill_color="none")
			self.elements.append(a)

		if self.rule is None:
			self.rule = lambda ix, iy: random.randint(0,1)

		if not self.rx:
			self.rx = self.s / 2
		if not self.ry:
			self.ry = self.s / 2

		for ix in range(self.nx):
			for iy in range(self.ny):
				p = self.rule(ix, iy)
				x0, y0 = ix * self.s, iy * self.s
				x1, y1 = (ix + 1) * self.s, (iy + 1) * self.s
				if p:
					arc_path(Point2D(x0, y0), Point2D(self.rx, self.ry), 270, 360)
					arc_path(Point2D(x1, y1), Point2D(self.rx, self.ry), 90, 180)
				else:
					arc_path(Point2D(x0, y1), Point2D(self.rx, self.ry), 0, 90)
					arc_path(Point2D(x1, y0), Point2D(self.rx, self.ry), 180, 270)

class TruchetCustom(Truchet):
	"""A class for creating a Truchet tiling of custom draw."""

	def __init__(self, width, height, s, color, drawfunc, rule=None):
		super(TruchetCustom, self).__init__(width, height, s, rule)
		self.color = color
		self.df = drawfunc
		self.svg_shape()

	def svg_shape(self):
		if self.rule is None:
			self.rule = lambda ix, iy: random.randint(0,4)

		for ix in range(self.nx):
			for iy in range(self.ny):
				x0, y0 = ix * self.s, iy * self.s
				x1, y1 = (ix + 1) * self.s, (iy + 1) * self.s
				elements = self.df(self.rule(ix, iy), Point2D(x0, y0), Point2D(x1, y1))
				self.elements.extend(elements)

if __name__ == '__main__':
	truchet = TruchetTriangles(600, 400, 10, color="#882ecf")
	truchet.make_svg("triangles")

	truchet = TruchetArcs(600, 400, 50, color="#2e88cf")
	truchet.make_svg("arcs")

	w = 600
	h = 400
	s = 50
	def df(orientation, tl, br):
		def set_style(el):
			el.set_style(fill_color="none", stroke_color="purple")
		elements = []
		if orientation == 0 or orientation == 3:
			e1 = EllipseArc(tl + Point2D(0, s), Point2D(s / 3, s / 2), 0, 90)
			e2 = EllipseArc(br - Point2D(0, s), Point2D(s / 1.5, s / 3), 180, 270)
			set_style(e1)
			set_style(e2)
			elements.append(e1)
			elements.append(e2)
		elif orientation == 1 or orientation == 2:
			e1 = EllipseArc(tl, Point2D(s / 1.5, s / 3), 270, 360)
			e2 = EllipseArc(br, Point2D(s / 3, s / 2), 90, 180)
			set_style(e1)
			set_style(e2)
			elements.append(e1)
			elements.append(e2)
		return elements

	rule = lambda xi, yi: xi % 2 + yi * s % 2
	truchet = TruchetCustom(w, h, s, drawfunc=df, color="#882ecf", rule=rule)
	truchet.make_svg("ellipse")
