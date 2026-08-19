const express = require('express');
const app = express();
const port = process.env.PORT || 6001;

app.get('/', (req, res) => res.json({ service: 'student-1-db', description: 'Student 1 Database API placeholder', health: '/health', data: '/data' }));
app.get('/health', (req, res) => res.json({ status: 'ok' }));
app.get('/data', (req, res) => res.json({ db: 'student-1-db', schemaOwner: 'student-1' }));

app.listen(port, () => console.log(`Student 1 DB API listening on port ${port}`));
