const express = require('express');
const app = express();
const port = process.env.PORT || 6000;

app.get('/', (req, res) => res.json({ service: 'shared-db', description: 'Shared Access DB API placeholder', health: '/health', schema: '/schema' }));
app.get('/health', (req, res) => res.json({ status: 'ok' }));
app.get('/schema', (req, res) => res.json({ db: 'shared-access-db', schemaOwner: 'shared' }));

app.listen(port, () => console.log(`Shared DB API listening on port ${port}`));
