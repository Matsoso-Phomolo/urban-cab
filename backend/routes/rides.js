const express = require("express");
const router = express.Router();
const db = require("../db");

router.post("/", (req, res) => {
  const { passenger_id, pickup_id, dropoff_id, payment_method } = req.body;
  
  // 🚀 Transaction Logic: Auto-calculate Maseru fare
  const baseFare = 20.00;
  const distancePremium = Math.random() * 25; // Simulated distance logic
  const totalFare = (baseFare + distancePremium).toFixed(2);

  const sql = "INSERT INTO rides (passenger_id, pickup_id, dropoff_id, status, fare, payment_method) VALUES (?, ?, ?, 'requested', ?, ?)";
  db.query(sql, [passenger_id, pickup_id, dropoff_id, totalFare, payment_method || 'Cash'], (err, result) => {
    if (err) return res.status(500).send(err);
    res.send({ message: "Ride Booked", ride_id: result.insertId, fare: totalFare });
  });
});

module.exports = router;
