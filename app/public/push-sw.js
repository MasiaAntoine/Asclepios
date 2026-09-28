/* global self */

self.addEventListener('push', function (event) {
  var data = { title: 'Asclepios', body: '', url: '/', tag: 'asclepios-push' }
  try {
    if (event.data) {
      var parsed = event.data.json()
      if (parsed && typeof parsed === 'object') {
        data.title = parsed.title || data.title
        data.body = parsed.body || ''
        data.url = parsed.url || '/'
        data.tag = parsed.tag || data.tag
      }
    }
  } catch (err) {
    try {
      data.body = event.data ? event.data.text() : ''
    } catch (_) {
      /* ignore */
    }
  }

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (windows) {
      var visible = windows.some(function (client) {
        return client.visibilityState === 'visible'
      })
      if (visible) return
      return self.registration.showNotification(data.title, {
        body: data.body,
        icon: '/pwa-192x192.png',
        badge: '/pwa-192x192.png',
        tag: data.tag,
        data: { url: data.url },
        renotify: true,
      })
    }),
  )
})

self.addEventListener('notificationclick', function (event) {
  event.notification.close()
  var url = (event.notification.data && event.notification.data.url) || '/'
  var absolute = new URL(url, self.registration.scope).href
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (windows) {
      for (var i = 0; i < windows.length; i++) {
        var client = windows[i]
        var sameApp = client.url && client.url.indexOf(self.registration.scope) === 0
        if (sameApp) {
          try {
            client.postMessage({ type: 'navigate', url: url })
          } catch (_) {
            /* ignore */
          }
          if (client.focus) return client.focus()
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(absolute)
    }),
  )
})
