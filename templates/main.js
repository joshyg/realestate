var serverdata;
google.load("visualization", "1", {packages:["corechart"]});
google.setOnLoadCallback(drawChart);

function drawChart() {
    console.log('in draw chart');
    if ( serverdata ) {
        sales_array = new Array();
        sales_array.push( [ 'Date', 'Price' ] );
        for (i in serverdata.sales) {
            if (  serverdata.sales[i].price  < 5000000 ) {
                sales_array.push( [ new Date( serverdata.sales[i].year, serverdata.sales[i].month, serverdata.sales[i].day), serverdata.sales[i].price ] );
            }
        }  
        var data = google.visualization.arrayToDataTable( sales_array );
        var formatter_short = new google.visualization.DateFormat({formatType: 'short'});
        formatter_short.format(data, 0);
        console.log('date formatted.');

        
        var options = {
          title: 'Sales vs. Time',
          hAxis: {title: 'Sales'},
          vAxis: {title: 'Price', minValue: 0, maxValue: 5000000},
          legend: 'none'
        };
      
        if ( serverdata.sales.length >= 1 ){
            var chart = new google.visualization.ScatterChart(document.getElementById('main_chart'));
            console.log(chart);
            chart.draw(data, options);
        }
    }
  
}

function ajax_submit(){
    var req = new XMLHttpRequest();
    //response received function
    req.onreadystatechange=function(){
        if (req.readyState==4 && req.status==200){
            document.getElementById('main_chart');
            serverdata = eval( '(' + req.responseText + ')');
            drawChart()
        }
    }

    console.log('sending...');
    str = 'zip='+document.forms['main_search']['zip'].value;
    req.open('GET', '/search/?'+str, true);
    req.send();
}


