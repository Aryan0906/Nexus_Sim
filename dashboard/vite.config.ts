import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

// Serve each city's graph straight from the repo's single source of truth
// (data/<city>/graph.json) so the dashboard never carries a stale copy. The
// engine data dir lives one level above the dashboard, so a normal public/
// file won't reach it.
const cityGraphsPlugin: Plugin = {
  name: 'city-graphs',
  configureServer(server) {
    server.middlewares.use('/graphs', (req, res, next) => {
      const m = req.url?.match(/^\/([a-zA-Z0-9_-]+)\/graph\.json$/)
      if (!m) return next()
      const file = path.join(repoRoot, 'data', m[1], 'graph.json')
      if (!fs.existsSync(file)) {
        res.statusCode = 404
        res.end('Not found')
        return
      }
      res.setHeader('Content-Type', 'application/json')
      fs.createReadStream(file).pipe(res)
    })
  },
}

// Serve any file under data/ directly (e.g. /data/chicago/cv_congestion.json)
const dataPlugin: Plugin = {
  name: 'data-static',
  configureServer(server) {
    const dataDir = path.resolve(repoRoot, 'data')
    server.middlewares.use('/data', (req, res, next) => {
      const parsedPath = req.url ? req.url.split('?')[0] : ''
      const safePath = path.normalize(parsedPath).replace(/^(\.\.(\/|\\|$))+/, '')
      const file = path.resolve(dataDir, '.' + safePath)
      if (!file.startsWith(dataDir + path.sep)) {
        res.statusCode = 403
        res.end('Forbidden')
        return
      }
      if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
        return next()
      }
      if (file.endsWith('.json')) {
        res.setHeader('Content-Type', 'application/json')
      }
      fs.createReadStream(file).pipe(res)
    })
  },
}

// Serve the multi-city MARL-vs-Webster comparison table straight from the
// evaluation output (ml/results/comparison.json) so the dashboard always
// reflects the latest run without shipping a stale copy.
const resultsPlugin: Plugin = {
  name: 'comparison-results',
  configureServer(server) {
    server.middlewares.use('/comparison.json', (_req, res, _next) => {
      const file = path.join(repoRoot, 'ml', 'results', 'comparison.json')
      if (!fs.existsSync(file)) {
        res.statusCode = 404
        res.end('Not found')
        return
      }
      res.setHeader('Content-Type', 'application/json')
      fs.createReadStream(file).pipe(res)
    })
  },
}

export default defineConfig({
  plugins: [cityGraphsPlugin, dataPlugin, resultsPlugin, react()],
  server: {
    port: 3000,
    // Bind IPv4 like the uvicorn sidecars (all 0.0.0.0). Vite's default
    // "localhost" binds IPv6 ::1 only, which makes the dashboard unreachable
    // via 127.0.0.1 and breaks clients that resolve localhost to IPv4 first.
    host: '0.0.0.0',
    fs: { allow: [repoRoot] },
    // HTTPS by default: serve TLS when certs are present (certs/ is generated
    // by scripts/gen_certs.sh; override with SSL_CERT/SSL_KEY env vars).
    // Resolve against the repo root (cwd is dashboard/ when run via npm).
    https: (() => {
      const cert = path.join(repoRoot, process.env.SSL_CERT || 'certs/server.crt')
      const key = path.join(repoRoot, process.env.SSL_KEY || 'certs/server.key')
      if (fs.existsSync(cert) && fs.existsSync(key)) {
        console.log(`TLS enabled: ${cert}`)
        return { key: fs.readFileSync(key), cert: fs.readFileSync(cert) }
      }
      console.log('WARNING: certs/server.{crt,key} not found; serving plain HTTP')
      return undefined
    })(),
    proxy: {
      '/api': {
        target: 'https://localhost:8000',
        changeOrigin: true,
        secure: false, // self-signed cert
      },
      '/ws': {
        target: 'wss://localhost:8000',
        ws: true,
        secure: false, // self-signed cert
      },
    },
  },
})
