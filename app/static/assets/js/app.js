// Datatables stuff

var fnFormatDetails = function ( oTable, nTr, details)
{
    var aData = oTable.fnGetData( nTr );
    var sOut = '<dl class="dl-horizontal">';
    for (var i in details) {
        var rv = aData;
        if (typeof details[i] === 'string') {
            rv = rv[details[i]];
        } else {
            for (var j in details[i]) {
                rv = rv[details[i][j]];
            }
        }
        sOut += '<dt>' + i + '</dt><dd>' + (rv || 'none') + '</li>';
    }
    sOut += '</dl>';
    return sOut;
}

var activate_table = function(table_id, options, data) {
    var table = $('#' + table_id);
    var options = options || {};
    options.bPaginate = options.bPaginate || true;
    options.bLengthChange = options.bLengthChange || false;
    options.bFilter = options.bFilter || false;
    options.bSort = options.bSort || true;
    options.bInfo = options.bInfo || true;
    options.bAutoWidth = options.bAutoWidth || false;
    options.iDisplayLength = options.iDisplayLength || 50;
    options.sPaginationType = "full_numbers";
    if (data) {
        var columns = [];
        for (var i in data.columns) {
            columns.push({'mData': data.columns[i]});
        }
        $.extend(options, {
            "bProcessing": true,
            "sAjaxDataProp": "result",
            "sAjaxSource": data.source,
            "aoColumns": columns
        });
    }
    if (data.details) {
    //  Insert a 'details' column to the table
        $(table).find('tr').each( function () {
            $(this).prepend('<th width="5px">&nbsp;</th>');
        } );
        //  Initialize DataTables, with no sorting on the 'details' column
        options.aoColumns.unshift({ 'mData': null, "bSortable": false, "aTargets": [ 0 ] });
        $.extend(options, {
            "aaSorting": [[1, 'desc']],
            "fnCreatedRow": function(nRow, aData, iDataIndex) {
                $(nRow).children(':first').html('<i data_toggle="true" class="icon-plus"></i>');
            }        
        });
        var oTable = $(table).dataTable(options);
        //  Add event listener for opening and closing details
        //  Note that the indicator for showing which row is open is not controlled by DataTables,
        //  rather it is done here
        $(table).find('[data_toggle]').live('click', function () {
            var nTr = $(this).parents('tr')[0];
            if ( oTable.fnIsOpen(nTr) )
            {
                // This row is already open - close it
                $(this).removeClass('icon-minus').addClass('icon-plus');
                oTable.fnClose( nTr );
            }
            else
            {
                // Open this row
                $(this).removeClass('icon-plus').addClass('icon-minus');
                oTable.fnOpen( nTr, fnFormatDetails(oTable, nTr, data.details), 'details');
            }
        });
    } else {
        $(table).dataTable(options);
    }
}

var job_index = function () {
    activate_table('jobs_table', {}, {
        source: '/jobs/lookup?q=all_jobs',
        columns: ['start_time', 'name', 'runtime', 'state'],
        details: {
            'ID': 'id',
            'Args': ['parameters', 'args'],
            'Kwargs': ['parameters', 'kwargs'],
            'Breakdown': ['infos', 'runtime_breakdown'],
        },
    });
}
