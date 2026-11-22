if ('serviceWorker' in navigator) {
    // Hand what this page loaded to a newly installed worker, so it is readable offline right away
    if (!navigator.serviceWorker.controller) {
        navigator.serviceWorker.ready.then(registration => registration.active.postMessage(
            [location.href, ...performance.getEntriesByType('resource').map(entry => entry.name)]));
    }
    navigator.serviceWorker.register('/sw.js');
}

// Theme toggle
(function() {
    var theme = document.documentElement.getAttribute('data-theme') || 'light';
    // Set the correct icon: show moon when light (click to go dark), sun when dark (click to go light)
    var icon = document.querySelector('#theme-toggle i');
    if (icon) {
        icon.className = theme === 'dark' ? 'fa fa-sun-o' : 'fa fa-moon-o';
    }
})();
$('#theme-toggle').click(function(e) {
    e.preventDefault();
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    var next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    $(this).find('i').toggleClass('fa-moon-o fa-sun-o');
});

function updateUrlHash(newParams) {
    const params = new URLSearchParams(window.location.hash.substring(1));
    for (const [key, value] of Object.entries(newParams)) {
        if (value !== null && value !== undefined && value !== '') {
            params.set(key, value);
        } else {
            params.delete(key);
        }
    }
    history.replaceState(null, null, `#${params}`);
}

// What each sort key reads from a story, ties keep the HN rank
const sortKeys = {
    rank: item => $(item).data('rank'),
    score: item => parseInt($(item).find('.score').text()) || 0,
    comments: item => parseInt($(item).find('.comment').text()) || 0,
    time: item => Date.parse($(item).find('.last-updated').data('submitted')),
};

// Rank starts ascending and the others descending
function applyAndRenderSort(sortBy, sortOrder = sortBy === 'rank' ? 'asc' : 'desc') {
    const key = sortKeys[sortBy];
    if (!key) return;
    const sign = sortOrder === 'asc' ? 1 : -1;
    const articles = $('.container > .post-item').get();
    const isAd = item => $(item).hasClass('ad');
    const news = articles.filter(item => !isAd(item)).sort((a, b) => sign * (key(a) - key(b)) || sortKeys.rank(a) - sortKeys.rank(b));
    articles.forEach((item, index) => isAd(item) && news.splice(index, 0, item));  // Ads keep their slots
    $(news).insertBefore('.container > footer');
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
    $('.sort-dropdown .dropdown-menu a').click(function () {
        const sortBy = $(this).data('sort');
        const hash = new URLSearchParams(location.hash.substring(1));
        // Clicking the current key again reverses its order
        const reversed = {asc: 'desc', desc: 'asc'}[hash.get('order')];
        applyAndRenderSort(sortBy, hash.get('sort') === sortBy ? reversed : undefined);
        $('.sort-dropdown').removeClass('open');
        return false;
    });
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

    $('#daily-picker').change(function () {
        if (this.value) location.href = $(this).data('url').replace('DATE', this.value);
    });

    const urlParams = new URLSearchParams(window.location.hash.substring(1));

    // Filter first
    const filterBy = urlParams.get('filter');
    if (filterBy) {
        applyAndRenderFilter(parseInt(filterBy));
    }

    // Apply sorting from hash
    const sortBy = urlParams.get('sort');
    if (sortBy) {
        applyAndRenderSort(sortBy, urlParams.get('order') || undefined);
    }
});

// We don't need to wait for the document.ready event, that costs a lot of time.
$.scrollUp({
    scrollTrigger: '<i class="fa fa-chevron-circle-up fa-3x" id="scrollUp"></i>',
    scrollTitle: 'Scroll to top'
});
// Sit between the day arrows; archives rendered before them keep it floating alone
$('#scrollUp').appendTo('.day-nav').css('position', '');
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

// Our copies of feature images expire, so fall back to the original, and drop the image if that is gone too
function imageFallBack() {
    const img = $(this);
    img.data('original') ? img.closest('.feature-image').remove() : img.data('original', true).attr('src', this.alt);
}
$('.feature-image img').on('error', imageFallBack).filter((i, img) => img.complete && !img.naturalWidth).each(imageFallBack);
// Load feature-image later
setTimeout(() => {
    $('.post-item img').attr('loading', 'eager');
}, 30 * 1000);
// Share a story as an image card, laid out at a fixed width and rendered sharp for phones
$('.share-icon > a').click(function () {
    const card = $(this).closest('.post-item').clone().addClass('share-card').appendTo('body');
    const time = card.find('.last-updated');
    time.text(time.data('submitted').slice(0, 10));  // A relative time goes stale in an image
    const qrcode = $('<div>');
    new QRCode(qrcode[0], {text: this.href, width: 64, height: 64, correctLevel: QRCode.CorrectLevel.L});
    card.append($('<footer class="share-footer">').append(`<span>${$('.navbar-brand').text()}<br>${this.origin}</span>`, qrcode));
    // Drop images the renderer cannot fetch, e.g. favicons without CORS, before they break the layout
    const fetchable = img => fetch(img.src).then(r => r.ok, () => false).then(ok => ok || img.remove());
    Promise.all(card.find('img').get().map(fetchable)).then(() => modernScreenshot.domToPng(card[0], {
        scale: 2,
        backgroundColor: getComputedStyle(document.body).backgroundColor,
        timeout: 3000,
    })).then(PreviewImage).finally(() => card.remove());
    return false;
});
