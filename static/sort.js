$('#sort-by-hn-rank').click(function() {
    $('article').sort(function(a, b){
        return $(a).data('rank') - $(b).data('rank');
    }).insertBefore($('footer'));
    return false;
});

$('#sort-by-score').click(function() {
    $('article').sort(function(a, b){
        var score1 = parseInt($(a).find('.post-meta .score').text()||0);
        var score2 = parseInt($(b).find('.post-meta .score').text()||0);
        if(score1 === score2)
            return $(a).data('rank') - $(b).data('rank');
        return score2 - score1;
    }).insertBefore($('footer'));
    return false;
});

$('#sort-by-comments').click(function() {
    $('article').sort(function(a, b){
        var comment1 = parseInt($(a).find('.post-meta .comment').text()||0);
        var comment2 = parseInt($(b).find('.post-meta .comment').text()||0);
        if(comment1 === comment2)
            return $(a).data('rank') - $(b).data('rank');
        return comment2 - comment1;
    }).insertBefore($('footer'));
    return false;
});

$('#sort-by-submit-time').click(function() {
    $('article').sort(function(a, b){
        var s_t1 = $(a).find('.post-meta .summit-time').text();
        var s_t2 = $(b).find('.post-meta .summit-time').text();
        if(s_t1 === s_t2)
            return $(a).data('rank') - $(b).data('rank');
        var t1 = parseInt(s_t1 || 0);
        var t2 = parseInt(s_t2 || 0);
        if(/minute/i.test(s_t1)) t1 *= 60;
        if(/minute/i.test(s_t2)) t2 *= 60;
        if(/hour/i.test(s_t1)) t1 *= 3600;
        if(/hour/i.test(s_t2)) t2 *= 3600;
        if(/day/i.test(s_t1)) t1 *= 86400;
        if(/day/i.test(s_t2)) t2 *= 86400;
        return t1 - t2;
    }).insertBefore($('footer'));
    return false;
});

