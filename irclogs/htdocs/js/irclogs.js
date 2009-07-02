irclogs_setup = function(param_current_date,param_start_date,param_int_month,param_base_path) {
        var $=jQuery;
        $('#showactions').click( function() {
            if ($(this).attr("checked")) {
                $('.server, .hidden_user').show();
            } else {
                $('.server, .hidden_user').hide();
            }
        } );
        Date.format = "yyyy/mm/dd/";
        $('.next').attr('href', param_base_path+'/irclogs/' + new Date(param_current_date).addDays(1).asString());
        $('.previous').attr('href',param_base_path+'/irclogs/' + new Date(param_current_date).addDays(-1).asString());
        Date.format = 'mm/dd/yyyy';
        $('.date-pick').datePicker({
            horizontalOffset: -160, 
            verticalOffset:20, 
            clickInput: true, 
            startDate: param_start_date, 
            endDate:(new Date()).asString(), 
            displayedMonth: Number(param_int_month)
        })
            .val( new Date(param_current_date).asString() )
            .trigger( 'change' );
        $('.date-pick').each(function() {
            $(this).bind('dateSelected', function(e, selectedDate, td) {
                Date.format = "yyyy/mm/dd/";
                window.location.href = param_base_path+"/irclogs/" + selectedDate.asString()
            } );
        });
        $('.link-datepicker').click(function(){
            $('.date-pick').trigger('click');
        });
        hidden_count = $(".server:hidden").length + $(".channel:hidden").length;
        $('#showactions').after("&nbsp;Show announcements (" + hidden_count  + ")");
        // controls are hidden unless JS is enabled
        $('#irclog-controls').show();
    };
