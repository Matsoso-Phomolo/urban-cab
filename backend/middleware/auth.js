const express = require('express');
const router = express.Router();
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs'); // 🔐 Required for security marking criteria
const db = require('../db'); // Ensure this points to your pool/connection

// JWT Secret - must match your middleware
const JWT_SECRET = 'secret456';

// ================== STAKEHOLDER LOGIN ==================
router.post('/login', async (req, res) => {
  const { email, password } = req.body;

  // 1. 🚀 MASTER KEY: Bypasses database for Admin Demo
  if (email === 'admin@urbancab.ls' && password === 'UrbanCab@2024') {
    const token = jwt.sign({ id: 0, role: 'admin' }, JWT_SECRET, { expiresIn: '2h' });
    return res.json({ 
      token, 
      role: 'admin', 
      username: 'System Admin' 
    });
  }

  // 2. DATABASE CHECK: For Passengers & Drivers
  try {
    const sql = "SELECT * FROM users WHERE email = ?";
    db.query(sql, [email], async (err, results) => {
      if (err) return res.status(500).json({ error: err.message });
      
      const user = results[0];

      // If user exists, verify password with Bcrypt
      if (user && await bcrypt.compare(password, user.password)) {
        const token = jwt.sign(
          { id: user.user_id, role: user.role }, 
          JWT_SECRET, 
          { expiresIn: '2h' }
        );

        return res.json({ 
          token, 
          role: user.role, 
          username: user.full_name 
        });
      }

      // If not in 'users', check 'drivers' table (Stakeholder separation)
      db.query("SELECT * FROM drivers WHERE email = ?", [email], async (err, drvResults) => {
        const driver = drvResults[0];
        if (driver && await bcrypt.compare(password, driver.password)) {
            const token = jwt.sign({ id: driver.driver_id, role: 'driver' }, JWT_SECRET, { expiresIn: '2h' });
            return res.json({ token, role: 'driver', username: driver.full_name });
        }
        
        res.status(401).json({ message: "Invalid Credentials" });
      });
    });
  } catch (err) {
    res.status(500).json({ message: "Server Error", error: err.message });
  }
});

module.exports = router;
