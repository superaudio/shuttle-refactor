var flower = (function () {
    "use strict";
    /*jslint browser: true */
    /*jslint unparam: true, node: true */
    /*global $, WebSocket, jQuery, Rickshaw */

    function on_alert_close(event) {
        event.preventDefault();
        event.stopPropagation();
        $(event.target).parent().hide();
    }

    function show_error_alert(message) {
        $("#alert").removeClass("alert-success").addClass("alert-error");
        $("#alert-message").html("<strong>Error!</strong>    " + message);
        $("#alert").show();
    }

    function show_success_alert(message) {
        $("#alert").removeClass("alert-error").addClass("alert-success");
        $("#alert-message").html("<strong>Success!</strong>    " + message);
        $("#alert").show();
    }

    function url_prefix() {
        var url_prefix = $('#url_prefix').val();
        if (url_prefix) {
            if (url_prefix.startsWith('/')) {
                return url_prefix;
            } else {
                return '/' + url_prefix;
            }
        }
        return '';
    }

    //https://github.com/DataTables/DataTables/blob/1.10.11/media/js/jquery.dataTables.js#L14882
    function htmlEscapeEntities(d) {
        return typeof d === 'string' ?
            d.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') :
            d;
    }

    function active_page(name) {
        var pathname = $(location).attr('pathname');
        if (name === '/') {
            return pathname === (url_prefix() + name);
        }
        else {
            return pathname.startsWith(url_prefix() + name);
        }
    }

    function on_worker_refresh(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text();

        $.ajax({
            type: 'GET',
            url: url_prefix() + '/api/workers',
            dataType: 'json',
            data: {
                workername: unescape(workername),
                refresh: 1
            },
            success: function (data) {
                show_success_alert(data.message || 'Refreshed');
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_worker_pool_restart(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/pool/restart/' + workername,
            dataType: 'json',
            data: {
                workername: workername
            },
            success: function (data) {
                show_success_alert(data.message);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_worker_shutdown(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/shutdown/' + workername,
            dataType: 'json',
            data: {
                workername: workername
            },
            success: function (data) {
                show_success_alert(data.message);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_pool_grow(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            grow_size = $('#pool-size option:selected').html();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/pool/grow/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'n': grow_size,
            },
            success: function (data) {
                show_success_alert(data.message);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_pool_shrink(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            shrink_size = $('#pool-size option:selected').html();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/pool/shrink/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'n': shrink_size,
            },
            success: function (data) {
                show_success_alert(data.message);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_pool_autoscale(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            min = $('#min-autoscale').val(),
            max = $('#max-autoscale').val();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/pool/autoscale/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'min': min,
                'max': max,
            },
            success: function (data) {
                show_success_alert(data.message);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_add_consumer(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            queue = $('#add-consumer-name').val();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/queue/add-consumer/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'queue': queue,
            },
            success: function (data) {
                show_success_alert(data.message);
                setTimeout(function () {
                    $('#tab-queues').load('/worker/' + workername + ' #tab-queues').fadeIn('show');
                }, 10000);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_cancel_consumer(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            queue = $(event.target).closest("tr").children("td:eq(0)").text();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/queue/cancel-consumer/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'queue': queue,
            },
            success: function (data) {
                show_success_alert(data.message);
                setTimeout(function () {
                    $('#tab-queues').load('/worker/' + workername + ' #tab-queues').fadeIn('show');
                }, 10000);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_task_timeout(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            taskname = $(event.target).closest("tr").children("td:eq(0)").text(),
            timeout = $(event.target).siblings().closest("input").val();

        taskname = taskname.split(' ')[0]; // removes [rate_limit=xxx]

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/task/timeout/' + taskname,
            dataType: 'json',
            data: {
                'workername': workername,
                'type': timeout,
            },
            success: function (data) {
                show_success_alert(data.message);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_task_rate_limit(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            taskname = $(event.target).closest("tr").children("td:eq(0)").text(),
            ratelimit = $(event.target).prev().val();

        taskname = taskname.split(' ')[0]; // removes [rate_limit=xxx]

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/task/rate-limit/' + taskname,
            dataType: 'json',
            data: {
                'workername': workername,
                'ratelimit': ratelimit,
            },
            success: function (data) {
                show_success_alert(data.message);
                setTimeout(function () {
                    $('#tab-limits').load('/worker/' + workername + ' #tab-limits').fadeIn('show');
                }, 10000);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_task_revoke(event) {
        event.preventDefault();
        event.stopPropagation();

        var taskid = $('#taskid').text();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/task/revoke/' + taskid,
            dataType: 'json',
            data: {
                'terminate': false,
            },
            success: function (data) {
                show_success_alert(data.message);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_task_terminate(event) {
        event.preventDefault();
        event.stopPropagation();

        var taskid = $('#taskid').text();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/task/revoke/' + taskid,
            dataType: 'json',
            data: {
                'terminate': true,
            },
            success: function (data) {
                show_success_alert(data.message);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function sum(a, b) {
        return parseInt(a, 10) + parseInt(b, 10);
    }

    function update_dashboard_counters() {
        var table = $('#workers-table').DataTable();
        $('a#btn-active').text('Active: ' + table.column(2).data().reduce(sum, 0));
        $('a#btn-processed').text('Processed: ' + table.column(3).data().reduce(sum, 0));
        $('a#btn-failed').text('Failed: ' + table.column(4).data().reduce(sum, 0));
        $('a#btn-succeeded').text('Succeeded: ' + table.column(5).data().reduce(sum, 0));
        $('a#btn-retried').text('Retried: ' + table.column(6).data().reduce(sum, 0));
    }

    function on_cancel_task_filter(event) {
        event.preventDefault();
        event.stopPropagation();

        $('#task-filter-form').each(function () {
            $(this).find('SELECT').val('');
            $(this).find('.datetimepicker').val('');
        });

        $('#task-filter-form').submit();
    }

    function current_unix_time() {
        var now = new Date();
        return Date.UTC(now.getUTCFullYear(), now.getUTCMonth(),
            now.getUTCDate(), now.getUTCHours(),
            now.getUTCMinutes(), now.getUTCSeconds()) / 1000;
    }

    function format_time(timestamp) {
        var time = $('#time').val(),
            prefix = time.startsWith('natural-time') ? 'natural-time' : 'time',
            tz = time.substr(prefix.length + 1) || 'UTC';

        if (prefix === 'natural-time') {
            return moment.unix(timestamp).tz(tz).fromNow();
        }
        return moment.unix(timestamp).tz(tz).format('YYYY-MM-DD HH:mm:ss.SSS');
    }

    function isColumnVisible(name) {
        var columns = $('#columns').val();
        if (columns === "all")
            return true;
        if (columns) {
            columns = columns.split(',').map(function (e) {
                return e.trim();
            });
            return columns.indexOf(name) !== -1;
        }
        return true;
    }

    $.urlParam = function (name) {
        var results = new RegExp('[\\?&]' + name + '=([^&#]*)').exec(window.location.href);
        return (results && results[1]) || 0;
    };

    $(document).ready(function () {
        //https://github.com/twitter/bootstrap/issues/1768
        var shiftWindow = function () {
            scrollBy(0, -50);
        };
        if (location.hash) {
            shiftWindow();
        }
        window.addEventListener("hashchange", shiftWindow);

        // Make bootstrap tabs persistent
        $(document).ready(function () {
            if (location.hash !== '') {
                $('a[href="' + location.hash + '"]').tab('show');
            }

            $('a[data-toggle="tab"]').on('shown', function (e) {
                location.hash = $(e.target).attr('href').substr(1);
            });
        });

    });

    $(document).ready(function () {
        if (!active_page('/') && !active_page('/dashboard')) {
            return;
        }

        $('#workers-table').DataTable({
            rowId: 'name',
            searching: true,
            paginate: false,
            select: false,
            scrollX: true,
            scrollY: true,
            scrollCollapse: true,
            ajax: url_prefix() + '/api/workers/list',
            order: [
                [1, "asc"]
            ],
            columnDefs: [{
                targets: 0,
                data: 'hostname',
                render: function (data, type, full, meta) {
                    return '<a href="' + url_prefix() + '/worker/' + data + '">' + data + '</a>';
                }
            }, {
                targets: 1,
                data: 'url',
                render: function (data, type, full, meta) {
                    return data;
                }
            }, {
                targets: 2,
                data: 'enabled',
                render: function (data, type, full, meta) {
                    if (data) {
                        return '<span class="label label-success">True</span>';
                    } else {
                        return '<span class="label label-important">False</span>';
                    }
                }
            }, {
                targets: 3,
                data: 'builder_status',
                render: function (data, type, full, meta) {
                    if (data != "BuilderStatus.OFFLINE") {
                        return '<span class="label label-success">' + data + '</span>';
                    } else {
                        return '<span class="label label-important">' + data + '</span>';
                    }
                }
            }, {
                targets: 4,
                data: 'uploading',
                defaultContent: "false",
                render: function (data, type, full, meta) {
                    return data;
                }
            }, {
                targets: 5,
                data: 'builder_info',
                render: function (data, type, full, meta) {
                    var builders = data['builders'];

                    if (Array.isArray(builders)) {
                        var result ="";
                        for (var arg in builders){
                            result += '<span class="label label-info">' + builders[arg] + '</span> ';
                        }
                        return result;
                    }
                    return data;
                }
            }, ],
        });

        var autorefresh = $.urlParam('autorefresh') || 1;
        if (autorefresh !== 0) {
            setInterval( function () {
                $('#workers-table').DataTable().ajax.reload();
            }, autorefresh * 1000);
        }

    });

    $(document).ready(function () {
        if (!active_page('/tasks')) {
            return;
        }
        var query = window.location.search.substring(1);
        var vars = query.split("&");
        var page = 1;
        var totalPages = 1;
        for (var i=0;i<vars.length;i++) {
            var pair = vars[i].split("=");
            if(pair[0] == "page"){ page = pair[1];}
        }
        $.ajax({
            type: "get",
            url: "/api/task/total",
            data: {},
            dataType: 'json',
            async: false,
            success: function (data) {
                totalPages = Math.ceil(data['total'] / 25);
            }
        });
        var options = {
            alignment:'center',
            currentPage: page,
            numberOfPages: 5,
            totalPages: totalPages,
            pageUrl: function(type, page, current){
                return "/tasks?page=" + page; }
            };
        $("#pagination").bootstrapPaginator(options);
        $('#tasks-table').DataTable({
            rowId: 'task',
            searching: true,
            paginate: false,
            scrollX: true,
            scrollCollapse: true,
            processing: true,
            serverSide: false,
            colReorder: true,
            order: [
                [ 0, "desc"]
            ],
            ajax: url_prefix() + '/api/task/list/' + page,
            oSearch: {
                "sSearch": $.urlParam('state') ? 'state:' + $.urlParam('state') : ''
            },
            columnDefs: [{
                targets: 0,
                data: 'id',
                visible: isColumnVisible('BuildId'),
                render: function (data, type, full, meta) {
                    return data;
                }
            }, {
                targets: 1,
                data: 'action',
                visible: isColumnVisible('Action'),
                render: function (data, type, full, meta) {
                    return data;
                }
            }, {
                targets: 2,
                data: 'pkgname',
                visible: isColumnVisible('Pkgname'),
                render: function (data, type, full, meta) {
                    return data;
                }
            }, {
                targets: 3,
                data: 'pkgver',
                visible: isColumnVisible('Version'),
                render: function (data, type, full, meta) {
                    return data;
                }
            }, {
                targets: 4,
                data: 'reponame',
                visible: isColumnVisible('Reponame'),
                render: function (data, type, full, meta) {
                    return data;
                }
            }, {
                targets: 5,
                data: 'triggered',
                render: function (data, type, full, meta) {
                    return data;
                }
            }, {
                targets: 6,
                data: 'build_args',
                orderable: false,
                render: function (data, type, full, meta) {
                    if (Array.isArray(data)) {
                        var result ="";
                        for (var arg in data){
                            result += '<span class="label label-default">' + data[arg] + '</span> ';
                        }
                        return result;
                    }
                    return '<span class="label label-default">' + data + '</span>';
                }
            }, {
                targets: 7,
                data: 'upload_status',
                render: function (data, type, full, meta) {
                    switch (data) {
                    case 'SUCCESS':
                        return '<a class="openLogModal label label-success">' + data + '</a>';
                    case 'FAILURE':
                        return '<a class="openLogModal label label-important">' + data + '</a>';
                    default:
                        return '<a class="openLogModal label label-default">' + data + '</a>';
                    }
                }

            }, {
                targets: 8,
                data: 'status_changed',
                render: function (data, type, full, meta) {
                    return data;
                }
            }, {
                targets: 9,
                data: 'tasks',
                orderable: false,
                render: function (data, type, full, meta) {
                    if (Array.isArray(data)) {  
                        var result ="";
                        for (var task of data){
                            switch (task['status']) {
                                case 'FAILED': 
                                    result += '<span class="label label-important">';
                                    break ;
                                case 'BUILDING':
                                    result += '<span class="label label-info">';
                                    break ;
                                case 'BUILD_OK':
                                    result += '<span class="label label-success">';
                                    break ;
                                default:
                                    result += '<span class="label label-default">';
                            }
                            result += '<a href="' + url_prefix() + '/job/' + task['id'] + '">';
                            result += task['task'] + '</a></span> ';
                        }
                        return result;
                    }
                }
            }, ],
        });
    });

    return {
        on_alert_close: on_alert_close,
        on_worker_refresh: on_worker_refresh,
        on_worker_pool_restart: on_worker_pool_restart,
        on_worker_shutdown: on_worker_shutdown,
        on_pool_grow: on_pool_grow,
        on_pool_shrink: on_pool_shrink,
        on_pool_autoscale: on_pool_autoscale,
        on_add_consumer: on_add_consumer,
        on_cancel_consumer: on_cancel_consumer,
        on_task_timeout: on_task_timeout,
        on_task_rate_limit: on_task_rate_limit,
        on_cancel_task_filter: on_cancel_task_filter,
        on_task_revoke: on_task_revoke,
        on_task_terminate: on_task_terminate,
    };

}(jQuery));
