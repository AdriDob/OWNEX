const express = require('express')
const path = require('path')
const app = express()

const distPath = path.join(__dirname, 'dist')

app.use(express.static(distPath))

// SPA fallback: serve index.html for all non-file routes
app.get('*', (req, res) => {
  res.sendFile(path.join(distPath, 'index.html'))
})

const PORT = 8081
app.listen(PORT, () => {
  console.log(`SPA server running on http://localhost:${PORT}`)
})
