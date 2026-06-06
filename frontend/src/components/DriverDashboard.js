import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import BackButton from "./BackButton";

const socket = io('http://localhost:5000');

export default function DriverDashboard() {
  const [rides, setRides] = useState([]);
  const [alert, setAlert] = useState("");
  const driverName = localStorage.getItem("username");

  useEffect(() => {
    socket.on('new_dispatch', (data) => {
      setRides(prev => [data, ...prev]);
      setAlert("🔔 NEW REQUEST RECEIVED");
    });

    socket.on('dispatch_claimed', (data) => {
      setRides(prev => prev.filter(r => r.ride_id !== data.ride_id));
      setAlert(data.message);
    });
  }, []);

  const claimRide = async (id) => {
    await fetch(`http://localhost:5000/api/rides/accept/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ driver_name: driverName })
    });
  };

  const S = {
    container: { minHeight: "100vh", background: "linear-gradient(135deg, #0a1628 0%, #1e4d8c 100%)", color: "#fff", padding: "40px" },
    card: { background: "rgba(255, 255, 255, 0.05)", borderRadius: "20px", padding: "20px", marginBottom: "15px", display: 'flex', justifyContent: 'space-between' },
    alert: { background: '#06b6d4', color: '#0a1628', padding: '10px', borderRadius: '10px', textAlign: 'center', marginBottom: '20px', fontWeight: 'bold' }
  };

  return (
    <div style={S.container}>
      <BackButton />
      <h2>Driver Dispatch Hub</h2>
      {alert && <div style={S.alert}>{alert}</div>}
      {rides.map(r => (
        <div key={r.ride_id} style={S.card}>
          <div><b>Trip #{r.ride_id}</b><br/>Fare: M {r.fare}</div>
          <button onClick={() => claimRide(r.ride_id)} style={{ background: '#06b6d4', border: 'none', padding: '10px 20px', borderRadius: '10px', fontWeight: 'bold', cursor: 'pointer' }}>CLAIM RIDE</button>
        </div>
      ))}
    </div>
  );
}
