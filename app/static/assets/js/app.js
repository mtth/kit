$(function() {
    $('.datatable').each(function() {
        $(this).dataTable({
            "bPaginate": true,
            "bLengthChange": false,
            "bFilter": false,
            "bSort": true,
            "bInfo": true,
            "bAutoWidth": false,
            "iDisplayLength": 50,
            "sPaginationType": "full_numbers",
//            for later
//            "bProcessing": true,
//            "sAjaxDataProp": "result"
//            these probably also want to be customized per table
//            "sAjaxSource": "sources/custom_prop.txt",
//            "aoColumns": [
//                { "mData": "engine" },
//                { "mData": "browser" },
//                { "mData": "platform" },
//                { "mData": "version" },
//                { "mData": "grade" }
//            ]
        });
    });
});
