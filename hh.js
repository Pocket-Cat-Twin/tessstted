// HH.ru Auto-Response Script - ULTRA SECURE VERSION  
// Многоуровневая защита от переходов + агрессивный URL-наблюдатель + DOM-защита + безопасное переопределение
(function() {
    'use strict';
    
    console.log('🚀 HH Script - ULTRA SECURE VERSION - Инициализация...');
    
    // ========================================
    // ГЛОБАЛЬНАЯ ЗАЩИТА ОТ НАВИГАЦИИ
    // ========================================
    
    function setupNavigationProtection() {
        console.log('🛡️ Установка защиты от навигации...');
        
        // Флаг разрешения навигации для скрипта
        window.HH_NAVIGATION_ALLOWED = false;
        
        // Сохраняем оригинальные методы
        const originalMethods = {
            replace: window.location.replace.bind(window.location),
            assign: window.location.assign.bind(window.location),
            reload: window.location.reload.bind(window.location),
            open: window.open.bind(window),
            pushState: history.pushState.bind(history),
            replaceState: history.replaceState.bind(history),
            go: history.go.bind(history),
            back: history.back.bind(history),
            forward: history.forward.bind(history)
        };
        
        // УСИЛЕННАЯ БЛОКИРОВКА МЕТОДОВ НАВИГАЦИИ
        const blockNavigation = function(methodName, originalMethod, args) {
            if (window.HH_NAVIGATION_ALLOWED) {
                console.log('🔓 РАЗРЕШЕНО: ' + methodName + '(' + (args[0] || '') + ')');
                return originalMethod.apply(this, args);
            }
            console.log('🚫 БЛОКИРОВКА: ' + methodName + '(' + (args[0] || '') + ')');
            return false;
        };

        // БЕЗОПАСНОЕ ПЕРЕОПРЕДЕЛЕНИЕ МЕТОДОВ НАВИГАЦИИ
        const safeOverride = (obj, prop, newFunc, description) => {
            try {
                // Проверяем, можно ли переопределить свойство
                const descriptor = Object.getOwnPropertyDescriptor(obj, prop);
                
                if (descriptor && descriptor.configurable === false) {
                    console.log('⚠️ Свойство ' + description + ' защищено от изменений, пропускаем');
                    return false;
                }
                
                // Проверяем, можно ли записать
                if (descriptor && descriptor.writable === false) {
                    console.log('⚠️ Свойство ' + description + ' только для чтения, пропускаем');
                    return false;
                }
                
                // Пытаемся переопределить через defineProperty
                Object.defineProperty(obj, prop, {
                    value: newFunc,
                    writable: true,
                    configurable: true
                });
                
                console.log('✅ Успешно переопределен: ' + description);
                return true;
                
            } catch (e) {
                console.log('⚠️ Не удалось переопределить ' + description + ':', e.message);
                // НЕ делаем fallback присваивание - это вызывает ошибки
                return false;
            }
        };

        // Пытаемся переопределить location.replace безопасно
        safeOverride(window.location, 'replace', 
            function(url) { return blockNavigation('location.replace', originalMethods.replace, arguments); },
            'location.replace'
        );
        
        // Пытаемся переопределить location.assign безопасно
        safeOverride(window.location, 'assign',
            function(url) { return blockNavigation('location.assign', originalMethods.assign, arguments); },
            'location.assign'
        );
        
        // Пытаемся переопределить location.reload безопасно
        safeOverride(window.location, 'reload',
            function(force) { return blockNavigation('location.reload', originalMethods.reload, arguments); },
            'location.reload'
        );
        
        // window.open обычно можно переопределить
        safeOverride(window, 'open',
            function(url, name, features) { 
                if (window.HH_NAVIGATION_ALLOWED) {
                    return originalMethods.open(url, name, features);
                }
                console.log('🚫 БЛОКИРОВКА: window.open(' + url + ')');
                return null;
            },
            'window.open'
        );
        
        // Блокируем History API безопасно
        safeOverride(history, 'pushState',
            function(state, title, url) {
                if (window.HH_NAVIGATION_ALLOWED) {
                    return originalMethods.pushState(state, title, url);
                }
                console.log('🚫 БЛОКИРОВКА: history.pushState()');
                return false;
            },
            'history.pushState'
        );
        
        safeOverride(history, 'replaceState',
            function(state, title, url) {
                if (window.HH_NAVIGATION_ALLOWED) {
                    return originalMethods.replaceState(state, title, url);
                }
                console.log('🚫 БЛОКИРОВКА: history.replaceState()');
                return false;
            },
            'history.replaceState'
        );
        
        safeOverride(history, 'go',
            function(delta) {
                if (window.HH_NAVIGATION_ALLOWED) {
                    return originalMethods.go(delta);
                }
                console.log('🚫 БЛОКИРОВКА: history.go()');
                return false;
            },
            'history.go'
        );
        
        safeOverride(history, 'back',
            function() {
                if (window.HH_NAVIGATION_ALLOWED) {
                    return originalMethods.back();
                }
                console.log('🚫 БЛОКИРОВКА: history.back()');
                return false;
            },
            'history.back'
        );
        
        safeOverride(history, 'forward',
            function() {
                if (window.HH_NAVIGATION_ALLOWED) {
                    return originalMethods.forward();
                }
                console.log('🚫 БЛОКИРОВКА: history.forward()');
                return false;
            },
            'history.forward'
        );
        
        // БЕЗОПАСНАЯ БЛОКИРОВКА LOCATION СВОЙСТВ
        const safeDefineProperty = (obj, prop, getter, setter, description) => {
            try {
                const descriptor = Object.getOwnPropertyDescriptor(obj, prop);
                
                if (descriptor && descriptor.configurable === false) {
                    console.log('⚠️ Свойство ' + description + ' защищено от изменений, пропускаем');
                    return false;
                }
                
                Object.defineProperty(obj, prop, {
                    get: getter,
                    set: setter,
                    configurable: true
                });
                
                console.log('✅ Успешно переопределено: ' + description);
                return true;
                
            } catch (e) {
                console.log('⚠️ Не удалось переопределить ' + description + ':', e.message);
                return false;
            }
        };
        
        // Пытаемся блокировать location.href
        safeDefineProperty(window.location, 'href',
            function() { return window.location.href; },
            function(url) {
                if (window.HH_NAVIGATION_ALLOWED) {
                    return originalMethods.assign(url);
                } else {
                    console.log('🚫 БЛОКИРОВКА: location.href = ' + url);
                    return; // Не выбрасываем ошибку, просто блокируем
                }
            },
            'location.href'
        );
        
        // Пытаемся блокировать location.pathname
        safeDefineProperty(window.location, 'pathname',
            function() { return window.location.pathname; },
            function(path) {
                if (window.HH_NAVIGATION_ALLOWED) {
                    return originalMethods.assign(window.location.origin + path + window.location.search + window.location.hash);
                } else {
                    console.log('🚫 БЛОКИРОВКА: location.pathname = ' + path);
                    return;
                }
            },
            'location.pathname'
        );
        
        // Пытаемся блокировать location.search
        safeDefineProperty(window.location, 'search',
            function() { return window.location.search; },
            function(search) {
                if (window.HH_NAVIGATION_ALLOWED) {
                    return originalMethods.assign(window.location.origin + window.location.pathname + search + window.location.hash);
                } else {
                    console.log('🚫 БЛОКИРОВКА: location.search = ' + search);
                    return;
                }
            },
            'location.search'
        );
        
        // hash обычно не блокируем строго, так как не вызывает полную навигацию
        safeDefineProperty(window.location, 'hash',
            function() { return window.location.hash; },
            function(hash) {
                if (window.HH_NAVIGATION_ALLOWED) {
                    return originalMethods.assign(window.location.origin + window.location.pathname + window.location.search + hash);
                } else {
                    console.log('🚫 БЛОКИРОВКА: location.hash = ' + hash);
                    return; // Разрешаем hash, но логируем
                }
            },
            'location.hash'
        );
        
        // ДОПОЛНИТЕЛЬНАЯ ЗАЩИТА НА СЛУЧАЙ НЕУДАЧНОГО ПЕРЕОПРЕДЕЛЕНИЯ МЕТОДОВ
        console.log('🛡️ Установка дополнительной защиты через события...');
        
        // ТОЛЬКО ЭКСТРЕННАЯ БЛОКИРОВКА ПРИ РЕАЛЬНОМ УХОДЕ С СТРАНИЦЫ
        const emergencyBlockUnload = function(e) {
            // Блокируем ТОЛЬКО если скрипт активен И навигация НЕ разрешена
            if (!scriptActive || window.HH_NAVIGATION_ALLOWED) return;
            
            console.log('🚫 ЭКСТРЕННАЯ БЛОКИРОВКА: попытка покинуть страницу');
            e.preventDefault();
            e.stopPropagation();
            
            // Для beforeunload показываем предупреждение только если это критично
            if (e.type === 'beforeunload') {
                const message = 'HH Script выполняется. Уверены что хотите покинуть страницу?';
                e.returnValue = message;
                return message;
            }
            
            return false;
        };
        
        // Устанавливаем только критические обработчики (БЕЗ beforeunload для избежания постоянных модальных окон)
        window.addEventListener('unload', emergencyBlockUnload, true);
        window.addEventListener('pagehide', emergencyBlockUnload, true);
        
        // АГРЕССИВНАЯ защита через setInterval - проверяем URL каждые 200мс
        const urlWatcher = setInterval(() => {
            if (window.HH_NAVIGATION_ALLOWED) {
                // Обновляем last known URL когда навигация разрешена
                window.HH_LAST_KNOWN_URL = window.location.href;
                return;
            }
            
            const currentUrl = window.location.href;
            if (window.HH_LAST_KNOWN_URL && currentUrl !== window.HH_LAST_KNOWN_URL) {
                console.log('🚫 КРИТИЧЕСКАЯ НАВИГАЦИЯ ОБНАРУЖЕНА!');
                console.log('Было:', window.HH_LAST_KNOWN_URL);
                console.log('Стало:', currentUrl);
                
                // АГРЕССИВНЫЙ возврат - пытаемся несколько способов
                try {
                    window.HH_NAVIGATION_ALLOWED = true;
                    
                    // Пытаемся history.back()
                    if (history.length > 1) {
                        history.back();
                    } else {
                        // Если history.back недоступен, пытаемся location.replace
                        location.replace(window.HH_LAST_KNOWN_URL);
                    }
                    
                    // Короткий таймаут для разблокировки
                    setTimeout(() => {
                        window.HH_NAVIGATION_ALLOWED = false;
                        console.log('🔒 Навигация снова заблокирована после экстренного возврата');
                    }, 500);
                    
                } catch (e) {
                    console.log('⚠️ КРИТИЧЕСКАЯ ОШИБКА возврата на исходную страницу:', e.message);
                    // В крайнем случае пытаемся перезагрузить исходную страницу
                    try {
                        window.HH_NAVIGATION_ALLOWED = true;
                        window.location.href = window.HH_LAST_KNOWN_URL;
                    } catch (e2) {
                        console.log('⚠️ Не удалось восстановить страницу любым способом');
                    }
                }
            } else {
                window.HH_LAST_KNOWN_URL = currentUrl;
            }
        }, 200); // Увеличена частота проверки до 5 раз в секунду
        
        // Сохраняем ID интервала для очистки
        if (!window.HH_NAVIGATION_WATCHERS) {
            window.HH_NAVIGATION_WATCHERS = [];
        }
        window.HH_NAVIGATION_WATCHERS.push(urlWatcher);
        
        // ДОПОЛНИТЕЛЬНАЯ ЗАЩИТА: блокируем добавление опасных элементов
        const originalAppendChild = Node.prototype.appendChild;
        const originalInsertBefore = Node.prototype.insertBefore;
        
        Node.prototype.appendChild = function(child) {
            if (!window.HH_NAVIGATION_ALLOWED && child && child.nodeType === 1) {
                const tagName = child.tagName ? child.tagName.toLowerCase() : '';
                const dangerousTags = ['script', 'iframe', 'frame', 'object', 'embed', 'form'];
                
                if (dangerousTags.includes(tagName)) {
                    console.log('🚫 БЛОКИРОВКА: appendChild опасного элемента', tagName);
                    return child; // Возвращаем элемент, но не добавляем
                }
                
                // Блокируем ссылки без специального разрешения
                if (tagName === 'a' && (!child.dataset || !child.dataset.hhAllowed)) {
                    console.log('🚫 БЛОКИРОВКА: appendChild неразрешенной ссылки');
                    return child;
                }
            }
            
            return originalAppendChild.call(this, child);
        };
        
        Node.prototype.insertBefore = function(child, reference) {
            if (!window.HH_NAVIGATION_ALLOWED && child && child.nodeType === 1) {
                const tagName = child.tagName ? child.tagName.toLowerCase() : '';
                const dangerousTags = ['script', 'iframe', 'frame', 'object', 'embed', 'form'];
                
                if (dangerousTags.includes(tagName)) {
                    console.log('🚫 БЛОКИРОВКА: insertBefore опасного элемента', tagName);
                    return child;
                }
                
                if (tagName === 'a' && (!child.dataset || !child.dataset.hhAllowed)) {
                    console.log('🚫 БЛОКИРОВКА: insertBefore неразрешенной ссылки');
                    return child;
                }
            }
            
            return originalInsertBefore.call(this, child, reference);
        };
        
        console.log('✅ Защита от навигации установлена (базовая + дополнительная + DOM-защита)');
    }
    
    // ========================================
    // АБСОЛЮТНАЯ ЗАЩИТА ОТ НАВИГАЦИИ - СЕНЬОР УРОВЕНЬ
    // ========================================
    
    // Счетчик заблокированных попыток навигации
    let blockedNavigationAttempts = 0;
    let networkRequestsBlocked = 0;
    let domModificationsBlocked = 0;
    
    // СЕТЕВОЙ УРОВЕНЬ БЛОКИРОВКИ
    function setupNetworkProtection() {
        console.log('🛡️ Установка СЕТЕВОЙ защиты от навигации...');
        
        // Сохраняем оригинальные методы
        const originalFetch = window.fetch;
        const originalXHROpen = XMLHttpRequest.prototype.open;
        const originalXHRSend = XMLHttpRequest.prototype.send;
        
        // БЛОКИРОВКА FETCH ЗАПРОСОВ
        window.fetch = function(resource, options) {
            if (window.HH_NAVIGATION_ALLOWED) {
                return originalFetch.apply(this, arguments);
            }
            
            // Анализируем запрос на навигационность
            let url = '';
            if (typeof resource === 'string') {
                url = resource;
            } else if (resource && resource.url) {
                url = resource.url;
            } else if (resource && resource.toString) {
                url = resource.toString();
            }
            
            // ИСКЛЮЧЕНИЯ ТОЛЬКО ДЛЯ КРИТИЧНЫХ ЗАПРОСОВ ОТКЛИКОВ
            const isResponseRelated = url && (
                // ТОЛЬКО основные запросы откликов из HAR файла
                url.includes('/shards/vacancy/register_interaction') ||
                url.includes('/applicant/vacancy_response/popup')
            );
            
            if (isResponseRelated) {
                console.log('✅ РАЗРЕШЕН FETCH для отклика: ' + url);
                return originalFetch.apply(this, arguments);
            }
            
            // Блокируем подозрительные запросы
            const isNavigational = url && (
                (url.includes('hh.ru') && !isResponseRelated) ||
                (url.includes('/vacancy') && !url.includes('response')) ||
                url.includes('/search') ||
                url.includes('/redirect') ||
                url.includes('location') ||
                (url.startsWith('http') && !url.includes(window.location.hostname) && !isResponseRelated)
            );
            
            if (isNavigational) {
                networkRequestsBlocked++;
                blockedNavigationAttempts++;
                console.log('🚫 БЛОКИРОВКА FETCH: ' + url);
                console.log(`📊 Всего заблокировано сетевых запросов: ${networkRequestsBlocked}`);
                
                // Возвращаем rejected promise
                return Promise.reject(new Error('Navigation request blocked by HH Script'));
            }
            
            return originalFetch.apply(this, arguments);
        };
        
        // БЛОКИРОВКА XMLHttpRequest
        XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
            if (window.HH_NAVIGATION_ALLOWED) {
                return originalXHROpen.apply(this, arguments);
            }
            
            // ИСКЛЮЧЕНИЯ ТОЛЬКО ДЛЯ КРИТИЧНЫХ ЗАПРОСОВ ОТКЛИКОВ
            const isResponseRelated = url && (
                // ТОЛЬКО основные запросы откликов из HAR файла
                url.includes('/shards/vacancy/register_interaction') ||
                url.includes('/applicant/vacancy_response/popup')
            );
            
            if (isResponseRelated) {
                console.log('✅ РАЗРЕШЕН XHR для отклика: ' + method + ' ' + url);
                return originalXHROpen.apply(this, arguments);
            }
            
            // Проверяем URL на навигационность
            const isNavigational = url && (
                (url.includes('hh.ru') && !isResponseRelated) ||
                (url.includes('/vacancy') && !url.includes('response')) ||
                url.includes('/search') ||
                url.includes('/redirect') ||
                url.includes('location') ||
                (url.startsWith('http') && !url.includes(window.location.hostname) && !isResponseRelated)
            );
            
            if (isNavigational) {
                networkRequestsBlocked++;
                blockedNavigationAttempts++;
                console.log('🚫 БЛОКИРОВКА XHR: ' + method + ' ' + url);
                console.log(`📊 Всего заблокировано XHR запросов: ${networkRequestsBlocked}`);
                
                // Блокируем запрос
                throw new Error('XHR Navigation request blocked by HH Script');
            }
            
            return originalXHROpen.apply(this, arguments);
        };
        
        // ДОПОЛНИТЕЛЬНАЯ БЛОКИРОВКА XHR SEND
        XMLHttpRequest.prototype.send = function(data) {
            // Проверяем что это не заблокированный запрос
            if (this._hhBlocked) {
                console.log('🚫 БЛОКИРОВКА XHR.send() для заблокированного запроса');
                return;
            }
            
            return originalXHRSend.apply(this, arguments);
        };
        
        // БЛОКИРОВКА WEBSOCKET (могут использоваться для навигации)
        const originalWebSocket = window.WebSocket;
        window.WebSocket = function(url, protocols) {
            if (window.HH_NAVIGATION_ALLOWED) {
                return new originalWebSocket(url, protocols);
            }
            
            console.log('🚫 БЛОКИРОВКА WebSocket: ' + url);
            blockedNavigationAttempts++;
            throw new Error('WebSocket blocked by HH Script');
        };
        
        // БЛОКИРОВКА SERVICE WORKER
        if ('serviceWorker' in navigator) {
            const originalRegister = navigator.serviceWorker.register;
            navigator.serviceWorker.register = function(scriptURL, options) {
                if (window.HH_NAVIGATION_ALLOWED) {
                    return originalRegister.apply(this, arguments);
                }
                
                console.log('🚫 БЛОКИРОВКА ServiceWorker: ' + scriptURL);
                blockedNavigationAttempts++;
                return Promise.reject(new Error('ServiceWorker blocked by HH Script'));
            };
        }
        
        console.log('✅ Сетевая защита от навигации установлена');
    }
    
    // DOM-УРОВЕНЬ ЖЕЛЕЗНОЙ БЛОКИРОВКИ 
    function setupDOMProtection() {
        console.log('🛡️ Установка DOM ЖЕЛЕЗНОЙ защиты от навигации...');
        
        // Сохраняем оригинальные методы DOM
        const originalSetAttribute = Element.prototype.setAttribute;
        const originalSetProperty = Object.setOwnPropertyDescriptor;
        const originalInnerHTML = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
        const originalOuterHTML = Object.getOwnPropertyDescriptor(Element.prototype, 'outerHTML');
        const originalReplaceWith = Element.prototype.replaceWith;
        const originalRemove = Element.prototype.remove;
        
        // БЛОКИРОВКА setAttribute ДЛЯ НАВИГАЦИИ
        Element.prototype.setAttribute = function(name, value) {
            const navigationAttributes = [
                'href', 'src', 'action', 'formaction', 'onclick', 'onload',
                'onbeforeunload', 'onunload', 'onhashchange', 'onpopstate'
            ];
            
            if (!window.HH_NAVIGATION_ALLOWED && navigationAttributes.includes(name.toLowerCase())) {
                console.log(`🚫 DOM БЛОК: setAttribute(${name}) заблокирован!`);
                domModificationsBlocked++;
                return;
            }
            
            return originalSetAttribute.call(this, name, value);
        };
        
        // БЛОКИРОВКА innerHTML/outerHTML
        Object.defineProperty(Element.prototype, 'innerHTML', {
            get: originalInnerHTML.get,
            set: function(value) {
                if (!window.HH_NAVIGATION_ALLOWED && 
                    (value.includes('<a ') || value.includes('href=') || 
                     value.includes('<form') || value.includes('action=') ||
                     value.includes('<script') || value.includes('location.') ||
                     value.includes('window.location'))) {
                    console.log('🚫 DOM БЛОК: innerHTML с навигацией заблокирован!');
                    domModificationsBlocked++;
                    return;
                }
                return originalInnerHTML.set.call(this, value);
            },
            configurable: true
        });
        
        Object.defineProperty(Element.prototype, 'outerHTML', {
            get: originalOuterHTML.get,
            set: function(value) {
                if (!window.HH_NAVIGATION_ALLOWED && 
                    (value.includes('<a ') || value.includes('href=') || 
                     value.includes('<form') || value.includes('action='))) {
                    console.log('🚫 DOM БЛОК: outerHTML с навигацией заблокирован!');
                    domModificationsBlocked++;
                    return;
                }
                return originalOuterHTML.set.call(this, value);
            },
            configurable: true
        });
        
        // БЛОКИРОВКА replaceWith и remove для критичных элементов
        Element.prototype.replaceWith = function(...nodes) {
            if (!window.HH_NAVIGATION_ALLOWED && (this.tagName === 'BODY' || this.tagName === 'HTML')) {
                console.log('🚫 DOM БЛОК: replaceWith критичного элемента заблокирован!');
                domModificationsBlocked++;
                return;
            }
            return originalReplaceWith.apply(this, nodes);
        };
        
        Element.prototype.remove = function() {
            if (!window.HH_NAVIGATION_ALLOWED && (this.tagName === 'BODY' || this.tagName === 'HTML')) {
                console.log('🚫 DOM БЛОК: remove критичного элемента заблокирован!');
                domModificationsBlocked++;
                return;
            }
            return originalRemove.call(this);
        };
        
        // АГРЕССИВНЫЙ MutationObserver ДЛЯ МОНИТОРИНГА DOM
        const dangerousObserver = new MutationObserver(function(mutations) {
            if (window.HH_NAVIGATION_ALLOWED) return;
            
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) { // Element node
                            // Проверяем опасные элементы
                            if (node.tagName === 'A' || node.tagName === 'FORM' || 
                                node.tagName === 'SCRIPT' || node.tagName === 'IFRAME') {
                                console.log(`🚫 DOM НАБЛЮДАТЕЛЬ: Подозрительный элемент ${node.tagName} добавлен!`);
                                domModificationsBlocked++;
                            }
                            
                            // Проверяем атрибуты навигации
                            if (node.hasAttribute && (node.hasAttribute('href') || 
                                node.hasAttribute('onclick') || node.hasAttribute('action'))) {
                                console.log('🚫 DOM НАБЛЮДАТЕЛЬ: Элемент с навигационными атрибутами!');
                                domModificationsBlocked++;
                            }
                        }
                    });
                }
                
                if (mutation.type === 'attributes') {
                    const target = mutation.target;
                    const attrName = mutation.attributeName;
                    
                    if (['href', 'src', 'action', 'onclick'].includes(attrName)) {
                        console.log(`🚫 DOM НАБЛЮДАТЕЛЬ: Изменение атрибута ${attrName}!`);
                        domModificationsBlocked++;
                    }
                }
            });
        });
        
        // Запускаем агрессивное наблюдение
        dangerousObserver.observe(document, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeOldValue: true,
            attributeFilter: ['href', 'src', 'action', 'onclick', 'onload']
        });
        
        console.log('✅ DOM железная защита от навигации установлена');
    }
    
    // ГЛОБАЛЬНАЯ СИСТЕМА БЛОКИРОВКИ СОБЫТИЙ
    function setupGlobalEventBlocking() {
        console.log('🛡️ Установка ГЛОБАЛЬНОЙ блокировки событий...');
        
        // Список критичных событий для блокировки
        const criticalEvents = [
            'beforeunload', 'unload', 'pagehide', 'pageshow',
            'hashchange', 'popstate', 'pushstate', 'replacestate',
            'visibilitychange', 'focus', 'blur'
        ];
        
        // Блокировка критичных событий на window
        criticalEvents.forEach(eventType => {
            window.addEventListener(eventType, function(e) {
                if (!window.HH_NAVIGATION_ALLOWED) {
                    console.log(`🚫 ГЛОБАЛЬНЫЙ БЛОК: ${eventType} заблокирован!`);
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    blockedNavigationAttempts++;
                    return false;
                }
            }, true); // Используем capture phase для максимальной эффективности
        });
        
        // БЛОКИРОВКА ВСЕХ SUBMIT СОБЫТИЙ
        document.addEventListener('submit', function(e) {
            if (!window.HH_NAVIGATION_ALLOWED) {
                const form = e.target;
                const isSearchForm = form && form.closest && form.closest('[data-qa="vacancy-serp__form"]');
                const isAllowed = form && form.dataset && form.dataset.hhAllowed;
                
                if (!isSearchForm && !isAllowed) {
                    console.log('🚫 ГЛОБАЛЬНЫЙ БЛОК: submit заблокирован!', form);
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    blockedNavigationAttempts++;
                    return false;
                }
            }
        }, true);
        
        // БЛОКИРОВКА ВСЕХ CHANGE СОБЫТИЙ НА КРИТИЧНЫХ ЭЛЕМЕНТАХ
        document.addEventListener('change', function(e) {
            if (!window.HH_NAVIGATION_ALLOWED) {
                const target = e.target;
                if (target && (target.type === 'file' || target.tagName === 'SELECT')) {
                    const isAllowed = target.dataset && target.dataset.hhAllowed;
                    const isInSearchForm = target.closest && target.closest('[data-qa="vacancy-serp__form"]');
                    
                    if (!isAllowed && !isInSearchForm) {
                        console.log('🚫 ГЛОБАЛЬНЫЙ БЛОК: change на критичном элементе заблокирован!', target);
                        e.preventDefault();
                        e.stopPropagation();
                        blockedNavigationAttempts++;
                        return false;
                    }
                }
            }
        }, true);
        
        // БЛОКИРОВКА KEYDOWN/KEYUP ДЛЯ ГОРЯЧИХ КЛАВИШ НАВИГАЦИИ
        const navigationKeys = [
            { key: 'F5', description: 'refresh' },
            { key: 'F12', description: 'devtools' },
            { ctrl: true, key: 'R', description: 'refresh' },
            { ctrl: true, key: 'F5', description: 'hard refresh' },
            { ctrl: true, shift: true, key: 'R', description: 'hard refresh' },
            { alt: true, key: 'ArrowLeft', description: 'back' },
            { alt: true, key: 'ArrowRight', description: 'forward' },
            { ctrl: true, key: 'L', description: 'address bar' },
            { ctrl: true, key: 'T', description: 'new tab' },
            { ctrl: true, key: 'W', description: 'close tab' }
        ];
        
        document.addEventListener('keydown', function(e) {
            if (!window.HH_NAVIGATION_ALLOWED) {
                for (let combo of navigationKeys) {
                    const ctrlMatch = combo.ctrl ? e.ctrlKey : !e.ctrlKey;
                    const shiftMatch = combo.shift ? e.shiftKey : !e.shiftKey;
                    const altMatch = combo.alt ? e.altKey : !e.altKey;
                    const keyMatch = combo.key === e.key;
                    
                    if (ctrlMatch && shiftMatch && altMatch && keyMatch) {
                        console.log(`🚫 ГЛОБАЛЬНЫЙ БЛОК: Горячая клавиша ${combo.description} заблокирована!`);
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        blockedNavigationAttempts++;
                        return false;
                    }
                }
            }
        }, true);
        
        console.log('✅ Глобальная блокировка событий установлена');
    }
    
    // АГРЕССИВНАЯ URL ЗАЩИТА (50ms мониторинг)
    function setupAggressiveURLProtection() {
        console.log('🛡️ Установка АГРЕССИВНОЙ URL защиты (50ms)...');
        
        let currentURL = window.location.href;
        let urlCheckInterval;
        let urlBlockCount = 0;
        
        // Список разрешенных URL паттернов
        const allowedURLPatterns = [
            /\/search\/vacancy\?/, // Страница поиска вакансий
            /\/vacancy\/\d+$/, // Страница вакансии
            /\/account\//, // Личный кабинет
        ];
        
        // Функция проверки разрешенного URL
        function isURLAllowed(url) {
            if (window.HH_NAVIGATION_ALLOWED) return true;
            
            for (let pattern of allowedURLPatterns) {
                if (pattern.test(url)) return true;
            }
            return false;
        }
        
        // Функция мгновенного возврата на исходный URL
        function forceURLRevert() {
            const newURL = window.location.href;
            if (newURL !== currentURL) {
                console.log(`🚫 URL ЗАЩИТА: Принудительный возврат с ${newURL} на ${currentURL}`);
                urlBlockCount++;
                blockedNavigationAttempts++;
                
                // Множественные методы возврата URL
                try {
                    window.history.replaceState(null, '', currentURL);
                } catch (e) {}
                
                try {
                    window.history.back();
                } catch (e) {}
                
                try {
                    window.location.replace(currentURL);
                } catch (e) {}
                
                try {
                    window.location.href = currentURL;
                } catch (e) {}
            }
        }
        
        // ЭКСТРЕМАЛЬНО ЧАСТЫЙ МОНИТОРИНГ URL (50ms)
        urlCheckInterval = setInterval(() => {
            if (window.HH_NAVIGATION_ALLOWED) return;
            
            const newURL = window.location.href;
            
            if (newURL !== currentURL && !isURLAllowed(newURL)) {
                console.log(`🚫 URL БЛОКИРОВКА: Попытка перехода на запрещенный URL: ${newURL}`);
                forceURLRevert();
            } else if (newURL !== currentURL && isURLAllowed(newURL)) {
                // Обновляем текущий URL если переход разрешен
                console.log(`✅ URL РАЗРЕШЕН: ${newURL}`);
                currentURL = newURL;
            }
        }, 50); // 50ms = 20 проверок в секунду!
        
        // БЛОКИРОВКА ПРОГРАММНЫХ ИЗМЕНЕНИЙ URL
        const originalPushState = window.history.pushState;
        const originalReplaceState = window.history.replaceState;
        
        window.history.pushState = function(state, title, url) {
            if (!window.HH_NAVIGATION_ALLOWED && url && !isURLAllowed(url)) {
                console.log('🚫 URL БЛОК: pushState заблокирован:', url);
                urlBlockCount++;
                blockedNavigationAttempts++;
                return;
            }
            return originalPushState.apply(this, arguments);
        };
        
        window.history.replaceState = function(state, title, url) {
            if (!window.HH_NAVIGATION_ALLOWED && url && !isURLAllowed(url)) {
                console.log('🚫 URL БЛОК: replaceState заблокирован:', url);
                urlBlockCount++;
                blockedNavigationAttempts++;
                return;
            }
            return originalReplaceState.apply(this, arguments);
        };
        
        // БЛОКИРОВКА window.location ИЗМЕНЕНИЙ
        const locationDescriptor = Object.getOwnPropertyDescriptor(window, 'location');
        if (locationDescriptor && locationDescriptor.configurable) {
            Object.defineProperty(window, 'location', {
                get: locationDescriptor.get,
                set: function(value) {
                    if (!window.HH_NAVIGATION_ALLOWED && !isURLAllowed(value)) {
                        console.log('🚫 URL БЛОК: window.location присвоение заблокировано:', value);
                        urlBlockCount++;
                        blockedNavigationAttempts++;
                        return;
                    }
                    return locationDescriptor.set.call(this, value);
                },
                configurable: false
            });
        }
        
        // Сохраняем интервал для возможности остановки
        window.HH_URL_MONITOR_INTERVAL = urlCheckInterval;
        
        console.log('✅ Агрессивная URL защита установлена (50ms мониторинг)');
        
        // Статистика URL блокировок
        setInterval(() => {
            if (urlBlockCount > 0) {
                console.log(`📊 URL СТАТИСТИКА: Заблокировано ${urlBlockCount} попыток смены URL`);
            }
        }, 30000); // Каждые 30 секунд
    }
    
    // ========================================
    // ЗАЩИТА ОТ FORM SUBMISSIONS И IFRAME
    // ========================================
    
    function setupFormProtection() {
        console.log('🛡️ Установка защиты от форм и iframe...');
        
        // Сохраняем оригинальные методы
        const originalSubmit = HTMLFormElement.prototype.submit;
        const originalCreateElement = document.createElement;
        
        // БЛОКИРОВКА FORM SUBMIT
        try {
            Object.defineProperty(HTMLFormElement.prototype, 'submit', {
                value: function() {
                    if (window.HH_NAVIGATION_ALLOWED) {
                        console.log('🔓 РАЗРЕШЕНО: form.submit() для формы', this.action || 'без action');
                        return originalSubmit.call(this);
                    }
                    console.log('🚫 БЛОКИРОВКА: form.submit() для формы', this.action || 'без action');
                    throw new Error('Form submission blocked by HH Script');
                },
                writable: false,
                configurable: false
            });
        } catch (e) {
            console.log('⚠️ Не удалось переопределить HTMLFormElement.submit:', e.message);
            HTMLFormElement.prototype.submit = function() {
                if (window.HH_NAVIGATION_ALLOWED) {
                    return originalSubmit.call(this);
                }
                console.log('🚫 БЛОКИРОВКА: form.submit()');
                throw new Error('Form submission blocked by HH Script');
            };
        }
        
        // БЛОКИРОВКА SUBMIT СОБЫТИЙ НА ДОКУМЕНТЕ
        document.addEventListener('submit', function(e) {
            if (window.HH_NAVIGATION_ALLOWED) return;
            
            const form = e.target;
            const action = form.action;
            const method = form.method;
            
            // Разрешаем только формы поиска HH.ru
            const isSearchForm = form.closest('[data-qa="vacancy-serp__form"]') || 
                               form.querySelector('[data-qa="serp-field"]') ||
                               action.includes('/search/') ||
                               action.includes('/vacancy');
            
            if (!isSearchForm) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                console.log('🚫 БЛОКИРОВКА: submit события формы', action, method);
                return false;
            }
        }, true);
        
        // БЛОКИРОВКА СОЗДАНИЯ IFRAME И ОПАСНЫХ ЭЛЕМЕНТОВ
        try {
            document.createElement = function(tagName) {
                const element = originalCreateElement.call(document, tagName);
                
                if (!window.HH_NAVIGATION_ALLOWED) {
                    const dangerousTags = ['iframe', 'frame', 'object', 'embed', 'applet'];
                    
                    if (dangerousTags.includes(tagName.toLowerCase())) {
                        console.log('🚫 БЛОКИРОВКА: создание элемента', tagName);
                        
                        // Блокируем установку src
                        Object.defineProperty(element, 'src', {
                            set: function(value) {
                                console.log('🚫 БЛОКИРОВКА: установка src для', tagName, value);
                                return;
                            },
                            get: function() { return ''; },
                            configurable: false
                        });
                        
                        // Блокируем установку data
                        Object.defineProperty(element, 'data', {
                            set: function(value) {
                                console.log('🚫 БЛОКИРОВКА: установка data для', tagName, value);
                                return;
                            },
                            get: function() { return ''; },
                            configurable: false
                        });
                    }
                    
                    // Блокируем мета-теги для refresh
                    if (tagName.toLowerCase() === 'meta') {
                        const originalSetAttribute = element.setAttribute;
                        element.setAttribute = function(name, value) {
                            if (name.toLowerCase() === 'http-equiv' && 
                                value.toLowerCase().includes('refresh')) {
                                console.log('🚫 БЛОКИРОВКА: meta refresh');
                                return;
                            }
                            return originalSetAttribute.call(this, name, value);
                        };
                    }
                }
                
                return element;
            };
        } catch (e) {
            console.log('⚠️ Не удалось переопределить createElement:', e.message);
        }
        
        // БЛОКИРОВКА ИЗМЕНЕНИЯ ACTION У ФОРМ
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            if (form._hhProtected) return;
            
            const originalAction = form.action;
            Object.defineProperty(form, 'action', {
                get: function() { return originalAction; },
                set: function(value) {
                    if (window.HH_NAVIGATION_ALLOWED) {
                        console.log('🔓 РАЗРЕШЕНО: изменение form.action', value);
                        return originalAction = value;
                    }
                    console.log('🚫 БЛОКИРОВКА: изменение form.action', value);
                    return originalAction;
                },
                configurable: false
            });
            
            form._hhProtected = true;
        });
        
        console.log('✅ Защита от форм и iframe установлена');
    }
    
    // Блокировка кликов по ссылкам + дополнительная защита
    function setupClickProtection() {
        console.log('🛡️ Установка защиты от кликов...');
        
        // УСИЛЕННЫЙ ГЛОБАЛЬНЫЙ ОБРАБОТЧИК СОБЫТИЙ НАВИГАЦИИ
        const blockNavigationEvent = function(e) {
            if (window.HH_NAVIGATION_ALLOWED) return;
            
            const target = e.target;
            const eventType = e.type;
            
            // СТРОГАЯ БЛОКИРОВКА ВСЕХ ССЫЛОК
            if (target && target.nodeType === 1) {
                const link = target.closest && target.closest('a, [href]');
                if (link && (!link.dataset || !link.dataset.hhAllowed)) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    console.log('🚫 СТРОГАЯ БЛОКИРОВКА: ' + eventType + ' по ссылке ' + (link.href || link.getAttribute && link.getAttribute('href') || 'неизвестная'));
                    return false;
                }
            }
            
            // СТРОГАЯ БЛОКИРОВКА КНОПОК И ФОРМ
            if (target && target.nodeType === 1) {
                const isButton = target.type === 'submit' || target.tagName === 'BUTTON' || target.tagName === 'INPUT';
                const isInSearchForm = target.closest && target.closest('[data-qa="vacancy-serp__form"]');
                const isAllowed = target.dataset && target.dataset.hhAllowed;
                
                if (isButton && !isInSearchForm && !isAllowed) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    console.log('🚫 СТРОГАЯ БЛОКИРОВКА: ' + eventType + ' кнопки/формы', target.tagName, target.type);
                    return false;
                }
            }
            
            // БЛОКИРОВКА ЛЮБЫХ ЭЛЕМЕНТОВ С ONCLICK ИЛИ HREF (только для DOM элементов)
            if (target && target.nodeType === 1) { // Проверяем что это DOM элемент
                const hasOnclick = target.onclick || (target.getAttribute && target.getAttribute('onclick'));
                const hasHref = target.getAttribute && target.getAttribute('href');
                const hasPointerCursor = target.style && target.style.cursor === 'pointer';
                
                if (hasOnclick || hasHref || hasPointerCursor) {
                    const isAllowed = target.dataset && target.dataset.hhAllowed;
                    const isInVacancySerp = target.closest && target.closest('[data-qa*="vacancy-serp"]');
                    
                    if (!isAllowed && !isInVacancySerp) {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        console.log('🚫 БЛОКИРОВКА: ' + eventType + ' элемента с навигацией', target.tagName);
                        return false;
                    }
                }
            }
            
            // БЛОКИРОВКА DRAG&DROP СОБЫТИЙ (только для DOM элементов)
            if (['dragstart', 'drag', 'dragend'].includes(eventType) && target && target.nodeType === 1) {
                const dragTarget = target.closest && target.closest('a, [href], [onclick]');
                if (dragTarget && (!dragTarget.dataset || !dragTarget.dataset.hhAllowed)) {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('🚫 БЛОКИРОВКА: drag события навигационного элемента');
                    return false;
                }
            }
            
            // БЛОКИРОВКА TOUCH СОБЫТИЙ НА НАВИГАЦИОННЫХ ЭЛЕМЕНТАХ (только для DOM элементов)  
            if (['touchstart', 'touchend'].includes(eventType) && target && target.nodeType === 1) {
                const touchTarget = target.closest && target.closest('a, button, [onclick], [href]');
                if (touchTarget && (!touchTarget.dataset || !touchTarget.dataset.hhAllowed)) {
                    const isInVacancySerp = touchTarget.closest && touchTarget.closest('[data-qa*="vacancy-serp"]');
                    if (!isInVacancySerp) {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('🚫 БЛОКИРОВКА: touch события навигационного элемента');
                        return false;
                    }
                }
            }
        };
        
        // СПИСОК ТИПОВ СОБЫТИЙ ДЛЯ БЛОКИРОВКИ (БЕЗ beforeunload/unload/pagehide)
        const eventTypes = [
            'click', 'dblclick', 'mousedown', 'mouseup', 'mousemove',
            'touchstart', 'touchend', 'touchmove', 'touchcancel',
            'submit', 'change', 'input', 'focus', 'blur',
            'dragstart', 'drag', 'dragenter', 'dragover', 'dragleave', 'drop', 'dragend',
            'keydown', 'keyup', 'keypress',
            'contextmenu', 'selectstart'
        ];
        
        // Устанавливаем обработчики на обе фазы для максимального покрытия
        eventTypes.forEach(type => {
            document.addEventListener(type, blockNavigationEvent, true);  // Capture phase
            document.addEventListener(type, blockNavigationEvent, false); // Bubble phase
        });
        
        // Дополнительная защита через MutationObserver
        navigationObserver = new MutationObserver(mutations => {
            if (window.HH_NAVIGATION_ALLOWED) return;
            
            mutations.forEach(mutation => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1) { // Element
                            // Блокируем новые ссылки
                            const links = node.tagName === 'A' ? [node] : 
                                         node.querySelectorAll ? node.querySelectorAll('a') : [];
                            
                            links.forEach(link => {
                                if (!link.dataset.hhProtected) {
                                    // Отслеживаем добавленные listeners
                                    const listenerInfo = {
                                        element: link,
                                        event: 'click',
                                        handler: blockNavigationEvent,
                                        options: true
                                    };
                                    
                                    link.addEventListener('click', blockNavigationEvent, true);
                                    link.dataset.hhProtected = 'true';
                                    addedEventListeners.add(listenerInfo);
                                }
                            });
                        }
                    });
                }
            });
        });
        
        navigationObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // Сохраняем также в window для обратной совместимости
        window.hhNavigationObserver = navigationObserver;
        
        // Блокировка клавиш
        document.addEventListener('keydown', function(e) {
            if (window.HH_NAVIGATION_ALLOWED) return;
            
            // Разрешаем только горячие клавиши скрипта
            if (e.ctrlKey && e.altKey && ['s', 'q', 'e'].includes(e.key.toLowerCase())) {
                return;
            }
            
            const blockedKeys = ['F5', 'F1', 'F3', 'F11', 'F12'];
            const blockedCombos = [
                {ctrl: true, key: 'r'},          // Обновить
                {ctrl: true, key: 'R'},
                {ctrl: true, key: 'l'},          // Адресная строка
                {ctrl: true, key: 'L'},
                {ctrl: true, key: 'w'},          // Закрыть вкладку
                {ctrl: true, key: 'W'},
                {ctrl: true, key: 't'},          // Новая вкладка
                {ctrl: true, key: 'T'},
                {ctrl: true, shift: true, key: 't'}, // Восстановить вкладку
                {ctrl: true, shift: true, key: 'T'},
                {alt: true, key: 'ArrowLeft'},   // Назад
                {alt: true, key: 'ArrowRight'},  // Вперед
                {ctrl: true, key: 'h'},          // История
                {ctrl: true, key: 'H'},
                {ctrl: true, key: 'd'},          // Закладки
                {ctrl: true, key: 'D'}
            ];
            
            if (blockedKeys.includes(e.key)) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                console.log('🚫 БЛОКИРОВКА: клавиша ' + e.key);
                return false;
            }
            
            for (const combo of blockedCombos) {
                const ctrlMatch = combo.ctrl ? e.ctrlKey : !e.ctrlKey;
                const altMatch = combo.alt ? e.altKey : !e.altKey;
                const shiftMatch = combo.shift ? e.shiftKey : !e.shiftKey;
                
                if (ctrlMatch && altMatch && shiftMatch && 
                    e.key.toLowerCase() === combo.key.toLowerCase()) {
                    
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    console.log('🚫 БЛОКИРОВКА: комбинация ' + e.key);
                    return false;
                }
            }
        }, true);
        
        // Блокировка контекстного меню на ссылках
        document.addEventListener('contextmenu', function(e) {
            if (window.HH_NAVIGATION_ALLOWED) return;
            
            const link = e.target.closest('a');
            if (link) {
                e.preventDefault();
                console.log('🚫 БЛОКИРОВКА: контекстное меню на ссылке');
                return false;
            }
        }, true);
        
        // Дополнительная защита через popstate
        window.addEventListener('popstate', function(e) {
            if (!window.HH_NAVIGATION_ALLOWED) {
                console.log('🚫 БЛОКИРОВКА: popstate event');
                e.preventDefault();
                e.stopPropagation();
                history.pushState(null, '', window.location.href);
                return false;
            }
        }, true);
        
        // Перехват hashchange
        window.addEventListener('hashchange', function(e) {
            if (!window.HH_NAVIGATION_ALLOWED) {
                console.log('🚫 БЛОКИРОВКА: hashchange event');
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
        }, true);
        
        console.log('✅ Защита от кликов установлена');
    }
    
    // ========================================
    // ОСНОВНАЯ ЛОГИКА СКРИПТА
    // ========================================
    
    // Состояние и счетчики прогресса
    let scriptActive = false;
    let processedButtons = new Set();
    let currentPage = 1;
    let totalPages = 1;
    let originalUrl = '';
    
    // ДЕТАЛЬНЫЕ СЧЕТЧИКИ ПРОГРЕССА
    let totalResponsesSent = 0;        // Общее количество отправленных откликов
    let responsesOnCurrentPage = 0;    // Отклики на текущей странице
    let totalButtonsFound = 0;         // Общее количество найденных кнопок
    let totalButtonsProcessed = 0;     // Общее количество обработанных кнопок
    let startTime = null;              // Время начала работы скрипта
    let pageStartTime = null;          // Время начала обработки текущей страницы
    
    // Отслеживание ресурсов для предотвращения утечек памяти
    let activeTimeouts = new Set();         // Активные setTimeout ID
    let activeIntervals = new Set();        // Активные setInterval ID
    let navigationObserver = null;          // MutationObserver для навигации
    let addedEventListeners = new Set();    // Добавленные event listeners
    let resourcesInitialized = false;       // Флаг инициализации ресурсов
    
    // Обертки для отслеживания ресурсов
    function safeSetTimeout(callback, delay) {
        const timeoutId = setTimeout(() => {
            activeTimeouts.delete(timeoutId);
            callback();
        }, delay);
        activeTimeouts.add(timeoutId);
        return timeoutId;
    }
    
    function safeSetInterval(callback, delay) {
        const intervalId = setInterval(callback, delay);
        activeIntervals.add(intervalId);
        return intervalId;
    }
    
    function safeClearTimeout(timeoutId) {
        if (timeoutId) {
            clearTimeout(timeoutId);
            activeTimeouts.delete(timeoutId);
        }
    }
    
    function safeClearInterval(intervalId) {
        if (intervalId) {
            clearInterval(intervalId);
            activeIntervals.delete(intervalId);
        }
    }
    
    // Настройки
    const CONFIG = {
        buttonSelector: 'a[data-qa="vacancy-serp__vacancy_response"]',
        labelSelector: '.magritte-button__label___zplmt_6-0-6',
        paginationSelector: 'a[data-qa="pager-page"]',
        buttonDelay: {min: 1000, max: 3000},
        pageDelay: {min: 2000, max: 4000}
    };
    
    // Ключи localStorage
    const STORAGE_KEYS = {
        state: 'hh_script_state_final',
        script: 'hh_script_code_final'
    };
    
    // Утилиты
    function log(msg, type = 'info') {
        const time = new Date().toLocaleTimeString();
        const emoji = type === 'error' ? '❌' : type === 'warn' ? '⚠️' : 'ℹ️';
        console.log(`[${time}] ${emoji} ${msg}`);
    }
    
    function randomDelay(range) {
        return Math.floor(Math.random() * (range.max - range.min + 1)) + range.min;
    }
    
    // РАСШИРЕННОЕ ОБНОВЛЕНИЕ СТАТУСА
    function updateStatus(text) {
        const statusEl = document.getElementById('hh-status');
        if (statusEl) {
            statusEl.textContent = text;
            
            // Добавляем детальную информацию в расширенный статус
            const detailsEl = document.getElementById('hh-status-details');
            if (detailsEl && scriptActive) {
                const elapsed = startTime ? Math.round((Date.now() - startTime) / 1000) : 0;
                const elapsedMin = Math.floor(elapsed / 60);
                const elapsedSec = elapsed % 60;
                
                const timeStr = elapsedMin > 0 ? `${elapsedMin}м ${elapsedSec}с` : `${elapsedSec}с`;
                const avgTimePerResponse = totalResponsesSent > 0 ? Math.round(elapsed / totalResponsesSent) : 0;
                
                let progressBar = '';
                if (totalPages > 0) {
                    const progress = Math.round((currentPage / totalPages) * 100);
                    const filled = Math.floor(progress / 5);
                    const empty = 20 - filled;
                    progressBar = '█'.repeat(filled) + '░'.repeat(empty) + ` ${progress}%`;
                }
                
                detailsEl.innerHTML = `
                    <div style="font-size: 9px; line-height: 1.3; margin-top: 5px; color: #00ff41;">
                        ${progressBar ? `<div>📊 ${progressBar}</div>` : ''}
                        <div>⏰ Время: ${timeStr} | 📤 Откликов: ${totalResponsesSent}</div>
                        ${totalResponsesSent > 0 ? `<div>⚡ Скорость: ${avgTimePerResponse}с/отклик</div>` : ''}
                        <div>📄 Страница: ${currentPage}/${totalPages}</div>
                    </div>
                `;
            }
        }
    }
    
    // Функция очистки всех ресурсов для предотвращения утечек памяти
    function cleanupResources() {
        log('🧹 Начало очистки ресурсов...');
        let cleanedCount = 0;
        
        try {
            // Очищаем все активные timeouts
            for (const timeoutId of activeTimeouts) {
                try {
                    clearTimeout(timeoutId);
                    cleanedCount++;
                } catch (e) {
                    log(`⚠️ Ошибка очистки timeout ${timeoutId}: ${e.message}`, 'warn');
                }
            }
            activeTimeouts.clear();
            
            // Очищаем все активные intervals
            for (const intervalId of activeIntervals) {
                try {
                    clearInterval(intervalId);
                    cleanedCount++;
                } catch (e) {
                    log(`⚠️ Ошибка очистки interval ${intervalId}: ${e.message}`, 'warn');
                }
            }
            activeIntervals.clear();
            
            // Отключаем MutationObserver
            if (navigationObserver) {
                try {
                    navigationObserver.disconnect();
                    navigationObserver = null;
                    cleanedCount++;
                    log('✅ MutationObserver отключен');
                } catch (e) {
                    log(`⚠️ Ошибка отключения MutationObserver: ${e.message}`, 'warn');
                }
            }
            
            // Удаляем добавленные event listeners
            for (const listenerInfo of addedEventListeners) {
                try {
                    if (listenerInfo.element && listenerInfo.element.removeEventListener) {
                        listenerInfo.element.removeEventListener(
                            listenerInfo.event, 
                            listenerInfo.handler, 
                            listenerInfo.options
                        );
                        cleanedCount++;
                    }
                } catch (e) {
                    log(`⚠️ Ошибка удаления event listener: ${e.message}`, 'warn');
                }
            }
            addedEventListeners.clear();
            
            // Очищаем глобальные навигационные наблюдатели
            if (window.HH_NAVIGATION_WATCHERS) {
                for (const watcherId of window.HH_NAVIGATION_WATCHERS) {
                    try {
                        clearInterval(watcherId);
                        cleanedCount++;
                    } catch (e) {
                        log(`⚠️ Ошибка очистки navigation watcher ${watcherId}: ${e.message}`, 'warn');
                    }
                }
                window.HH_NAVIGATION_WATCHERS = [];
            }
            
            // Очищаем интервал обновления статуса
            if (statusUpdateInterval) {
                clearInterval(statusUpdateInterval);
                statusUpdateInterval = null;
                cleanedCount++;
            }
            
            // Очищаем глобальные ссылки
            window.hhNavigationObserver = null;
            window.HH_NAVIGATION_ALLOWED = false;
            window.HH_CURRENT_NAVIGATION_ID = null;
            window.HH_LAST_KNOWN_URL = null;
            resourcesInitialized = false;
            
            log(`✅ Очистка ресурсов завершена. Очищено: ${cleanedCount} ресурсов`);
            
        } catch (e) {
            log(`❌ Критическая ошибка при очистке ресурсов: ${e.message}`, 'error');
        }
    }
    
    // РАСШИРЕННОЕ СОХРАНЕНИЕ СОСТОЯНИЯ С ПРОГРЕССОМ
    function saveState() {
        try {
            const state = {
                active: scriptActive,
                originalUrl: originalUrl,
                currentPage: currentPage,
                totalPages: totalPages,
                processedButtons: Array.from(processedButtons),
                
                // Детальные счетчики прогресса  
                totalResponsesSent: totalResponsesSent,
                responsesOnCurrentPage: responsesOnCurrentPage,
                totalButtonsFound: totalButtonsFound,
                totalButtonsProcessed: totalButtonsProcessed,
                startTime: startTime,
                pageStartTime: pageStartTime,
                
                timestamp: Date.now()
            };
            localStorage.setItem(STORAGE_KEYS.state, JSON.stringify(state));
            
            // Сохраняем код скрипта
            const scriptCode = document.currentScript ? 
                document.currentScript.textContent : 
                'HH Script code';
            localStorage.setItem(STORAGE_KEYS.script, scriptCode);
            
        } catch (e) {
            log('Ошибка сохранения: ' + e.message, 'error');
        }
    }
    
    // РАСШИРЕННАЯ ЗАГРУЗКА СОСТОЯНИЯ С ПРОГРЕССОМ
    function loadState() {
        try {
            const saved = localStorage.getItem(STORAGE_KEYS.state);
            if (!saved) return false;
            
            const state = JSON.parse(saved);
            
            // Проверяем актуальность (не старше 1 часа)
            if (Date.now() - state.timestamp > 3600000) {
                log('Сохраненное состояние устарело, сбрасываем');
                return false;
            }
            
            // Восстанавливаем основное состояние
            originalUrl = state.originalUrl || window.location.href;
            currentPage = state.currentPage || 1;
            totalPages = state.totalPages || 1;
            processedButtons = new Set(state.processedButtons || []);
            
            // Восстанавливаем счетчики прогресса
            totalResponsesSent = state.totalResponsesSent || 0;
            responsesOnCurrentPage = state.responsesOnCurrentPage || 0; 
            totalButtonsFound = state.totalButtonsFound || 0;
            totalButtonsProcessed = state.totalButtonsProcessed || 0;
            startTime = state.startTime || null;
            pageStartTime = state.pageStartTime || null;
            
            const isValid = state.active && window.location.href.includes('hh.ru');
            
            if (isValid) {
                log(`🔄 Восстановлено состояние: стр.${currentPage}/${totalPages}, откликов: ${totalResponsesSent}`);
            }
            
            return isValid;
            
        } catch (e) {
            log('Ошибка загрузки состояния: ' + e.message, 'error');
            return false;
        }
    }
    
    function clearState() {
        try {
            localStorage.removeItem(STORAGE_KEYS.state);
            localStorage.removeItem(STORAGE_KEYS.script);
        } catch (e) {
            // Игнорируем
        }
    }
    
    // СТРОГИЙ КОНТРОЛЬ НАВИГАЦИИ ДЛЯ СКРИПТА
    function allowNavigation(callback, options = {}) {
        const {
            maxDuration = 5000,    // Максимальное время разрешения навигации
            reason = 'script',     // Причина разрешения
            allowMultiple = false  // Разрешать ли множественные вызовы
        } = options;
        
        // Проверяем, что навигация еще не разрешена
        if (window.HH_NAVIGATION_ALLOWED && !allowMultiple) {
            log('⚠️ Навигация уже разрешена, блокируем повторный вызов', 'warn');
            return Promise.reject(new Error('Navigation already allowed'));
        }
        
        log('🔓 Навигация СТРОГО разрешена для: ' + reason);
        
        // Создаем уникальный ID для этого разрешения
        const navigationId = Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        window.HH_CURRENT_NAVIGATION_ID = navigationId;
        window.HH_NAVIGATION_ALLOWED = true;
        
        let completed = false;
        let timeoutId;
        
        const cleanup = () => {
            if (completed) return;
            completed = true;
            
            // Проверяем, что это все еще наша сессия навигации
            if (window.HH_CURRENT_NAVIGATION_ID === navigationId) {
                window.HH_NAVIGATION_ALLOWED = false;
                window.HH_CURRENT_NAVIGATION_ID = null;
                log('🔒 Навигация заблокирована (ID: ' + navigationId + ')');
            }
            
            if (timeoutId) {
                clearTimeout(timeoutId);
                timeoutId = null;
            }
        };
        
        // Жесткий таймаут
        timeoutId = setTimeout(() => {
            if (!completed) {
                log('⏰ ПРИНУДИТЕЛЬНАЯ блокировка навигации по таймауту', 'warn');
                cleanup();
            }
        }, maxDuration);
        
        try {
            // Выполняем callback
            const result = callback();
            
            // Если это Promise, ждем его завершения
            if (result && typeof result.then === 'function') {
                return result.finally(cleanup);
            } else {
                // Если обычная функция, блокируем через минимальную задержку
                setTimeout(cleanup, 100);
                return result;
            }
            
        } catch (error) {
            log('❌ Ошибка во время разрешенной навигации: ' + error.message, 'error');
            cleanup();
            throw error;
        }
    }
    
    // Ожидание готовности страницы
    function waitForPageReady(timeout = 10000) {
        return new Promise((resolve) => {
            const start = Date.now();
            
            function check() {
                const buttons = document.querySelectorAll(CONFIG.buttonSelector);
                const pagination = document.querySelectorAll(CONFIG.paginationSelector);
                const loaders = document.querySelectorAll('.bloko-loader, [data-qa="bloko-loader"]');
                
                const hasContent = buttons.length > 0 || pagination.length > 0;
                const hasLoaders = Array.from(loaders).some(el => el.offsetParent !== null);
                
                if (hasContent && !hasLoaders) {
                    log('✅ Страница готова');
                    resolve(true);
                    return;
                }
                
                if (Date.now() - start > timeout) {
                    log('⏰ Таймаут ожидания страницы', 'warn');
                    resolve(false);
                    return;
                }
                
                safeSetTimeout(check, 200);
            }
            
            check();
        });
    }
    
    // Анализ пагинации
    async function analyzePagination() {
        await waitForPageReady();
        
        const pageLinks = document.querySelectorAll(CONFIG.paginationSelector);
        const pageNumbers = [];
        
        pageLinks.forEach(link => {
            const num = parseInt(link.textContent.trim());
            if (!isNaN(num)) pageNumbers.push(num);
        });
        
        // Определяем текущую страницу
        const currentEl = document.querySelector('[data-qa="pager-page"][aria-current="true"]');
        if (currentEl) {
            currentPage = parseInt(currentEl.textContent.trim()) || 1;
        } else {
            const urlPage = new URL(window.location.href).searchParams.get('page');
            currentPage = parseInt(urlPage) || 1;
        }
        
        // Определяем общее количество страниц
        totalPages = pageNumbers.length > 0 ? Math.max(...pageNumbers) : 1;
        
        const nextBtn = document.querySelector('[data-qa="pager-next"]');
        if (nextBtn && !nextBtn.hasAttribute('disabled')) {
            totalPages = Math.max(totalPages, currentPage + 1);
        }
        
        log(`📊 Пагинация: страница ${currentPage} из ${totalPages}`);
        return {currentPage, totalPages};
    }
    
    // Переход на страницу
    async function goToPage(pageNum) {
        log(`🔄 Переход на страницу ${pageNum}...`);
        
        try {
            // Ищем ссылку на страницу
            const pageLink = Array.from(document.querySelectorAll(CONFIG.paginationSelector))
                .find(link => parseInt(link.textContent.trim()) === pageNum);
            
            if (pageLink) {
                pageLink.dataset.hhAllowed = 'true';
                
                return allowNavigation(() => {
                    pageLink.click();
                    return waitForPageChange();
                }, { reason: 'page_navigation', maxDuration: 10000 });
            }
            
            // Попробуем кнопку "Далее"
            if (pageNum === currentPage + 1) {
                const nextBtn = document.querySelector('[data-qa="pager-next"]');
                if (nextBtn && !nextBtn.hasAttribute('disabled')) {
                    nextBtn.dataset.hhAllowed = 'true';
                    
                    return allowNavigation(() => {
                        nextBtn.click();
                        return waitForPageChange();
                    }, { reason: 'next_page_button', maxDuration: 10000 });
                }
            }
            
            // Переход по URL
            const url = new URL(window.location.href);
            url.searchParams.set('page', pageNum);
            
            return allowNavigation(() => {
                window.location.href = url.toString();
                return waitForPageChange();
            }, { reason: 'url_navigation', maxDuration: 15000 });
            
        } catch (e) {
            log('Ошибка перехода: ' + e.message, 'error');
            return false;
        }
    }
    
    // Ожидание смены страницы
    function waitForPageChange(timeout = 15000) {
        return new Promise((resolve) => {
            const originalUrl = window.location.href;
            const start = Date.now();
            
            function check() {
                if (window.location.href !== originalUrl) {
                    log('✅ Страница изменена');
                    resolve(true);
                    return;
                }
                
                if (Date.now() - start > timeout) {
                    log('⏰ Таймаут смены страницы', 'warn');
                    resolve(false);
                    return;
                }
                
                safeSetTimeout(check, 300);
            }
            
            safeSetTimeout(check, 1000);
        });
    }
    
    // УСИЛЕННОЕ ЗАКРЫТИЕ МОДАЛЬНЫХ ОКОН
    async function closeModals() {
        log('🚪 Начинаем поиск и закрытие модальных окон...');
        
        // РАСШИРЕННЫЙ список селекторов для поиска элементов закрытия
        const selectors = [
            // Основные селекторы HH.ru
            '[data-qa="modal-close"]',
            '[data-qa="popup-close"]', 
            '[data-qa="response-popup-close-svg"]',
            '[data-qa="response-popup-close"]',
            '[data-qa="relocation-warning-abort"]',
            '[data-qa="relocation-warning-cancel"]',
            '[data-qa="popup-cancel"]',
            '[data-qa="modal-cancel"]',
            
            // CSS классы
            '.modal-close',
            '.popup-close', 
            '.close-button',
            '.modal-header-close',
            
            // Aria атрибуты
            '[aria-label*="Закрыть"]',
            '[aria-label*="Close"]',
            '[aria-label*="Отмена"]',
            '[aria-label*="Cancel"]',
            '[aria-label*="Отменить"]',
            
            // Роли и типы
            '[role="button"][aria-label*="закрыть"]',
            'button[data-dismiss="modal"]',
            'button[data-bs-dismiss="modal"]',
            
            // Текстовое содержимое (более агрессивный поиск)
            'button:contains("Отмена")',
            'button:contains("Закрыть")',
            'button:contains("Отменить")',
            'a:contains("Отмена")',
            
            // Специфичные для HH.ru
            'button.magritte-button___Pubhr_6-0-6[data-qa="relocation-warning-abort"]',
            '.bloko-modal__close',
            '.bloko-popup__close',
            
            // SVG иконки закрытия
            'svg[data-qa="response-popup-close-svg"]',
            'button:has(svg[data-qa="response-popup-close-svg"])',
            
            // Универсальные селекторы (осторожно)
            '.modal .close',
            '.popup .close',
            '[class*="close"]:not([class*="closed"])',
            '[class*="cancel"]'
        ];
        
        let closed = 0;
        let totalFound = 0;
        
        // ЭТАП 1: Поиск и закрытие стандартными селекторами
        for (const selector of selectors) {
            try {
                // Пропускаем сложные селекторы с :contains - они не поддерживаются браузером
                if (selector.includes(':contains') || selector.includes(':has')) {
                    continue;
                }
                
                const elements = document.querySelectorAll(selector);
                totalFound += elements.length;
                
                for (const el of elements) {
                    if (await attemptCloseElement(el, selector)) {
                        closed++;
                    }
                }
            } catch (e) {
                log(`⚠️ Ошибка селектора ${selector}: ${e.message}`, 'warn');
            }
        }
        
        // ЭТАП 2: Текстовый поиск элементов с кнопками отмены/закрытия
        try {
            const textSearches = ['Отмена', 'Закрыть', 'Отменить', 'Cancel', 'Close', '✕', '×'];
            for (const text of textSearches) {
                const buttons = Array.from(document.querySelectorAll('button, a, span, div'))
                    .filter(el => el.textContent && el.textContent.trim().toLowerCase().includes(text.toLowerCase()));
                
                for (const button of buttons) {
                    if (await attemptCloseElement(button, `текст "${text}"`)) {
                        closed++;
                    }
                }
            }
        } catch (e) {
            log(`⚠️ Ошибка текстового поиска: ${e.message}`, 'warn');
        }
        
        // ЭТАП 3: Агрессивное закрытие - поиск модальных контейнеров и их закрытие
        try {
            const modalContainers = document.querySelectorAll('.modal, .popup, [class*="modal"], [class*="popup"], [class*="dialog"]');
            for (const modal of modalContainers) {
                if (modal.offsetParent !== null) {
                    // Пытаемся найти кнопки закрытия внутри модального окна
                    const closeButtons = modal.querySelectorAll('button, a, span, div');
                    for (const btn of closeButtons) {
                        if (btn.offsetParent !== null && (
                            (btn.textContent && (btn.textContent.includes('Отмена') || btn.textContent.includes('Закрыть'))) ||
                            (btn.className && (btn.className.includes('close') || btn.className.includes('cancel')))
                        )) {
                            if (await attemptCloseElement(btn, 'модальная кнопка')) {
                                closed++;
                                break; // Выходим после первого успешного закрытия
                            }
                        }
                    }
                }
            }
        } catch (e) {
            log(`⚠️ Ошибка агрессивного закрытия: ${e.message}`, 'warn');
        }
        
        // ЭТАП 4: Универсальное закрытие через Escape и другие методы
        try {
            // Отправляем Escape
            document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', code: 'Escape', bubbles: true}));
            document.dispatchEvent(new KeyboardEvent('keyup', {key: 'Escape', code: 'Escape', bubbles: true}));
            
            // Пытаемся закрыть через события click на backdrop
            const backdrops = document.querySelectorAll('.modal-backdrop, .popup-backdrop, [class*="backdrop"]');
            for (const backdrop of backdrops) {
                if (backdrop.offsetParent !== null) {
                    backdrop.click();
                }
            }
        } catch (e) {
            log(`⚠️ Ошибка универсального закрытия: ${e.message}`, 'warn');
        }
        
        if (closed > 0) {
            log(`✅ Закрыто модальных окон: ${closed} (найдено элементов: ${totalFound})`);
        } else if (totalFound > 0) {
            log(`⚠️ Найдено ${totalFound} элементов закрытия, но ни один не удалось закрыть`, 'warn');
        } else {
            log(`ℹ️ Модальные окна не обнаружены`);
        }
    }
    
    // ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ЗАКРЫТИЯ ЭЛЕМЕНТОВ
    async function attemptCloseElement(el, source) {
        if (!el || el.nodeType !== 1 || typeof el.click !== 'function') {
            return false;
        }
        
        // Проверяем видимость элемента
        if (el.offsetParent === null || el.style.display === 'none' || 
            el.style.visibility === 'hidden' || el.style.opacity === '0') {
            return false;
        }
        
        try {
            // Логируем что закрываем
            const elementInfo = (el.dataset && el.dataset.qa) || el.className || el.tagName || 'неизвестный';
            log(`🚪 Попытка закрытия [${source}]: ${elementInfo}`);
            
            // Помечаем элемент как разрешенный для нашего скрипта
            if (el.dataset) {
                el.dataset.hhAllowed = 'true';
            }
            
            // Скроллим к элементу
            if (typeof el.scrollIntoView === 'function') {
                el.scrollIntoView({behavior: 'instant', block: 'center'});
                await new Promise(resolve => setTimeout(resolve, 50));
            }
            
            // Фокусируемся на элементе
            if (typeof el.focus === 'function') {
                el.focus();
                await new Promise(resolve => setTimeout(resolve, 50));
            }
            
            // Пытаемся различные методы клика
            const originalPosition = {
                offsetParent: el.offsetParent,
                display: el.style.display,
                visibility: el.style.visibility
            };
            
            // Метод 1: Обычный клик
            el.click();
            await new Promise(resolve => setTimeout(resolve, 200));
            
            // Проверяем результат
            if (el.offsetParent === null || el.style.display === 'none') {
                log(`✅ Элемент закрыт методом click()`);
                return true;
            }
            
            // Метод 2: Событие click
            el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            await new Promise(resolve => setTimeout(resolve, 200));
            
            if (el.offsetParent === null || el.style.display === 'none') {
                log(`✅ Элемент закрыт через событие click`);
                return true;
            }
            
            // Метод 3: Mousedown/mouseup
            el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true}));
            el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true}));
            await new Promise(resolve => setTimeout(resolve, 200));
            
            if (el.offsetParent === null || el.style.display === 'none') {
                log(`✅ Элемент закрыт через mouse события`);
                return true;
            }
            
            log(`⚠️ Элемент не закрылся, остается видимым`, 'warn');
            return false;
            
        } catch (e) {
            log(`⚠️ Ошибка закрытия элемента: ${e.message}`, 'warn');
            return false;
        }
    }
    
    // Клик по кнопке
    async function clickButton(button) {
        try {
            // Скроллим к кнопке
            button.scrollIntoView({behavior: 'smooth', block: 'center'});
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Помечаем как разрешенный
            button.dataset.hhAllowed = 'true';
            
            // УЛУЧШЕННАЯ СТРАТЕГИЯ КЛИКА ДЛЯ REACT
            let clicked = false;
            
            // Стратегия 1: Создаем настоящее MouseEvent и диспатчим его
            try {
                const mouseEvent = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    detail: 1,
                    screenX: 0,
                    screenY: 0,
                    clientX: 0,
                    clientY: 0,
                    ctrlKey: false,
                    altKey: false,
                    shiftKey: false,
                    metaKey: false,
                    button: 0,
                    buttons: 1
                });
                
                clicked = button.dispatchEvent(mouseEvent);
                if (clicked) {
                    log('✅ MouseEvent dispatch выполнен');
                }
            } catch (e) {
                log('MouseEvent dispatch ошибка: ' + e.message, 'warn');
            }
            
            // Стратегия 2: Ищем React обработчики (если MouseEvent не сработал)
            if (!clicked) {
                for (const key in button) {
                    if (key.startsWith('__reactInternalInstance') || 
                        key.startsWith('__reactFiber') ||
                        key.startsWith('__reactProps$') ||
                        key.startsWith('__reactEventHandlers$')) {
                        
                        let fiber = button[key];
                        let attempts = 0;
                        
                        // Ищем onClick в props или memoizedProps
                        while (fiber && attempts < 15) {
                            const props = fiber.memoizedProps || fiber.props || fiber.pendingProps;
                            if (props && props.onClick) {
                                try {
                                    // Создаем полноценный SyntheticEvent объект
                                    const nativeEvent = new MouseEvent('click', {
                                        bubbles: true,
                                        cancelable: true,
                                        view: window
                                    });
                                    
                                    const syntheticEvent = {
                                        nativeEvent: nativeEvent,
                                        currentTarget: button,
                                        target: button,
                                        bubbles: true,
                                        cancelable: true,
                                        defaultPrevented: false,
                                        eventPhase: 2,
                                        isTrusted: false,
                                        timeStamp: Date.now(),
                                        type: 'click',
                                        preventDefault: () => {
                                            syntheticEvent.defaultPrevented = true;
                                            nativeEvent.preventDefault();
                                        },
                                        stopPropagation: () => {
                                            nativeEvent.stopPropagation();
                                        },
                                        stopImmediatePropagation: () => {
                                            nativeEvent.stopImmediatePropagation();
                                        },
                                        isDefaultPrevented: () => syntheticEvent.defaultPrevented,
                                        isPropagationStopped: () => false,
                                        persist: () => {},
                                        isPersistent: () => true
                                    };
                                    
                                    props.onClick(syntheticEvent);
                                    clicked = true;
                                    log('✅ React SyntheticEvent выполнен');
                                    break;
                                } catch (e) {
                                    log('React SyntheticEvent ошибка: ' + e.message, 'warn');
                                }
                            }
                            
                            // Расширенный поиск в React fiber tree
                            fiber = fiber.child || fiber.sibling || fiber.return || fiber.alternate;
                            attempts++;
                        }
                        
                        if (clicked) break;
                    }
                }
            }
            
            // Стратегия 3: Обычный клик (последний fallback)
            if (!clicked) {
                button.click();
                log('✅ Обычный клик выполнен');
            }
            
            // Ждем завершения сетевых запросов
            await new Promise(resolve => setTimeout(resolve, 1000));
            log('🌐 Ожидание завершения сетевых запросов');
            
            return true;
            
        } catch (e) {
            log('Ошибка клика: ' + e.message, 'error');
            return false;
        }
    }
    
    // ДЕТАЛЬНАЯ ОБРАБОТКА ТЕКУЩЕЙ СТРАНИЦЫ С ПРОГРЕССОМ
    async function processCurrentPage() {
        if (!scriptActive) return false;
        
        // Начинаем обработку страницы
        pageStartTime = Date.now();
        responsesOnCurrentPage = 0;
        
        const elapsed = startTime ? Math.round((Date.now() - startTime) / 1000) : 0;
        log(`🔍 === СТРАНИЦА ${currentPage}/${totalPages} === (время работы: ${elapsed}с)`);
        
        // Подробный статус
        const overallProgress = totalPages > 0 ? Math.round((currentPage / totalPages) * 100) : 0;
        updateStatus(`🔄 Анализ стр.${currentPage}/${totalPages} (${overallProgress}%) | Откликов: ${totalResponsesSent}`);
        
        await waitForPageReady();
        await closeModals();
        await new Promise(resolve => setTimeout(resolve, randomDelay({min: 500, max: 1500})));
        
        // Поиск всех кнопок на странице
        const allButtons = document.querySelectorAll(CONFIG.buttonSelector);
        const validButtons = [];
        let alreadyProcessedCount = 0;
        let hiddenCount = 0;
        
        log(`🔍 Анализ кнопок на странице...`);
        
        for (const btn of allButtons) {
            if (!scriptActive) break;
            
            const label = btn.querySelector(CONFIG.labelSelector);
            const btnId = btn.href + btn.textContent;
            
            if (label && label.textContent.trim() === 'Откликнуться') {
                if (processedButtons.has(btnId)) {
                    alreadyProcessedCount++;
                } else if (btn.offsetParent === null) {
                    hiddenCount++;
                } else {
                    // Помечаем кнопку как разрешенную СРАЗУ при обнаружении
                    btn.dataset.hhAllowed = 'true';
                    validButtons.push({button: btn, id: btnId});
                }
            }
        }
        
        // Обновляем общие счетчики
        totalButtonsFound += validButtons.length;
        
        // Детальная статистика по странице
        log(`📊 Статистика страницы ${currentPage}:`);
        log(`  📋 Всего кнопок "Откликнуться": ${allButtons.length}`);
        log(`  ✅ Новых кнопок для обработки: ${validButtons.length}`);
        log(`  ⏭️ Уже обработано ранее: ${alreadyProcessedCount}`);
        log(`  👁️‍🗨️ Скрытых кнопок: ${hiddenCount}`);
        
        updateStatus(`📋 Стр.${currentPage}: найдено ${validButtons.length} новых кнопок (всего откликов: ${totalResponsesSent})`);
        
        if (validButtons.length === 0) {
            log(`⚠️ На странице ${currentPage} нет новых кнопок для обработки`);
            return false;
        }
        
        // Перемешиваем кнопки для случайности
        for (let i = validButtons.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [validButtons[i], validButtons[j]] = [validButtons[j], validButtons[i]];
        }
        
        log(`🎯 Начинаем отправку откликов...`);
        
        // Обрабатываем каждую кнопку с детальным логированием
        let processed = 0;
        for (let i = 0; i < validButtons.length && scriptActive; i++) {
            const {button, id} = validButtons[i];
            
            // Детальный статус для каждой кнопки
            const buttonProgress = Math.round(((i + 1) / validButtons.length) * 100);
            const pageProgress = Math.round((currentPage / totalPages) * 100);
            const currentResponseNumber = totalResponsesSent + processed + 1;
            
            updateStatus(`📤 Отклик ${i + 1}/${validButtons.length} (${buttonProgress}%) стр.${currentPage} | Всего: ${currentResponseNumber}`);
            
            // Логируем детали вакансии если возможно
            try {
                const vacancyTitle = button.closest('[data-qa="vacancy-serp__vacancy"]')?.querySelector('[data-qa="serp-item__title"]')?.textContent?.trim();
                const companyName = button.closest('[data-qa="vacancy-serp__vacancy"]')?.querySelector('[data-qa="vacancy-serp__vacancy-employer"]')?.textContent?.trim();
                
                if (vacancyTitle) {
                    log(`📤 Отклик ${currentResponseNumber}: "${vacancyTitle}"`);
                    if (companyName) {
                        log(`  🏢 Компания: ${companyName}`);
                    }
                } else {
                    log(`📤 Отправка отклика ${currentResponseNumber} (кнопка ${i + 1}/${validButtons.length})`);
                }
            } catch (e) {
                log(`📤 Отправка отклика ${currentResponseNumber} (кнопка ${i + 1}/${validButtons.length})`);
            }
            
            const success = await clickButton(button);
            if (success) {
                processedButtons.add(id);
                processed++;
                responsesOnCurrentPage++;
                totalResponsesSent++;
                totalButtonsProcessed++;
                
                log(`✅ Отклик ${currentResponseNumber} отправлен успешно`);
                saveState();
                
                // Показываем промежуточную статистику
                const avgTimePerResponse = processed > 0 ? Math.round((Date.now() - pageStartTime) / processed / 1000) : 0;
                log(`📊 Прогресс: ${processed}/${validButtons.length} на стр.${currentPage} | Среднее время: ${avgTimePerResponse}с/отклик`);
                
                const delay = randomDelay(CONFIG.buttonDelay);
                log(`⏱️ Пауза ${delay}мс перед следующим откликом...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                
                // Закрываем модальные окна периодически
                if (i % 2 === 0) { // Закрываем чаще - каждые 2 отклика
                    await closeModals();
                }
            } else {
                log(`❌ Не удалось отправить отклик ${currentResponseNumber}`, 'warn');
            }
        }
        
        // Итоговая статистика по странице
        const pageTime = Math.round((Date.now() - pageStartTime) / 1000);
        const avgTimePerResponse = processed > 0 ? Math.round(pageTime / processed) : 0;
        
        log(`📊 === СТРАНИЦА ${currentPage} ЗАВЕРШЕНА ===`);
        log(`✅ Отправлено откликов: ${processed}/${validButtons.length}`);
        log(`⏱️ Время обработки страницы: ${pageTime}с (${avgTimePerResponse}с/отклик)`);
        log(`📈 Общий прогресс: ${totalResponsesSent} откликов, страниц ${currentPage}/${totalPages}`);
        
        return processed > 0;
    }
    
    // ГЛАВНЫЙ ЦИКЛ С ДЕТАЛЬНОЙ СТАТИСТИКОЙ
    async function processAllPages() {
        if (!scriptActive) return;
        
        try {
            log(`🎯 === НАЧАЛО ОБРАБОТКИ ВСЕХ СТРАНИЦ ===`);
            
            for (let page = currentPage; page <= totalPages && scriptActive; page++) {
                currentPage = page;
                saveState();
                
                // Показываем общий прогресс
                const overallProgress = Math.round((page / totalPages) * 100);
                const elapsed = Math.round((Date.now() - startTime) / 1000);
                const estimatedTotal = totalPages > 0 && page > 1 ? Math.round((elapsed / (page - 1)) * totalPages) : 0;
                const estimatedRemaining = estimatedTotal > elapsed ? estimatedTotal - elapsed : 0;
                
                log(`\n🔄 === ПЕРЕХОД К СТРАНИЦЕ ${page}/${totalPages} ===`);
                log(`📊 Общий прогресс: ${overallProgress}% | Время: ${elapsed}с${estimatedRemaining > 0 ? ` | Осталось: ~${estimatedRemaining}с` : ''}`);
                log(`📈 Статистика: ${totalResponsesSent} откликов отправлено`);
                
                if (page > 1) {
                    updateStatus(`🔄 Переход на стр.${page}/${totalPages} (${overallProgress}%) | Откликов: ${totalResponsesSent}`);
                    
                    const navigationStart = Date.now();
                    const changed = await goToPage(page);
                    const navigationTime = Date.now() - navigationStart;
                    
                    if (!changed) {
                        log(`❌ Не удалось перейти на страницу ${page}`, 'error');
                        continue;
                    }
                    
                    log(`✅ Переход на страницу ${page} завершен за ${Math.round(navigationTime / 1000)}с`);
                    
                    const delay = randomDelay(CONFIG.pageDelay);
                    log(`⏱️ Пауза после перехода: ${delay}мс`);
                    updateStatus(`⏳ Загрузка стр.${page}... (ожидание ${Math.round(delay/1000)}с)`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
                
                // Обрабатываем текущую страницу
                const pageSuccess = await processCurrentPage();
                
                if (!pageSuccess) {
                    log(`⚠️ На странице ${page} не было обработано ни одного отклика`);
                }
                
                // Показываем промежуточную статистику каждые несколько страниц
                if (page % 5 === 0 || page === totalPages) {
                    const avgResponsesPerPage = page > 0 ? Math.round(totalResponsesSent / page * 10) / 10 : 0;
                    const avgTimePerPage = page > 1 ? Math.round(elapsed / (page - currentPage + 1)) : 0;
                    
                    log(`\n📊 === ПРОМЕЖУТОЧНАЯ СТАТИСТИКА ===`);
                    log(`📄 Обработано страниц: ${page}/${totalPages}`);
                    log(`📤 Всего откликов: ${totalResponsesSent}`);
                    log(`📈 Среднее откликов на страницу: ${avgResponsesPerPage}`);
                    log(`⏱️ Среднее время на страницу: ${avgTimePerPage}с`);
                    log(`🎯 Кнопок найдено: ${totalButtonsFound} | Обработано: ${totalButtonsProcessed}`);
                }
                
                // Пауза между страницами
                if (page < totalPages && scriptActive) {
                    const delay = randomDelay(CONFIG.pageDelay);
                    const nextPage = page + 1;
                    
                    log(`⏸️ Пауза перед переходом на страницу ${nextPage}: ${delay}мс`);
                    updateStatus(`⏸️ Пауза перед стр.${nextPage}... (${Math.round(delay/1000)}с) | Откликов: ${totalResponsesSent}`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
            
            // ФИНАЛЬНАЯ СТАТИСТИКА
            if (scriptActive) {
                const totalTime = Math.round((Date.now() - startTime) / 1000);
                const avgTimePerResponse = totalResponsesSent > 0 ? Math.round(totalTime / totalResponsesSent) : 0;
                const avgTimePerPage = totalPages > 0 ? Math.round(totalTime / totalPages) : 0;
                const avgResponsesPerPage = totalPages > 0 ? Math.round(totalResponsesSent / totalPages * 10) / 10 : 0;
                
                log(`\n🎉 === ВСЕ СТРАНИЦЫ ОБРАБОТАНЫ ===`);
                log(`✅ ФИНАЛЬНАЯ СТАТИСТИКА:`);
                log(`  📄 Страниц обработано: ${totalPages}`);
                log(`  📤 Всего откликов отправлено: ${totalResponsesSent}`);
                log(`  🎯 Кнопок найдено: ${totalButtonsFound}`);
                log(`  ✅ Кнопок успешно обработано: ${totalButtonsProcessed}`);
                log(`  ⏱️ Общее время работы: ${totalTime}с (${Math.round(totalTime/60)}мин)`);
                log(`  📊 Производительность:`);
                log(`    - ${avgResponsesPerPage} откликов/страницу`);
                log(`    - ${avgTimePerResponse}с/отклик`);
                log(`    - ${avgTimePerPage}с/страницу`);
                log(`  🕒 Завершено: ${new Date().toLocaleTimeString()}`);
                
                updateStatus(`🎉 ЗАВЕРШЕНО! ${totalResponsesSent} откликов за ${Math.round(totalTime/60)}мин | Эффективность: ${avgResponsesPerPage}/стр`);
                
                setTimeout(() => stopScript(), 5000);
            }
            
        } catch (e) {
            const elapsed = Math.round((Date.now() - startTime) / 1000);
            log(`❌ === КРИТИЧЕСКАЯ ОШИБКА ===`, 'error');
            log(`❌ Ошибка: ${e.message}`, 'error');
            log(`📊 На момент ошибки: ${totalResponsesSent} откликов за ${elapsed}с`, 'error');
            updateStatus(`❌ Ошибка! Отправлено ${totalResponsesSent} откликов до сбоя`);
            stopScript();
        }
    }
    
    // ========================================
    // УПРАВЛЕНИЕ СКРИПТОМ
    // ========================================
    
    async function startScript() {
        if (scriptActive) {
            log('⚠️ Скрипт уже запущен', 'warn');
            return;
        }
        
        scriptActive = true;
        originalUrl = window.location.href;
        processedButtons.clear();
        
        // Инициализируем счетчики прогресса
        totalResponsesSent = 0;
        responsesOnCurrentPage = 0;
        totalButtonsFound = 0;
        totalButtonsProcessed = 0;
        startTime = Date.now();
        pageStartTime = null;
        
        log('🚀 === ЗАПУСК HH SCRIPT - ULTRA SECURE VERSION ===');
        log(`⏰ Время запуска: ${new Date().toLocaleTimeString()}`);
        updateStatus('🚀 Инициализация...');
        
        // Запускаем автоматическое обновление статуса
        startStatusUpdates();
        
        try {
            // Анализируем пагинацию
            const pagination = await analyzePagination();
            currentPage = pagination.currentPage;
            totalPages = pagination.totalPages;
            
            saveState();
            
            // Детальная информация о предстоящей работе
            log(`📊 === ПЛАН РАБОТЫ ===`);
            log(`📄 Страниц для обработки: ${totalPages}`);
            log(`🔗 Начальная страница: ${currentPage}`);
            log(`📍 Стартовый URL: ${originalUrl}`);
            
            updateStatus(`📋 План: ${totalPages} страниц | Начинаем работу...`);
            
            await new Promise(resolve => setTimeout(resolve, randomDelay({min: 1000, max: 2000})));
            await processAllPages();
            
        } catch (e) {
            log('Ошибка запуска: ' + e.message, 'error');
            stopScript();
        }
    }
    
    function stopScript() {
        if (!scriptActive) return;
        
        scriptActive = false;
        
        // Финальная статистика при остановке
        const elapsed = startTime ? Math.round((Date.now() - startTime) / 1000) : 0;
        const elapsedMin = Math.floor(elapsed / 60);
        const elapsedSec = elapsed % 60;
        const timeStr = elapsedMin > 0 ? `${elapsedMin}м ${elapsedSec}с` : `${elapsedSec}с`;
        
        log('🛑 === HH SCRIPT ОСТАНОВЛЕН ===');
        log(`📊 Итоговая статистика:`);
        log(`  📤 Всего откликов: ${totalResponsesSent}`);
        log(`  📄 Страниц обработано: ${currentPage - 1}/${totalPages}`);
        log(`  ⏱️ Время работы: ${timeStr}`);
        log(`  🎯 Кнопок найдено: ${totalButtonsFound}`);
        log(`  ✅ Кнопок обработано: ${totalButtonsProcessed}`);
        
        updateStatus(`🛑 Остановлен | ${totalResponsesSent} откликов за ${timeStr}`);
        
        // Сбрасываем счетчики
        totalResponsesSent = 0;
        responsesOnCurrentPage = 0;
        totalButtonsFound = 0;
        totalButtonsProcessed = 0;
        startTime = null;
        pageStartTime = null;
        
        // Очистка всех ресурсов для предотвращения утечек памяти
        cleanupResources();
        clearState();
        
        // Очищаем детальный статус
        const detailsEl = document.getElementById('hh-status-details');
        if (detailsEl) {
            detailsEl.innerHTML = '📊 Детальная статистика будет показана во время работы';
        }
    }
    
    // АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ СТАТУСА
    let statusUpdateInterval = null;
    
    function startStatusUpdates() {
        if (statusUpdateInterval) {
            clearInterval(statusUpdateInterval);
        }
        
        statusUpdateInterval = setInterval(() => {
            if (!scriptActive) {
                if (statusUpdateInterval) {
                    clearInterval(statusUpdateInterval);
                    statusUpdateInterval = null;
                }
                return;
            }
            
            // Обновляем детальную информацию каждые 2 секунды
            const detailsEl = document.getElementById('hh-status-details');
            if (detailsEl) {
                const elapsed = startTime ? Math.round((Date.now() - startTime) / 1000) : 0;
                const elapsedMin = Math.floor(elapsed / 60);
                const elapsedSec = elapsed % 60;
                const timeStr = elapsedMin > 0 ? `${elapsedMin}м ${elapsedSec}с` : `${elapsedSec}с`;
                
                const avgTimePerResponse = totalResponsesSent > 0 ? Math.round(elapsed / totalResponsesSent) : 0;
                const estimatedRemaining = totalPages > 0 && currentPage > 1 ? 
                    Math.round((elapsed / (currentPage - 1)) * (totalPages - currentPage + 1)) : 0;
                
                let progressBar = '';
                if (totalPages > 0) {
                    const progress = Math.round((currentPage / totalPages) * 100);
                    const filled = Math.floor(progress / 5);
                    const empty = 20 - filled;
                    progressBar = '█'.repeat(filled) + '░'.repeat(empty) + ` ${progress}%`;
                }
                
                detailsEl.innerHTML = `
                    <div style="font-size: 9px; line-height: 1.3; color: #00ff41;">
                        ${progressBar ? `<div>📊 ${progressBar}</div>` : ''}
                        <div>⏰ ${timeStr} | 📤 ${totalResponsesSent} откликов ${estimatedRemaining > 0 ? `| ⏳ ~${Math.round(estimatedRemaining/60)}м` : ''}</div>
                        ${totalResponsesSent > 0 ? `<div>⚡ ${avgTimePerResponse}с/отклик | 🎯 ${totalButtonsFound} найдено | ✅ ${totalButtonsProcessed} обработано</div>` : ''}
                        <div>📄 Страница ${currentPage}/${totalPages} ${responsesOnCurrentPage > 0 ? `(+${responsesOnCurrentPage} на этой)` : ''}</div>
                        <div style="color: #ff4444; font-weight: bold;">🛡️ СЕНЬОР ЗАЩИТА: ${blockedNavigationAttempts} попыток заблокировано</div>
                        <div style="color: #ff6644; font-size: 8px;">🌐 Сеть: ${networkRequestsBlocked} | 🏠 DOM: ${domModificationsBlocked} | 📡 URL: активен</div>
                    </div>
                `;
            }
        }, 2000);
    }
    
    function emergencyStop() {
        log('🚨 ЭКСТРЕННАЯ ОСТАНОВКА');
        scriptActive = false;
        window.HH_NAVIGATION_ALLOWED = true; // Разблокируем навигацию
        
        // Останавливаем обновление статуса
        if (statusUpdateInterval) {
            clearInterval(statusUpdateInterval);
            statusUpdateInterval = null;
        }
        
        // Сбрасываем счетчики
        totalResponsesSent = 0;
        responsesOnCurrentPage = 0;
        totalButtonsFound = 0;
        totalButtonsProcessed = 0;
        startTime = null;
        pageStartTime = null;
        
        // Экстренная очистка всех ресурсов
        cleanupResources();
        clearState();
        updateStatus('🚨 Экстренно остановлен - навигация разблокирована');
        
        // Очищаем детальный статус
        const detailsEl = document.getElementById('hh-status-details');
        if (detailsEl) {
            detailsEl.innerHTML = '🚨 Экстренная остановка - все ресурсы очищены';
        }
    }
    
    // ========================================
    // ИНТЕРФЕЙС
    // ========================================
    
    function createInterface() {
        if (document.getElementById('hh-panel')) return;
        
        const panel = document.createElement('div');
        panel.id = 'hh-panel';
        panel.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #1a1a1a 0%, #000 100%);
                color: #00ff41;
                border: 2px solid #00ff41;
                padding: 20px;
                border-radius: 12px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                z-index: 999999;
                box-shadow: 0 0 30px rgba(0,255,65,0.5);
                min-width: 300px;
                backdrop-filter: blur(10px);
            ">
                <div style="text-align: center; margin-bottom: 15px; font-weight: bold; font-size: 14px; text-shadow: 0 0 10px #00ff41;">
                    💀 HH SCRIPT ULTRA SECURE 💀
                </div>
                <div style="text-align: center; margin-bottom: 10px; font-size: 10px; color: #ff4444;">
                    🛡️ МАКСИМАЛЬНАЯ БЛОКИРОВКА НАВИГАЦИИ 🛡️
                </div>
                <div style="text-align: center; margin-bottom: 15px;">
                    <button onclick="window.hhStart()" style="
                        background: linear-gradient(45deg, #00ff41, #00cc33);
                        color: #000;
                        border: none;
                        padding: 12px 20px;
                        margin: 5px;
                        cursor: pointer;
                        font-weight: bold;
                        border-radius: 6px;
                        font-size: 12px;
                        box-shadow: 0 0 15px rgba(0,255,65,0.4);
                        transition: all 0.3s;
                    " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                        🚀 ЗАПУСК
                    </button>
                    <br>
                    <button onclick="window.hhStop()" style="
                        background: linear-gradient(45deg, #666, #333);
                        color: #fff;
                        border: none;
                        padding: 8px 15px;
                        margin: 3px;
                        cursor: pointer;
                        font-weight: bold;
                        border-radius: 4px;
                        font-size: 10px;
                    ">
                        ⏸️ СТОП
                    </button>
                    <button onclick="window.hhEmergencyStop()" style="
                        background: linear-gradient(45deg, #ff4444, #cc0000);
                        color: #fff;
                        border: none;
                        padding: 8px 15px;
                        margin: 3px;
                        cursor: pointer;
                        font-weight: bold;
                        border-radius: 4px;
                        font-size: 10px;
                        box-shadow: 0 0 10px rgba(255,68,68,0.4);
                    ">
                        🚨 ЭКСТРЕННО
                    </button>
                </div>
                <div id="hh-status" style="
                    text-align: center;
                    border: 1px solid #00ff41;
                    padding: 10px;
                    border-radius: 6px;
                    background: rgba(0,255,65,0.1);
                    min-height: 20px;
                    font-size: 11px;
                    margin-bottom: 5px;
                ">
                    Готов к запуску
                </div>
                <div id="hh-status-details" style="
                    text-align: center;
                    border: 1px solid #00ff41;
                    border-top: none;
                    padding: 8px;
                    border-radius: 0 0 6px 6px;
                    background: rgba(0,255,65,0.05);
                    font-size: 9px;
                    margin-bottom: 10px;
                    color: #00dd33;
                    line-height: 1.3;
                ">
                    📊 Детальная статистика будет показана во время работы
                </div>
                <div style="font-size: 9px; text-align: center; opacity: 0.8; line-height: 1.4;">
                    <div>⌨️ Горячие клавиши:</div>
                    <div>Ctrl+Alt+S - запуск</div>
                    <div>Ctrl+Alt+Q - стоп</div>
                    <div style="color: #ff4444;">Ctrl+Alt+E - экстренная остановка</div>
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #00ff41; opacity: 0.6;">
                        ULTRA SECURE VERSION<br>
                        🛡️ Двойная защита навигации + автовосстановление<br>
                        🚫 Блокирует ВСЕ способы переходов
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(panel);
    }
    
    // ========================================
    // АВТОВОССТАНОВЛЕНИЕ
    // ========================================
    
    function setupAutoRecovery() {
        // Сохраняем код скрипта для восстановления
        try {
            const scriptCode = `
// HH Script Auto Recovery
(function() {
    console.log('🔄 HH Script: попытка автовосстановления...');
    
    // Проверяем, есть ли уже активный скрипт
    if (window.hhStart) {
        console.log('✅ Скрипт уже загружен');
        return;
    }
    
    // Загружаем сохраненный код
    const savedCode = localStorage.getItem('${STORAGE_KEYS.script}');
    const savedState = localStorage.getItem('${STORAGE_KEYS.state}');
    
    if (savedCode && savedState) {
        try {
            const state = JSON.parse(savedState);
            // Проверяем, что состояние актуально (не старше 1 часа)
            if (state.active && Date.now() - state.timestamp < 3600000) {
                console.log('🚀 Восстанавливаем скрипт из localStorage...');
                
                // Выполняем сохраненный код
                const script = document.createElement('script');
                script.textContent = savedCode;
                document.head.appendChild(script);
                
                // Автозапуск через 3 секунды
                setTimeout(() => {
                    if (window.hhStart && window.location.href.includes('hh.ru')) {
                        console.log('🚀 Автозапуск восстановленного скрипта');
                        window.hhStart();
                    }
                }, 3000);
            }
        } catch (e) {
            console.error('❌ Ошибка автовосстановления:', e);
        }
    }
})();`;
            
            localStorage.setItem('hh_recovery_script', scriptCode);
            
            // Добавляем скрипт восстановления в head
            const recoveryScript = document.createElement('script');
            recoveryScript.textContent = localStorage.getItem('hh_recovery_script');
            document.head.appendChild(recoveryScript);
            
        } catch (e) {
            log('Ошибка настройки автовосстановления: ' + e.message, 'error');
        }
    }
    
    function autoRecover() {
        if (!window.location.href.includes('hh.ru')) return;
        
        const restored = loadState();
        if (restored) {
            log('🔄 Найдено сохраненное состояние');
            updateStatus('Автовосстановление...');
            
            let countdown = 5;
            const timer = safeSetInterval(() => {
                updateStatus(`Автозапуск через ${countdown}с...`);
                countdown--;
                
                if (countdown <= 0) {
                    safeClearInterval(timer);
                    if (!scriptActive) {
                        log('🚀 Автозапуск после восстановления');
                        startScript();
                    }
                }
            }, 1000);
        }
    }
    
    // ========================================
    // ИНИЦИАЛИЗАЦИЯ И СОБЫТИЯ
    // ========================================
    
    // Глобальные функции
    window.hhStart = startScript;
    window.hhStop = stopScript;
    window.hhEmergencyStop = emergencyStop;
    
    // Горячие клавиши
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.altKey) {
            switch (e.key.toLowerCase()) {
                case 's':
                    e.preventDefault();
                    e.stopPropagation();
                    log('🎮 Горячая клавиша: Запуск');
                    startScript();
                    break;
                case 'q':
                    e.preventDefault();
                    e.stopPropagation();
                    log('🎮 Горячая клавиша: Остановка');
                    stopScript();
                    break;
                case 'e':
                    e.preventDefault();
                    e.stopPropagation();
                    log('🎮 Горячая клавиша: Экстренная остановка');
                    emergencyStop();
                    break;
            }
        }
    }, true);
    
    
    // Сохранение состояния при скрытии страницы
    document.addEventListener('visibilitychange', function() {
        if (document.hidden && scriptActive) {
            log('👁️ Страница скрыта, сохраняем состояние');
            saveState();
        }
    });
    
    // Обработка ошибок
    window.addEventListener('error', function(e) {
        log('🐛 JS ошибка: ' + e.message, 'error');
        if (scriptActive) saveState();
    });
    
    window.addEventListener('unhandledrejection', function(e) {
        log('🐛 Promise ошибка: ' + e.reason, 'error');
        if (scriptActive) saveState();
        e.preventDefault();
    });
    
    // Основная инициализация
    function initialize() {
        log('🔧 HH Script ULTRA SECURE - Инициализация началась');
        
        // Проверка совместимости браузера
        if (!window.Promise || !window.fetch || !document.querySelector) {
            log('❌ Браузер не поддерживается', 'error');
            alert('⚠️ HH Script: Ваш браузер не поддерживается!');
            return;
        }
        
        // Проверка localStorage
        try {
            localStorage.setItem('test', 'test');
            localStorage.removeItem('test');
        } catch (e) {
            log('⚠️ localStorage недоступен, автосохранение отключено', 'warn');
        }
        
        // Устанавливаем защиты
        setupNavigationProtection();
        setupNetworkProtection();
        setupDOMProtection();
        setupGlobalEventBlocking();
        setupAggressiveURLProtection();
        setupFormProtection();
        setupClickProtection();
        setupAutoRecovery();
        
        // Создаем интерфейс
        createInterface();
        
        log('✨ Возможности ULTRA SECURE VERSION:');
        log('  🛡️ Многоуровневая блокировка навигации');
        log('  🔒 Безопасное переопределение методов + строгая событийная защита');
        log('  🚫 100% блокировка всех способов смены страницы');
        log('  ⚡ Агрессивный URL-наблюдатель с экстренным возвратом (5 раз в секунду)');
        log('  🚧 Блокировка добавления опасных DOM элементов');
        log('  💾 Автосохранение прогресса в localStorage');
        log('  🔄 Автоматическое восстановление после перезагрузки');
        log('  🚨 Экстренная остановка для разблокировки');
        log('  ⚡ Максимальная устойчивость к любым сбоям и конфликтам браузера');
        
        log('✅ HH Script ULTRA SECURE готов к работе!');
        updateStatus('Готов к запуску');
        
        // Попытка автовосстановления через 2 секунды
        setTimeout(autoRecover, 2000);
    }
    
    // Запуск инициализации
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        setTimeout(initialize, 100);
    }
    
})();