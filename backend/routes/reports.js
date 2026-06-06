const express = require("express");
const router = express.Router();
const db = require("../db");

// ✅ Advanced Report: Revenue by Pickup Location
router.get("/revenue", (req, res) => {
  const sql = `
    SELECT l.name as location, SUM(r.fare) as totalRevenue, COUNT(r.ride_id) as rideCount
    FROM locations l
    JOIN rides r ON l.location_id = r.pickup_id
    GROUP BY l.location_id
    ORDER BY totalRevenue DESC
  `;

  db.query(sql, (err, results) => {
    if (err) return res.status(500).send(err);
    res.send(results);
  });
});

module.exports = router;
