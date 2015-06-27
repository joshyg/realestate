var serverdata;
sales_array = new Array();;
roi_array = new Array();;
var num_datasets = 0;
google.load("visualization", "1", {packages:["corechart"]});
google.setOnLoadCallback(draw_chart);

function init_page() {
    sales_array[0] = ['Date']
    roi_array[0] = ['Date']
    for ( var year = 1990; year <= 2015; year++ ) {
        for ( var month = 1; month <= 12; month++ ) {
            sales_array.push( [ month+'/'+year ] );
            roi_array.push( [ month+'/'+year ] );
        }
    }
}

function draw_chart() {
    console.log('in draw chart');
    console.log('initial sales_array')
    console.log(sales_array);
    if ( serverdata ) {
        var sales_array_index=0; 
        sales_array[0].push( new String ( serverdata.header ) );
        roi_array[0].push( new String ( serverdata.header ) );
        for (i in serverdata.sales) {
            sales_array_index += 1; 
            console.log( sales_array[sales_array_index] );
            sales_array[sales_array_index].push( serverdata.sales[i].avg_price );
            roi_array[sales_array_index].push( serverdata.sales[i].roi );
        }  
        sales_array = sales_array.slice(0, sales_array_index+1);
        roi_array   = roi_array.slice(0, sales_array_index+1);
        console.log('sales_array')
        console.log(sales_array);
        var data = google.visualization.arrayToDataTable( sales_array );

        
        var options = {
          title: 'Sales vs. Time',
          hAxis: {title: 'Sales'},
          vAxis: {title: 'Price'},
          curveType: 'function',
          legend: { position: 'bottom' }
        };
      
        if ( serverdata.sales.length >= 1 ){
            var chart = new google.visualization.LineChart(document.getElementById('main_chart'));
            chart.draw(data, options);
        }
        
        data = google.visualization.arrayToDataTable( roi_array );

        options = {
          title: 'ROI vs. Time',
          hAxis: {title: 'Sales'},
          vAxis: {title: 'ROI'},
          curveType: 'function',
          legend: { position: 'bottom' }
        };

        if ( serverdata.sales.length >= 1 ){
            var chart = new google.visualization.LineChart(document.getElementById('roi_chart'));
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
            draw_chart()
        }
    }

    console.log('sending...');
    str = 'search_term='+document.forms['main_search']['search_term'].value;
    req.open('GET', '/search/?'+str, true);
    req.send();
}


