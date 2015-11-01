var last_sort_by = 'rank';

$('#sort-by-hn-rank').click(function() {
    $('article').sort(function(a, b){
        if(last_sort_by === 'rank')
            return $(b).data('rank') - $(a).data('rank');
        return $(a).data('rank') - $(b).data('rank');
    }).insertBefore($('footer'));
    if(last_sort_by === 'rank') {
        last_sort_by = '';
    } else {
        last_sort_by = 'rank';
    }
    $('.navbar-nav>li.dropdown').toggleClass("open");
    return false;
});

$('#sort-by-score').click(function() {
    $('article').sort(function(a, b){
        var score1 = parseInt($(a).find('.post-meta .score').text()||0);
        var score2 = parseInt($(b).find('.post-meta .score').text()||0);
        if(score1 === score2) {
            return $(a).data('rank') - $(b).data('rank');
        }
        if(last_sort_by === 'score')
            return score1 - score2;
        return score2 - score1;
    }).insertBefore($('footer'));
    if(last_sort_by === 'score') {
        last_sort_by = '';
    } else {
        last_sort_by = 'score';
    }
    $('.navbar-nav>li.dropdown').toggleClass("open");
    return false;
});

$('#sort-by-comments').click(function() {
    $('article').sort(function(a, b){
        var comment1 = parseInt($(a).find('.post-meta .comment').text()||0);
        var comment2 = parseInt($(b).find('.post-meta .comment').text()||0);
        if(comment1 === comment2) {
            return $(a).data('rank') - $(b).data('rank');
        }
        if(last_sort_by === 'comment')
            return comment1 - comment2;
        return comment2 - comment1;
    }).insertBefore($('footer'));
    if(last_sort_by === 'comment') {
       last_sort_by = '';
    } else {
       last_sort_by = 'comment';
    }
    $('.navbar-nav>li.dropdown').toggleClass("open");
    return false;
});

$('#sort-by-submit-time').click(function() {
    $('article').sort(function(a, b){
        var s_t1 = $(a).find('.post-meta .summit-time .last-updated').data('submitted');
        var s_t2 = $(b).find('.post-meta .summit-time .last-updated').data('submitted');
        if(s_t1 === s_t2) {
            return $(a).data('rank') - $(b).data('rank');
        }
        var t1 = new Date(s_t1);
        var t2 = new Date(s_t2);
        //var t1 = parseInt(s_t1 || 0);
        //var t2 = parseInt(s_t2 || 0);
        //if(/minute/i.test(s_t1)) t1 *= 60;
        //if(/minute/i.test(s_t2)) t2 *= 60;
        //if(/hour/i.test(s_t1)) t1 *= 3600;
        //if(/hour/i.test(s_t2)) t2 *= 3600;
        //if(/day/i.test(s_t1)) t1 *= 86400;
        //if(/day/i.test(s_t2)) t2 *= 86400;
        if(last_sort_by === 'submit-time')
            return t1 - t2;
        return t2 - t1;
    }).insertBefore($('footer'));
    if(last_sort_by === 'submit-time') {
        last_sort_by = '';
    } else {
        last_sort_by = 'submit-time';
    }
    $('.navbar-nav>li.dropdown').toggleClass("open");
    return false;
});

