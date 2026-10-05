// Base PWA, sem cache de HTML, API ou dados pessoais nesta etapa.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
