#! /usr/bin/env python

import sys
import os.path
import re
import json
import yaml
import jinja2
import requests
import lxml.etree # cssselect
import PyPDF2
import io
import subprocess
import base64
import magic

import util
import conffmt
import transition

# Features:
# When a relative transform is applied, store the backstop as a relative transform as well!
# For HTML export, export plain SVG (Inkscape -l) and embed linked media and fonts
# Need to patch Velocity.js for fx and fy
# Speaker notes somehow?
# Look into ways to keep PDF size down
# Page number, date, and other dynamic content in overlay
# Support mouse drag and zoom
# Use hashes in URL to specify current slide
# Hide overlay on (e.g. title) slide
# Fix layers that have transforms applied to them (causes rect-based viewboxes to be off)

rsrcdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "rsrc")

def xmlns(ns, prop): # FIXME Ick.
	return "{%s}%s" % (ns, prop)

def b64uri(mime, data):
	return "data:%s;base64,%s" % (mime, data.decode("UTF-8"))

def b64enc(fname):
	mime = magic.Magic(mime=True).from_file(fname)
	with open(fname, "rb") as inf: data = base64.b64encode(inf.read())
	return b64uri(mime, data)

def standalone(fname, svg):
	xlns = "http://www.w3.org/1999/xlink"
	svg = lxml.etree.fromstring(svg.encode("UTF-8"))
	for img in svg.findall(".//{*}image"):
		if xmlns(xlns, "href") not in img.keys(): continue
		href = img.get(xmlns(xlns, "href"))
		if href.startswith("data:") or len(href) == 0 or href[0] in ["#", "."]: continue
		if not re.match("^[a-z]://", href):
			path = os.path.join(os.path.dirname(fname), href)
			if not os.path.isfile(path): continue
			uri = b64enc(path)
		else:
			req = requests.get(href)
			uri = b64uri(req.headers["Content-Type"], req.content)
		img.set(xmlns(xlns, "href"), uri)
	fonts = {}
	for text in svg.findall(".//{*}text") + svg.findall(".//{*}tspan"):
		if "style" not in text.keys(): continue
		style = util.csssplit(text.get("style"), True)
		if "font-family" not in style.keys(): continue
		fontname = style["font-family"]
		fontweight = style["font-weight"] if "font-weight" in style else "normal"
		if fontname in ["serif", "sans-serif", "monospace"]: continue
		if (fontname, fontweight) in fonts.keys(): continue
		fonts[(fontname, fontweight)] = util.fclist(fontname, fontweight)
	for ((font, weight), files) in fonts.items():
		for file in files:
			qual = "; ".join([ "%s: %s" % (k, v) for (k, v) in file[0].items() ])
			if len(qual) > 0: qual += ";"
			fonttext = "@font-face { font-family: \"%s\"; src: url(\"%s\"); %s }\n" % (font, b64enc(file[1]), qual)
			fontsect = lxml.etree.Element("style")
			fontsect.text = lxml.etree.CDATA(fonttext)
			svg.findall(".//{*}defs")[0].append(fontsect)
	return lxml.etree.tostring(svg).decode("UTF-8").replace("<svg:", "<").replace("</svg:", "</") # FIXME HELP I cannot for the life of me figure out how lxml handles namespaces.

def splitlayers(svg):
	isns = "http://www.inkscape.org/namespaces/inkscape"
	svg = lxml.etree.fromstring(svg.encode("UTF-8"))
	for g in svg.findall("{*}g"):
		if xmlns(isns, "groupmode") not in g.keys() or g.get(xmlns(isns, "groupmode")) != "layer": continue
		enclosure = lxml.etree.Element("svg")
		enclosure.set("viewBox", svg.get("viewBox"))
		if xmlns(isns, "label") in g.keys(): enclosure.set("id", g.get(xmlns(isns, "label")))
		else: enclosure.set("id", g.get("id"))
		if "style" in g.attrib: del g.attrib["style"]
		g.getparent().replace(g, enclosure)
		enclosure.append(g)
	return lxml.etree.tostring(svg).decode("UTF-8").replace("<svg:", "<").replace("</svg:", "</") # FIXME HELP I cannot for the life of me figure out how lxml handles namespaces.

def svg2pdf(svg):
	cmd = ["inkscape", "/dev/stdin", "-z", "--export-area-page", "--export-pdf", "/dev/stdout"]
	try: return subprocess.run(cmd, input=svg.encode("UTF-8"), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
	except subprocess.CalledProcessError as e:
		print(e.stderr.decode("UTF-8"))
		raise

def html(srcname, svg, title, init, slides, out):
	with open(os.path.join(rsrcdir, "templ.html")) as infile: templ = jinja2.Template(infile.read())
	scripts = ["jquery-3.2.1.min.js", "velocity.min.js", "data", "pres.js"]
	js = ""
	svg = standalone(srcname, svg)
	tree = lxml.etree.fromstring(svg.encode("UTF-8"))
	for script in scripts:
		if script == "data":
			lines = ["var init = " + json.dumps([ trans.encode(tree) for trans in init ]) + ";",
				"var stops = " + json.dumps([ [ trans.encode(tree) for trans in slide ] for slide in slides ]) + ";"]
			content = "\n".join(lines);
		elif re.search("^http(s)?://", script): content = requests.get(script).text
		else:
			with open(os.path.join(rsrcdir, script)) as infile: content = infile.read()
		js += "<script>" + content + "</script>\n"
	with open(out, "w") as outfile: outfile.write(templ.render(title=title, js=js, slides=svg))

def pdf(doc, title, slides, size, out):
	num = 1
	pages = []
	tree = lxml.etree.fromstring(doc.encode("UTF-8"))
	for slide in slides:
		print("\r%d/%d" % (num, len(slides)), end="")
		for trans in slide: trans.apply(tree)
		pages.append(svg2pdf(lxml.etree.tostring(tree).decode("UTF-8")))
		num += 1
	print()
	writer = PyPDF2.PdfFileMerger()
	for page in pages: writer.append(io.BytesIO(page))
	writer.addMetadata({"/Title": title})
	writer.write(out)

if len(sys.argv) < 3: raise RuntimeError("Usage: pres.py slides.pres (output.pdf|output.html)")
conffile = os.path.abspath(sys.argv[1])
if not os.path.isfile(conffile): raise Exception("Bad configuration input")
dest = os.path.join(os.path.dirname(conffile), sys.argv[2])
with open(conffile) as infile: (props, slides) = conffmt.getconf(infile)
size = [ int(x) for x in props["size"] ] if "size" in props else [800, 600]
with open(props["source"][0]) as inf: svg = splitlayers(inf.read())
if dest.endswith(".html"): html(props["source"][0], svg, props["title"][0], slides[0], slides[1:], dest)
elif dest.endswith(".pdf"): pdf(svg, props["title"][0], slides, size, dest)
else: raise RuntimeError("Output file must end in .html or .pdf")
