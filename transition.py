import re

import util

intre = "-?\\d+"
floatre = "-?\\d+(\\.\\d+)?"

def retype(val):
	if re.match("^%s$" % (intre), val): return int(val)
	elif re.match("^%s$" % (floatre), val): return float(val)
	return val

def mkdict(args):
	args = [ arg.split(" ") for arg in args ]
	for i in range(len(args)):
		for j in range(len(args[i])): args[i][j] = retype(args[i][j])
	args = { arg[0]: arg[1:] for arg in args }
	for arg in args.keys():
		if len(args[arg]) == 0: args[arg] = None
		elif len(args[arg]) == 1: args[arg] = args[arg][0]
	return args

def apply_op(n, op, delta):
	if op == "+": return n + delta
	elif op == "-": return n - delta
	elif op == "*": return n * delta
	elif op == "/": return n / delta
	else: raise RuntimeError("Bad arithmetic operation: %s" % (op))

noncss = ["width", "height", "x", "y", "cx", "cy", "fx", "fy", "r", "rx", "ry", "x1", "x2", "y1", "y2"];

def updstyle(elem, k, v):
	if elem.get("style"): style = util.csssplit(elem.get("style"), False)
	else: style = {}
	style[k] = v
	style = ";".join([ "%s:%s" % (k, v) for (k, v) in style.items() ])
	elem.set("style", style)

def getlayers(svg):
	layers = { group.get("id"): group for group in svg.findall("{*}svg") }
	if len(layers) == 0: return { "content": svg }
	return layers

def rect2vb(rect):
	return [rect.get("x"), rect.get("y"), rect.get("width"), rect.get("height")]

class Transition:
	def apply(self, svg): pass
	def encode(self, svg): pass

class Viewbox(Transition):
	def __init__(self, args, params):
		self.args = args
		self.params = params
	def apply(self, tree):
		if len(self.args) == 4: box = self.args
		elif len(self.args) == 1: box = rect2vb(tree.cssselect(self.args[0])[0])
		getlayers(tree)["content"].set("viewBox", " ".join([ str(x) for x in box ]))
	def encode(self, tree):
		if len(self.args) == 4: box = self.args
		elif len(self.args) == 1: box = rect2vb(tree.cssselect(self.args[0])[0])
		else: box = None
		return {"type": "view", "box": box, **self.params}

class Element(Transition):
	def __init__(self, elem, attrs, params):
		self.elem = elem
		self.attrs = attrs
		self.params = params
	def calcvalue(self, tree, elem, k, v):
		if type(v) is not str: return v
		match = re.match("^(.)=(%s)$" % (floatre), v)
		if match: return apply_op(float(elem.get(k)), match.group(1), float(match.group(2)))
		match = re.match("^=(.[^.]*)\.(.+)([-+*/]%s)?" % (floatre), v)
		if match:
			target = tree.cssselect(match.group(1))[0].get(match.group(2))
			if match.group(3): target = apply_op(float(target), match.group(3)[0], float(match.group(3)[1:]))
			return target
		return v
	def apply(self, tree):
		elems = tree.cssselect(self.elem)
		for e in elems:
			for (k, v) in self.attrs.items():
				v = self.calcvalue(tree, e, k, v)
				if k in noncss: e.set(k, str(v))
				else: updstyle(e, k, str(v))
	def encode(self, tree):
		return {"type": "elem", "select": self.elem, "attr": self.attrs, **self.params}

class Display(Transition):
	def __init__(self, elem, show):
		self.elem = elem[0] # TODO Support multiple elements per line
		self.show = show
	def apply(self, tree):
		for target in tree.cssselect(self.elem):
			updstyle(target, "display", "block" if self.show else "none")
	def encode(self, tree):
		return {"type": "show" if self.show else "hide", "elem": self.elem}

def mktrans(desc, defaults):
	params = {**defaults.copy(), **mkdict(desc[2])}
	if desc[0] is None or len(desc[0]) == 0: raise RuntimeError("Cannot make null transition")
	elif desc[0] == "view": return Viewbox([ retype(arg) for arg in desc[1] ], params)
	elif desc[0] == "show": return Display(desc[1], True)
	elif desc[0] == "hide": return Display(desc[1], False)
	elif desc[0][0] in [".", "#"]: return Element(desc[0], mkdict(desc[1]), params)
