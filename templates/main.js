<script type="text/javascript" src="https://www.google.com/jsapi"></script>

function property_search(){
    var req = new XMLHttpRequest();
    //response received function
    req.onreadystatechange=function(){
        if (req.readyState==4 && req.status==200){
        document.getElementById('main_chart')
        var serverdata = eval( '(' + req.responseText + ')');
        draw_chart( serverdata );
        }
    }

    str = 'zipcode='+documents.forms['zipcode']
    req.open('GET', '/search/?'+str, true);
    req.send();
}

function draw_chart(serverdata) {
    google.load("visualization", "1", {packages:["corechart"]});
    google.setOnLoadCallback(drawChart);
    var price_plot = new Array();
    price_plot[0] = [ 'Date', 'Price' ] 
    for ( i in serverdata.sales ) {
        proce_plot.append( serverdata.sales[i].date, serverdata.sale[i].price );
    }
    function drawChart() {
      var data = google.visualization.arrayToDataTable( price_plot );

      var options = {
        title: 'Sales vs. Time,
        hAxis: {title: 'Sales', minValue: 0, maxValue: 15},
        vAxis: {title: 'Proce', minValue: 0, maxValue: 15},
        legend: 'none'
      };

      var chart = new google.visualization.ScatterChart(document.getElementById('main_chart'));

      chart.draw(data, options);
}
