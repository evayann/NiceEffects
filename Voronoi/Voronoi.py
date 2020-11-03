# Implementation from https://github.com/jansonh/Voronoi
# Update to compute animation

__author__ = "Yann Zavattero"
__version__ = "1"

# region Imports
import heapq
from itertools import count
import math
from random import seed as set_seed, randint
from argparse import ArgumentParser

from SVGVideoMaker import Point2D as Point, Segment as S, Arc as A
from SVGVideoMaker import Video as Video
from SVGVideoMaker import SVG, save
from SVGVideoMaker import AnimationType
from SVGVideoMaker import Rectangle
# endregion Imports

class Segment:
	def __init__(self, y, voronoi):
		self.start = y
		self.end = None
		self.done = False
		self.segment = None
		self.v = voronoi

	def compute_bound(self, seg):
		for pt in [seg.intersect_point(bd_seg) for bd_seg in self.v.bounds.get_segments()]: # Get intersection point with segment and 4 segments of bounds
			if pt:
				if not self.v.bounds.is_in(seg.endpoints[0]):
					seg.endpoints[0] = round(pt, 3)
				elif not self.v.bounds.is_in(seg.endpoints[1]):  # movement endpoints[1]
					seg.endpoints[1] = round(pt, 3)

	def compute_segment(self):
		# Round and reorient segment
		self.start, self.end = round(self.start, 3), round(self.end, 3)
		seg = S(self.start, self.end) if self.start < self.end else S(self.end, self.start)

		# Crop segment to map to size
		self.compute_bound(seg)
		start_frame = int((seg.endpoints[0].x / self.v.width) * self.v.duration)
		end_frame = int((seg.endpoints[1].x / self.v.width) * self.v.duration)

		if start_frame != end_frame:
			# Draw segment by inflation
			segment = S(seg.endpoints[0], seg.endpoints[0])
			segment.set_style(stroke_color=self.v.color, stroke_dasharray=self.v.dasharray)
			segment.animations.add_animation(start_frame, AnimationType.INFLATION, value=Point(0, 0))

			movement = seg.endpoints[1] - seg.endpoints[0]
			segment.animations.add_animation(end_frame, AnimationType.INFLATION, value=movement)
			if self.v.bounds.is_in(segment.endpoints[0]) and \
					self.v.bounds.is_in(segment.endpoints[1]):
				self.v.last_frame = max(self.v.last_frame, end_frame)
		else:
			# Draw segment by pop
			segment = S(seg.endpoints[0], seg.endpoints[1], opacity=0)
			segment.set_style(stroke_color="blue")
			segment.add_opacity(start_frame - 1 if start_frame > 0 else 0, 0)
			segment.add_opacity(end_frame, 1)

		self.segment = segment

	def set_end(self, end, is_finish):
		self.end = end
		self.done = is_finish
		self.compute_segment()

	def finish(self, p):
		if self.done:
			return
		self.set_end(p, True)

	def get_segment(self):
		return self.segment

class Event:
	def __init__(self, x, p, a):
		self.x = x
		self.p = p
		self.a = a
		self.valid = True

class Arc(A):
	def __init__(self, p, a=None, b=None):
		super().__init__(0, 0, 0)
		self.p = p
		self.pprev = a
		self.pnext = b
		self.e = None
		self.s0 = None
		self.s1 = None

class PriorityQueue:
	def __init__(self):
		self.pq = []
		self.entry_finder = {}
		self.counter = count()

	def push(self, item):
		# check for duplicate
		if item in self.entry_finder:
			return
		# use x-coordinate as a primary key (heapq in python is min-heap)
		entry = [item.x, next(self.counter), item]
		self.entry_finder[item] = entry
		heapq.heappush(self.pq, entry)

	def remove_entry(self, item):
		entry = self.entry_finder.pop(item)
		entry[-1] = 'Removed'

	def pop(self):
		while self.pq:
			_, _, item = heapq.heappop(self.pq)
			if item != 'Removed':
				del self.entry_finder[item]
				return item
		raise KeyError('pop from an empty priority queue')

	def top(self):
		while self.pq:
			_, _, item = heapq.heappop(self.pq)
			if item != 'Removed':
				del self.entry_finder[item]
				self.push(item)
				return item
		raise KeyError('top from an empty priority queue')

	def empty(self):
		return not self.pq

class Line:
	def __init__(self, width, height):
		self.line = S(Point(0, 0), Point(0, height), id="Defilement Line")
		self.line.set_style(stroke_color="red")
		self.previous_x_line = 0
		self.width = width

	def compute_line(self, frame, x):
		# Add animation only if line move from his previous position
		if self.width >= x > self.previous_x_line:
			self.line.add_translation(frame, x - self.previous_x_line, 0)
			self.previous_x_line = x

	def get_line(self):
		return self.line

class VoronoiGenerator:
	def __init__(self, fps, width, height, color, stroke_width, nb_pts, duration, line, dasharray, dp, seed=None):
		set_seed(seed)

		self.dp = dp
		self.fps = fps
		self.width, self.height = width, height
		self.color = color
		self.stroke_width = stroke_width
		self.bounds = Rectangle(Point(0, 0), width, height)
		self.duration = duration * fps
		self.dasharray = dasharray
		self.last_frame = -1

		self.output = []  # list of line segment
		self.arc = None  # binary tree for parabola arcs

		self.voronoi_points = []
		for _ in range(nb_pts):
			pt = Point(randint(0, width), randint(0, height))
			pt.set_style(fill_color=self.color, stroke_width=0)
			self.voronoi_points.append(pt)
		self.line = Line(width, height) if line else None

		# Display
		self.segments_outputs = []  # list of animate segment

		self.points = PriorityQueue()  # site events
		self.event = PriorityQueue()  # circle events

		iterator_pts = iter(self.voronoi_points)
		# bounding box
		first_pt = next(iterator_pts)
		self.points.push(first_pt)
		self.x0, self.y0 = first_pt
		self.x1, self.y1 = self.x0, self.y0

		# insert points to site event
		for point in iterator_pts:
			self.points.push(point)
			# keep track of bounding box size
			if point.x < self.x0:
				self.x0 = point.x
			elif point.x > self.x1:
				self.x1 = point.x
			if point.y < self.y0:
				self.y0 = point.y
			elif point.y > self.y1:
				self.y1 = point.y

		# add margins to the bounding box
		dx = (self.x1 - self.x0 + 1) / 5.0
		dy = (self.y1 - self.y0 + 1) / 5.0
		self.x0 = self.x0 - dx
		self.x1 = self.x1 + dx
		self.y0 = self.y0 - dy
		self.y1 = self.y1 + dy

	def process(self):
		while not self.points.empty():
			if not self.event.empty() and (self.event.top().x <= self.points.top().x):
				self.process_event()  # handle circle event

			else:
				self.process_point()  # handle site event

		# after all points, process remaining circle events
		while not self.event.empty():
			self.process_event()

		self.finish_edges()
		if self.line:
			self.line.compute_line(self.last_frame, self.width)
			# Add an extra translation to make disappear the bar
			self.line.line.add_translation(self.last_frame + self.fps, 20, 0)

	def process_point(self):
		# get next event from site pq
		p = self.points.pop()
		# add new arc (parabola)
		self.arc_insert(p)

	def process_event(self):
		# get next event from circle pq
		e = self.event.pop()

		if e.valid:
			# start new edge
			s = Segment(e.p, self)
			self.output.append(s)

			# remove associated arc (parabola)
			a = e.a
			if a.pprev is not None:
				a.pprev.pnext = a.pnext
				a.pprev.s1 = s
			if a.pnext is not None:
				a.pnext.pprev = a.pprev
				a.pnext.s0 = s

			# finish the edges before and after a
			if a.s0 is not None:
				a.s0.finish(e.p)
			if a.s1 is not None:
				a.s1.finish(e.p)

			# recheck circle events on either side of p
			if a.pprev is not None:
				self.check_circle_event(a.pprev)
			if a.pnext is not None:
				self.check_circle_event(a.pnext)

	def arc_insert(self, p):
		if self.arc is None:
			self.arc = Arc(p)
			# self.arcs_output.append(A(None, None, None))
		else:
			# find the current arcs at p.y
			i = self.arc
			while i is not None:
				flag, z = self.intersect(p, i)
				if flag:
					# new parabola intersects arc i
					flag, zz = self.intersect(p, i.pnext)
					if (i.pnext is not None) and (not flag):
						i.pnext.pprev = Arc(i.p, i, i.pnext)
						i.pnext = i.pnext.pprev
					else:
						i.pnext = Arc(i.p, i)
					i.pnext.s1 = i.s1

					# add p between i and i.pnext
					i.pnext.pprev = Arc(p, i, i.pnext)
					i.pnext = i.pnext.pprev

					i = i.pnext  # now i points to the new arc

					# add new half-edges connected to i's endpoints
					seg = Segment(z, self)
					self.output.append(seg)
					i.pprev.s1 = i.s0 = seg

					seg = Segment(z, self)
					self.output.append(seg)
					i.pnext.s0 = i.s1 = seg

					# check for new circle events around the new arc
					self.check_circle_event(i)
					self.check_circle_event(i.pprev)
					self.check_circle_event(i.pnext)

					return

				i = i.pnext

			# if p never intersects an arc, append it to the list
			i = self.arc
			while i.pnext is not None:
				i = i.pnext
			i.pnext = Arc(p, i)

			# insert new segment between p and i
			x = self.x0
			y = (i.pnext.p.y + i.p.y) / 2.0
			start = Point(x, y)

			seg = Segment(start, self)
			i.s1 = i.pnext.s0 = seg
			self.output.append(seg)

	def check_circle_event(self, i):
		# look for a new circle event for arc i
		if (i.e is not None) and (i.e.x != self.x0):
			i.e.valid = False
		i.e = None

		if (i.pprev is None) or (i.pnext is None):
			return

		flag, x, o = self.circle(i.pprev.p, i.p, i.pnext.p)
		if flag and (x > self.x0):
			i.e = Event(x, o, i)
			self.event.push(i.e)

	def circle(self, a, b, c):
		# check if bc is a "right turn" from ab
		if ((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)) > 0:
			return False, None, None

		# Joseph O'Rourke, Computational Geometry in C (2nd ed.) p.189
		A = b.x - a.x
		B = b.y - a.y
		C = c.x - a.x
		D = c.y - a.y
		E = A * (a.x + b.x) + B * (a.y + b.y)
		F = C * (a.x + c.x) + D * (a.y + c.y)
		G = 2 * (A * (c.y - b.y) - B * (c.x - b.x))

		if G == 0:
			return False, None, None  # Points are co-linear

		# point o is the center of the circle
		ox = 1.0 * (D * E - B * F) / G
		oy = 1.0 * (A * F - C * E) / G

		# o.x plus radius equals max x coord
		x = ox + math.sqrt((a.x - ox) ** 2 + (a.y - oy) ** 2)
		o = Point(ox, oy)

		return True, x, o

	def intersect(self, p, i):
		# check whether a new parabola at point p intersect with arc i
		if i is None:
			return False, None
		if i.p.x == p.x:
			return False, None

		a = 0.0
		b = 0.0

		if i.pprev is not None:
			a = (self.intersection(i.pprev.p, i.p, 1.0 * p.x)).y
		if i.pnext is not None:
			b = (self.intersection(i.p, i.pnext.p, 1.0 * p.x)).y

		if ((i.pprev is None) or (a <= p.y)) and ((i.pnext is None) or (p.y <= b)):
			py = p.y
			px = 1.0 * (i.p.x ** 2 + (i.p.y - py) ** 2 - p.x ** 2) / (2 * i.p.x - 2 * p.x)
			res = Point(px, py)
			return True, res
		return False, None

	def intersection(self, p0, p1, l):
		# get the intersection of two parabolas
		p = p0
		if p0.x == p1.x:
			py = (p0.y + p1.y) / 2.0
		elif p1.x == l:
			py = p1.y
		elif p0.x == l:
			py = p0.y
			p = p1
		else:
			# use quadratic formula
			z0 = 2.0 * (p0.x - l)
			z1 = 2.0 * (p1.x - l)

			a = 1.0 / z0 - 1.0 / z1
			b = -2.0 * (p0.y / z0 - p1.y / z1)
			c = 1.0 * (p0.y ** 2 + p0.x ** 2 - l ** 2) / z0 - 1.0 * (p1.y ** 2 + p1.x ** 2 - l ** 2) / z1

			py = 1.0 * (-b - math.sqrt(b * b - 4 * a * c)) / (2 * a)

		px = 1.0 * (p.x ** 2 + (p.y - py) ** 2 - l ** 2) / (2 * p.x - 2 * l)
		return Point(px, py)

	def finish_edges(self):
		l = self.x1 + (self.x1 - self.x0) + (self.y1 - self.y0)
		i = self.arc
		while i.pnext is not None:
			if i.s1 is not None:
				p = self.intersection(i.p, i.pnext.p, l * 2.0)
				i.s1.finish(p)
			i = i.pnext

	def save_animation(self, name, ext):
		svg = SVG(width=self.width, height=self.height)
		# Border
		r = Rectangle(Point(0, 0), self.width, self.height)
		r.set_style(stroke_color="black", stroke_width=5, fill_color="none")
		svg.append(r)

		if self.line:
			svg.append(self.line.get_line())

		for out in self.output:
			segment = out.get_segment()
			if self.bounds.is_in(segment.endpoints[0]) and self.bounds.is_in(segment.endpoints[1]):
				svg.append(segment)

		if self.dp:
			svg.append(self.voronoi_points)

		svg.set_view_box(Point(0, 0), Point(self.width, self.height))
		Video(svg, fps=self.fps).save_movie(name=name, ext=ext)

	def save_frame(self, name, ext):
		svg = SVG(width=self.width, height=self.height)
		# Border
		r = Rectangle(Point(0, 0), self.width, self.height)
		r.set_style(stroke_color="black", stroke_width=5, fill_color="none")
		svg.append(r)

		svg.append(self.get_frame())
		svg.set_view_box(Point(0, 0), Point(self.width, self.height))
		save(svg.get_svg(), name, ext)

	def get_frame(self):
		elements = []
		for o in self.output:
			segment = S(Point(o.start.x, o.start.y), Point(o.end.x, o.end.y))
			segment.set_style(stroke_color=self.color, stroke_width=self.stroke_width, stroke_dasharray=self.dasharray)
			elements.append(segment)
		if self.dp:
			elements.extend(self.voronoi_points)
		return elements

def generate_cli():
	ap = ArgumentParser(
			description="Make Voronoi Diagram with animation of creation",
			epilog="Report bugs, request features, or provide suggestions via https://github.com/evayann/NiceEffects",
			add_help=False
	)

	g = ap.add_argument_group("Generation")
	g.add_argument("-nb", "--points", metavar="INT", type=int,
	               help="Number of points for Voronoi diagram.", default=10)
	g.add_argument("-d", "--duration", metavar="INT", type=int,
	               help="Time in second for the animation. Default 10 seconds.", default=10)
	g.add_argument("-s", "--seed", metavar="INT", type=int,
	               help="Seed for initialization of the random number generator for predictable results.", default=None)

	g = ap.add_argument_group("Style")
	g.add_argument("-l", "--line", metavar="BOOL", type=bool,
	               help="Display line for animation. Default is True.", default=True)
	g.add_argument("-c", "--color", metavar="STR", type=str,
	               help="The color of Voronoi segment. Default is blue.", default="blue")
	g.add_argument("-dash", "--dasharray", metavar="STR", type=str,
	               help="The string who describe Voronoi segment.", default=None)
	g.add_argument("-ss", "--stroke-size", metavar="INT", type=int,
	               help="The size of stroke of Voronoi segment.", default=1)
	g.add_argument("-dp", "--display-points", metavar="BOOL", type=bool,
	               help="If need to display point.", default=True)

	g = ap.add_argument_group("Output")
	g.add_argument("-wdt", "--width", metavar="INT", type=int, help="Width of output element.",
	               default=500)
	g.add_argument("-hgt", "--height", metavar="INT", type=int, help="Height of output element.",
	               default=500)
	g.add_argument("-fps", "--frame-per-seconds", metavar="INT", type=int,
	               help="The number of frame per seconds.", default=30)
	g.add_argument("-o", "--output", metavar="FILENAME", type=str,
	               help="Name of output file.", default="Voronoi")
	g.add_argument("-ext", "--extension", metavar="EXTENSION", type=str,
	               help="Extension of the output file.", default="gif", choices=["png", "svg", "gif", "mp4"])

	g = ap.add_argument_group("Misc")
	g.add_argument("-v", "--version", action="version", help="Show version number and exit.",
	               version=f"%(prog)s V.{__version__}")
	g.add_argument("-h", "--help", action="help", help="Show this help message and exit.")

	return ap

def main():
	args = generate_cli().parse_args()
	vg = VoronoiGenerator(args.frame_per_seconds, args.width, args.height, args.color, args.stroke_size,
	                      args.points, args.duration, args.line, args.dasharray, args.display_points, args.seed)
	vg.process()

	if args.extension in ["gif", "mp4"]:
		vg.save_animation(args.output, args.extension)
	elif args.extension in ["svg", "png"]:
		vg.save_frame(args.output, args.extension)

if __name__ == '__main__':
	main()
