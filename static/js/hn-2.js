var last_sort_by = 'rank';

$('#sort-by-hn-rank').click(function () {
    $('article').sort(function (a, b) {
        if (last_sort_by === 'rank')
            return $(b).data('rank') - $(a).data('rank');
        return $(a).data('rank') - $(b).data('rank');
    }).insertBefore($('footer'));
    if (last_sort_by === 'rank') {
        last_sort_by = '';
    } else {
        last_sort_by = 'rank';
    }
    $('.navbar-nav>li.dropdown').toggleClass("open");
    return false;
});

$('#sort-by-score').click(function () {
    $('article').sort(function (a, b) {
        var score1 = parseInt($(a).find('.post-meta .score').text() || 0);
        var score2 = parseInt($(b).find('.post-meta .score').text() || 0);
        if (score1 === score2) {
            return $(a).data('rank') - $(b).data('rank');
        }
        if (last_sort_by === 'score')
            return score1 - score2;
        return score2 - score1;
    }).insertBefore($('footer'));
    if (last_sort_by === 'score') {
        last_sort_by = '';
    } else {
        last_sort_by = 'score';
    }
    $('.navbar-nav>li.dropdown').toggleClass("open");
    return false;
});

$('#sort-by-comments').click(function () {
    $('article').sort(function (a, b) {
        var comment1 = parseInt($(a).find('.post-meta .comment').text() || 0);
        var comment2 = parseInt($(b).find('.post-meta .comment').text() || 0);
        if (comment1 === comment2) {
            return $(a).data('rank') - $(b).data('rank');
        }
        if (last_sort_by === 'comment')
            return comment1 - comment2;
        return comment2 - comment1;
    }).insertBefore($('footer'));
    if (last_sort_by === 'comment') {
        last_sort_by = '';
    } else {
        last_sort_by = 'comment';
    }
    $('.navbar-nav>li.dropdown').toggleClass("open");
    return false;
});

$('#sort-by-submit-time').click(function () {
    $('article').sort(function (a, b) {
        var s_t1 = $(a).find('.post-meta .summit-time .last-updated').data('submitted');
        var s_t2 = $(b).find('.post-meta .summit-time .last-updated').data('submitted');
        if (s_t1 === s_t2) {
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
        if (last_sort_by === 'submit-time')
            return t1 - t2;
        return t2 - t1;
    }).insertBefore($('footer'));
    if (last_sort_by === 'submit-time') {
        last_sort_by = '';
    } else {
        last_sort_by = 'submit-time';
    }
    $('.navbar-nav>li.dropdown').toggleClass("open");
    return false;
});

// We don't need to wait for the document.ready event, that costs a lot of time.
$.scrollUp({
    scrollTrigger: '<i class="fa fa-chevron-circle-up fa-3x" id="scrollUp"></i>',
    scrollTitle: 'Scroll to top'
});
// submit time humanize
$('.last-updated').each((index, item) => {
    $(item).find('span').text(humanizeDuration(new Date() - new Date($(item).data('submitted')), {
        largest: 1,
        round: true
    }) + ' ago')
});
// last-updated tooltip
$(function () {
    let lastUpdate = $('li.last-updated[data-toggle="tooltip"]');
    lastUpdate.prop('title', new Date(lastUpdate.data('submitted')).toLocaleString());
    $('[data-toggle="tooltip"]').tooltip({html: true});
});

// feature-image modal
function PreviewImage(src) {
    $('#img-preview-modal img').attr('src', src);
    $('#img-preview-modal').modal();
}

$('.post-item .post-summary .feature-image').click(function (e) {
    PreviewImage($('img', this).attr('src'));
    return false;
});
// screenshot
//   prepare qrcode as it's rendered asynchronously, or wait until https://github.com/davidshimjs/qrcodejs/pull/136 is merged
$(function () {
    $('.post-item').each((i, ele) => {
        let shareIcon = ele.querySelector('.share-icon');
        if (!shareIcon) {
            return;  // google ads
        }
        const permalink = shareIcon.getAttribute('href');
        if (permalink) {
            let qrcode = new QRCode(ele.querySelector('.qrcode'), {
                text: permalink,
                width: 60,
                height: 60,  // cannot be too small - too blurry to scan, cannot be too big - avoid wrap of summary text
                correctLevel: QRCode.CorrectLevel.L  // cleaner and easier to scan
            });
        } else {
            console.warn("no href for", shareIcon);
        }
    });
});
$('.post-item .share-icon').click(function (e) {
    const node = $(this).closest('.post-item').get(0);
    modernScreenshot.domToPng(node, {
        timeout: 3000,
        fetch: {
            placeholderImage: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAMSURBVBhXY7h79y4ABTICmGnXPbMAAAAASUVORK5CYII=",
        },
        style: {
            paddingTop: '5px',
            paddingLeft: '10px',
            paddingRight: '10px',
        },
        onCloneNode: (cloned) => {
            cloned.querySelector(".qrcode").style.display = "block";
        }
    }).then((dataUrl) => {
        PreviewImage(dataUrl);
    });
    return false;
});
