// Datatables stuff

var fnFormatDetails = function ( oTable, nTr, details)
{
    var aData = oTable.fnGetData( nTr );
    var sOut = '<dl class="dl-horizontal">';
    for (var attr in details) {
        var rv = aData;
        var rk = details[attr].key;
        sOut += '<dt>' + attr + '</dt>';
        if (typeof rk === 'string') {
            rv = rv[rk];
        } else {
            for (var j in rk) {
                rv = rv[details[attr].key[j]];
            }
        }
        if ('special' in details[attr]) {
            if (details[attr].special == 'bar') {
                var colors = ['success', 'warning', 'info']
                sOut += '<dd><div class="progress">'
                var total_duration = 0;
                for (var i in rv) {
                    total_duration += rv[i][1];
                }
                for (var i in rv) {
                    sOut += '<div class="bar bar-' + colors[i % 3] + '" title="' + rv[i][0] + ' (' + rv[i][1] + ' seconds)" style="width: ' + (100 * rv[i][1] / total_duration) + '%;"></div>';
                }
                sOut += '</div></dd>';
            } else if (details[attr].special == 'label') {
                var mapping = {'SUCCESS': 'success'};
                sOut += '<dd><span class="label label-' + mapping[rv] + '">' + rv + '</span></dd>';
            }
        } else {
            sOut += '<dd>' + (rv || 'None') + '</dd>';
        }
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
    options.iDisplayLength = options.iDisplayLength || 20;
    options.sPaginationType = "full_numbers";
    if (data) {
        var columns = [];
        for (var attr in data.columns) {
            var new_column = {'mData': attr};
            $.extend(new_column, data.columns[attr]);
            columns.push(new_column);
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
            "aaSorting": [[5, 'desc']],
            "fnCreatedRow": function(nRow, aData, iDataIndex) {
                $(nRow).children(':first').addClass('details_expander').html('<i class="icon-plus"></i>');
            }        
        });
        var oTable = $(table).dataTable(options);
        $(table).find('.details_expander').live('click', function () {
            var nTr = $(this).parents('tr')[0];
            if ( oTable.fnIsOpen(nTr) )
            {
                $(this).children('i').removeClass('icon-minus').addClass('icon-plus');
                oTable.fnClose( nTr );
            }
            else
            {
                $(this).children('i').removeClass('icon-plus').addClass('icon-minus');
                oTable.fnOpen( nTr, fnFormatDetails(oTable, nTr, data.details), 'details');
                oTable.find('[title]').each(function() {
                    $(this).tooltip();
                });
            }
        });
    } else {
        $(table).dataTable(options);
    }
}

var labelize = function(container) {
    var c = $(container);
    var html = c.html();
    c.html('<span class="label">' + html + '</span>');
}

var job_index = function () {
    activate_table('jobs_table', {}, {
        source: '/jobs/lookup?q=all_jobs',
        columns: {
            'name': {},
            'parameters': {},
            'runtime': {'sClass': 'center'},
            'state': {'sClass': 'center'},
            'start_time': {'sClass': 'center'},
        },
        details: {
            'ID': {'key': 'id'},
            'Started': {'key': 'start_time'},
            'Finished': {'key': 'end_time'},
            'Breakdown': {'key': ['infos', 'runtime_breakdown'], 'special': 'bar'}
        },
    });
}

// general activations
$(function() {
    $('[title]').each(function() {
        $(this).tooltip();
    });
});
