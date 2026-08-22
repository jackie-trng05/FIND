const express = require('express');
const app = express();
const port = process.env.PORT || 5000;

app.get('/', (req, res) => res.json({ service: 'shared-api', description: 'Shared Access API placeholder', health: '/health', info: '/info' }));
app.get('/health', (req, res) => res.json({ status: 'ok' }));
app.get('/info', (req, res) => res.json({ service: 'shared-api', note: 'Access API placeholder' }));

app.listen(port, () => console.log(`Shared API listening on port ${port}`));
