jQuery(window).ready(function() {
    if (window.location.hash) {
        search_a = $("//tr/td/a[name='"+window.location.hash.substr(1)+"']");
        search_tr = search_a.parent().parent();
        search_tr.effect('highlight', {}, 10000);
    }
});
