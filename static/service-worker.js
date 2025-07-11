const CACHE_NAME = 'sybemacademia-cache-v1.0.3'; // Changez cette version si vous modifiez le cache
const urlsToCache = [
    '/', // Page d'accueil (ex: connexion)
    '/login/', // Si vous avez une URL de connexion spécifique
    '/static/css/custom_styles.css', // Assurez-vous que ce chemin est correct
    '/static/bootstrap/css/bootstrap.min.css', // Exemple si vous avez Bootstrap en local
    '/static/bootstrap/js/bootstrap.bundle.min.js', // Exemple si vous avez Bootstrap en local
    // Ajoutez ici les chemins de VOS FICHIERS JS essentiels si vous en avez
    // '/static/js/mon_script_principal.js',
    // Liste des icônes à mettre en cache immédiatement (doivent correspondre au manifest)
    '/static/images/icons/icon-72x72.png',
    '/static/images/icons/icon-96x96.png',
    '/static/images/icons/icon-128x128.png',
    '/static/images/icons/icon-144x144.png',
    '/static/images/icons/icon-152x152.png',
    '/static/images/icons/icon-192x192.png',
    '/static/images/icons/icon-384x384.png',
    '/static/images/icons/icon-512x512.png'
];

self.addEventListener('install', event => {
  console.log('[Service Worker] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Caching essential resources');
        return cache.addAll(urlsToCache);
      })
      .catch(error => {
        console.error('[Service Worker] Cache addAll failed:', error);
      })
  );
});

self.addEventListener('activate', event => {
  console.log('[Service Worker] Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      return self.clients.claim(); // Rend le SW actif immédiatement pour tous les clients
    })
  );
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') {
    return; // Ignorer les requêtes non-GET (ex: POST, PUT)
  }

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          console.log('[Service Worker] Serving from cache:', event.request.url);
          return response;
        }

        console.log('[Service Worker] Fetching from network:', event.request.url);
        return fetch(event.request).then(
          response => {
            if(!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            const responseToCache = response.clone();
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              })
              .catch(error => {
                console.error('[Service Worker] Failed to cache:', event.request.url, error);
              });

            return response;
          }
        ).catch(error => {
            console.error('[Service Worker] Network request failed:', event.request.url, error);
            // Optionnel: retourner une page offline si la requête échoue et n'est pas dans le cache
            // return caches.match('/offline.html');
        });
      })
    );
});