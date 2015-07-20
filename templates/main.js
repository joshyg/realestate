var serverdata;
var sales_array = new Array();;
var pct_change_array = new Array();;
var num_datasets = 0;
var data_type = 0;
var advanced_search= 0;
google.load("visualization", "1", {packages:["corechart"]});
google.setOnLoadCallback(draw_chart);
var instruction_str = "Enter Zipcode, Neighborhood, City, County or State";


data_type_array = [ 
    'Median Sale Price All Homes',
    'Price/Rent ratio All Homes',
    'Median Price Per Sq Ft All Homes',
    'Median Price Per Sq ft Condo',
    'Median Price Per Sq ft Single Family',
    'Median Rental Price All Homes',
    'Median Rental Price Per Sq ft All Homes',
    'Pct Of Homes Increasing In Value',
    'Pct Of Homes Decreasing In Value',
    'Ratio Of Homes Sold as Foreclosure',
    '# Homes for Rent',
    'Turnover',
    'Sale Price To List Ratio',
    'Median Listing Price',
    'Median Listing Price Per Sq ft',
    'Pct of listings with Price Reductions'
]

function init_page() {
    document.getElementById('search_term').value=instruction_str;
    sales_array[0] = ['Date']
    pct_change_array[0] = ['Date']
}

function init_data_type_select() {
    var str = '<select name="data_type" class="selectpicker">'
    for ( i in data_type_array ) {
        str += '<option value='+i;
        if ( i == 0 ) {
            str += ' selected';
        }
        str += '>'+data_type_array[i]+'</option>';
    }
    str += '</select>'
    document.getElementById('data_type_select').innerHTML = str;
}

function draw_chart( ) {
    console.log('in draw chart');
    console.log('initial sales_array')
    document.getElementById('main_chart').style.display = 'block';
    document.getElementById('pct_change_chart').style.display = 'block';
    console.log(clear_chart);
    if ( serverdata.sales.length >= 1 ){
        var sales_array_index=0; 
        sales_array[0].push( String ( serverdata.header ) );
        pct_change_array[0].push( String ( serverdata.header ) );
        for (i in serverdata.sales) {
            sales_array_index += 1; 
            if ( sales_array.length <= sales_array_index ) {
                sales_array.push( [ serverdata.sales[i].period, serverdata.sales[i].avg_price ] );
                pct_change_array.push(   [ serverdata.sales[i].period, serverdata.sales[i].pct_change ] );
            }
            else {
                sales_array[sales_array_index].push( serverdata.sales[i].avg_price );
                pct_change_array[sales_array_index].push(   serverdata.sales[i].pct_change );
            }
        }
        sales_array = sales_array.slice(0, sales_array_index+1);
        pct_change_array   = pct_change_array.slice(0, sales_array_index+1);
        console.log('sales_array');
        console.log(sales_array);
        sales_data = google.visualization.arrayToDataTable( sales_array );

        
        var options = {
          title: data_type_array[ document.forms['main_search']['data_type'].value ],
          hAxis: {title: 'Dates'},
          vAxis: {title: 'Price'},
          curveType: 'function',
          legend: { position: 'right' }
        };
      
        if ( serverdata.sales.length >= 1 ){
            console.log('drawing sales chart');
            var sales_chart = new google.visualization.LineChart(document.getElementById('main_chart'));
            sales_chart.draw(sales_data, options);
        }
        
        pct_change_data = google.visualization.arrayToDataTable( pct_change_array );

        options = {
          title: 'Increase vs. Time',
          hAxis: {title: 'Dates'},
          vAxis: {title: 'Increase'},
          curveType: 'function',
          legend: { position: 'bottom' }
        };

        if ( serverdata.sales.length >= 1 ){
            var pct_change_chart = new google.visualization.LineChart(document.getElementById('pct_change_chart'));
            pct_change_chart.draw(pct_change_data, options);
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
            draw_chart();
            modify_search_bar();
            update_warning();
        }
    }

    // If the data type has changed we clear the charts.
    if ( data_type != document.forms['main_search']['data_type'].value ) {
        data_type = document.forms['main_search']['data_type'].value;
        clear_chart();
    }

    console.log('sending...');
    str = 'search_term='+document.forms['main_search']['search_term'].value;
    str += '&data_type='+data_type;
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

function modify_search_bar() {
    $('#help_modal_div')[0].style.display="none";
    document.getElementById('clear_button').innerHTML = '<button type="button" class="btn btn-primary btn-large" onclick="clear_chart()" >Clear</button>';
}

function update_warning() {
    if ( serverdata.warning != '' ) {
        document.getElementById('warning').innerHTML = '<b>'+serverdata.warning+'</b/>';
    }
    else {
        document.getElementById('warning').innerHTML = '';
    }
}

function clear_chart() {
    sales_array = [ ['Date'] ];
    pct_change_array = [ ['Date'] ];
    serverdata = {};
    console.log( 'clearing charts' );
    document.getElementById('main_chart').style.display = "none";
    document.getElementById('pct_change_chart').style.display = "none";
}

function clear_textbox() {
    if ( $('#search_term')[0].value == instruction_str ) {
        console.log('in clear_textbox');
        document.getElementById('search_term').value = '';
    }
}
