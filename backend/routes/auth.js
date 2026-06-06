const express = require("express");
const router = express.Router();
const db = require("../db");
const bcrypt = require("bcryptjs");

// ✅ Register with Hashing
router.post("/register", async (req, res) => {
  const { full_name, email, phone, password, role } = req.body;
  const hash = await bcrypt.hash(password, 10);

  const sql = "INSERT INTO users (full_name, email, phone, password, role) VALUES (?, ?, ?, ?, ?)";
  db.query(sql, [full_name, email, phone, hash, role || 'passenger'], (err) => {
    if (err) return res.status(500).send(err);
    res.send({ message: "User created successfully" });
  });
});

module.exports = router;
