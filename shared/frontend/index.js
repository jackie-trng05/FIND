const express = require('express');
const path = require('path');
const port = process.env.PORT || 3000;
const app = express();

// Serve static files from this directory
app.use(express.static(path.join(__dirname, '/')));

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(port, () => console.log(`Shared frontend listening on ${port}`));
