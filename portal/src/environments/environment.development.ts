export const environment = {
  production: false,
  // En desarrollo se usa /api con el proxy de `ng serve` (proxy.conf.json)
  // hacia http://localhost:8000 (evita problemas de CORS).
  apiUrl: '/api',
};
