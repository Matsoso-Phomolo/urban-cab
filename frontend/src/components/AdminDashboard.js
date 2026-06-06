import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

export default function AdminDashboard() {
  const [rides, setRides] = useState([]);
  const [users, setUsers] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:5000/api/admin/rides').then(res => setRides(res.data));
    axios.get('http://localhost:5000/api/users?search=').then(res => setUsers(res.data));
  }, []);

  const S = {
    container: { height: "100vh", background: "#0a1628", color: "#fff", padding: "20px 40px", display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "20px", overflow: 'hidden' },
    card: { background: "rgba(255, 255, 255, 0.03)", padding: "20px", borderRadius: "20px", border: "1px solid rgba(255,255,255,0.1)", overflowY: 'auto' }
  };

  return (
    <div style={S.container}>
      <div style={S.card}>
        <h3>DIRECTORY</h3>
        <Link to="/register-driver" style={{color: '#06b6d4', textDecoration: 'none'}}>+ ENROLL STAFF</Link>
        {users.map(u => <div key={u.user_id} style={{padding: '10px 0', borderBottom: '1px solid #1e293b'}}>{u.full_name} <br/> <small>{u.employee_no || u.email}</small></div>)}
      </div>
      <div style={S.card}>
        <h3>REVENUE</h3>
        <div style={{padding: '20px', background: '#1e4d8c', borderRadius: '15px'}}>Total Fleet Income: <br/> <b>M 1,450.00</b></div>
      </div>
      <div style={S.card}>
        <h3>SAFETY LOG (24H)</h3>
        {rides.map(r => (
          <div key={r.ride_id} style={{padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '10px', marginBottom: '10px'}}>
            <b>Trip #{r.ride_id}</b> <br/>
            {r.name ? <span style={{color: '#06b6d4'}}>{r.name} ({r.phone})</span> : <span style={{color: '#ef4444'}}>PII PURGED</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
