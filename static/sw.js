const CACHE_NAME = 'wallpaper-cache-v1';
const urlsToCache = [
    'https://w.wallhaven.cc/full/pn/wallhaven-pneeln.jpg',
    'https://w.wallhaven.cc/full/76/wallhaven-76w7vo.jpg',
    'https://w.wallhaven.cc/full/96/wallhaven-96wkm1.jpg',
    'https://w.wallhaven.cc/full/zy/wallhaven-zypp2w.jpg',
    'https://w.wallhaven.cc/full/xl/wallhaven-xl5kzl.jpg',
    'https://w.wallhaven.cc/full/1p/wallhaven-1p651w.png'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                return fetch(event.request);
            })
    );
});
