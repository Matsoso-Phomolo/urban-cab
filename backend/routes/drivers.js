const express = require("express");
const router = express.Router();
const db = require("../db");

// ✅ Get all drivers (includes Search/Find logic)
router.get("/", (req, res) => {
  const { search } = req.query;
  const sql = search ? "SELECT * FROM drivers WHERE full_name LIKE ?" : "SELECT * FROM drivers";
  db.query(sql, [`%${search}%`], (err, results) => {
    if (err) return res.status(500).send(err);
    res.send(results);
  });
});

// ✅ Add new driver (Classy inputs)
router.post("/", (req, res) => {
  const { full_name, phone, license_no, vehicle_reg, vehicle_type } = req.body;
  const sql = "INSERT INTO drivers (full_name, phone, license_no, vehicle_reg, vehicle_type) VALUES (?, ?, ?, ?, ?)";
  db.query(sql, [full_name, phone, license_no, vehicle_reg, vehicle_type], (err) => {
    if (err) return res.status(500).send(err);
    res.send({ message: "Driver added successfully" });
  });
});

module.exports = router;
