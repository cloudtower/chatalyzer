function summary_init() {
    var main_table_body = document.getElementById("chats_table_body");
    var stats_table_body = document.getElementById("stats_table_body");
    makeapicall("gettotalsummary", (message) => { stats_table_body.parentNode.row_widths = []; updatetable(stats_table_body, message, minimal=true) });
    makeapicall("getchatssummary", (message) => {
        main_table_body.parentNode.row_widths = [];
        updatetable(main_table_body, message, minimal=true);
        main_table_body.childNodes.forEach(tr => {
            var newcell = tr.insertCell(6);
            newcell.innerHTML = "<button onclick='loadfile(\"" + tr.childNodes[0].innerHTML + "\", true, false);location.href=\"main.html\"'><i class='fas fa-angle-right' style='font-size: 18px; color: #000000'></button>";
        })
    });
}