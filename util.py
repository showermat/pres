import subprocess
import re

def unquote(val):
	while val[0] == val[-1] == "'" or val[0] == val[-1] == "\"": val = val[1:-1]
	return val

def csssplit(style, rm_quotes = False):
	if style is None: return {}
	style = [ re.split(":\\s*", item) for item in re.split(";\\s*", style) ]
	ret = {}
	for item in style:
		val = item[1]
		if len(val) == 0: continue
		if rm_quotes: val = unquote(val)
		ret[item[0]] = val
	return ret

def fclist(name, weight = None):
	ret = []
	weights = {
		"thin": "100",
		"light": "300",
		"normal": "400",
		"regular": "400",
		"medium": "500",
		"bold": "700",
		"heavy": "800",
		"black": "900"
	}
	def stylepair(fw, fs): return {"font-weight": fw, "font-style": fs}
	if weight in weights.keys(): weight = weights[weight]
	fallback = None
	done = set()
	for line in subprocess.run(["fc-list", name], stdout=subprocess.PIPE).stdout.decode("UTF-8").strip().split("\n"):
		line = line.split(":")
		fname = line[0]
		if len(line) <= 2: ret.append(({}, fname))
		else:
			if fallback is None: fallback = fname
			style = [ item.lower() for item in line[2].split("=")[1].split(",") ][0]
			fw = "400"
			fs = "normal"
			if style in ["roman"]: pass
			elif style in weights.keys(): fw = weights[style]
			elif style in ["italic"]: fs = style
			elif style in ["bold italic"]:
				fs = "italic"
				fw = weights["bold"]
			else: continue
			if fw == "400" and fs == "normal": fallback = fname
			if weight is not None and weight != fw: continue
			if (fw, fs) in done: continue
			done.add((fw, fs))
			ret.append((stylepair(fw, fs), fname))
	if len(ret) == 0: ret.append((stylepair("400", "normal"), fallback))
	return ret

