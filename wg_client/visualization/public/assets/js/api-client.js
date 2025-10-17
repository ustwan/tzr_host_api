/**
 * API Client для WG_HUB API5
 * 
 * Общий клиент для всех дашбордов визуализации.
 * Поддерживает retry, timeout, error handling.
 */

// Конфигурация API
const API_CONFIG = {
  // Базовый URL API - всегда через Nginx прокси
  baseURL: '/api',
  
  timeout: 30000,      // 30 секунд
  retries: 2,          // Количество повторов при ошибке
  retryDelay: 1000,    // Задержка между повторами (мс)
};

class APIClient {
  constructor(config = API_CONFIG) {
    this.baseURL = config.baseURL;
    this.timeout = config.timeout;
    this.retries = config.retries;
    this.retryDelay = config.retryDelay;
  }

  /**
   * Базовый запрос с retry и timeout
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    const defaultOptions = {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      signal: controller.signal,
      ...options,
    };

    let lastError = null;
    
    for (let attempt = 0; attempt <= this.retries; attempt++) {
      try {
        const response = await fetch(url, defaultOptions);
        clearTimeout(timeoutId);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        return { success: true, data, status: response.status };
        
      } catch (error) {
        lastError = error;
        
        // Не повторяем для определённых ошибок
        if (error.name === 'AbortError') {
          throw new Error(`Timeout: запрос превысил ${this.timeout}мс`);
        }
        
        // Последняя попытка
        if (attempt === this.retries) {
          break;
        }
        
        // Ждём перед следующей попыткой
        await this.sleep(this.retryDelay * (attempt + 1));
      }
    }
    
    clearTimeout(timeoutId);
    throw lastError || new Error('Неизвестная ошибка API');
  }

  /**
   * GET запрос
   */
  async get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const fullEndpoint = queryString ? `${endpoint}?${queryString}` : endpoint;
    return this.request(fullEndpoint);
  }

  /**
   * POST запрос
   */
  async post(endpoint, body = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  /**
   * Server-Sent Events (SSE) для real-time данных
   */
  createEventSource(endpoint, callbacks = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const eventSource = new EventSource(url);
    
    eventSource.onopen = () => {
      console.log(`[SSE] Подключено: ${endpoint}`);
      callbacks.onOpen?.();
    };
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        callbacks.onMessage?.(data);
      } catch (e) {
        console.error('[SSE] Ошибка парсинга:', e);
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('[SSE] Ошибка соединения:', error);
      callbacks.onError?.(error);
    };
    
    return eventSource;
  }

  /**
   * Утилита для задержки
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// === API Endpoints ===

class WG_API {
  constructor() {
    this.client = new APIClient();
  }

  // === Battles (Бои) ===

  /**
   * Получить тепловую карту боёв
   * @param {Object} params - { limit, min_battles }
   */
  async getBattlesHeatmap(params = {}) {
    return this.client.get('/battles/heatmap', params);
  }

  /**
   * Получить детали боя
   */
  async getBattleDetails(battleId) {
    return this.client.get(`/battles/${battleId}`);
  }

  // === Players (Игроки) ===

  /**
   * Поиск игрока по нику
   */
  async searchPlayer(nickname) {
    return this.client.get('/player/search', { nickname });
  }

  /**
   * Получить статистику игрока
   */
  async getPlayerStats(accountId) {
    return this.client.get(`/player/${accountId}/stats`);
  }

  /**
   * Получить историю боёв игрока
   */
  async getPlayerBattles(accountId, params = {}) {
    return this.client.get(`/player/${accountId}/battles`, params);
  }

  /**
   * Получить тепловую карту игрока
   */
  async getPlayerHeatmap(accountId) {
    return this.client.get(`/player/${accountId}/heatmap`);
  }

  /**
   * Получить топ танки игрока
   */
  async getPlayerTopTanks(accountId, limit = 10) {
    return this.client.get(`/player/${accountId}/tanks/top`, { limit });
  }

  // === Antibot (Антибот) ===

  /**
   * Проверить игрока на бота
   */
  async checkAntibot(accountId) {
    return this.client.get('/antibot/check', { account_id: accountId });
  }

  /**
   * Получить последние проверки антибота
   */
  async getAntibotRecent(limit = 100) {
    return this.client.get('/antibot/recent', { limit });
  }

  /**
   * Получить топ подозрительных игроков
   */
  async getAntibotSuspicious(limit = 50) {
    return this.client.get('/antibot/suspicious', { limit });
  }

  /**
   * Получить статистику антибота за 24ч
   */
  async getAntibotStats() {
    return this.client.get('/antibot/stats/24h');
  }

  /**
   * Real-time поток проверок антибота (SSE)
   */
  streamAntibotChecks(callbacks) {
    return this.client.createEventSource('/antibot/stream', callbacks);
  }

  // === ML Clusters (Кластеры) ===

  /**
   * Получить кластер игрока
   */
  async getPlayerCluster(accountId) {
    return this.client.get('/ml/cluster', { account_id: accountId });
  }

  /**
   * Получить статистику по всем кластерам
   */
  async getClustersStats() {
    return this.client.get('/ml/clusters/stats');
  }

  /**
   * Получить игроков из кластера
   */
  async getClusterPlayers(clusterId, limit = 100) {
    return this.client.get(`/ml/cluster/${clusterId}/players`, { limit });
  }

  /**
   * Получить центроиды кластеров (для визуализации)
   */
  async getClustersCentroids() {
    return this.client.get('/ml/clusters/centroids');
  }

  // === Locations (Локации) ===

  /**
   * Получить все локации
   */
  async getLocations() {
    return this.client.get('/locations');
  }

  /**
   * Получить локацию по ID
   */
  async getLocation(locationId) {
    return this.client.get(`/locations/${locationId}`);
  }

  /**
   * Создать новую локацию
   */
  async createLocation(locationData) {
    return this.client.post('/locations', locationData);
  }

  /**
   * Обновить локацию
   */
  async updateLocation(locationId, locationData) {
    return this.client.post(`/locations/${locationId}`, locationData);
  }

  /**
   * Удалить локацию
   */
  async deleteLocation(locationId) {
    return this.client.post(`/locations/${locationId}/delete`);
  }

  /**
   * Получить статистику локации (бои, винрейт и т.д.)
   */
  async getLocationStats(locationId) {
    return this.client.get(`/locations/${locationId}/stats`);
  }

  /**
   * Получить тепловую карту с учётом локаций
   */
  async getHeatmapWithLocations(params = {}) {
    return this.client.get('/battles/heatmap/locations', params);
  }

  // === Analytics (Аналитика) ===

  /**
   * Контроль кланов на карте (за последние 30 дней)
   */
  async getMapClanControl(days = 30) {
    return this.client.get('/analytics/map/clan-control', { days });
  }

  /**
   * Пиковые часы активности
   * @param {Object} params - { date_from, date_to, timezone }
   */
  async getPeakHours(params = {}) {
    return this.client.get('/analytics/time/peak-hours', params);
  }

  /**
   * Предсказание оттока игроков (churn prediction)
   * @param {Object} params - { date_from, date_to, risk_threshold, limit }
   */
  async getChurnPrediction(params = {}) {
    return this.client.get('/analytics/predictions/churn', params);
  }

  /**
   * Детали предсказания для конкретного игрока
   */
  async getPlayerChurnDetails(accountId) {
    return this.client.get(`/analytics/predictions/churn/${accountId}`);
  }

  /**
   * Тепловая карта аналитики
   * @param {Object} params - { date_from, date_to }
   */
  async getAnalyticsHeatmap(params = {}) {
    return this.client.get('/analytics/map/heatmap', params);
  }

  /**
   * Топ PvE локаций
   * @param {Object} params - { date_from, date_to, limit }
   */
  async getPveTopLocations(params = {}) {
    return this.client.get('/analytics/pve/top-locations', params);
  }

  /**
   * PvP горячие точки
   * @param {Object} params - { date_from, date_to }
   */
  async getPvpHotspots(params = {}) {
    return this.client.get('/analytics/map/pvp-hotspots', params);
  }

  /**
   * PvP ELO рейтинг
   * @param {Object} params - { date_from, date_to, limit }
   */
  async getPvpElo(params = {}) {
    return this.client.get('/analytics/pvp/elo', params);
  }

  /**
   * Игроки по профессиям
   * @param {Object} params - { date_from, date_to, profession }
   */
  async getPlayersByProfession(params = {}) {
    return this.client.get('/players/by-profession', params);
  }

  /**
   * Тепловая карта активности по времени
   * @param {Object} params - { date_from, date_to }
   */
  async getActivityHeatmap(params = {}) {
    return this.client.get('/analytics/time/activity-heatmap', params);
  }

  // === System (Система) ===

  /**
   * Health check
   */
  async healthCheck() {
    return this.client.get('/health');
  }

  /**
   * Статистика системы
   */
  async getSystemStats() {
    return this.client.get('/stats');
  }
}

// === Глобальный экземпляр ===
const api = new WG_API();

// === Утилиты для UI ===

/**
 * Отобразить ошибку в UI
 */
function showError(message, containerId = 'error-container') {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error('Error container not found:', containerId);
    alert(`Ошибка: ${message}`);
    return;
  }
  
  container.innerHTML = `
    <div class="error-toast">
      <span class="error-icon">⚠️</span>
      <span class="error-message">${message}</span>
      <button class="error-close" onclick="this.parentElement.remove()">✕</button>
    </div>
  `;
  container.style.display = 'block';
  
  // Автоматически скрыть через 5 секунд
  setTimeout(() => {
    if (container.firstElementChild) {
      container.firstElementChild.style.opacity = '0';
      setTimeout(() => container.remove(), 300);
    }
  }, 5000);
}

/**
 * Показать индикатор загрузки
 */
function showLoading(containerId = 'loading-container') {
  const container = document.getElementById(containerId);
  if (container) {
    container.style.display = 'flex';
  }
}

/**
 * Скрыть индикатор загрузки
 */
function hideLoading(containerId = 'loading-container') {
  const container = document.getElementById(containerId);
  if (container) {
    container.style.display = 'none';
  }
}

/**
 * Форматирование числа с разделителями
 */
function formatNumber(num) {
  return new Intl.NumberFormat('ru-RU').format(num);
}

/**
 * Форматирование процента
 */
function formatPercent(num, decimals = 1) {
  return num.toFixed(decimals) + '%';
}

/**
 * Форматирование даты/времени
 */
function formatDateTime(timestamp) {
  const date = new Date(timestamp);
  return new Intl.DateTimeFormat('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/**
 * Относительное время ("2 минуты назад")
 */
function timeAgo(timestamp) {
  const seconds = Math.floor((Date.now() - new Date(timestamp)) / 1000);
  
  const intervals = [
    { label: 'год', seconds: 31536000 },
    { label: 'месяц', seconds: 2592000 },
    { label: 'день', seconds: 86400 },
    { label: 'час', seconds: 3600 },
    { label: 'минута', seconds: 60 },
    { label: 'секунда', seconds: 1 },
  ];
  
  for (const interval of intervals) {
    const count = Math.floor(seconds / interval.seconds);
    if (count >= 1) {
      return `${count} ${getRussianPlural(count, interval.label)} назад`;
    }
  }
  
  return 'только что';
}

/**
 * Склонение русских слов
 */
function getRussianPlural(count, word) {
  const cases = {
    'год': ['год', 'года', 'лет'],
    'месяц': ['месяц', 'месяца', 'месяцев'],
    'день': ['день', 'дня', 'дней'],
    'час': ['час', 'часа', 'часов'],
    'минута': ['минута', 'минуты', 'минут'],
    'секунда': ['секунда', 'секунды', 'секунд'],
  };
  
  const forms = cases[word] || [word, word, word];
  const mod100 = count % 100;
  const mod10 = count % 10;
  
  if (mod100 >= 11 && mod100 <= 19) return forms[2];
  if (mod10 === 1) return forms[0];
  if (mod10 >= 2 && mod10 <= 4) return forms[1];
  return forms[2];
}

/**
 * Debounce функция (для поиска)
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Экспорт для использования в модулях
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { api, WG_API, APIClient, showError, showLoading, hideLoading };
}

