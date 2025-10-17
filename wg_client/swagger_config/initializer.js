// Swagger UI Initializer - динамические URLs
window.onload = function() {
  // Определяем hostname динамически
  const baseUrl = window.location.protocol + '//' + window.location.hostname;
  
  // Инициализируем Swagger UI
  const ui = SwaggerUIBundle({
    urls: [
      {"name":"API 1 - Server Status","url": baseUrl + ":8081/openapi.json"},
      {"name":"API 2 - Registration","url": baseUrl + ":8082/openapi.json"},
      {"name":"API 4 - Battles & Analytics","url": baseUrl + ":8084/openapi.json"},
      {"name":"API 5 - Shop Parser","url": baseUrl + ":8085/openapi.json"},
      {"name":"API Father - Orchestrator","url": baseUrl + ":9000/openapi.json"},
      {"name":"API Mother - File Sync","url": baseUrl + ":8083/openapi.json"}
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
