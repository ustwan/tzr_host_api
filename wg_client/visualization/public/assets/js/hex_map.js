// Модуль для работы с гексагональной картой
class HexMap {
    constructor() {
        this.grid = null;
        this.mapData = null;
        this.battleData = null;
        this.hexes = new Map(); // Кэш гексов по координатам
        this.selectedHexes = new Set(); // Выбранные гексы
        this.showLabels = false;
        this.currentTooltip = null; // Для управления tooltip
        // Конфигурация ассетов (по умолчанию можно переопределить через setAssetsConfig)
        this.assetsConfig = {
            spritesBasePath: 'exp/sprites/',
            tilesBasePath: 'exp/images/',
            defaultSprite: '1128.png', // запасной спрайт
            objectSprite: '1125.png',  // запасной спрайт объекта
            // Резолвер имен сущностей в файл спрайта (можно переопределить)
            spriteResolver: (login) => {
                // Пример: по префиксам монстров/игроков вернуть конкретные файлы
                if (login && login.startsWith('$rat')) return '1439.png';
                if (login && login.startsWith('$stich')) return '1441.png';
                return null;
            },
        };
    }
    
    // Инициализация сетки
    init() {
        this.grid = document.getElementById('hex-grid');
        if (this.grid) {
            this.grid.classList.add('hide-labels');
        }
        // Подтягиваем локально сохранённые настройки
        this.loadLocalConfig();
        this.createHexGrid();
    }

    // Установка конфигурации ассетов (пути, дефолтные спрайты, резолвер)
    setAssetsConfig(config) {
        this.assetsConfig = { ...this.assetsConfig, ...config };
    }

    async loadTokenSpriteMap(url = 'bmap/token_sprite_map.json') {
        try {
            const res = await fetch(`${url}?t=${Date.now()}`, { cache: 'no-store' });
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const data = await res.json();
            // Поддержка как старого формата, так и нового словаря
            if (data && data.tokens) {
                // Новый формат: { tokens: { T: { sprite, props, visual } } }
                const t2s = {}; const props = {}; const visual = {};
                for (const [tok, def] of Object.entries(data.tokens)) {
                    if (!def || typeof def !== 'object') continue;
                    if (def.sprite) t2s[tok] = def.sprite;
                    if (def.props) props[tok] = def.props;
                    if (def.visual) visual[tok] = def.visual;
                }
                this.assetsConfig.tokenToSprite = t2s;
                this.assetsConfig.tokenProps = props;
                this.assetsConfig.tokenVisual = visual;
            } else {
                // Старый формат: { tokenToSprite, tokenProps, tokenVisual }
                this.assetsConfig.tokenToSprite = data.tokenToSprite || {};
                this.assetsConfig.tokenProps = data.tokenProps || {};
                this.assetsConfig.tokenVisual = data.tokenVisual || {};
            }
            // Поверх сервера применяем локальные правки
            this.mergeLocalConfig();
            return true;
        } catch (e) {
            console.warn('Failed to load token sprite map:', e.message);
            this.assetsConfig.tokenToSprite = this.assetsConfig.tokenToSprite || {};
            this.assetsConfig.tokenProps = this.assetsConfig.tokenProps || {};
            this.assetsConfig.tokenVisual = this.assetsConfig.tokenVisual || {};
            this.mergeLocalConfig();
            return false;
        }
    }

    // Удалено: поддержка единого словаря — используем только token_sprite_map.json

    // Локальное хранение/загрузка настроек
    loadLocalConfig() {
        try {
            const raw = localStorage.getItem('hexMapConfig');
            if (!raw) return;
            const cfg = JSON.parse(raw);
            // Не перекрываем сопоставления спрайтов из файла
            if (cfg.tokenProps) this.assetsConfig.tokenProps = { ...this.assetsConfig.tokenProps, ...cfg.tokenProps };
            if (cfg.tokenVisual) this.assetsConfig.tokenVisual = { ...this.assetsConfig.tokenVisual, ...cfg.tokenVisual };
        } catch {}
    }

    mergeLocalConfig() { this.loadLocalConfig(); }

    saveLocalConfig() {
        try {
            const payload = {
                // Не сохраняем tokenToSprite в localStorage, источником истины является JSON
                tokenProps: this.assetsConfig.tokenProps || {},
                tokenVisual: this.assetsConfig.tokenVisual || {},
            };
            localStorage.setItem('hexMapConfig', JSON.stringify(payload));
        } catch {}
    }

    // Установка фонового тайла (мозаика) аналогично DrawBGTile(tile_<type>)
    setBackgroundTile(tileFileName) {
        if (!this.grid) return;
        if (!tileFileName) {
            this.grid.style.backgroundImage = '';
            return;
        }
        const url = `${this.assetsConfig.tilesBasePath}${tileFileName}`;
        this.grid.style.backgroundImage = `url('${url}')`;
        this.grid.style.backgroundRepeat = 'repeat';
        this.grid.style.backgroundPosition = '0 0';
    }
    
    // Создание сетки гексов
    createHexGrid() {
        if (!this.grid) {
            console.error('Grid not found!');
            return;
        }
        
        this.grid.innerHTML = '';
        this.hexes.clear();
        
        // Создаем 1400 гексов (50x28)
        for (let y = 0; y < 28; y++) {
            for (let x = 0; x < 50; x++) {
                const hex = this.createHex(x, y);
                this.grid.appendChild(hex);
                this.hexes.set(`${x},${y}`, hex);
            }
        }
        
        console.log(`Created ${this.hexes.size} hexes`);
        this.updateCounts();
    }
    
    // Создание одного гекса
    createHex(x, y) {
        const hex = document.createElement('div');
        hex.className = 'hex';
        hex.dataset.x = x;
        hex.dataset.y = y;
        
        // Позиционируем гекс
        const { left, top } = this.getHexPosition(x, y);
        hex.style.left = `${left}px`;
        hex.style.top = `${top}px`;
        
        // Определяем тип гекса
        if (this.isExitZone(x, y)) {
            hex.classList.add('exit');
        } else {
            hex.classList.add('passable');
        }
        
        // Добавляем подпись снизу
        const label = document.createElement('div');
        label.className = 'hex-label';
        label.textContent = this.getHexLabel(x, y);
        hex.appendChild(label);
        
        // Добавляем текст внутри гекса
        const text = document.createElement('div');
        text.className = 'hex-text';
        text.textContent = this.getHexLabel(x, y);
        hex.appendChild(text);
        
        // Добавляем обработчики событий
        hex.addEventListener('click', (e) => this.toggleHexSelection(hex, e));
        hex.addEventListener('mouseenter', (e) => this.onHexHover(hex, e));
        hex.addEventListener('mouseleave', (e) => this.onHexLeave(hex, e));
        
        return hex;
    }
    
    // Получение позиции гекса (формулы из игры)
    getHexPosition(x, y) {
        const hexWidth = 36;  // ширина гекса (визуал)
        const hexHeight = 19; // высота гекса (визуал)
        const hexRadius = hexWidth / 2;

        // Логика позиционирования как в simple_hex.html (staggered rows):
        // - Нечетные ряды (1,3,5,...) без сдвига
        // - Четные ряды (0,2,4,...) сдвинуты на половину ширины
        // - Вертикальный шаг составляет ~3/4 высоты гекса
        const xOffset = ((y + 1) % 2) * hexRadius;
        const left = x * hexWidth + xOffset;
        const top = y * (hexHeight * 0.75);

        return { left, top };
    }
    
    // Проверка зоны выхода
    isExitZone(x, y) {
        return y === 0 || y === 27 || x === 0 || x === 49;
    }
    
    // Преобразование bx/by в x/y (правильная формула)
    bxByToXy(bx, by) {
        const x = bx - (24 - by) / 2 + 1;
        const y = by + 1; // Правильная формула
        return [Math.floor(x), Math.floor(y)];
    }

    // Получение подписи гекса (как в игре)
    getHexLabel(x, y) {
        if (y === 0) return `AA${x}`;
        if (y === 27) return `ZZ${x}`;
        
        const rowChar = String.fromCharCode(65 + y - 1);
        return `${rowChar}${x}`;
    }
    
    // Загрузка данных карты
    async loadMapData(xmlContent) {
        console.log('Загружаем данные карты...');
        console.log('Размер XML:', xmlContent.length, 'символов');
        
        try {
            const response = await fetch('/api/parse-map', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ xml: xmlContent })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.mapData = await response.json();
            console.log('Данные карты получены с сервера:', this.mapData);
            this.applyMapData();
        } catch (error) {
            console.error('Ошибка загрузки карты через API:', error);
            console.log('Переключаемся на локальный парсинг...');
            // Fallback - парсим локально
            this.parseMapLocally(xmlContent);
        }
    }
    
    // Локальный парсинг карты
    parseMapLocally(xmlContent) {
        console.log('Начинаем локальный парсинг карты...');
        const mapRows = [];
        const lines = xmlContent.trim().split(/\r?\n/);
        console.log(`Найдено ${lines.length} строк в файле`);
        
        for (const line of lines) {
            const match = line.match(/<MAP v="([^"]+)"/);
            if (match) {
                mapRows.push(match[1]);
            }
        }
        
        console.log(`Найдено ${mapRows.length} строк карты`);
        this.mapData = { rows: mapRows };
        this.applyMapData();
    }
    
    // Применение данных карты
    applyMapData() {
        if (!this.mapData || !this.mapData.rows) return;
        
        const rows = this.mapData.rows;
        for (let y = 0; y < rows.length; y++) {
            const row = rows[y];
            for (let x = 0; x < row.length; x++) {
                const token = row[x];
                const hex = this.hexes.get(`${x + 1},${y + 1}`); // +1 для учета зон выхода
                if (hex) {
                    this.updateHexType(hex, token);
                    if (this.assetsConfig.tokenToSprite && this.assetsConfig.tokenToSprite[token]) {
                        const img = hex.querySelector('.tile-sprite') || document.createElement('img');
                        img.className = 'tile-sprite';
                        img.src = `${this.assetsConfig.spritesBasePath}${this.assetsConfig.tokenToSprite[token]}`;
                        img.style.position = 'absolute';
                        // Полноразмерный спрайт (как в оригинале): точно 36x19, без клипования по гексу
                        img.style.top = '0';
                        img.style.left = '0';
                        img.style.width = '36px';
                        img.style.height = '19px';
                        img.style.right = '';
                        img.style.bottom = '';
                        img.style.objectFit = 'fill';
                        img.style.clipPath = '';
                        // Применяем визуальные настройки токена
                        const v = (this.assetsConfig.tokenVisual && this.assetsConfig.tokenVisual[token]) || {};
                        if (v.center) {
                            img.style.top = '50%';
                            img.style.left = '50%';
                            img.style.transform = `translate(-50%, -50%) scale(${v.scaleX || 1}, ${v.scaleY || 1})`;
                        } else {
                            img.style.transform = `translate(${v.offsetX || 0}px, ${v.offsetY || 0}px) scale(${v.scaleX || 1}, ${v.scaleY || 1})`;
                        }
                        img.style.zIndex = String(v.z != null ? v.z : 5);
                        img.style.pointerEvents = 'none';
                        if (!img.parentElement) hex.appendChild(img);
                        hex.classList.add('has-sprite');
                    } else {
                        hex.classList.remove('has-sprite');
                    }
                }
            }
        }
        
        this.updateCounts();
    }
    
    // Обновление типа гекса
    updateHexType(hex, token) {
        // Убираем все классы типов
        const typeClasses = ['passable', 'impassable', 'wall', 'wall-window', 'stone', 'sandbag', 'barbed-wire', 'hedgehog', 'tree', 'bush', 'stump'];
        typeClasses.forEach(cls => hex.classList.remove(cls));
        
        // Определяем тип по токену
        const type = this.getTokenType(token);
        hex.classList.add(type);
        
        // Добавляем токен в подпись
        const label = hex.querySelector('.hex-label');
        if (label) {
            const baseLabel = label.textContent;
            label.textContent = `${baseLabel}(${token})`;
        }
    }
    
    // Определение типа токена
    getTokenType(token) {
        // Свойства токена переопределяют тип
        if (this.assetsConfig.tokenProps && this.assetsConfig.tokenProps[token] && this.assetsConfig.tokenProps[token].passable != null) {
            return this.assetsConfig.tokenProps[token].passable ? 'passable' : 'impassable';
        }
        if (this.assetsConfig.tokenToSprite && this.assetsConfig.tokenToSprite[token]) return 'passable';
        const code = token.charCodeAt(0);
        if (code >= 65 && code <= 79) return 'passable';
        switch (token) {
            case 'P': return 'sandbag';
            case 'D': return 'wall';
            case 'C': return 'wall-window';
            case 'B': return 'stone';
            case 'Z': return 'hedgehog';
            case 'R': return 'tree';
            case 'L': return 'bush';
            case 'K': return 'stump';
            default: return 'impassable';
        }
    }
    
    // Загрузка данных боя
    async loadBattleData(battleContent) {
        console.log('Загружаем данные боя...');
        console.log('Размер файла:', battleContent.length, 'символов');
        
        try {
            const response = await fetch('/api/parse-battle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ battle: battleContent })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.battleData = await response.json();
            console.log('Данные боя получены с сервера:', this.battleData);
            this.applyBattleData();
        } catch (error) {
            console.error('Ошибка загрузки боя через API:', error);
            console.log('Переключаемся на локальный парсинг...');
            // Fallback - парсим локально
            this.parseBattleLocally(battleContent);
        }
    }
    
    // Локальный парсинг боя
    parseBattleLocally(battleContent) {
        console.log('Начинаем парсинг боя...');
        const positions = [];
        const objects = [];
        
        // Извлекаем только содержимое между тегами <BATTLE> и </BATTLE>
        const battleMatch = battleContent.match(/<BATTLE[^>]*>(.*?)<\/BATTLE>/s);
        if (!battleMatch) {
            console.error('Тег <BATTLE> не найден в файле');
            console.log('Первые 500 символов файла:', battleContent.substring(0, 500));
            return;
        }
        
        console.log('Тег <BATTLE> найден, извлекаем данные...');
        const battleData = battleMatch[1];
        const lines = battleData.split('\n');
        console.log(`Найдено ${lines.length} строк в теге <BATTLE>`);
        
        for (const line of lines) {
            // Парсим USER теги - ищем атрибуты независимо от порядка
            const loginMatch = line.match(/login="([^"]+)"/);
            const levelMatch = line.match(/level="(\d+)"/);
            const hpMatch = line.match(/HP="(\d+)"/);
            const bxMatch = line.match(/bx="(\d+)"/);
            const byMatch = line.match(/by="(\d+)"/);
            const maxHPMatch = line.match(/maxHP="(\d+)"/);
            
            if (loginMatch && levelMatch && hpMatch && bxMatch && byMatch && maxHPMatch) {
                positions.push({
                    login: loginMatch[1],
                    x: parseInt(bxMatch[1]),
                    y: parseInt(byMatch[1]),
                    hp: parseInt(hpMatch[1]),
                    maxHP: parseInt(maxHPMatch[1]),
                    lvl: parseInt(levelMatch[1]) || 1,
                    def: 0 // В файле нет def атрибута
                });
            }
            
            // Парсим объекты (O теги) - ищем атрибуты независимо от порядка
            const objBxMatch = line.match(/bx="(\d+)"/);
            const objByMatch = line.match(/by="(\d+)"/);
            const txtMatch = line.match(/txt="([^"]+)"/);
            const countMatch = line.match(/count="(\d+)"/);
            
            if (objBxMatch && objByMatch && txtMatch && countMatch) {
                objects.push({
                    x: parseInt(objBxMatch[1]),
                    y: parseInt(objByMatch[1]),
                    txt: txtMatch[1],
                    count: parseInt(countMatch[1])
                });
            }
        }
        
        console.log(`Найдено ${positions.length} сущностей и ${objects.length} объектов в теге <BATTLE>`);
        this.battleData = { positions, objects };
        this.applyBattleData();
    }
    
    // Применение данных боя
    applyBattleData() {
        console.log('Применяем данные боя...');
        if (!this.battleData) {
            console.error('Данные боя отсутствуют!');
            return;
        }
        
        console.log('Данные боя:', this.battleData);
        
        // Очищаем предыдущие позиции и объекты
        document.querySelectorAll('.hex.monster, .hex.player, .hex.object').forEach(hex => {
            hex.classList.remove('monster', 'player', 'object');
            // Удаляем изображения
            const existingImg = hex.querySelector('.entity-image, .object-image');
            if (existingImg) {
                existingImg.remove();
            }
            // Удаляем данные сущности и объекта
            delete hex.dataset.entityData;
            delete hex.dataset.objectData;
        });
        
        // Добавляем позиции сущностей
        if (this.battleData.positions) {
            console.log('Добавляем позиции сущностей:', this.battleData.positions);
            this.battleData.positions.forEach(pos => {
                // Преобразуем bx/by в x/y координаты
                const [x, y] = this.bxByToXy(pos.x, pos.y);
                
                // Проверяем границы (наша сетка 50x28, координаты 0-49 и 0-27)
                if (x >= 0 && x < 50 && y >= 0 && y < 28) {
                    const hex = this.hexes.get(`${x},${y}`);
                    if (hex) {
                        const isMonster = pos.login.startsWith('$');
                        hex.classList.add(isMonster ? 'monster' : 'player');
                        
                        // Сохраняем данные сущности в dataset
                        hex.dataset.entityData = JSON.stringify({
                            login: pos.login,
                            hp: pos.hp,
                            maxHP: pos.maxHP,
                            lvl: pos.lvl,
                            def: pos.def
                        });
                        
                        console.log(`Добавляем сущность ${pos.login} на координаты ${x},${y} (bx=${pos.x}, by=${pos.y}) -> ${this.getHexLabel(x, y)}`);
                        // Добавляем изображение
                        this.addEntityImage(hex, pos.login, pos.hp, pos.maxHP);
                    } else {
                        console.log(`Гекс не найден для координат ${x},${y}`);
                    }
                } else {
                    console.log(`Сущность ${pos.login} вне границ: bx=${pos.x}, by=${pos.y} -> x=${x}, y=${y}`);
                }
            });
        }
        
        // Добавляем объекты
        if (this.battleData.objects) {
            console.log('Добавляем объекты:', this.battleData.objects);
            this.battleData.objects.forEach(obj => {
                // Преобразуем bx/by в x/y координаты
                const [x, y] = this.bxByToXy(obj.x, obj.y);
                
                // Проверяем границы (наша сетка 50x28, координаты 0-49 и 0-27)
                if (x >= 0 && x < 50 && y >= 0 && y < 28) {
                    const hex = this.hexes.get(`${x},${y}`);
                    if (hex) {
                        hex.classList.add('object');
                        
                        // Сохраняем данные объекта в dataset
                        hex.dataset.objectData = JSON.stringify({
                            txt: obj.txt,
                            count: obj.count
                        });
                        
                        console.log(`Добавляем объект ${obj.txt} на координаты ${x},${y} (bx=${obj.x}, by=${obj.y}) -> ${this.getHexLabel(x, y)}`);
                        // Добавляем изображение объекта
                        this.addObjectImage(hex, obj.txt, obj.count);
                    } else {
                        console.log(`Гекс не найден для объекта ${obj.txt} на координатах ${x},${y}`);
                    }
                } else {
                    console.log(`Объект ${obj.txt} вне границ: bx=${obj.x}, by=${obj.y} -> x=${x}, y=${y}`);
                }
            });
        }
        
        this.updateCounts();
    }
    
    // Добавление изображения сущности
    addEntityImage(hex, login, hp, maxHP) {
        const img = document.createElement('img');
        img.className = 'entity-image';
        // Определяем изображение по логину через резолвер/дефолт
        let spriteFile = null;
        try {
            spriteFile = this.assetsConfig.spriteResolver ? this.assetsConfig.spriteResolver(login) : null;
        } catch (_) { /* no-op */ }
        if (!spriteFile) spriteFile = this.assetsConfig.defaultSprite;
        img.src = `${this.assetsConfig.spritesBasePath}${spriteFile}`;
        img.alt = login;
        img.title = `${login} (${hp}/${maxHP} HP)`;
        
        // Позиционируем изображение по центру гекса
        img.style.position = 'absolute';
        img.style.top = '50%';
        img.style.left = '50%';
        img.style.transform = 'translate(-50%, -50%)';
        img.style.width = '36px';  // Размер гекса
        img.style.height = '19px'; // Размер гекса
        img.style.zIndex = '10';
        img.style.pointerEvents = 'none';
        // Убираем все лишние стили, оставляем только PNG
        img.style.borderRadius = '0';
        img.style.boxShadow = 'none';
        img.style.border = 'none';
        img.style.outline = 'none';
        
        hex.appendChild(img);
    }
    
    // Добавление изображения объекта
    addObjectImage(hex, txt, count) {
        const img = document.createElement('img');
        img.className = 'object-image';
        // Изображение объекта (можно заменить через setAssetsConfig)
        img.src = `${this.assetsConfig.spritesBasePath}${this.assetsConfig.objectSprite}`;
        img.alt = txt;
        img.title = `${txt} (${count} шт.)`;
        
        // Позиционируем изображение по центру гекса
        img.style.position = 'absolute';
        img.style.top = '50%';
        img.style.left = '50%';
        img.style.transform = 'translate(-50%, -50%)';
        img.style.width = '30px';  // Немного меньше гекса
        img.style.height = '15px'; // Немного меньше гекса
        img.style.zIndex = '5';
        img.style.pointerEvents = 'none';
        // Убираем все лишние стили, оставляем только PNG
        img.style.borderRadius = '0';
        img.style.boxShadow = 'none';
        img.style.border = 'none';
        img.style.outline = 'none';
        
        hex.appendChild(img);
    }
    
    // Обновление счетчиков
    updateCounts() {
        const hexCount = document.querySelectorAll('.hex').length;
        const monsterCount = document.querySelectorAll('.hex.monster').length;
        const playerCount = document.querySelectorAll('.hex.player').length;
        const selectedCount = this.selectedHexes.size;

        const hexEl = document.getElementById('hex-count');
        const monsterEl = document.getElementById('monster-count');
        const playerEl = document.getElementById('player-count');
        const selectedEl = document.getElementById('selected-count');

        if (hexEl) hexEl.textContent = hexCount;
        if (monsterEl) monsterEl.textContent = monsterCount;
        if (playerEl) playerEl.textContent = playerCount;
        if (selectedEl) selectedEl.textContent = selectedCount;
    }
    
    // Очистка карты
    clearMap() {
        const hexes = document.querySelectorAll('.hex');
        hexes.forEach(hex => {
            const x = parseInt(hex.dataset.x);
            const y = parseInt(hex.dataset.y);
            
            // Убираем все классы типов
            const typeClasses = ['passable', 'impassable', 'wall', 'wall-window', 'stone', 'sandbag', 'barbed-wire', 'hedgehog', 'tree', 'bush', 'stump', 'monster', 'player', 'object'];
            typeClasses.forEach(cls => hex.classList.remove(cls));
            
            // Удаляем изображения сущностей и объектов
            const existingImg = hex.querySelector('.entity-image, .object-image');
            if (existingImg) {
                existingImg.remove();
            }
            
            // Удаляем данные сущности и объекта
            delete hex.dataset.entityData;
            delete hex.dataset.objectData;
            
            // Возвращаем базовый тип
            if (this.isExitZone(x, y)) {
                hex.classList.add('exit');
            } else {
                hex.classList.add('passable');
            }
            
            // Очищаем подпись
            const label = hex.querySelector('.hex-label');
            if (label) {
                label.textContent = this.getHexLabel(x, y);
            }
        });
        
        this.updateCounts();
    }
    
    // Переключение выбора гекса
    toggleHexSelection(hex, event) {
        const key = `${hex.dataset.x},${hex.dataset.y}`;
        
        if (this.selectedHexes.has(key)) {
            this.selectedHexes.delete(key);
            hex.classList.remove('selected');
        } else {
            // снимаем выделение со всех
            this.selectedHexes.forEach(k => {
                const h = this.hexes.get(k);
                if (h) h.classList.remove('selected');
            });
            this.selectedHexes.clear();
            // выделяем текущий
            this.selectedHexes.add(key);
            hex.classList.add('selected');
        }
        
        this.updateCounts();
        event.stopPropagation();
    }
    
    // Hover эффект
    onHexHover(hex, event) {
        if (!hex.classList.contains('selected')) {
            hex.style.transform = 'scale(1.1)';
        }
        
        // Показываем tooltip
        this.showTooltip(hex, event);
    }
    
    onHexLeave(hex, event) {
        if (!hex.classList.contains('selected')) {
            hex.style.transform = '';
        }
        
        // Скрываем tooltip
        this.hideTooltip();
    }
    
    // Показать tooltip
    showTooltip(hex, event) {
        const x = parseInt(hex.dataset.x);
        const y = parseInt(hex.dataset.y);
        const token = this.getTokenFromHex(hex);
        
        // Удаляем старый tooltip
        this.hideTooltip();
        
        // Создаем новый tooltip
        const tooltip = document.createElement('div');
        tooltip.className = 'hex-tooltip';
        
        // Проверяем, есть ли сущность или объект на этом гексе
        const entityData = hex.dataset.entityData;
        const objectData = hex.dataset.objectData;
        let tooltipContent = `
            <div>Гекс: ${this.getHexLabel(x, y)}</div>
            <div>Токен: ${token}</div>
            <div>Координаты: bx=${x}, by=${y}</div>
        `;
        
        if (entityData) {
            try {
                const entity = JSON.parse(entityData);
                const isMonster = entity.login.startsWith('$');
                const entityType = isMonster ? 'Монстр' : 'Игрок';
                
                tooltipContent = `
                    <div><strong>${entityType}: ${entity.login}</strong></div>
                    <div>Гекс: ${this.getHexLabel(x, y)}</div>
                    <div>Токен: ${token}</div>
                    <div>Координаты: bx=${x}, by=${y}</div>
                    <div>HP: ${entity.hp}/${entity.maxHP}</div>
                    <div>Уровень: ${entity.lvl}</div>
                `;
                
                if (entity.def > 0) {
                    tooltipContent += `<div>Защита: ${entity.def}</div>`;
                }
            } catch (e) {
                console.error('Ошибка парсинга данных сущности:', e);
            }
        } else if (objectData) {
            try {
                const obj = JSON.parse(objectData);
                
                tooltipContent = `
                    <div><strong>Объект: ${obj.txt}</strong></div>
                    <div>Гекс: ${this.getHexLabel(x, y)}</div>
                    <div>Токен: ${token}</div>
                    <div>Координаты: bx=${x}, by=${y}</div>
                    <div>Количество: ${obj.count} шт.</div>
                `;
            } catch (e) {
                console.error('Ошибка парсинга данных объекта:', e);
            }
        }
        
        tooltip.innerHTML = tooltipContent;
        document.body.appendChild(tooltip);
        this.currentTooltip = tooltip;
        
        // Позиционируем tooltip под курсором на 20px ниже
        const mouseX = event.clientX;
        const mouseY = event.clientY;
        
        tooltip.style.left = mouseX + 'px';
        tooltip.style.top = (mouseY + 20) + 'px';
        tooltip.style.position = 'fixed';
        tooltip.style.zIndex = '1000';
    }
    
    // Скрыть tooltip
    hideTooltip() {
        if (this.currentTooltip) {
            this.currentTooltip.remove();
            this.currentTooltip = null;
        }
    }
    
    // Получить токен из гекса
    getTokenFromHex(hex) {
        // Получаем токен из данных карты или используем заглушку
        if (this.mapData && this.mapData.rows) {
            const y = parseInt(hex.dataset.y) - 1; // -1 для учета зон выхода
            const x = parseInt(hex.dataset.x) - 1; // -1 для учета зон выхода
            if (y >= 0 && y < this.mapData.rows.length && x >= 0 && x < this.mapData.rows[y].length) {
                return this.mapData.rows[y][x];
            }
        }
        return '?';
    }
    
    // Переключение подписей
    toggleLabels() {
        this.showLabels = !this.showLabels;
        const grid = document.getElementById('hex-grid');
        
        if (this.showLabels) {
            grid.classList.remove('hide-labels');
            document.getElementById('labels-btn').textContent = '🏷️ Подписи';
        } else {
            grid.classList.add('hide-labels');
            document.getElementById('labels-btn').textContent = '🏷️ Показать';
        }
    }
    
    
    // Очистка выбора
    clearSelection() {
        this.selectedHexes.forEach(key => {
            const hex = this.hexes.get(key);
            if (hex) {
                hex.classList.remove('selected');
            }
        });
        this.selectedHexes.clear();
        this.updateCounts();
    }
}

// Глобальный экземпляр
const hexMap = new HexMap();

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    console.log('hex_map.js: DOM loaded, initializing...');
    hexMap.init();
});

// Дополнительная инициализация через небольшую задержку
setTimeout(() => {
    if (hexMap.grid && hexMap.hexes.size === 0) {
        console.log('hex_map.js: Delayed initialization...');
        hexMap.init();
    }
}, 100);

// Экспорт для использования в HTML
window.hexMap = hexMap;
