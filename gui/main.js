dialog = require('electron').remote.dialog;
api_url = "http://127.0.0.1:5000/api/";

function toggleSidebar(open) {
    if (open) {
        document.getElementById("sidenav_main").style.width = "300px";
    } else {
        document.getElementById("sidenav_main").style.width = "0px";
    }
}

function toggleNewChatDialog(open) {
    if (open) {
        document.getElementById("newchat_dialog").style.display = "block";
        toggleSidebar(false);
    } else {
        document.getElementById("newchat_dialog").style.display = "none";
        resetNewChatDialog();
    }
}

function summary_init() {
    var main_table_body = document.getElementById("chats_table_body");
    makeapicall("getchatssummary", (message) => { main_table_body.parentNode.row_widths = []; updatetable(main_table_body, message, minimal=true) });
    var stats_table_body = document.getElementById("stats_table_body");
    makeapicall("gettotalsummary", (message) => { stats_table_body.parentNode.row_widths = []; updatetable(stats_table_body, message, minimal=true) });
}

function resetNewChatDialog(resetnewfile = true) {
    document.getElementById("loadnewfile_submit_wrap").innerHTML = "<button class=\"btn\" onclick=\"loadnewfile()\">Submit</button>";
    document.getElementById("loadnewfile_submit_wrap").setAttribute("class", "");
    if (resetnewfile) {
        newfile_name = undefined;
    }
}

function getavailfiles(doloadfile = true, select_override = null) {
    makeapicall("getavailfiles", function (message) {
        var data = JSON.parse(message);
        var file_display_div = document.getElementById("current_file_div");
        if (data.length == 0) {
            file_display_div.innerHTML = "<button class=\"btn\" style=\"background-color: #ffffff\" onclick=\"toggleNewChatDialog(true)\">Load new Chat</button>"
            document.getElementById("primary_controls").querySelectorAll(".mode_btn").forEach((button) => (button.disabled = true))
        } else {
            document.getElementById("primary_controls").querySelectorAll(".mode_btn").forEach((button) => (button.disabled = false))
            file_display_div.innerHTML = "";
            var sel = add_select(file_display_div, data, data, "Chat", id_additional = "", prepend = "", empty_option = false);
            sel.setAttribute("id", "chat_sel");
            if (doloadfile) {
                loadfile(sel.options[sel.selectedIndex].value, silent = true);
            }
            if (select_override) {
                sel.selectedIndex = data.indexOf(select_override);
            }
            sel.addEventListener("change", function () {
                loadfile(sel.options[sel.selectedIndex].value, silent = true);
            })
        }
    })
}

function getprocessingoptions() {
    getoptions("langmain", "default_lang");
    getoptions("devmain", "default_dev");
    getoptions("chatmain", "default_chat");
}

function getoptions(selectid, key) {
    makeapicall("getoptions?key=" + key, function (message) {
        var data = JSON.parse(message);
        var options = data["options"];
        var lang_select = document.getElementById(selectid);
        for (var i = 0; i < options.length; i++) {
            var option = document.createElement("option")
            option.innerHTML = options[i];
            lang_select.appendChild(option);
        }
        lang_select.selectedIndex = Math.min(data["selected"], options.length);
    })
}

function loadfile(prefix, silent = false) {
    makeapicall("loadfile?prefix=" + prefix, function (message) {
        if (!silent) swal(message)
    })
    changemode(null, none = true);
}

function loadnewfile() {
    document.getElementById("loadnewfile_submit_wrap").innerHTML = "<div class=\"loader\"></div>";
    document.getElementById("loadnewfile_submit_wrap").setAttribute("class", "btn");
    if (typeof newfile_name == "undefined" || newfile_name == undefined) {
        swal("No file selected!");
        resetNewChatDialog();
    } else {
        makeapicall("loadnewfile?filename=" + String(encodeURIComponent(newfile_name)), function (message) {
            var data = JSON.parse(message);
            if (data[0] == 0) {
                document.getElementById("loadnewfile_submit_wrap").innerHTML = "<i class='fas fa-check' style='color: #00bb00'></i>"
                if (document.location.href.endsWith("summary.html")) {
                    summary_init();
                } else {
                    getavailfiles(doloadfile = false, select_override = data[2]);
                    loadfile(data[2], true);
                }
            } else if (data[0] == 1) {
                swal(data[1]);
                resetNewChatDialog(false);
            } else if (data[0] == 2) {
                swal("Chat format check failed. Please check if you selected the correct language.")
                resetNewChatDialog(false);
            }
        })
    }
}

function pickfile() {
    resetNewChatDialog();
    dialog.showOpenDialog({ properties: ['openFile'] }).then((file) => {
        newfile_name = file != undefined ? file.filePaths[0] : undefined;
    });
}

function activitybyname() {
    changemode(document.getElementById("btn_abn"));
    var ctrl_div = document.getElementById("primary_controls");
    var radio_div = document.createElement("div");
    radio_div.setAttribute("class", "btn secondary_control");
    radio_div.setAttribute("id", "abn_radiobuttons");
    radio_div.innerHTML = "<label class=\"radio-inline\"><input type=\"radio\" name=\"abn_radio\" id=\"abn_radiobutton_table\" checked>Table</label><label class=\"radio-inline\"><input type=\"radio\" name=\"abn_radio\" id=\"abn_radiobutton_chart\">Chart</label>";
    ctrl_div.appendChild(radio_div);
    document.getElementById("abn_radiobutton_table").addEventListener("click", function () { activitybyname_switch() });
    document.getElementById("abn_radiobutton_chart").addEventListener("click", function () { activitybyname_switch() });
    activitybyname_switch();
}

function activityraw() {
    changemode(document.getElementById("btn_ar"));
    var table = createtable("", "<tr><th name=\"name\">Name</th><th name=\"date\">Date</th><th name=\"hour\">Hour</th><th name=\"weekday\">Weekday</th><th name=\"ispost\">Is Post?</th><th name=\"ismedia\">Is Media?</th><th name=\"islogmsg\">Is Logmsg?</th><th name=\"words\">Words</th><th name=\"chars\">Chars</th><th name=\"emojis\">Emojis</th><th name=\"puncts\">Punctuation</th></tr>", "actraw", 0, document.getElementById("main_data"), []).querySelector("table");
    table.refresh();
    maketablessortable(table, true);
}

function activitybyname_switch() {
    var data_div = document.getElementById("main_data");
    var is_table = document.getElementById("abn_radiobutton_table").checked;
    data_div.innerHTML = "";
    if (is_table) {
        deleteiffound("abn_checkboxes");
        $(".daterangepicker").remove();
        var table_div = createtable("", "<tr><th>Name</th><th>Posts</th><th>Media</th><th>Logs</th><th>Words</th><th>Chars</th><th>Emojis</th><th>Puncts</th></tr>", "abn", 0, data_div, ["20"]);
        var table = table_div.querySelector("table");
        table.refresh();
        maketablessortable(table);
    } else {
        var chart = createchart("abn").chart;
        add_filters([chart], chart.url, "?mode=chart", true, false, true, true, false);
    }
}

function usagebyword() {
    changemode(document.getElementById("btn_ubw"));
    var data_div = document.getElementById("main_data");
    data_div.innerHTML = "";
    var div_upper = document.createElement("div");
    var div_lower = document.createElement("div");
    div_upper.style.display = "inline-block";
    div_lower.style.display = "inline-block";
    var table_w_div = createtable("", "<tr><th name=\"word\">Word</th><th>Usage</th></tr>", "ubc?type=word", 1, div_upper, ["75"]);
    var table_e_div = createtable("", "<tr><th>Emoji</th><th>Usage</th></tr>", "ubc?type=emoji", 1, div_upper, ["75"], make_emoji=0);
    var table_p_div = createtable("", "<tr><th>Punctuation</th><th>Usage</th></tr>", "ubc?type=punct", 1, div_upper, ["75"]);
    var table_l_div = createtable("", "<tr><th>Links</th><th>Usage</th></tr>", "ubc?type=link", 1, div_lower, ["90"], make_emoji=0);
    var table_u_div = createtable("", "<tr><th>Uncategorized</th><th>Usage</th></tr>", "ubc?type=uncat", 1, div_lower, ["75"], make_emoji=0);
    var table_w = table_w_div.querySelector("table");
    var table_e = table_e_div.querySelector("table");
    var table_p = table_p_div.querySelector("table");
    var table_l = table_l_div.querySelector("table");
    var table_u = table_u_div.querySelector("table");
    table_w_div.parentNode.setAttribute("style", "display: inline-block; width: 33%; margin-right: 0.25%");
    table_e_div.parentNode.setAttribute("style", "display: inline-block; width: 33%; margin-right: 0.25%; margin-left: 0.25%");
    table_p_div.parentNode.setAttribute("style", "display: inline-block; width: 33%; margin-left: 0.25%");
    table_l_div.parentNode.setAttribute("style", "display: inline-block; width: 49.75%; margin-right: 0.25%");
    table_u_div.parentNode.setAttribute("style", "display: inline-block; width: 49.75%; margin-left: 0.25%;");
    table_w.refresh();
    table_e.refresh();
    table_p.refresh();
    table_l.refresh();
    table_u.refresh();
    maketablessortable(table_w);
    maketablessortable(table_p);
    maketablessortable(table_e);
    maketablessortable(table_l);
    maketablessortable(table_u);
    data_div.appendChild(div_upper);
    data_div.appendChild(div_lower);
    add_filters([table_e, table_l, table_p, table_u, table_w], "ubw", "", false, true, true, true, false);
}

function append_select_to_url(param, select, value = false) {
    var append = value ? select.options[select.selectedIndex].value : select.options[select.selectedIndex].text;
    if (append != "") {
        return "&" + param + "=" + String(encodeURI(append));
    }
    return "";
}

function statsbyword() {
    changemode(document.getElementById("btn_sbw"));
    var data_div = document.getElementById("main_data");
    var searchdiv = document.createElement("div");
    var head_div = document.createElement("div");
    head_div.setAttribute("style", "display: inline-flex");
    searchdiv.setAttribute("class", "buttonlike");
    searchdiv.setAttribute("style","width: 400px")
    searchdiv.innerHTML = "<span style=\"padding: 7px; padding-left: 12px; width: 200px;\">Search for word:</span>";

    var search_input = document.createElement("input");
    search_input.setAttribute("type", "text");
    search_input.setAttribute("class", "form-input");
    search_input.setAttribute("style", "text-align: left; width: 100%");
    searchdiv.appendChild(search_input);

    var totalusage_div = document.createElement("div");
    totalusage_div.entries = [];
    totalusage_div.setAttribute("style", "height: 40px; padding-top: 7px;")
    var mode_selection_div = document.createElement("div");
    mode_selection_div.setAttribute("style", "width: 200px");
    var mode_selection = add_select(mode_selection_div, ["bydaytime", "byweekday", "bytime", "byname"], ["by daytime", "by weekday", "over time", "by name"], "Mode", id_additional="", prepend=false, empty_option=false);

    head_div.appendChild(searchdiv);
    head_div.appendChild(mode_selection_div);
    data_div.appendChild(head_div);
    data_div.appendChild(totalusage_div);

    var chart_div = createchart("ubw");
    chart_div.setAttribute("class", "multichart");
    var sbw_chart = chart_div.chart;

    var name_select = add_name_filter(chart_div, "_name", true);

    var weekday_options = ["0", "1", "2", "3", "4", "5", "6"];
    var weekday_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Satursday", "Sunday"];
    var weekday_select = add_select(chart_div, weekday_options, weekday_labels, "Filter by weekday", "_weekday", true);

    var daytime_options = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"];
    var daytime_select = add_select(chart_div, daytime_options, daytime_options, "Filter by daytime", "_daytime", true);

    update_fun = (() => {
        var mode = mode_selection.options[mode_selection.selectedIndex].value;
        var url = append_select_to_url("namefilter", name_select) + append_select_to_url("daytimefilter", daytime_select) + append_select_to_url("weekdayfilter", weekday_select, true);
        if (mode == "bytime") {
            sbw_chart.options.scales.xAxes = [{ type: "time" }];
        } else {
            sbw_chart.options.scales.xAxes = [{ type: "category" }];
        }
        if (document.getElementById("timefilter_check").checked) {
            url += "&timefilter=" + $('#timefilter').data("daterangepicker").startDate.format("YYYY-MM-DD") + "t" + $('#timefilter').data("daterangepicker").endDate.format("YYYY-MM-DD");
        }

        word = JSON.stringify(totalusage_div.entries);
        makeapicall("ubw?mode=total&words=" + word, ((message) => { update_labellist(totalusage_div, message); }));
        sbw_chart.filter_url = "?mode=" + mode + "&words=" + word + url;
        sbw_chart.refresh();
    });

    totalusage_div.update_fun = update_fun;

    var time_select = add_time_select(chart_div, update_fun, "", true);

    search_input.addEventListener("change", (() => {newentry = String(encodeURI(emojione.shortnameToUnicode(search_input.value.toLowerCase()))); totalusage_div.entries.push(newentry); search_input.value = ""; }))
    data_div.querySelectorAll("select").forEach((select) => select.addEventListener("change", update_fun));
    data_div.querySelectorAll("input").forEach((select) => select.addEventListener("change", update_fun));
}

function update_labellist(parentdiv, message) {
    parentdiv.innerHTML = "";
    var data = JSON.parse(message);
    for (var i = 0; i < data.length; i++) {
        var newspan = document.createElement("div");
        newspan.setAttribute("style", "vertical-align: middle; padding: 1px; padding-left: 8px; padding-right: 8px; background-color: #eeeeee");
        newspan.setAttribute("class", "buttonlike");
        newspan.innerHTML = data[i][0] + " " + (data[i][1] == null ? "0" : data[i][1]);

        var delbtn = document.createElement("span");
        delbtn.innerHTML = "⨯";
        delbtn.setAttribute("style", "padding-left: 3px");
        delbtn.addEventListener("click", function (i) { return function () {
            parentdiv.entries.splice(i, 1);
            parentdiv.update_fun();
        }}(i));
        newspan.appendChild(delbtn);
        parentdiv.appendChild(newspan);
    }
}

function updatetable(tbody, message, minimal=false, deletable=false) {
    tbody.innerHTML = "";
    var content = JSON.parse(message);
    var table = tbody.parentNode;
    if (!minimal) {
        table.length = content[0];
        content = content[1];
        table.lengthdisplay.innerHTML = "Results " + ((table.pagesize * table.pagenum) + 1) + " - " + Math.min((table.pagesize * (table.pagenum + 1)), table.length) + " of " + table.length;
    }
    if (content.length != 0) { tbody.parentNode.parentNode.style.visibility = "visible"; }
    for (var i = 0; i < content.length; i++) {
        var row = tbody.insertRow(i);
        var offset = 0;
        if (deletable) {
            var btncell = row.insertCell(0);
            var delbtn = document.createElement("i");
            delbtn.setAttribute("class","fas fa-times-circle");
            btncell.setAttribute("style","vertical-align: middle; width: 15%")
            delbtn.addEventListener("click", function (i) { return function () {
                table.entries.splice(i, 1);
                table.update_fun();
            }}(i));
            btncell.appendChild(delbtn);
            var offset = 1;
        }
        for (var j = 0; j < content[i].length; j++) {
            if (minimal) { content[i][j] = content[i][j] == null ? 0 : content[i][j]}
            if (table.make_emoji >= 0 && j == table.make_emoji) {
                var new_cell = row.insertCell(j + offset);
                new_cell.innerHTML = emojione.toImage(String(content[i][j]));
            } else {
                var new_cell = row.insertCell(j + offset);
                new_cell.innerHTML = content[i][j];
                if (table.make_emoji >= 0) {
                    new_cell.setAttribute("style","vertical-align: middle;");
                }
            }
            if (j < table.row_widths.length) {
                new_cell.style.width = table.row_widths[j] + "%";
            }
        }
    }
}

function createtable(attributes_table, header, url, sort_by, data_div, row_widths, make_emoji=-1) {
    var table = document.createElement("table");
    var head = document.createElement("thead");
    var body = document.createElement("tbody");
    var wrapper = document.createElement("div");
    var container = document.createElement("div");
    var btndiv = document.createElement("div");
    var numinput_div = document.createElement("div");
    numinput_div.setAttribute("class", "buttonlike")
    numinput_div.setAttribute("style", "margin-left: 6px; margin-right: 3px");
    var numinput_label = document.createElement("span");
    numinput_label.setAttribute("style", "padding: 7px; padding-left: 12px");
    numinput_label.innerHTML = "Page number:";
    var numinput = document.createElement("input");
    numinput.setAttribute("class", "form-control");
    numinput.setAttribute("type", "text");
    numinput.setAttribute("style", "width: 50px; border-color: #444444");
    numinput.value = 1;
    numinput.addEventListener("change", (function () { table.pagenum = (numinput.value - 1); table.pagenum = Math.max(table.pagenum, 0); table.pagenum = Math.min(table.pagenum, (Math.trunc(table.length / table.pagesize))); table.refresh() }));
    numinput_div.appendChild(numinput_label);
    numinput_div.appendChild(numinput);
    var sizeinput_div = document.createElement("div");
    sizeinput_div.setAttribute("class", "buttonlike")
    sizeinput_div.setAttribute("style", "margin-left: 3px; margin-right: 6px");
    var sizeinput_label = document.createElement("span");
    sizeinput_label.setAttribute("style", "padding: 7px; padding-left: 12px");
    sizeinput_label.innerHTML = "Page size:";
    var sizeinput = document.createElement("input");
    sizeinput.setAttribute("class", "form-control");
    sizeinput.setAttribute("type", "text");
    sizeinput.setAttribute("style", "width: 100px; border-color: #444444");
    sizeinput.value = 50;
    sizeinput.addEventListener("change", (function () { table.pagesize = sizeinput.value; table.pagesize = Math.max(table.pagesize, 1); table.pagesize = Math.min(table.pagesize, table.length); table.refresh() }));
    sizeinput_div.appendChild(sizeinput_label);
    sizeinput_div.appendChild(sizeinput);
    var checkbounds_and_set = function () {
        table.pagenum = Math.max(table.pagenum, 0); table.pagenum = Math.min(table.pagenum, (Math.trunc(table.length / table.pagesize)));
        table.querySelector("tbody").scrollTop = 0;
        numinput.value = (table.pagenum + 1);
        table.refresh()
    }
    var forwardbtn = createbtn(">", function () { table.pagenum++; checkbounds_and_set() });
    var backwardbtn = createbtn("<", function () { table.pagenum--; checkbounds_and_set() });
    var lengthdisplay = document.createElement("span");
    lengthdisplay.setAttribute("style", "padding: 6px 12px; width: 200px")
    table.lengthdisplay = lengthdisplay;
    btndiv.appendChild(backwardbtn);
    btndiv.appendChild(numinput_div);
    btndiv.appendChild(sizeinput_div);
    btndiv.appendChild(forwardbtn);
    btndiv.appendChild(lengthdisplay);
    btndiv.setAttribute("align", "center");
    container.style.visibility = "hidden";
    head.innerHTML = header;
    container.setAttribute("class", "table-container");
    wrapper.setAttribute("class","table-wrap")
    table.setAttribute("class", "table table-striped table-all table-fixed" + attributes_table);
    table.appendChild(head);
    table.appendChild(body);
    table.sort_by = sort_by;
    table.asc = false;
    table.url = url;
    table.refresh = function () { makeapicall(table.url + "&sortby=" + table.sort_by + "&asc=" + table.asc + "&pagenumber=" + table.pagenum + "&pagesize=" + table.pagesize + "&filters=" + JSON.stringify(table.filters) + table.filter_url, function (message) { updatetable(table.getElementsByTagName("tbody")[0], message) }) };
    table.pagenum = 0;
    table.pagesize = 50;
    table.length = 0;
    table.filters = {};
    table.filter_url = "";
    table.make_emoji = make_emoji;
    table.row_widths = row_widths;
    var row_id = 0;
    table.querySelectorAll("th").forEach(th => {
        if (row_id < row_widths.length) {
            th.style.width = row_widths[row_id] + "%";
        }
        row_id++;
    })
    table.setAttribute("style", "margin-bottom: 10px")
    container.appendChild(table);
    container.appendChild(btndiv);
    wrapper.appendChild(container);
    data_div.appendChild(wrapper);
    return container;
}

function maketablessortable(table, filterable = false) {
    var i = 0;
    table.querySelectorAll('th').forEach(th => th.row_id = i++);
    table.querySelectorAll('th').forEach(th => { if (th.row_id == table.sort_by) { th.innerHTML = th.innerHTML + (table.asc ? String.fromCharCode(9650) : String.fromCharCode(9660)) } });
    table.querySelectorAll('th').forEach(th => th.addEventListener('click', (() => {
        table.querySelector('tr').querySelectorAll('th').forEach(th2 => {
            th2.innerHTML = th2.innerHTML.replace(String.fromCharCode(9650), "");
            th2.innerHTML = th2.innerHTML.replace(String.fromCharCode(9660), "");
        });
        if (table.sort_by == th.row_id) {
            table.asc = !table.asc;
        } else {
            table.asc = false;
        }
        th.innerHTML = th.innerHTML + (table.asc ? String.fromCharCode(9650) : String.fromCharCode(9660));
        table.sort_by = th.row_id;
        table.refresh();
    })));
    if (filterable) {
        var inputrow = document.createElement("tr");
        table.querySelectorAll('th').forEach(th => inputrow.innerHTML += "<th><input type=\"text\" name=\"" + th.getAttribute("name") + "\" style=\"width: 100%\"></th>");
        table.querySelector('thead').appendChild(inputrow);
        table.querySelector("thead").querySelectorAll("input").forEach(input => input.addEventListener("change", (() => {
            var filters = {};
            table.querySelector("thead").querySelectorAll("input").forEach(input2 => { if (input2.value != "") { filters[input2.name] = String(encodeURI(input2.value)) } });
            table.filters = filters;
            table.refresh();
        })));
    }
}

function activitybyweekday() {
    changemode(document.getElementById("btn_abw"));
    var chart = createchart("abw").chart;
    add_filters([chart], chart.url, "", true, true, true, false, false);
}

function activitybydaytime() {
    changemode(document.getElementById("btn_abdt"));
    var chart = createchart("abdt").chart;
    add_filters([chart], chart.url, "", true, true, false, true, false);
}

function activitybytime() {
    changemode(document.getElementById("btn_abt"));
    var chart = createchart("abt").chart;
    add_filters([chart], chart.url, "", true, true, true, true, true);
    chart.options.scales.xAxes = [{ type: "time" }];
}

function switchlang() {
    var langmain = document.getElementById("langmain");
    var devmain = document.getElementById("devmain");
    var chatmain = document.getElementById("chatmain");
    makeapicall(("setlang?lang=" + langmain.options[langmain.selectedIndex].text + "&dev=" + devmain.options[devmain.selectedIndex].text) + "&chat=" + chatmain.options[chatmain.selectedIndex].text, function(){});
}

function add_name_filter(parent_div, id_additional = "", prepend = false) {
    var select = add_select(parent_div, [], [], "Filter by name", id_additional, prepend);
    callback = function (select) {
        return function (message) {
            var names = JSON.parse(message);
            for (var i = 0; i < names.length; i++) {
                var option = document.createElement("option");
                option.innerHTML = names[i];
                option.value = names[i];
                select.appendChild(option);
            }
        }
    }
    makeapicall("getnames", callback(select));
    return select;
}

function add_select(parent_div, options, labels, label, id_additional = "", prepend = false, empty_option = true) {
    var name_select_div = document.createElement("div");
    name_select_div.setAttribute("class", "buttonlike");
    name_select_div.innerHTML = "<span style=\"padding: 7px; padding-left: 12px\"> " + label + " </span>";
    var select = document.createElement("select");
    select.setAttribute("id", "name_sel" + id_additional);
    select.setAttribute("class", "form-control");
    select.setAttribute("style", "width: 200px");
    if (empty_option) {
        select.innerHTML = "<option value=\"\"></option>";
    }
    name_select_div.appendChild(select);
    if (prepend) {
        parent_div.insertBefore(name_select_div, parent_div.firstChild);
    } else {
        parent_div.appendChild(name_select_div);
    }
    for (var i = 0; i < options.length; i++) {
        var option = document.createElement("option");
        option.innerHTML = labels[i];
        option.value = options[i];
        select.appendChild(option);
    }
    return select;
}

function add_time_select(parent_div, callback, id_additional = "", prepend = false) {
    var timefilterdiv = document.createElement("div");
    timefilterdiv.setAttribute("class", "buttonlike secondary_control");
    timefilterdiv.setAttribute("style", "width: 300px; height: 34px; margin-right: 4px");
    timefilterdiv.innerHTML = "<span style=\"padding: 7px; padding-left: 12px\">Filter by time</span><input id=\"timefilter" + id_additional + "\" name=\"dates\" type=\"text\" style=\"width: 180px; border: none; padding: 7; vertical-align: top; border-radius: 4px\"><input type=\"checkbox\" id=\"timefilter_check" + id_additional + "\" style=\"margin-left:4px; margin-top: 10px\">"
    if (prepend) {
        parent_div.insertBefore(timefilterdiv, parent_div.firstChild);
    } else {
        parent_div.appendChild(timefilterdiv);
    }

    $('#timefilter' + id_additional).daterangepicker({
        ranges: {
            'Today': [moment(), moment()],
            'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
            'Last 7 Days': [moment().subtract(6, 'days'), moment()],
            'Last 30 Days': [moment().subtract(29, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')],
            'Last Year': [moment().subtract(1, 'year').startOf('year'), moment().subtract(1, 'year').endOf('year')],
            'This Year': [moment().startOf('year'), moment().endOf('year')]
        },
        "startDate": moment().subtract(1, 'month').format("MM/DD/YYYY"),
        "endDate": moment().format("MM/DD/YYYY")
    }, callback);
}

function add_filters(outputs, spec_string, url_additional = "", filter_types = true, filter_names = true, filter_daytime = true, filter_weekday = true, aggregation_input = false) {
    var ctrl_div = document.getElementById("controls");
    var checkbox_div = document.createElement("div");
    checkbox_div.setAttribute("style", "margin: 5px")
    checkbox_div.setAttribute("id", spec_string + "_checkboxes");

    if (filter_types) {
        var ctype_filter_select = document.createElement("select");
        ctype_filter_select.setAttribute("id", "ctype_select");
        ctype_filter_select.setAttribute("multiple", "multiple");
        var post_type_select = document.createElement("div");
        post_type_select.setAttribute("id", "post_type_select");
        post_type_select.setAttribute("multiple", "multiple");
        var permessage_select = document.createElement("div");
        permessage_select.setAttribute("id", "permessage_select");
        permessage_select.setAttribute("multiple", "multiple");
        var perall_select = document.createElement("div");
        perall_select.setAttribute("id", "perall_select");
        perall_select.setAttribute("multiple", "multiple");
        var percharacter_select = document.createElement("div");
        percharacter_select.setAttribute("id", "percharacter_select");
        percharacter_select.setAttribute("multiple", "multiple");
        var pwc_select = document.createElement("div");
        pwc_select.setAttribute("id", "pwc_select");
        pwc_select.setAttribute("multiple", "multiple");
        var pergeneral_select = document.createElement("div");
        pergeneral_select.setAttribute("id", "pergeneral_select");
        pergeneral_select.setAttribute("multiple", "multiple");

        pwc_select.innerHTML = "<option selected=\"selected\">Messages</option><option>Text Elements</option><option>Characters</option>";
        ctype_filter_select.innerHTML = "<option>Words</option><option>Emojis</option><option>Punctuation</option>";
        post_type_select.innerHTML = "<option>Media</option><option>Log Messages</option>";
        permessage_select.innerHTML = "<option>Emojis per Message</option><option>Punctuation per Message</option><option>Words per Message</option>";
        perall_select.innerHTML = "<option>Emojis per Textelement</option><option>Punctuation per Text Element</option><option>Words per Textelement</option";
        percharacter_select.innerHTML = "<option>Emojis per Character</option><option>Punctuation per Character</option><option>Words per Character</option>";
        pergeneral_select.innerHTML = "<option>Characters per Message</option><option>Text Elements per Message</option><option>Characters per Textelement</option><option>Characters per Word</option>";

        checkbox_div.appendChild(pwc_select);
        checkbox_div.appendChild(ctype_filter_select);
        checkbox_div.appendChild(post_type_select);
        checkbox_div.appendChild(permessage_select);
        checkbox_div.appendChild(perall_select);
        checkbox_div.appendChild(percharacter_select);
        checkbox_div.appendChild(pergeneral_select);
    }

    if (filter_names) {
        name_select = add_name_filter(checkbox_div);
    }

    if (aggregation_input) {
        var aggr_input_div = document.createElement("div");
        aggr_input_div.setAttribute("class", "buttonlike");
        aggr_input_div.innerHTML = "<span style=\"padding: 7px; padding-left: 12px\">Aggregate by days:</span>";
        aggr_input = document.createElement("input");
        aggr_input.setAttribute("id", "aggr_input");
        aggr_input.setAttribute("type", "text");
        aggr_input.setAttribute("class", "form-control");
        aggr_input.setAttribute("style", "width: 100px")
        aggr_input_div.appendChild(aggr_input);
        checkbox_div.appendChild(aggr_input_div);
    }

    if (filter_daytime) {
        var daytime_options = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"];
        daytime_select = add_select(checkbox_div, daytime_options, daytime_options, "Filter by daytime", "_dt");
    }

    if (filter_weekday) {
        var weekday_options = ["0", "1", "2", "3", "4", "5", "6"];
        weekday_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Satursday", "Sunday"];
        weekday_select = add_select(checkbox_div, weekday_options, weekday_labels, "Filter by weekday", "_wd");
    }

    ctrl_div.appendChild(checkbox_div);

    if (filter_types) {
        $('#pwc_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Activity Type") });
        $('#ctype_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Text Elements") });
        $('#post_type_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Special Messages") });
        $('#permessage_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Average per Message") });
        $('#perall_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Average per Textelement") });
        $('#percharacter_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Average per Character") });
        $('#pergeneral_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Average per Miscellaneous") });
    }

    var checkbox_onclick = (() => {
        var url = url_additional;
        if (filter_types) {
            params = ["getmessages", "getall", "getchars", "getwords", "getemojis", "getpunct", "getmedia", "getlogs", "getepmsg", "getppmsg", "getwpmsg", "getepa", "getppa", "getwpa", "getepc", "getppc", "getwpc", "getcpmsg", "getapmsg", "getcpa", "getcpw"];
            n = 0;
            checkbox_div.querySelectorAll('li').forEach(li => li.querySelectorAll("input").forEach(input_inner => { url += ((input_inner.checked) ? "&" + params[n] + "=true" : ""); n++ }));
        }
        if (filter_names) {
            url += append_select_to_url("namefilter", name_select, true);
        }
        if (aggregation_input) {
            var aggr = aggr_input.value;
            if (aggr != "") {
                url += "&aggregate=" + aggr;
            }
        }
        if (filter_daytime) {
            url += append_select_to_url("daytimefilter", daytime_select);
        }
        if (filter_weekday) {
            url += append_select_to_url("weekdayfilter", weekday_select, true);
        }
        if (document.getElementById("timefilter_check").checked) {
            url += "&timefilter=" + $('#timefilter').data("daterangepicker").startDate.format("YYYY-MM-DD") + "t" + $('#timefilter').data("daterangepicker").endDate.format("YYYY-MM-DD")
        }
        for (var i = 0; i < outputs.length; i++) {
            outputs[i].filter_url = url;
            outputs[i].refresh();
        }
    });

    add_time_select(checkbox_div, checkbox_onclick);

    checkbox_div.querySelectorAll('input').forEach(input => input.addEventListener('click', checkbox_onclick));
    checkbox_div.querySelectorAll('select').forEach(select => select.addEventListener('change', checkbox_onclick));

    if (aggregation_input) {
        aggr_input.addEventListener('change', checkbox_onclick);
    }

    checkbox_onclick();
}

function updatechart(chart, data) {
    chart.data.datasets = [];
    var content = JSON.parse(data);
    var data_dicts = []
    var labels = content[0];
    for (var i = 0; i < content[1].length; i++) {
        data_dicts = []
        for (var j = 0; j < content[1][i][1].length; j++) {
            if (content[1][i][1][j].length == undefined) {
                data_dicts.push({ y: content[1][i][1][j] });
            } else {
                data_dicts.push({ x: content[1][i][1][j][0], y: content[1][i][1][j][1] });
            }
        }
        chart.data.datasets.push({ label: content[1][i][0], data: data_dicts, backgroundColor: 'rgba(155, 155, 155, 1)' });
    }
    chart.data.labels = labels;
    chart.update({ duration: 0 });
    chart.resize();
}

function createchart(url, type = 'bar') {
    var data_div = document.getElementById("main_data");
    var wrapper_div = document.createElement("div");
    wrapper_div.style.height = "100%";
    var data_canvas = document.createElement("canvas");
    data_canvas.setAttribute("style", "height: 80%")
    var chart = new Chart(data_canvas, {
        type: type,
        data: {
            labels: "",
            datasets: [{
                label: "",
                data: [],
                backgroundColor: 'rgba(155, 155, 155, 1)',
            }]
        },
        options: {
            maintainAspectRatio: false,
            tooltips: {
                displayColors: false,
            },
            scales: {
                yAxes: [{
                    ticks: {
                        beginAtZero: true
                    }
                }]
            }
        }
    });
    wrapper_div.appendChild(data_canvas);
    data_div.appendChild(wrapper_div);
    chart.url = url;
    chart.filter_url = "";
    chart.refresh = function () { makeapicall(chart.url + chart.filter_url, function (message) { updatechart(chart, message) }) };
    wrapper_div.chart = chart;
    return wrapper_div;
}

function changemode(button, none = false) {
    document.getElementById("main_data").innerHTML = "";
    document.getElementById("primary_controls").querySelectorAll("button").forEach((button) => {button.setAttribute("style", "background-color: buttonface");})
    if (!none) {
        button.setAttribute("style", "background-color: #ccccff");
    }
    destroyallothers();
}

function destroyallothers() {
    deleteiffound("abw_checkboxes");
    deleteiffound("abdt_checkboxes");
    deleteiffound("abt_checkboxes");
    deleteiffound("abn_checkboxes");
    deleteiffound("abn_radiobuttons");
    deleteiffound("ubw_checkboxes");
    $(".daterangepicker").remove();
}

function deleteiffound(id) {
    if (document.getElementById(id) != null) {
        document.getElementById(id).remove();
    }
}

function createbtn(label, fun) {
    var btn = document.createElement("button");
    btn.innerHTML = label;
    btn.setAttribute("class", "btn");
    btn.onclick = fun;
    return btn;
}

function makeapicall(url, callback) {
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function () {
        if (this.readyState == 4 && this.status == 200) {
            callback(this.responseText);
        }
    };
    var url = url.replace("?", "&").replace("&", "?");
    xhttp.open("GET", api_url + url, true);
    xhttp.send();
}
