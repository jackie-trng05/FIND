const express = require('express');
const app = express();
const port = process.env.PORT || 5001;

app.get('/', (req, res) => res.send('Student 1 backend placeholder'));
app.get('/health', (req, res) => res.json({ status: 'ok' }));

// Example route that would call the student DB API (placeholder)
app.get('/db-info', async (req, res) => {
  res.json({ note: 'This would call the student-1 database API at http://student-1-db:6001 in full integration.' });
});

app.listen(port, () => console.log(`Student 1 backend listening on port ${port}`));
