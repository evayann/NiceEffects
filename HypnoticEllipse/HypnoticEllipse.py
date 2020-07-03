"""
Implementation of nice effect
Inspired from https://github.com/the-real-tokai/macuahuitl/blob/master/comitl.py
"""

from enum import Enum
from random import seed as set_seed, uniform, randint, choice
from argparse import ArgumentParser
from colorsys import hls_to_rgb, rgb_to_hls
from SVGVideoMaker import EllipseArc, Ellipse, Point2D, SVG, Video

__author__ = "Yann Zavattero"
__version__ = "1"


class AnimGenerator(Enum):
	CHAOS = "CHAOS"
	CREASE = "CREASE"
	LINEAR = "LINEAR"
	DECREASE = "DECREASE"

class HypnoticEllipse:
	def __init__(self, fps, rx, ry, om, stroke, linecaps, gap, nb_ellipse, sens,
	             duration, bg, color, gdt, type, name, ext, seed=None):
		self.svg = SVG(background_color=bg)

		colored = "128,128,128" if gdt else color # Grey
		# Set first part of border if necessary
		if om in ["both", "inside"]:
			ellipse = Ellipse(Point2D(0, 0), rx - 2 - gap - stroke, ry - 2 - gap - stroke)
			ellipse.set_style(fill_color="none", stroke_width=stroke * 2, stroke_color=f"rgb({colored})")
			self.svg.append(ellipse)
		elif om == "fill":
			ellipse = Ellipse(Point2D(0, 0), rx - 2 - gap, ry - 2 - gap)
			ellipse.set_style(fill_color=color, stroke_width=stroke * 2, stroke_color=f"rgb({colored})")
			self.svg.append(ellipse)

		set_seed(seed)

		self.anim_generator = self.set_anim_generator(type)
		self.nb_ellipse = nb_ellipse
		self.rx, self.ry = rx, ry
		self.duration = duration
		self.linecaps = linecaps
		self.stroke = stroke
		self.color = color
		self.sens = sens
		self.gdt = gdt
		self.fps = fps
		self.gap = gap
		self.om = om

		self.video = Video(self.svg, width=1500, height=1500, fps=fps)
		self.name = name
		self.ext = ext

	def set_anim_generator(self, anim_type):
		if anim_type == AnimGenerator.CHAOS.value:
			return self.chaos
		elif anim_type == AnimGenerator.CREASE.value:
			return self.crease
		elif anim_type == AnimGenerator.DECREASE.value:
			return self.decrease
		elif anim_type == AnimGenerator.LINEAR.value:
			return self.linear
		else:
			raise Exception("Not supported")

	def compute_color(self, increment):
		if self.color and self.gdt:
			rgb_percent = hls_to_rgb(self.color[0], self.color[1], self.color[2] + increment)
			return "rgb({}, {}, {})".format(*[int(col * 255) for col in rgb_percent])
		else:
			return self.color

	def generate_ellipse(self):
		# Position
		center = Point2D(0, 0)
		rx, ry = self.rx, self.ry
		space = self.gap + self.stroke
		# Style
		color_inc = 0
		color_inc_sens = lambda index, inc: index * inc if self.gdt == "up" else (self.nb_ellipse - index) * inc

		if self.color and self.gdt:
			self.color = self.color.split(",")
			# rgb_to_hls Use value between 0 and 1 (percentage).
			self.color = rgb_to_hls(*[int(v)/255 for v in self.color])
			color_inc = -self.color[2] / self.nb_ellipse

		for i in range(self.nb_ellipse):
			offset = uniform(0, 359.0)
			angle = uniform(0, 359.0)

			arc = EllipseArc(center, Point2D(rx, ry), offset, offset + angle)
			arc.set_style(stroke_linecaps=self.linecaps, stroke_width=self.stroke,
			              stroke_color=self.compute_color(color_inc_sens(i, color_inc)))
			self.anim_generator(arc, i)
			self.svg.append(arc)

			rx += space
			ry += space

		if self.om in ["both", "outside"]:
			border_stroke = self.stroke * 2
			ellipse = Ellipse(Point2D(0, 0), rx + self.stroke, ry + self.stroke)
			ellipse.set_style(fill_color="none", stroke_width=border_stroke,
			                  stroke_color=self.compute_color(color_inc_sens(i, color_inc)))
			rx += border_stroke
			ry += border_stroke
			self.svg.append(ellipse)

		# Set View box on last circle
		x = rx * 2 * 5
		if x > 2300:
			x = 2300
		elif x < 700:
			x = 700

		y = ry * 2 * 5
		if y > 2300:
			y = 2300
		elif y < 700:
			y = 700

		self.svg.set_size(x, y)
		self.svg.set_view_box(Point2D(-rx, -ry), Point2D(rx, ry))

	def crease_decrease(self, arc, low_to_quick, index):
		rotation = 360 * index if low_to_quick else 360 * (self.nb_ellipse - index)
		arc.add_rotate(self.fps * self.duration, self.sens * rotation)

	def crease(self, arc, index):
		self.crease_decrease(arc, True, index)

	def decrease(self, arc, index):
		self.crease_decrease(arc, False, index)

	def linear(self, arc, index):
		arc.add_rotate(self.fps * self.duration, self.sens * 360)

	def chaos(self, arc, index):
		nb_turn_to_do = randint(1, 10)
		sens = choice([-1, 1])
		for split in range(self.nb_ellipse):
			arc.add_rotate(int((split + 1) * self.duration / self.nb_ellipse * self.fps),
			               sens * (360 * nb_turn_to_do) / self.nb_ellipse)

	def make_animation(self):
		self.video.save_movie(name=self.name, ext=self.ext)


def generate_cli():
	ap = ArgumentParser(
			description=("""Arranges randomly sized ellipse arcs into ellipse shape. \
						Animation is make with SVGVideoMaker and can generate animation to gif/mp4."""),
			epilog="Report bugs, request features, or provide suggestions via https://github.com/evayann/NiceEffects",
			add_help=False,
	)

	g = ap.add_argument_group("Generation")
	g.add_argument("-nb", "--ellipse", metavar="INT", type=int,
	               help="number of concentric ellipse arc elements to generate inside the ellipse ", default=10)
	g.add_argument("-g", "--gap", metavar="FLOAT", type=float, help="distance between the generated ellipse", default=1)
	g.add_argument("-rx", "--x-radius", metavar="INT", type=int, help="setup x radius of ellipse shape",
	               default=10, choices=range(3, 31))
	g.add_argument("-ry", "--y-radius", metavar="INT", type=int, help="setup x radius of ellipse shape",
	               default=10, choices=range(3, 31))
	g.add_argument("-d", "--duration", metavar="INT", type=int, help="Time in second to make one animation. Default 10 seconds",
	               default=10, choices=range(3, 31))
	g.add_argument("-t", "--type", metavar="STR", type=str,
	               help="Type of generation system.", default="CHAOS",
	               choices=["CHAOS", "CREASE", "DECREASE", "LINEAR"])
	g.add_argument("-s", "--seed", metavar="INT", type=int,
	               help="Seed for initialization of the random number generator for predictable results.", default=None)

	g = ap.add_argument_group("Style")
	g.add_argument("-ss", "--stroke-size", metavar="FLOAT", type=float, help="Stroke size of each ellipse.",
	               default=1, choices=range(1, 5))
	g.add_argument("-om", "--outline-mode", metavar="OUTLINE", type=str,
	               help="Generate bounding outline ellipse.", choices=["both", "outside", "inside", "fill", None],
	               default="both")
	g.add_argument("-bg", "--background-color", metavar="COLOR", type=str,
	               help="The background color of animation. If you want transparent, use none", default="white")
	g.add_argument("-c", "--color", metavar="R,G,B", type=str,
	               help="The color of circles with RGB values. If none, use random color.", default="26,158,53")
	g.add_argument("-gdt", "--gradient", metavar="STR", type=str,
	               help="The sens of gradient for coloring. From color to grey. Need to have a color",
	               default="down", choices=["up", "down", None])
	g.add_argument("-l", "--linecaps", metavar="CAPS STYLE", type=str,
	               help="The style of border of ellipse", default="round", choices=[None, "butt", "round"])
	g.add_argument("-r", "--rotation", metavar="INT", type=int,
	               help="The sens of rotation. Incompatible with CHAOS type.", default=1, choices=[-1, 1])

	g = ap.add_argument_group("Output")
	g.add_argument("-fps", "--frame-per-seconds", metavar="INT", type=int,
	               help="The number of frame per seconds.", default=30)
	g.add_argument("-o", "--output", metavar="FILENAME", type=str,
	               help="Name of output file.", default="HypnoticEllipse")
	g.add_argument("-ext", "--extension", metavar="EXTENSION", type=str,
	               help="Extension of the output file.", default="gif", choices=["gif", "mp4"])

	g = ap.add_argument_group("Misc")
	g.add_argument("-v", "--version", action="version", help="show version number and exit",
	               version=f"%(prog)s V.{__version__}")
	g.add_argument("-h", "--help", action="help", help="show this help message and exit")

	return ap


def main():
	args = generate_cli().parse_args()
	hyptonic = HypnoticEllipse(fps=args.frame_per_seconds,
	                           rx=args.x_radius, ry=args.y_radius,
	                           om=str(args.outline_mode), stroke=args.stroke_size,
	                           linecaps=str(args.linecaps), gap=args.gap,
	                           nb_ellipse=args.ellipse, sens=args.rotation,
	                           duration=args.duration, bg=args.background_color,
	                           color=args.color, gdt=args.gradient,
	                           type=args.type, name=args.output, ext=args.extension,
	                           seed=args.seed)
	hyptonic.generate_ellipse()
	hyptonic.make_animation()


if __name__ == "__main__":
	main()
