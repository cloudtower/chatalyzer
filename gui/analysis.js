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
    var table = createtable("", "<tr><th name=\"name\">Name</th><th name=\"date\">Date</th><th name=\"time\">Time</th><th name=\"hour\">Hour</th><th name=\"weekday\">Weekday</th><th name=\"ispost\">Is Post?</th><th name=\"ismedia\">Is Media?</th><th name=\"islogmsg\">Is Logmsg?</th><th name=\"words\">Words</th><th name=\"chars\">Chars</th><th name=\"emojis\">Emojis</th><th name=\"puncts\">Punctuation</th></tr>", "actraw", 0, document.getElementById("main_data"), []).querySelector("table");
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
    add_filters([table_e, table_l, table_p, table_u, table_w], "ubw", "", false, true, true, true, false, true);
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