let last_sort_by = 'rank';

function updateUrlHash(newParams) {
    const params = new URLSearchParams(window.location.hash.substring(1));
    for (const [key, value] of Object.entries(newParams)) {
        if (value !== null && value !== undefined && value !== '') {
            params.set(key, value);
        } else {
            params.delete(key);
        }
    }
    const newHash = params.toString();
    if (history.replaceState) {
        history.replaceState(null, null, `#${newHash}`);
    } else {
        window.location.hash = newHash;
    }
}

const comparators = {
    'rank': (a, b) => $(a).data('rank') - $(b).data('rank'),
    'score': (a, b) => {
        const score1 = parseInt($(a).find('.post-meta .score').text() || 0);
        const score2 = parseInt($(b).find('.post-meta .score').text() || 0);
        if (score1 === score2) return $(a).data('rank') - $(b).data('rank');
        return score1 - score2;
    },
    'comments': (a, b) => {
        const comment1 = parseInt($(a).find('.post-meta .comment').text() || 0);
        const comment2 = parseInt($(b).find('.post-meta .comment').text() || 0);
        if (comment1 === comment2) return $(a).data('rank') - $(b).data('rank');
        return comment1 - comment2;
    },
    'time': (a, b) => {
        const t1 = new Date($(a).find('.post-meta .summit-time .last-updated').data('submitted'));
        const t2 = new Date($(b).find('.post-meta .summit-time .last-updated').data('submitted'));
        if (t1.getTime() === t2.getTime()) return $(a).data('rank') - $(b).data('rank');
        return t2 - t1; // Descending order for time
    }
};

function applyAndRenderSort(sortBy, sortOrder) {
    const comparator = comparators[sortBy];
    if (!comparator) {
        console.error(`Unknown sort type: ${sortBy}`);
        return;
    }

    const articles = $('article');
    const items = articles.get(); // Get all articles as a plain array

    // Store ads and their original indices. Ads are identified by the '.ad' class.
    const ads = [];
    items.forEach(function(item, index) {
        if ($(item).hasClass('ad')) {
            ads.push({index: index, element: item});
        }
    });

    // Filter out ads to get only news items for sorting
    const newsItems = items.filter(function(item) {
        return !$(item).hasClass('ad');
    });

    // Sort the news items
    newsItems.sort(function(a, b) {
        const result = comparator(a, b);
        return sortOrder === 'desc' ? -result : result;
    });

    // Re-insert ads into the sorted list at their original indices to maintain their position
    ads.forEach(function(ad) {
        newsItems.splice(ad.index, 0, ad.element);
    });

    // Detach all original articles from the DOM
    articles.detach();
    
    // And then insert the newly ordered list of items (news + ads) back
    $(newsItems).insertBefore($('footer'));

    updateUrlHash({sort: sortBy, order: sortOrder});
}

function applyAndRenderFilter(topN) {
    if (!topN || topN <= 0) {
        $('article').show();
        return;
    }

    let points = $.map($('article'), function (e) {
        return parseInt($(e).find('.post-meta .score').text() || 0);
    }).sort(function (a, b) {
        return b - a;
    });

    let threshold = 0;
    if (topN < points.length) {
        threshold = points[topN - 1];
    }

    $('article').each(function () {
        let scoreDom = $(this).find('.post-meta .score');
        if (!scoreDom.length) {
            return; // ads
        }
        let point = parseInt(scoreDom.text() || 0);
        if (point >= threshold) {
            $(this).show();
        } else {
            $(this).hide();
        }
    });
}

function setupSortHandlers() {
    const sortConfig = {
        '#sort-by-hn-rank': {key: 'rank', internal: 'rank'},
        '#sort-by-score': {key: 'score', internal: 'score'},
        '#sort-by-comments': {key: 'comments', internal: 'comment'},
        '#sort-by-submit-time': {key: 'time', internal: 'submit-time'}
    };

    for (const [buttonId, config] of Object.entries(sortConfig)) {
        $(buttonId).click(function () {
            const sortOrder = (last_sort_by === config.internal) ? 'asc' : 'desc';
            applyAndRenderSort(config.key, sortOrder);
            last_sort_by = (sortOrder === 'desc') ? config.internal : '';
            $('.navbar-nav>li.sort-dropdown').removeClass("open");
            return false; // Prevent default link behavior so that we can update the URL hash
        });
    }
}

function setupFilterHandlers() {
    $('.navbar-nav>li.filter-dropdown .dropdown-menu a').click(function () {
        let topN = parseInt($(this).data('top'));
        applyAndRenderFilter(topN);
        if (topN === -1) {
            topN = ''; // Clear filter
        }
        updateUrlHash({filter: topN});
        $('.navbar-nav>li.filter-dropdown').removeClass("open");
        return false;
    });
}

// Initial setup on page load
$(function () {
    setupSortHandlers();
    setupFilterHandlers();

    // Reset daily links dropdown on open
    $('.daily-dropdown').on('show.bs.dropdown', function () {
        $('#daily-links-menu .extra-link').hide();
        $('#more-daily-links').parent().show();
    });

    $('#more-daily-links').click(function (e) {
        $('#daily-links-menu .extra-link').show();
        $(this).parent().hide();
        return false;
    });

    const urlParams = new URLSearchParams(window.location.hash.substring(1));

    // Filter first
    const filterBy = urlParams.get('filter');
    if (filterBy) {
        applyAndRenderFilter(parseInt(filterBy));
    }

    // Apply sorting from hash
    const sortBy = urlParams.get('sort');
    const sortOrder = urlParams.get('order') || 'desc';
    if (sortBy) {
        if (comparators[sortBy]) {
            applyAndRenderSort(sortBy, sortOrder);
            const internalKeyMap = {
                'rank': 'rank', 'score': 'score', 'comments': 'comment', 'time': 'submit-time'
            };
            last_sort_by = (sortOrder === 'desc') ? internalKeyMap[sortBy] : '';
        } else {
            console.error(`Unknown sort type: ${sortBy}`);
        }
    }
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
// Load feature-image later
setTimeout(() => {
    $('.post-item img').attr('loading', 'eager');
}, 30 * 1000);
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
