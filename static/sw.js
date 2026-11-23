// Pages come from the network, falling back to the last copy when slow or offline;
// assets come from the cache and are refreshed in the background.
const PAGES = 'pages-v1', ASSETS = 'assets-v1';
const ASSET_HOSTS = [location.host, 'cdnjs.cloudflare.com', 'code.jquery.com', 'cdn.jsdelivr.net'];

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', event => event.waitUntil(
    caches.keys()
        .then(names => Promise.all(names.filter(name => name !== PAGES && name !== ASSETS).map(name => caches.delete(name))))
        .then(() => self.clients.claim())
));

self.addEventListener('fetch', event => {
    const request = event.request;
    // Requests bypassing caches, like the story poller, go straight to the network
    if (request.method !== 'GET' || request.cache === 'no-store') return;
    if (request.mode === 'navigate') {
        event.respondWith(networkFirst(event));
    } else if (ASSET_HOSTS.includes(new URL(request.url).host)) {
        event.respondWith(staleWhileRevalidate(event));
    }
});

self.addEventListener('notificationclick', event => {
    event.notification.close();
    const url = new URL(event.notification.data, location.origin).href;
    // Jump to the story in a tab already on that page, or open one
    event.waitUntil(clients.matchAll({type: 'window'}).then(tabs => {
        const tab = tabs.find(client => pageKey(client.url) === pageKey(url));
        return tab ? tab.focus().then(tab => tab.navigate(url)) : clients.openWindow(url);
    }));
});

// Pages and assets the page loaded before this worker took control
self.addEventListener('message', event => {
    const [page, ...assets] = event.data;
    event.waitUntil(Promise.allSettled([
        fetch(page).then(response => response.ok && put(PAGES, pageKey(page), response, 30)),
        ...assets.filter(url => ASSET_HOSTS.includes(new URL(url).host))
            .map(url => fetch(url).then(response => response.ok && put(ASSETS, url, response, 300))),
    ]));
});

const pageKey = href => {
    const url = new URL(href);
    return url.origin + url.pathname;  // Ignore queries like ?utm_source=pwa
};

async function networkFirst(event) {
    const key = pageKey(event.request.url);
    const network = fetch(event.request);
    event.waitUntil(network.then(response => response.ok && put(PAGES, key, response.clone(), 30)).catch(() => {}));
    try {
        // Server errors and slow responses fall back to the last saved copy
        const fresh = network.then(response => response.status < 500 ? response : Promise.reject());
        return await Promise.race([fresh, new Promise((_, reject) => setTimeout(reject, 3000))]);
    } catch {
        return await caches.match(key, {cacheName: PAGES}) || network;
    }
}

async function staleWhileRevalidate(event) {
    const network = fetch(event.request);
    event.waitUntil(network.then(response => (response.ok || response.type === 'opaque')
        && put(ASSETS, event.request, response.clone(), 300)).catch(() => {}));
    return await caches.match(event.request, {cacheName: ASSETS}) || network;
}

// Re-putting moves an entry to the end, so trimming from the front drops the least recently fetched
async function put(name, key, response, limit) {
    const cache = await caches.open(name);
    await cache.put(key, response);
    const keys = await cache.keys();
    await Promise.all(keys.slice(0, -limit).map(old => cache.delete(old)));
}
