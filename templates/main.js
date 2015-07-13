var serverdata;
sales_array = new Array();;
roi_array = new Array();;
var num_datasets = 0;
advanced_search= 0;
google.load("visualization", "1", {packages:["corechart"]});
google.setOnLoadCallback(draw_chart);

function init_page() {
    sales_array[0] = ['Date']
    roi_array[0] = ['Date']
}

function draw_chart() {
    console.log('in draw chart');
    console.log('initial sales_array')
    if ( serverdata ) {
        var sales_array_index=0; 
        sales_array[0].push( String ( serverdata.header ) );
        roi_array[0].push( String ( serverdata.header ) );
        for (i in serverdata.sales) {
            sales_array_index += 1; 
            if ( sales_array.length <= sales_array_index ) {
                sales_array.push( [ serverdata.sales[i].period, serverdata.sales[i].avg_price ] );
                roi_array.push(   [ serverdata.sales[i].period, serverdata.sales[i].roi ] );
            }  
            else {
                sales_array[sales_array_index].push( serverdata.sales[i].avg_price );
                roi_array[sales_array_index].push(   serverdata.sales[i].roi );
            }  
        }  
        sales_array = sales_array.slice(0, sales_array_index+1);
        roi_array   = roi_array.slice(0, sales_array_index+1);
        console.log('sales_array')
        console.log(sales_array);
        var data = google.visualization.arrayToDataTable( sales_array );

        
        var options = {
          title: 'Sales vs. Time',
          hAxis: {title: 'Dates'},
          vAxis: {title: 'Price'},
          curveType: 'function',
          legend: { position: 'right' }
        };
      
        if ( serverdata.sales.length >= 1 ){
            var chart = new google.visualization.LineChart(document.getElementById('main_chart'));
            chart.draw(data, options);
        }
        
        data = google.visualization.arrayToDataTable( roi_array );

        options = {
          title: 'ROI vs. Time',
          hAxis: {title: 'Dates'},
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
            document.getElementById("main_form").className = "results_form";
            serverdata = eval( '(' + req.responseText + ')');
            draw_chart()
        }
    }

    console.log('sending...');
    str = 'search_term='+document.forms['main_search']['search_term'].value;
    if ( advanced_search == 1 ) {
        str += '&region_type='+document.forms['main_search']['region_type'].value;
        str += '&data_type='+document.forms['main_search']['data_type'].value;
    }
    req.open('GET', '/search/?'+str, true);
    req.send();
}

function show_advanced_search() {
    advanced_search = 1;
    search_form = 'Region Type';
    search_form += '<select name="region_type">';
    search_form += '<option value=0>State</option>';
    search_form += '<option value=1>City</option>';
    search_form += '<option value=2>County</option>';
    search_form += '<option value=3>Neighborhood</option>';
    search_form += '<option value=4>Zip</option>';
    search_form += '</select>';
    search_form += '<br>';
    search_form += 'Data';
    search_form += '<select name="data_type">';
    search_form += '<option value=0>Median Sale Price All Homes</option>';
    search_form += '<option value=1>Median Price To Rent Ratio All Homes</option>';
    search_form += '<option value=2>Median Price Per Sqft Single Family Residence</option>';
    search_form += '</select>';
    document.getElementById('advanced_search').innerHTML = search_form;
}
