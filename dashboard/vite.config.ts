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
const handleGraphs = (req: any, res: any, next: any) => {
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
}

const cityGraphsPlugin: Plugin = {
  name: 'city-graphs',
  configureServer(server) {
    server.middlewares.use('/graphs', handleGraphs)
  },
  configurePreviewServer(server) {
    server.middlewares.use('/graphs', handleGraphs)
  },
}

const handleData = (req: any, res: any, next: any) => {
  const dataDir = path.resolve(repoRoot, 'data')
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
}

// Serve any file under data/ directly (e.g. /data/chicago/cv_congestion.json)
const dataPlugin: Plugin = {
  name: 'data-static',
  configureServer(server) {
    server.middlewares.use('/data', handleData)
  },
  configurePreviewServer(server) {
    server.middlewares.use('/data', handleData)
  },
}

const handleComparison = (_req: any, res: any, _next: any) => {
  const file = path.join(repoRoot, 'ml', 'results', 'comparison.json')
  if (!fs.existsSync(file)) {
    res.statusCode = 404
    res.end('Not found')
    return
  }
  res.setHeader('Content-Type', 'application/json')
  fs.createReadStream(file).pipe(res)
}

// Serve the multi-city MARL-vs-Webster comparison table straight from the
// evaluation output (ml/results/comparison.json) so the dashboard always
// reflects the latest run without shipping a stale copy.
const resultsPlugin: Plugin = {
  name: 'comparison-results',
  configureServer(server) {
    server.middlewares.use('/comparison.json', handleComparison)
  },
  configurePreviewServer(server) {
    server.middlewares.use('/comparison.json', handleComparison)
  },
}

const resolveHttps = () => {
  const cert = path.join(repoRoot, process.env.SSL_CERT || 'certs/server.crt')
  const key = path.join(repoRoot, process.env.SSL_KEY || 'certs/server.key')
  if (fs.existsSync(cert) && fs.existsSync(key)) {
    console.log(`TLS enabled: ${cert}`)
    return { key: fs.readFileSync(key), cert: fs.readFileSync(cert) }
  }
  console.log('WARNING: certs/server.{crt,key} not found; serving plain HTTP')
  return undefined
}

export default defineConfig({
  plugins: [cityGraphsPlugin, dataPlugin, resultsPlugin, react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    fs: { allow: [repoRoot] },
    https: resolveHttps(),
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
  preview: {
    port: 3000,
    host: '0.0.0.0',
    https: resolveHttps(),
  },
})
