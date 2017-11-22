import re
import collections

import transition

keywords = {
	"title": "raw",
	"source": "raw",
	"note": "raw",
	"init": "recurse",
	"view": "space",
	"show": "space",
	"hide": "space",
	"duration": "space",
	"select": "comma",
	":": "raw",
}

com = ";"

def parse(s, sep, com = None): # Separates a line on `sep`, skipping quoted or parenthesized strings and removing comments
	matching = {"]": "[", "}": "{", ")": "("}
	ret = []
	cur = ""
	stack = []
	i = 0
	while i < len(s):
		if s[i] in ["[", "{", "("]:
			stack.append(s[i])
			cur += s[i]
		elif s[i] in ["]", "}", ")"] and len(stack) > 0 and stack[-1] == matching[s[i]]:
			stack.pop()
			cur += s[i]
		elif s[i] in ["\"", "\'"]:
			if len(stack) > 0 and stack[-1] == s[i]: stack.pop()
			else: stack.append(s[i])
			cur += s[i]
		elif len(stack) > 0: cur += s[i]
		else:
			if com and re.match(com, s[i:]): return ret;
			match = re.match(sep, s[i:])
			if match:
				ret.append(cur)
				cur = ""
				i += len(match.group(0))
				continue
			else: cur += s[i]
		i += 1
	ret.append(cur)
	return ret

def preproc(line): # Return (indent, keyword, argstring)
	indent = 0
	for c in line:
		if c != "\t": break
		indent += 1
	line = line.strip()
	if indent > 0: return (indent, None, line)
	split = re.split("\\s+", line, 1)
	if split[0] == "" or split[0].startswith(com): return (0, None, None)
	return (0, split[0], split[1] if len(split) > 1 else None)

def args(lines): # Splits args and takes care of indented regions. Return (keyword, args, paren args)
	first = lines.popleft()
	indented = []
	parenargs = []
	while len(lines) > 0 and lines[0][0] > first[0]: indented.append(lines.popleft())
	if first[1] is None or len(first[1]) == 0: raise RuntimeError("Unexpected blank line in block")
	if first[1] in keywords: kwclass = keywords[first[1]]
	elif first[1][0] in ["#", "."]: kwclass = keywords["select"]
	else: raise RuntimeError("Unknown keyword \"%s\"" % (first[1]))
	if kwclass == "raw": lineargs = [first[2]] if first[2] else []
	elif first[2] is None:
		lineargs = []
		parenargs = []
	else:
		match = re.match("^()(\\((.*)\\))$", first[2]) # Case with only paren args
		if not match: match = re.match("^(.*?)(\\s+\\((.*)\\))?$", first[2])
		if not match: raise RuntimeError("Unexpected line format")
		if match.group(1) is None or match.group(1) == "": lineargs = []
		else:
			if kwclass == "space": lineargs = parse(match.group(1), "\\s+", com)
			else: lineargs = parse(match.group(1), ",\\s+", com)
		parenargs = parse(match.group(3), ",\\s+", com) if match.group(3) else []
	if kwclass  == "recursive":
		indented = [ line[2] for line in indented ] # TODO
	else: indented = [ line[2] for line in indented ]
	return (first[1], lineargs + indented, parenargs)

def blocks(lines):
	ret = []
	cur = []
	while len(lines) > 0:
		if lines[0][1] is None:
			if lines[0][0] > 0: raise RuntimeError("Unexpected indent")
			if len(cur) > 0:
				ret.append(cur)
				cur = []
			lines.popleft()
		else:
			a = args(lines)
			cur.append(a)
	if len(cur) > 0: ret.append(cur)
	return ret

def getconf(infile):
	conf = blocks(collections.deque([ preproc(line) for line in infile.readlines() ]))
	if len(conf) < 2: raise RuntimeError("Properties and init blocks are required")
	props = { prop[0]: prop[1] for prop in conf[0] }
	slides = []
	for slide in conf[1:]:
		cur = []
		defaults = {}
		for trans in slide:
			if trans[0] is None or trans[0] is "": continue
			elif trans[0] in [":", "note"]: continue
			elif trans[0] in ["view", "show", "hide"] or trans[0][0] in ["#", "."]:
				cur.append(transition.mktrans(trans, defaults))
			elif trans[0] in ["duration"]: defaults[trans[0]] = int(trans[1][0])
			else: raise RuntimeError("Unknown slide command \"%s\"" % (trans[0]))
		slides.append(cur)
	return (props, slides)

