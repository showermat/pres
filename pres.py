#! /usr/bin/python

import sys
import os.path
import re
import json
import yaml
import jinja2
import requests
import lxml.etree # cssselect
import cairosvg
import PyPDF2
import io

import conffmt

# Features:
# Add overlays that don't move with the slide
# Make duration per-slide rather than per-trans and allow overriding it for individual transes
# Speaker notes somehow?

rsrcdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "rsrc")

def html(svg, title, init, slides, out):
	with open(os.path.join(rsrcdir, "templ.html")) as infile: templ = jinja2.Template(infile.read())
	scripts = ["jquery-3.2.1.min.js", "velocity.min.js", "data", "pres.js"]
	js = ""
	for script in scripts:
		if script == "data":
			lines = [
				"var init = " + json.dumps(init) + ";",
				"var stops = " + json.dumps(slides) + ";"
			]
			content = "\n".join(lines);
		elif re.search("^http(s)?://", script): content = requests.get(script).text
		else:
			with open(os.path.join(rsrcdir, script)) as infile: content = infile.read()
		js += "<script>" + content + "</script>\n"
	with open(out, "w") as outfile: outfile.write(templ.render(title=title, js=js, svg=svg))

def pdf(doc, slides, out):
	num = 1
	pages = []
	svg = lxml.etree.fromstring(doc.encode("UTF-8"))
	for slide in slides:
		print("\r%d/%d" % (num, len(slides)), end="")
		for trans in slide:
			if trans["type"] == "view":
				svg.set("viewBox", " ".join([ str(x) for x in trans["box"] ]))
			elif trans["type"] == "elem":
				elems = svg.cssselect(trans["select"])
				for elem in elems:
					for (k, v) in trans["attr"].items(): elem.set(k, str(v))
			else: pass
		pages.append(cairosvg.svg2pdf(bytestring=lxml.etree.tostring(svg)))
		num += 1
	print()
	writer = PyPDF2.PdfFileMerger()
	for page in pages: writer.append(io.BytesIO(page))
	writer.write(out)

if len(sys.argv) < 3: raise RuntimeError("Usage: pres.py slides.pres (output.pdf|output.html)")
conffile = os.path.abspath(sys.argv[1])
if not os.path.isfile(conffile): raise Exception("Bad configuration input")
dest = os.path.join(os.path.dirname(conffile), sys.argv[2])
with open(conffile) as infile: (props, slides) = conffmt.getconf(infile)
with open(os.path.join(os.path.dirname(conffile), props["source"])) as infile: svg = infile.read()
if dest.endswith(".html"): html(svg, props["title"], slides[0], slides[1:], dest)
elif dest.endswith(".pdf"): pdf(svg, slides, dest)
else: raise RuntimeError("Output file must end in .html or .pdf")
