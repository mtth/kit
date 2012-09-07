
###

DATATABLES
==========

The main function here is `activate_table`. Simplest usage is::

    activate_table('the_table_id')

Options can also be provided::

    options = ['paginate', 'filter']
    activate_table('the_table_id', options)

Available options:

    *   paginate            pagination
    *   filter              search bar
    *   infos               infos
    *   auto_width          activate max width

AJAX table populating is equally easy. Let's imagine we want to display in a
table the results of an API call (in our example, let's say we receive back a
list of member objects and we want to display their member ID and name). We 
simply pass in a third argument with the AJAX request URL and the columns we
want to display::

    data = 
        source: '/lookup?q=members'
        columns:
            Member ID:
                key: 'id'
            Name:
                key: 'full_name'
    options = []
    activate_table('the_table_id', options, data)

It is also possible to display toggable details for each row by specifying
a details key on the data argument.

Technical API:

The data object must have the following attributes:

    *   source              the url of the AJAX GET request
    *   columns             the columns
    *   details (optional)  details that can be toggled for each row

Columns and details are objects where each attribute corresponds to a column /
detail name and contains an object with the following attributes:

For columns and details:

    *   key                 attribute name in the AJAX response (for nested
                            properties, use 'level1.level2.prop' syntax)
Only for columns:

    *   special (optional)  options for special formatting (cf below)
    *   width (optional)    width of the column

The special object can have the following attributes:

    *   url                 the key of the url to which the column text will
                            be pointed to (attribute of row)
    *   label               a function determining the class of the label to
                            apply (must return 'success', 'info', etc.)

###


window.activate_table = (table_id, options=null, data=null) ->

    table = $('#' + table_id)

    table_options = 
        bPaginate: options?.paginate?
        bLengthChange: false
        bFilter: options?.filter?
        bSort: true
        bInfo: options?.info?
        bAutoWidth: options?.auto_width?
        iDisplayLength: 50

    if not data
        # not using AJAX, we simply call datatables on the data
        $(table).dataTable(table_options)

    else
        # we format the columns to be compatible with datatables and we
        # add the table header
        columns = []
        th = '<thead><tr>'
        for attr, column of data.columns
            if 'width' of column
                th += "<th width='#{column.width}'>#{attr}</th>"
            else
                th += "<th>#{attr}</th>"
            columns.push({mData: column.key})
        th += '</tr></thead><tbody></tbody>'
        table.html(th)
        
        # and the function to postformat certain columns
        specialize_row = (row, row_data, row_index) ->
            if row_data.id?
                $(row).attr('id', "row_#{row_data.id}")
            tds = $(row).children('td')
            i = 0
            for col_name, col of data.columns
                html = $(tds[i]).html()
                if col.special?.label?
                    lc = col.special.label(row_data)
                    html = "<span class='label label-#{lc}'>#{html}</span>"
                if col.special?.url?
                    url = row_data[col.special.url]
                    html = "<a href='#{url}'>#{html}</a>"
                if col.special?.bar?
                    # we want a bar
                    # TODO
                    html = ''
                $(tds[i]).html(html)
                i++
            if data.details?
                $(row).children(':last').html(
                    '<a href="#" class="label" data-toggle="row">
                    <i class="icon-plus-sign icon-white"></i></a>'
                )

        # we define a few extra options to use AJAX
        ajax_options =
            bProcessing: true
            sAjaxDataProp: 'result'
            sAjaxSource: data.source
            aoColumns: columns
            aaSorting: [[0, 'asc']]
            fnCreatedRow: specialize_row
        $.extend(table_options, ajax_options)

        if not data.details
            # we are ready to activate the table
            activated_table = $(table).dataTable(table_options)

        else
            # before activating, we need to do a few things
            # first add a column in the header and the in data
            $(table).find('tr').each ->
                $(this).append(
                    '<th style="width: 40px; padding: 0;">
                    <span class="label label-info">
                    <i class="icon-info-sign icon-white"></i>
                    </span></th>'
                )
            details_opener_column = 
                mData: null
                bSortable: false
                sClass: 'center'
                aTargets: [0]
            table_options.aoColumns.push(details_opener_column)

            # then we define the function to format row details
            row_details = (table, row, details) ->
                row_data = table.fnGetData(row)
                rv = '<dl class="dl-horizontal">'
                for attr, detail of details
                    rv += "<dt>#{attr}</dt>"
                    # we first find the value to display
                    key = detail.key.split('.')
                    rd = row_data
                    for k in key
                        rd = rd[k]
                    # we now do the display formatting
                    rv += "<dd>#{rd}</dd>"
                rv += '</dl>'
                return rv

            # activate the table now that the setup is done
            activated_table = $(table).dataTable(table_options)

            # enable interactive details expansion
            table.find('[data-toggle=row]').live(
                'click',
                (event) ->
                    row = $(this).parents('tr')[0]
                    if activated_table.fnIsOpen(row)
                        $(this).removeClass('label-warning')
                        icon = $(this).find('i')
                        icon.removeClass('icon-minus-sign')
                        icon.addClass('icon-plus-sign')
                        activated_table.fnClose(row)
                    else
                        $(this).addClass('label-warning')
                        icon = $(this).find('i')
                        icon.removeClass('icon-plus-sign')
                        icon.addClass('icon-minus-sign')
                        activated_table.fnOpen(
                            row,
                            row_details(activated_table, row, data.details),
                            'row-details'
                        )
            )

###

AUTOCOMPLETE
============

Example usage::

    window.activate_autocomplete(
        'the_form_id',
        '/the_lookup_url',
            q: 'autocomplete',
        ['with_categories']
    )

###

window.activate_autocomplete = (form_id, url, query, options) ->
    if 'categories' in options
        attr = 'catcomplete'
        $.widget(
            'custom.catcomplete',
            $.ui.autocomplete,
                _renderMenu: (ul, items) ->
                    currentCategory = ''
                    $.each items, (index, item) =>
                        if item.category != currentCategory
                            ul.append("<li class='ui-autocomplete-category'>
                                #{item.category}</li>")
                            currentCategory = item.category
                        this._renderItem(ul, item)
        )
    else
        attr = 'autocomplete'
    if 'multiple' in options
        split = (val) ->
            return val.split(/,\s*/)
        extractLast = (term) ->
            return split(term).pop()
        $('#' + form_id).bind(
                'keydown',
                (event) ->
                    if event.keyCode == $.ui.keyCode.TAB and
                            $(this).data('autocomplete').menu.active
                        event.preventDefault()
            ).autocomplete(
                minLength: 1
                source: (request, response) ->
                    query.input = extractLast(request.term)
                    $.getJSON(
                        url,
                        query,
                        (data) ->
                            response(data['result'])
                    )
                focus: () ->
                    return false
                select: (event, ui) ->
                    terms = split(this.value)
                    terms.pop()
                    terms.push(ui.item.value)
                    this.value = terms.join(', ') + ', '
                    return false
            )
    else
        $('#' + form_id)[attr](
            minLength: 2,
            delay: 100,
            source: (request, response) ->
                query.input = request.term
                $.getJSON(
                    url,
                    query,
                    (data) ->
                        response(data['result'])
                )
        )

