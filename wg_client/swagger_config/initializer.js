// Swagger UI Initializer - правильная инициализация с URLS из env
window.onload = function() {
  // Парсим URLS из переменной окружения (передаётся через Docker)
  const urlsFromEnv = window.location.search.includes('urls=') 
    ? JSON.parse(decodeURIComponent(window.location.search.split('urls=')[1]))
    : [];

  // Инициализируем Swagger UI
  const ui = SwaggerUIBundle({
    urls: urlsFromEnv.length > 0 ? urlsFromEnv : [
      {"name":"API 1","url":"http://localhost:8081/openapi.json"},
      {"name":"API 2","url":"http://localhost:8082/openapi.json"},
      {"name":"API 4","url":"http://localhost:8084/openapi.json"},
      {"name":"API 5 - Shop Parser","url":"http://localhost:8085/openapi.json"},
      {"name":"API Father","url":"http://localhost:8080/openapi.json"},
      {"name":"API Mother","url":"http://localhost:8083/openapi.json"}
    ],
    dom_id: '#swagger-ui',
    deepLinking: true,
    presets: [
      SwaggerUIBundle.presets.apis,
      SwaggerUIStandalonePreset
    ],
    plugins: [
      SwaggerUIBundle.plugins.DownloadUrl
    ],
    layout: "StandaloneLayout",
    persistAuthorization: true,
    tryItOutEnabled: true,
    filter: true,
    displayRequestDuration: true,
    docExpansion: "list"
  });

  window.ui = ui;

  // Автоматическая авторизация (после инициализации UI)
  setTimeout(function() {
    try {
      const adminToken = localStorage.getItem('swagger_admin_token') || 'local_admin_token';
      
      // Устанавливаем авторизацию
      if (window.ui && window.ui.preauthorizeApiKey) {
        window.ui.preauthorizeApiKey('AdminAuth', adminToken);
        console.log('✅ Swagger UI: автоматическая авторизация применена');
      }
      
      // Сохраняем настройки
      localStorage.setItem('swagger_tryItOut', 'true');
      localStorage.setItem('swagger_admin_token', adminToken);
      
    } catch (e) {
      console.warn('Автоавторизация пропущена:', e.message);
    }
  }, 2000); // Даём время на полную загрузку UI
};
