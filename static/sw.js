/**
 * ClubVoice Service Worker
 * 提供离线支持和后台音频保持
 */

const CACHE_NAME = 'clubvoice-v1.0.0';
const RUNTIME_CACHE = 'clubvoice-runtime';

// 需要缓存的静态资源
const urlsToCache = [
  '/',
  '/static/index.html',
  '/static/full.html',
  '/static/debug.html',
  '/static/manifest.json',
  '/static/js/client.js'
];

// 安装 Service Worker
self.addEventListener('install', event => {
  console.log('[SW] 安装中...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[SW] 缓存静态资源');
        return cache.addAll(urlsToCache);
      })
      .then(() => {
        console.log('[SW] 安装完成，跳过等待');
        return self.skipWaiting();
      })
      .catch(err => {
        console.error('[SW] 安装失败:', err);
      })
  );
});

// 激活 Service Worker
self.addEventListener('activate', event => {
  console.log('[SW] 激活中...');
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          // 删除旧版本缓存
          if (cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE) {
            console.log('[SW] 删除旧缓存:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
    .then(() => {
      console.log('[SW] 激活完成，接管所有客户端');
      return self.clients.claim();
    })
  );
});

// 拦截网络请求
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Socket.IO 和 API 请求不缓存
  if (url.pathname.includes('/socket.io/') || 
      url.pathname.includes('/api/') ||
      request.method !== 'GET') {
    return;
  }
  
  // 使用缓存优先策略（对于静态资源）
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request)
        .then(response => {
          if (response) {
            console.log('[SW] 从缓存返回:', url.pathname);
            return response;
          }
          
          return fetch(request).then(response => {
            // 缓存新的静态资源
            if (response.status === 200) {
              const responseClone = response.clone();
              caches.open(CACHE_NAME).then(cache => {
                cache.put(request, responseClone);
              });
            }
            return response;
          });
        })
        .catch(() => {
          // 离线时返回缓存
          return caches.match('/static/index.html');
        })
    );
  } else {
    // 网络优先策略（对于动态内容）
    event.respondWith(
      fetch(request)
        .then(response => {
          // 缓存到运行时缓存
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(RUNTIME_CACHE).then(cache => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // 网络失败时使用缓存
          return caches.match(request);
        })
    );
  }
});

// 处理来自客户端的消息
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'KEEP_ALIVE') {
    // 保持 Service Worker 活跃
    console.log('[SW] Keep-alive ping 收到');
    
    // 响应客户端
    event.ports[0].postMessage({ type: 'PONG' });
  }
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    console.log('[SW] 收到跳过等待请求');
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CLAIM_CLIENTS') {
    console.log('[SW] 收到接管客户端请求');
    self.clients.claim();
  }
});

// 后台同步（如果支持）
self.addEventListener('sync', event => {
  console.log('[SW] 后台同步:', event.tag);
  
  if (event.tag === 'sync-audio-state') {
    event.waitUntil(
      // 这里可以添加音频状态同步逻辑
      Promise.resolve()
    );
  }
});

// 推送通知（预留）
self.addEventListener('push', event => {
  console.log('[SW] 收到推送:', event);
  
  const options = {
    body: event.data ? event.data.text() : '新消息',
    icon: '/static/icon-192.png',
    badge: '/static/icon-96.png',
    vibrate: [200, 100, 200],
    tag: 'clubvoice-notification',
    requireInteraction: false
  };
  
  event.waitUntil(
    self.registration.showNotification('ClubVoice', options)
  );
});

// 通知点击处理
self.addEventListener('notificationclick', event => {
  console.log('[SW] 通知被点击');
  
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow('/')
  );
});

console.log('[SW] Service Worker 已加载');
