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
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (windows) {
      for (var i = 0; i < windows.length; i++) {
        var client = windows[i]
        if ('focus' in client) {
          return client.focus().then(function (focused) {
            if (focused && 'navigate' in focused) return focused.navigate(url)
            return focused
          })
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(url)
    }),
  )
})
