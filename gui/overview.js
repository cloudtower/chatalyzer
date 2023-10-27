function bynamepie() {
    makeapicall("abn?mode=chart&getmessages=true", function (message) {
        data = JSON.parse(message);
        var data_div = document.getElementById("main_data");
        var wrapper_div = document.createElement("div");
        wrapper_div.style.height = "100%";
        var data_canvas = document.createElement("canvas");
        data_canvas.setAttribute("style", "height: 80%");
        var pie = new Chart(data_canvas, {
            type: 'pie',
            data: {
                labels: data[0],
                datasets: [{
                    label: "",
                    data: data[1][0][1],
                    backgroundColor: 'rgba(155, 155, 155, 1)',
                }]
            },
            options: {}
        });
        wrapper_div.appendChild(data_canvas);
        data_div.appendChild(wrapper_div);
    })
}