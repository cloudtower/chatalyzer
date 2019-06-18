function get_all_options() {
    makeapicall("getoptions", function (message) {
        data = JSON.parse(message);
        table = document.getElementById("table_options");
        for (const [key, value] of Object.entries(data)) {
            row = table.insertRow(0);
            row.key = key;
            desc_cell = row.insertCell(0);
            desc_cell.innerHTML = value["desc"];
            desc_cell.setAttribute("style", "vertical-align: middle");
            select_cell = row.insertCell(1);
            select = add_select(select_cell, value["options"], value["options"], "", "", false, false);
            select.selectedIndex = Math.min(value["options"].length, value["selected"]);
            select.parentNode.setAttribute("style", "margin-bottom: 0");
            callback = function (row, select) {
                return function () {
                    set_option(row.key, select.selectedIndex);
                }
            };
            select.addEventListener("change", callback(row, select));
            row.setAttribute("class","buttonlike");
        }
    })
}

function set_option(key, value) {
    makeapicall("setoption?key=" + key + "&value=" + value);
}