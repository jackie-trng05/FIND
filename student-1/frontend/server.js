const express = require('express');
const app = express();
const port = process.env.PORT || 3001;

app.get('/', (req, res) => res.send('Student 1 frontend placeholder'));
app.get('/health', (req, res) => res.json({ status: 'ok' }));

app.listen(port, () => console.log(`Student 1 frontend listening on port ${port}`));
