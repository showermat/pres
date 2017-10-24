function rgb2hex(rgb) {
	var m = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
	function hex(x) { return ("0" + parseInt(x).toString(16)).slice(-2); }
	return "#" + hex(m[1]) + hex(m[2]) + hex(m[3]);
}
function copy(obj) {
	return $.extend(true, {}, obj);
}
var noncss = ["width", "height", "x", "y", "cx", "cy", "r", "rx", "ry", "x1", "x2", "y1", "y2"];

var svg;
var backstops = [];
function genBackstop(trans) {
	var ret = copy(trans);
	switch (trans["type"]) {
	case "view":
		ret["box"] = svg.attr("viewBox").split(" ");
		break;
	case "elem":
		var elem = $(trans["select"]);
		var reset = {};
		$.each(trans["attr"], function(k, v) {
			var attr = elem.attr(k) || elem.css(k);
			if (attr.match("^rgb()")) attr = rgb2hex(attr);
			if (!isNaN(attr)) attr = parseInt(attr);
			reset[k] = attr;
		});
		ret["attr"] = reset;
		break;
	}
	return ret;
}
function apply(trans, skip) {
	return new Promise(function(resolve, reject) {
		duration = trans["duration"] || 400
		easing = trans["ease"] || "swing"
		switch (trans["type"]) {
		case "view":
			if (skip) {
				svg.attr("viewBox", trans["box"].join(" "));
				resolve();
			}
			else {
				var ovb = svg.attr("viewBox").split(" ");
				for (var i = 0; i < 4; i++) ovb[i] = parseFloat(ovb[i]);
				var nvb = trans["box"];
				var dvb = [];
				for (var i = 0; i < 4; i++) dvb.push(nvb[i] - ovb[i]);
				svg.velocity({ tween: 1 }, { progress: function(elements, complete, remaining, start, tween) {
					var vb = [];
					for (var i = 0; i < 4; i++) vb.push(ovb[i] + dvb[i] * tween);
					$(elements[0]).attr("viewBox", vb.join(" "));
				}, duration: duration, easing: easing, complete: resolve() });
			}
			break;
		case "elem":
			if (skip) {
				var elem = $(trans["select"]);
				var attr = {};
				var css = {};
				$.each(trans["attr"], function(k, v) {
					if (noncss.indexOf(k) > -1) attr[k] = v;
					else css[k] = v;
				});
				elem.attr(attr);
				elem.css(css);
				// Ick.  The body up to this point is required because dimensional attributes are not handled by CSS.  Otherwise we could just use the line below.
				//$(trans["select"]).css(trans["attr"]);
				resolve();
			}
			else $(trans["select"]).velocity(trans["attr"], { duration: duration, easing: easing, complete: resolve() });
			break;
		}
	});
}

var slide = 0;
function go(target, skip = false) {
	if (target > stops.length) target = stops.length;
	if (target < 0) target = 0;
	if (target == slide) return;
	if (target > slide) {
		var newBackstops = [];
		var makeBackstops = false;
		if (backstops.length == slide) makeBackstops = true;
		var complete = [];
		for (var i = 0; i < stops[slide].length; i++) {
			if (makeBackstops) newBackstops.push(genBackstop(stops[slide][i]));
			complete.push(apply(stops[slide][i], skip));
		}
		if (makeBackstops) backstops.push(newBackstops);
		Promise.all(complete).then(function() { go(target, skip); });
		slide++;
	}
	else {
		slide--;
		var complete = [];
		for (var i = backstops[slide].length - 1; i >= 0; i--) complete.push(apply(backstops[slide][i], skip));
		Promise.all(complete).then(function() { go(target, skip); });
	}
}
function keydown(e) {
	//console.log(e.keyCode);
	switch (e.keyCode) {
	case 32:
	case 39:
		go(slide + 1, e.shiftKey);
		break;
	case 37:
		go(slide - 1, e.shiftKey);
		break;
	case 72:
		go(0, true);
		break;
	}
}
$(document).ready(function() {
	svg = $("svg#slides");
	for (var i = 0; i < init.length; i++) apply(init[i], true);
	$(document).keydown(keydown);
});
