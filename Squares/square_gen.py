# Nice squares 

__author__ = "Yann Zavattero"
__version__ = "1"

from random import uniform, randint, seed
from itertools import islice, cycle, product
from argparse import ArgumentParser


X, Y = 0, 1

def intersection_between(s1, s2):
	on_segment = lambda p, q, r: min(p[X], r[X]) <= q[X] <= max(p[X], r[X]) and min(p[Y], r[Y]) <= q[Y] <= max(p[Y], r[Y])
	def orientation(p, p1, p2):
		val = (p1[Y] - p[Y]) * (p2[X] - p1[X]) - (p1[X] - p[X]) * (p2[Y] - p1[Y])
		if val == 0:
			return 0 # colinear
		return 1 if val > 0 else 2 # clock or counterclock wise

	p1, q1 = s1
	p2, q2 = s2

	o1 = orientation(p1, q1, p2)
	o2 = orientation(p1, q1, q2)
	o3 = orientation(p2, q2, p1)
	o4 = orientation(p2, q2, q1)

	if (o1 != o2 and o3 != o4) or (o1 == 0 and on_segment(p1, p2, q1)) or (o2 == 0 and on_segment(p1, q2, q1)) \
		or (o3 == 0 and on_segment(p2, p1, q2)) or (o4 == 0 and on_segment(p2, q1, q2)):
		return True

	return False

class Square:
	def __init__(self, x, y, side):
		self.points = [
			(x, y),
			(x + side, y),
			(x + side, y + side),
			(x, y + side)
		]

		self.size = side
		self.top_left = (x, y)

	def segs(self):
		"""
		iterate through all segments.
		"""
		return zip(self.points, islice(cycle(self.points), 1, None))	

	def intersection_with(self, polygon):
		"""
		return true if polygon and self
		have an intersection
		"""
		for s1, s2 in product(self.segs(), polygon.segs()):
			if intersection_between(s1, s2):
				return True
		return False

	def svg_content(self):
		"""
		svg string to fill svg file
		"""
		return f'<polygon points="{" ".join(("{},{}".format(*p) for p in self.points))}"/>\n'

def pip(point, polygon):
	wn = 0   # the winding number counter
	x, y = point

	# pt_j = next point after pt_i
	for pt_i, pt_j in polygon.segs():
		# Get the 2 points
		xi, yi = pt_i
		xj, yj = pt_j
		if yi <= y:
			if yj > y:
				if (xj - xi) * (y - yi) - (x - xi) * (yj - yi) > 0:
					wn += 1
		else:
			if yj <= y:
				if (xj - xi) * (y - yi) - (x - xi) * (yj - yi) < 0:
					wn -= 1

	return wn


class Displayer:
	file_count = 0

	def __init__(self, dimensions=None, colors=None):
		self.svg_dimensions = dimensions if dimensions else (DIMENSION, DIMENSION)
		self.colors = colors.split() if colors else \
						"#F93F42 #91BF6D #4C918F #227EA3 #F9A64B\
						 #485F36 #F9C84E #567691 #91BF6D #227EA3".split()


	def display(self, polygons, name, path):
		"""
		Create a svg who contains all polygons
		"""

		filename = "{}/{}.svg".format(path, name)

		svg_strings = self.compute_displays(polygons)

		svg_file = open(filename, 'w')
		svg_file.write('<svg width="{}" height="{}"'.format(*self.svg_dimensions))
		svg_file.write(' viewBox="0 0')
		svg_file.write(' {} {}"'.format(*self.svg_dimensions))
		svg_file.write(' xmlns="http://www.w3.org/2000/svg">\n')
		svg_file.write('<rect x="0" y="0"')
		svg_file.write(' width="{}" height="{}" fill="black"/>\n'.format(*self.svg_dimensions))

		for string in svg_strings:
			svg_file.write(string)

		svg_file.write("</svg>\n")
		svg_file.close()
		
	def compute_displays(self, things):
		strings = []
		for color, thing in zip(cycle(iter(self.colors)), things):
			strings.append('<g fill="{}" stroke="black">\n'.format(color))
			inner_strings = self.compute_display(thing)
			strings.extend(inner_strings)
			strings.append('</g>\n')
		return strings

	def compute_display(self, thing):
		strings = []
		try:
			iterator = iter(thing)
			for subthing in iterator:
				inner_strings = self.compute_display(subthing)
				strings.extend(inner_strings)
		except TypeError:
			# we cannot iterate on it
			strings.append(thing.svg_content())
		return strings


def all_good(pt, elements):
	for element in elements:
		if pip(pt, element):
			return False
	return True

def one_intersect(poly, elements):
	for element in elements:
		if poly.intersection_with(element):
			return True
	return False

def generate_square_in(in_poly, same_level, min_size, max_try):
	if in_poly.size < min_size:
		return

	size = in_poly.size
	tl = in_poly.top_left

	offX = randint(0, size)
	offY = randint(0, size) 
	p = (tl[X] + offX, tl[Y] + offY)

	counter = 0  
	while not all_good(p, same_level):
		if max_try <= counter:
			return
		offX = randint(0, size)
		offY = randint(0, size)
		p = (tl[X] + offX, tl[Y] + offY)
		counter += 1

	counter = 0
	max_size = size - max(abs(offX), abs(offY))
	c_size = randint(max_size // 2, max_size)
	x, y = tl[X] + offX, tl[Y] + offY

	sq = Square(x, y, c_size)

	while one_intersect(sq, same_level):
		if max_try <= counter or c_size <= min_size:
			return
		c_size -= 1
		sq = Square(x, y, c_size)
		counter += 1

	if not one_intersect(sq, same_level):
		return sq

	return None

def generate_random_square(elements, parent, min_size, max_try, max_depth, nb_at_level, depth=0):
	if depth >= max_depth:
		return 

	depth += 1
	same_level = []
	for i in range(nb_at_level):
		square = generate_square_in(parent, same_level, min_size, max_try)
		if square:
			elements.append(square)
			same_level.append(square)
			generate_random_square(elements, square, min_size, max_try, max_depth, nb_at_level, depth)

def generate_cli():
	ap = ArgumentParser(
			description=("""Arranges randomly squares into others squares. """),
			epilog="Report bugs, request features, or provide suggestions via https://github.com/evayann/NiceEffects",
			add_help=False,
	)

	g = ap.add_argument_group("Generation")
	g.add_argument("-mt", "--max-try", metavar="INT", type=int,
	               help="Limit of test before create each new square", default=5000)
	g.add_argument("-md", "--max-depth", metavar="INT", type=int, 
					help="Max number of square in square", default=2)
	g.add_argument("-ms", "--min-size", metavar="INT", type=int, 
					help="Minimal size of a square", default=10)
	g.add_argument("-nbs", "--squares-at-level", metavar="INT", type=int, 
					help="Number of sqaure at level of depth", default=75)
	g.add_argument("-s", "--seed", metavar="INT", type=int,
	               help="Seed for initialization of the random number generator for predictable results.", default=None)

	
	g = ap.add_argument_group("Output") 
	g.add_argument("-d", "--dimension", metavar="INT", type=int, help="Dimension of svg file",
	               default=800)
	g.add_argument("-n", "--name", metavar="STR", type=str, help="Name of ouput svg file",
	               default="Square")
	g.add_argument("-p", "--path", metavar="STR", type=str, help="Path to save svg file", default="./")
	
	return ap

DIMENSION = -1
def main():
	args = generate_cli().parse_args()

	selected_seed = args.seed if args.seed else randint(0, 1000000) 
	seed(selected_seed)
	print("> Seed :", selected_seed)

	max_try = args.max_try
	max_depth = args.max_depth
	nb_at_level = args.squares_at_level
	min_size = args.min_size

	global DIMENSION
	DIMENSION = args.dimension

	elements = []
	generate_random_square(elements, Square(0, 0, DIMENSION), min_size, max_try, max_depth, nb_at_level)
	Displayer().display(elements, name=args.name, path=args.path)

if __name__ == "__main__":
	main() 
