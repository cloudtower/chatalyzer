function getloadedfile() {
    makeapicall("getloadedfile", function (message) {
        document.getElementById("current_file_display").innerHTML = message;
    })
}

function pickfile() {
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function () {
        if (this.readyState == 4 && this.status == 200) {
            pickfile_handle(this.responseText);
            getloadedfile();
        }
    };
    dialog.showOpenDialog({ properties: ['openFile'] }, function (file) {
        xhttp.open("GET", "http://127.0.0.1:5000/api/loadfile?filename=" + String(encodeURI(file)).replace(/\//g, "%2F"), true);
        xhttp.send();
    });
}

function pickfile_handle(message) {
    swal(message);
}

function activitybyname() {
    changemode();
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
    changemode();
    document.getElementById("main_data").innerHTML = "";
    var table = createtable("", "table-wrap", "<tr><th name=\"name\">Name</th><th name=\"date\">Date</th><th name=\"hour\">Hour</th><th name=\"weekday\">Weekday</th><th name=\"ispost\">Is Post?</th><th name=\"ismedia\">Is Media?</th><th name=\"islogmsg\">Is Logmessage?</th><th name=\"words\">Words</th><th name=\"chars\">Chars</th><th name=\"emojis\">Emojis</th><th name=\"puncts\">Punctuation</th></tr>", "actraw?placeholder=uninteresting", 0).querySelector("table");
    table.refresh();
    maketablessortable(table, true);
}

function activitybyname_switch() {
    var data_div = document.getElementById("main_data");
    var is_table = document.getElementById("abn_radiobutton_table").checked;
    data_div.innerHTML = "";
    if (is_table) {
        deleteiffound("abn_checkboxes");
        var table_div = createtable("", "table-wrap", "<tr><th>Name</th><th>Posts</th><th>Media</th><th>Logs</th><th>Words</th><th>Chars</th><th>Emojis</th><th>Puncts</th></tr>", "abn?placeholder=uninteresting", 0);
        var table = table_div.querySelector("table");
        table.refresh();
        maketablessortable(table);
    } else {
        var chart = createchart().chart;
        add_act_controls(chart, "abn", false, "?mode=chart");
    }
}

function usagebyword() {
    changemode();
    var data_div = document.getElementById("main_data");
    data_div.innerHTML = "";
    var table_w_div = createtable("", "table-wrap", "<tr><th name=\"word\">Word</th><th>Usage</th></tr>", "ubc?type=word", 1);
    var table_e_div = createtable("", "table-wrap", "<tr><th>Emoji</th><th>Usage</th></tr>", "ubc?type=emoji", 1);
    var table_p_div = createtable("", "table-wrap", "<tr><th>Puctuation</th><th>Usage</th></tr>", "ubc?type=puncts", 1);
    var table_u_div = createtable("", "table-wrap", "<tr><th>Uncategorized</th><th>Usage</th></tr>", "ubc?type=uncat", 1);
    var table_w = table_w_div.querySelector("table");
    var table_e = table_e_div.querySelector("table");
    var table_p = table_p_div.querySelector("table");
    var table_u = table_u_div.querySelector("table");
    table_w.refresh(table_w);
    table_e.refresh(table_e);
    table_p.refresh(table_p);
    table_u.refresh(table_u);
    maketablessortable(table_w);
    maketablessortable(table_p);
    maketablessortable(table_e);
    maketablessortable(table_u);
}

function updatetable(tbody, message) {
    tbody.innerHTML = "";
    var content = JSON.parse(message);
    if (content.length != 0) { tbody.parentNode.parentNode.style.visibility = "visible"; }
    for (i = 0; i < content.length; i++) {
        var row = tbody.insertRow(i);
        for (j = 0; j < content[i].length; j++) {
            row.insertCell(j).innerHTML = content[i][j];
        }
    }
    var table = tbody.parentNode;
    table.pagenum = Math.max(table.pagenum, 0);
    if (content.length < table.pagesize) {
        table.pagenum -= 1;
    }
}

function createtable(attributes_table, attributes_div, header, url, sort_by) {
    var data_div = document.getElementById("main_data");
    var table = document.createElement("table");
    var head = document.createElement("thead");
    var body = document.createElement("tbody");
    var div = document.createElement("div");
    var btndiv = document.createElement("div");
    var forwardbtn = createbtn(">", function () { table.pagenum += 1; table.querySelector("tbody").scrollTop = 0; table.refresh() });
    var backwardbtn = createbtn("<", function () { table.pagenum -= 1; table.querySelector("tbody").scrollTop = 0; table.refresh() });
    var numinput = document.createElement("input");
    numinput.setAttribute("class", "btn");
    numinput.setAttribute("type", "text");
    numinput.setAttribute("style", "width: 50px; border-color: #444444");
    numinput.value = 50;
    numinput.addEventListener("change", (function () { table.pagesize = numinput.value; table.refresh() }));
    btndiv.appendChild(backwardbtn);
    btndiv.appendChild(numinput);
    btndiv.appendChild(forwardbtn);
    btndiv.setAttribute("align", "center");
    div.style.visibility = "hidden";
    head.innerHTML = header;
    div.setAttribute("class", "" + attributes_div);
    table.setAttribute("class", "table table-striped table-all table-fixed" + attributes_table);
    table.appendChild(head);
    table.appendChild(body);
    table.sort_by = sort_by;
    table.asc = false;
    table.url = url;
    table.refresh = function () { makeapicall(table.url + "&sortby=" + table.sort_by + "&asc=" + table.asc + "&pagenumber=" + table.pagenum + "&pagesize=" + table.pagesize + "&filters=" + JSON.stringify(table.filters), function (message) { updatetable(table.getElementsByTagName("tbody")[0], message) }) };
    table.pagenum = 0;
    table.pagesize = 50;
    table.filters = {};
    table.setAttribute("style", "margin-bottom: 10px")
    div.appendChild(table);
    div.appendChild(btndiv);
    data_div.appendChild(div);
    return div;
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
        table.refresh(table);
    })));
    if (filterable) {
        var inputrow = document.createElement("tr");
        table.querySelectorAll('th').forEach(th => inputrow.innerHTML += "<th><input type=\"text\" name=\"" + th.innerHTML.replace(String.fromCharCode(9650), "").replace(String.fromCharCode(9660), "") + "\" style=\"width: 100%\"></th>");
        table.querySelector('thead').appendChild(inputrow);
        table.querySelector("thead").querySelectorAll("input").forEach(input => input.addEventListener("change", (() => {
            var filters = {};
            table.querySelector("thead").querySelectorAll("input").forEach(input2 => { if (input2.value != "") { filters[input2.name] = String(encodeURI(input2.value)) } });
            console.log("changed");
            table.filters = filters;
            table.refresh(table);
        })));
    }
}

function activitybyweekday() {
    changemode();
    var chart = createchart().chart;
    add_act_controls(chart, "abw");
}

function activitybydaytime() {
    changemode();
    var chart = createchart().chart;
    add_act_controls(chart, "abdt");
}

function activitybytime() {
    changemode();
    var chart = createchart().chart;
    add_act_controls(chart, "abt", true, "?placeholder=uninteresting",  true);
    chart.options.scales.xAxes = [{ type: "time" }];
}

function switchlang() {
    var langmain = document.getElementById("langmain");
    makeapicall(("setlang?lang=" + langmain.options[langmain.selectedIndex].text), swal);
}

function add_act_controls(chart, spec_string, filter_names = true, url_additional = "?placeholder=uninteresting", aggregation_input = false) {
    var ctrl_div = document.getElementById("controls");
    var checkbox_div = document.createElement("div");
    checkbox_div.setAttribute("style","margin: 5px")
    checkbox_div.setAttribute("id", spec_string + "_checkboxes");

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
    pergeneral_select.innerHTML = "<option>Characters per Message</option><option>Text Elements per Message</option><option>Characters per Textelement</option>";

    checkbox_div.appendChild(pwc_select);
    checkbox_div.appendChild(ctype_filter_select);
    checkbox_div.appendChild(post_type_select);
    checkbox_div.appendChild(permessage_select);
    checkbox_div.appendChild(perall_select);
    checkbox_div.appendChild(percharacter_select);
    checkbox_div.appendChild(pergeneral_select);

    var timefilterdiv = document.createElement("div");
    timefilterdiv.setAttribute("class", "btn secondary_control");
    timefilterdiv.setAttribute("style", "width: 230px; height: 34px");
    timefilterdiv.innerHTML = "<i style=\"font-size: 16px; padding-right: 10px\" class=\"fa\">&#xf073;</i><input id=\"timefilter\" name=\"dates\" type=\"text\" style=\"width: 80%; border: none; padding: 0; vertical-align: top\"><input type=\"checkbox\" id=\"timefilter_check\" style=\"margin-left:6px\">"
    checkbox_div.appendChild(timefilterdiv);

    if (filter_names) {
        name_select_div = document.createElement("div");
        name_select_div.setAttribute("class","buttonlike");
        name_select_div.innerHTML = "<span style=\"padding: 7px; padding-left: 12px\">Filter by name:</span>";
        select = document.createElement("select");
        select.setAttribute("id", "name_sel");
        select.setAttribute("class", "btn form-control");
        select.setAttribute("style", "width: 200px")
        select.innerHTML = "<option></option>";
        name_select_div.appendChild(select);
        checkbox_div.appendChild(name_select_div);
        makeapicall("getnames", function (message) {
            var names = JSON.parse(message);
            for (i = 0; i < names.length; i++) {
                var option = document.createElement("option");
                option.innerHTML = names[i];
                select.appendChild(option);
            }
        });
    }

    if (aggregation_input) {
        aggr_input_div = document.createElement("div");
        aggr_input_div.setAttribute("class","buttonlike");
        aggr_input_div.innerHTML = "<span style=\"padding: 7px; padding-left: 12px\">Aggregate by days:</span>";
        aggr_input = document.createElement("input");
        aggr_input.setAttribute("id", "aggr_input");
        aggr_input.setAttribute("type","text");
        aggr_input.setAttribute("class", "btn form-control");
        aggr_input.setAttribute("style", "width: 100px")
        aggr_input_div.appendChild(aggr_input);
        checkbox_div.appendChild(aggr_input_div);
    }

    ctrl_div.appendChild(checkbox_div);

    $('#pwc_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Activity Type") });
    $('#ctype_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Text Elements") });
    $('#post_type_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Special Messages") });
    $('#permessage_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Average per Message") });
    $('#perall_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Average per Textelement") });
    $('#percharacter_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Average per Character") });
    $('#pergeneral_select').multiselect({ numberDisplayed: 1, buttonText: (() => "Average per Miscellaneous") });

    var checkbox_onclick = (() => {
        params = ["getmessages", "getall", "getchars", "getwords", "getemojis", "getpunct", "getmedia", "getlogs", "getepmsg", "getppmsg", "getwpmsg", "getepa", "getppa", "getwpa", "getepc", "getppc", "getwpc", "getcpmsg", "getapmsg", "getcpa"];
        i = 0;
        url = spec_string + url_additional;
        checkbox_div.querySelectorAll('li').forEach(li => li.querySelectorAll("input").forEach(input_inner => url += ("&" + params[i++] + "=" + input_inner.checked)));
        if (filter_names) {
            var name = select.options[select.selectedIndex].text;
            if (name != "") {
                url += "&namefilter=" + String(encodeURI(name));
            }
        }
        if (aggregation_input) {
            var aggr = aggr_input.value;
            if (aggr != "") {
                url += "&aggregate=" + aggr;
            }
        }
        if (document.getElementById("timefilter_check").checked) {
            url += "&timefilter=" + $('#timefilter').data("daterangepicker").startDate.format("YYYY-MM-DD") + "t" + $('#timefilter').data("daterangepicker").endDate.format("YYYY-MM-DD")
        }
        chart.refresh(url)
    });

    ctrl_div.querySelectorAll('input').forEach(input => input.addEventListener('click', checkbox_onclick));
    if (filter_names) {
        select.addEventListener('change', checkbox_onclick);
    }
    if (aggregation_input) {
        aggr_input.addEventListener('change', checkbox_onclick);
    }
    $('#timefilter').daterangepicker({
        ranges: {
            'Today': [moment(), moment()],
            'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
            'Last 7 Days': [moment().subtract(6, 'days'), moment()],
            'Last 30 Days': [moment().subtract(29, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
        },
        "startDate": moment().subtract(1, 'month').format("MM/DD/YYYY"),
        "endDate": moment().format("MM/DD/YYYY")
    }, checkbox_onclick);

    checkbox_onclick();
}

function updatechart(chart, data) {
    chart.data.datasets = [];
    var content = JSON.parse(data);
    var data_dicts = []
    labels = content[0];
    for (i = 0; i < content[1].length; i++) {
        data_dicts = []
        for (j = 0; j < content[1][i][1].length; j++) {
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

function createchart(type = 'bar') {
    var data_div = document.getElementById("main_data");
    data_div.innerHTML = "";
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
    data_div.appendChild(data_canvas);
    chart.refresh = function (url) { makeapicall(url, function (message) { updatechart(chart, message) }) };
    data_canvas.chart = chart;
    return data_canvas;
}

function changemode() {
    destroyallothers();
}

function destroyallothers() {
    deleteiffound("abw_checkboxes");
    deleteiffound("abdt_checkboxes");
    deleteiffound("abt_checkboxes");
    deleteiffound("abn_checkboxes");
    deleteiffound("abn_radiobuttons");
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
    xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function () {
        if (this.readyState == 4 && this.status == 200) {
            callback(this.responseText);
        }
    };
    xhttp.open("GET", api_url + url, true);
    xhttp.send();
}