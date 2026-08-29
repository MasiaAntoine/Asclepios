import fs from 'node:fs'
import path from 'node:path'
import type { Plugin } from 'vite'
import type { IncomingMessage, ServerResponse } from 'node:http'

/**
 * Serves the private data directory at /data during Vite dev.
 * Clinical files stay outside the app bundle and outside the GitHub app repo.
 */
export function servePrivateData(dataDir: string): Plugin {
  const root = path.resolve(dataDir)

  function sendFile(filePath: string, res: ServerResponse) {
    if (!filePath.startsWith(root) || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
      res.statusCode = 404
      res.end('Not found')
      return
    }
    const ext = path.extname(filePath).toLowerCase()
    const types: Record<string, string> = {
      '.json': 'application/json; charset=utf-8',
      '.csv': 'text/csv; charset=utf-8',
      '.md': 'text/markdown; charset=utf-8',
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.pdf': 'application/pdf',
    }
    res.setHeader('Content-Type', types[ext] || 'application/octet-stream')
    res.setHeader('Cache-Control', 'no-store')
    fs.createReadStream(filePath).pipe(res)
  }

  function rapportsIndex(): string {
    const dir = path.join(root, 'rapports')
    if (!fs.existsSync(dir)) return '[]'
    const files = fs
      .readdirSync(dir)
      .filter((f) => f.endsWith('.md') && f.toLowerCase() !== 'readme.md')
      .sort()
      .map((f) => ({
        id: f.replace(/\.md$/i, ''),
        file: f,
      }))
    return JSON.stringify(files)
  }

  return {
    name: 'serve-private-data',
    configureServer(server) {
      server.middlewares.use((req: IncomingMessage, res: ServerResponse, next: () => void) => {
        if (!req.url?.startsWith('/data')) return next()

        const url = new URL(req.url, 'http://localhost')
        const rel = decodeURIComponent(url.pathname.replace(/^\/data\/?/, ''))

        if (rel === 'rapports/index.json') {
          res.statusCode = 200
          res.setHeader('Content-Type', 'application/json; charset=utf-8')
          res.setHeader('Cache-Control', 'no-store')
          res.end(rapportsIndex())
          return
        }

        sendFile(path.normalize(path.join(root, rel)), res)
      })
    },
  }
}
