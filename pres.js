var stops = [
	{ type: "view", box: [0, 100, 100, 100] },
	{ type: "view", box: [0, 0, 300, 300] },
	{ type: "elem", select: "obj", attr: { r: 50 } },
	{ type: "elem", select: "obj", attr: { fill: "#0f0" } },
	{ type: "elem", select: "obj", attr: { cx: 200, r: 200 } },
];
var backstops = [];
function genBackstop(trans) {
	switch (trans["type"]) {
	case "view":
		var ovb = $("svg").attr("viewBox").split(" ");
		for (var i = 0; i < 4; i++) ovb[i] = parseInt(ovb[i]);
		return { type: "view", box: ovb };
		break;
	case "elem":
		var elem = $("#" + trans["select"]);
		var reset = {};
		$.each(trans["attr"], function(k, v) {
			var attr = elem.attr(k);
			if (!isNaN(attr)) attr = parseInt(attr);
			reset[k] = attr;
		});
		return { type: "elem", select: trans["select"], attr: reset };
		break;
	}
}
function apply(trans) {
	switch (trans["type"]) {
	case "view":
		var ovb = $("svg").attr("viewBox").split(" ");
		for (var i = 0; i < 4; i++) ovb[i] = parseInt(ovb[i]);
		var nvb = trans["box"];
		var dvb = [];
		for (var i = 0; i < 4; i++) dvb.push(nvb[i] - ovb[i]);
		$("svg").velocity({ tween: 1 }, { progress: function(elements, complete, remaining, start, tween) {
			var vb = [];
			for (var i = 0; i < 4; i++) vb.push(Math.trunc(ovb[i] + dvb[i] * tween));
			$(elements[0]).attr("viewBox", vb.join(" "));
		}});
		break;
	case "elem":
		$("#" + trans["select"]).velocity(trans["attr"]);
		break;
	}
}
var slide = 0;
function keydown(e) {
	//console.log(e.keyCode);
	switch (e.keyCode) {
	case 32:
	case 39:
		if (slide >= stops.length) break;
		if (backstops.length == slide) backstops.push(genBackstop(stops[slide]));
		apply(stops[slide++]);
		break;
	case 37:
		if (slide <= 0) break;
		apply(backstops[--slide]);
		break;
	}
}
$(document).ready(function() {
	$(document).keydown(keydown);
});
