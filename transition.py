import re

def retype(val):
	if re.match("^-?\\d+$", val): return int(val)
	elif re.match("^-?\\d+(.\\d+)?$", val): return float(val)
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

noncss = ["width", "height", "x", "y", "cx", "cy", "r", "rx", "ry", "x1", "x2", "y1", "y2"];

def updstyle(elem, k, v):
	style = [ re.split(":\\s*", item) for item in re.split(";\\s*", elem.get("style")) ]
	style = { item[0]: item[1] for item in style }
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
		elif len(self.args) == 1:
			box = rect2vb(tree.cssselect(self.args[0])[0])
		return {"type": "view", "box": box, **self.params}

class Element(Transition):
	def __init__(self, elem, attrs, params):
		self.elem = elem
		self.attrs = attrs
		self.params = params
	def apply(self, tree):
		elems = tree.cssselect(self.elem)
		for e in elems:
			for (k, v) in self.attrs.items():
				if k in noncss: e.set(k, str(v))
				else: updstyle(e, k, str(v))
	def encode(self, tree):
		return {"type": "elem", "select": self.elem, "attr": self.attrs, **self.params}

def mktrans(desc, defaults):
	params = {**defaults.copy(), **mkdict(desc[2])}
	if desc[0] is None or len(desc[0]) == 0: raise RuntimeError("Cannot make null transition")
	elif desc[0] == "view": return Viewbox([ retype(arg) for arg in desc[1] ], params)
	elif desc[0][0] in [".", "#"]: return Element(desc[0], mkdict(desc[1]), params)