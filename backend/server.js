const express = require('express');
const http = require('http'); // 🚀 Required for Socket.io
const { Server } = require('socket.io');
const mysql = require('mysql2/promise');
const cors = require('cors');
const jwt = require('jsonwebtoken');

const app = express();
const server = http.createServer(app); // 🚀 Create the Server
const io = new Server(server, { cors: { origin: "*" } }); // 🚀 Initialize Socket

app.use(cors()); app.use(express.json());

const JWT_SECRET = 'secret456';
let pool;

const initDB = async () => {
  pool = await mysql.createPool({ 
    host: 'localhost', 
    user: 'root', 
    password: '@Master5725#', // 👈 Verify your MySQL password
    database: 'urbancab' 
  });
  console.log('✅ System B: Real-Time Fleet Network Active');
};

// ================== 🚀 LOGIN: MASTER KEY BYPASS ==================
app.post('/api/auth/login', async (req, res) => {
  const { identifier, password } = req.body;
  
  // Strict check for your Admin ID
  if (identifier === 'ADMIN-01' && password === 'UrbanCab@2024') {
    return res.json({ token: 'jwt_secure', role: 'admin', username: 'System Admin' });
  }
  
  // Support for Driver IDs starting with EN-
  if (identifier.startsWith('EN-') && password === 'UrbanCab@2024') {
    return res.json({ token: 'jwt_secure', role: 'driver', username: 'Maseru Driver' });
  }

  res.status(401).json({ message: "Check Credentials" });
});

// ================== 🚀 OTHER ROUTES ==================
app.get('/api/locations', async (req, res) => {
  const [rows] = await pool.query('SELECT location_id as id, name FROM locations');
  res.json(rows);
});

io.on('connection', (socket) => console.log('📡 Fleet Stakeholder Connected'));

const PORT = 5000;
initDB().then(() => {
  // 🚀 CRITICAL: Use server.listen (NOT app.listen) to stop the 404 errors
  server.listen(PORT, () => {
    console.log(`🚀 Dispatch Center Live on http://localhost:${PORT}`);
  });
});
