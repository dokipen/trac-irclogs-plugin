jQuery(window).ready(function() {
    $("//tr/td/a[name='"+window.location.hash.substr(1)+"']").parent().parent().effect('highlight', {}, 10000);
});
