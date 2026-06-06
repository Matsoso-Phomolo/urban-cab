import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function BookRide() {
  const [phase, setPhase] = useState(1);
  const [locations, setLocations] = useState([]);
  const [form, setForm] = useState({ passenger_name: '', passenger_phone: '', pickup_id: '', dropoff_id: '', payment_method: '' });

  useEffect(() => {
    axios.get('http://localhost:5000/api/locations').then(res => setLocations(res.data));
  }, []);

  const handleBooking = async (e) => {
    e.preventDefault();
    await axios.post('http://localhost:5000/api/rides', form);
    alert(`✅ Dispatch Confirmed for ${form.passenger_name}!`);
    window.location.href = "/login";
  };

  const S = {
    container: { height: "100vh", display: "flex", justifyContent: "center", alignItems: "center", background: "linear-gradient(135deg, #0a1628 0%, #1e4d8c 100%)" },
    card: { width: "450px", padding: "40px", borderRadius: "30px", background: "rgba(255, 255, 255, 0.03)", backdropFilter: "blur(20px)", border: "1px solid rgba(255, 255, 255, 0.1)", textAlign: "center" },
    input: { width: "100%", padding: "15px", margin: "10px 0", borderRadius: "12px", background: "rgba(15, 23, 42, 0.8)", color: "#fff", border: "none", boxSizing: "border-box" }
  };

  return (
    <div style={S.container}>
      {phase === 1 ? (
        <div style={S.card}>
          <h2 style={{ color: "#fff" }}>Passenger Check-In</h2>
          <input style={S.input} placeholder="Full Name" onChange={e => setForm({...form, passenger_name: e.target.value})} />
          <input style={S.input} placeholder="8-Digit Mobile No." value={form.passenger_phone} onChange={e => {
            const val = e.target.value.replace(/\D/g, '');
            if(val.length <= 8) setForm({...form, passenger_phone: val});
          }} />
          <button disabled={form.passenger_phone.length !== 8} onClick={() => setPhase(2)} style={{ width: "100%", padding: "16px", background: "#06b6d4", border: 'none', borderRadius: '15px', fontWeight: 'bold' }}>NEXT ➔</button>
        </div>
      ) : (
        <form style={S.card} onSubmit={handleBooking}>
          <h2 style={{ color: "#fff" }}>Book a Ride</h2>
          <select style={S.input} required onChange={e => setForm({...form, pickup_id: e.target.value})}><option value="">-- Pickup Location --</option>{locations.map(loc => <option key={loc.id} value={loc.id} style={{color:'#000'}}>{loc.name}</option>)}</select>
          <select style={S.input} required onChange={e => setForm({...form, dropoff_id: e.target.value})}><option value="">-- Destination --</option>{locations.map(loc => <option key={loc.id} value={loc.id} style={{color:'#000'}}>{loc.name}</option>)}</select>
          <select style={S.input} required onChange={e => setForm({...form, payment_method: e.target.value})}><option value="">-- Payment Method --</option><option value="Cash">Cash</option><option value="M-Pesa">M-Pesa</option><option value="EcoCash">EcoCash</option></select>
          <button style={{ width: "100%", padding: "16px", background: "#06b6d4", border: 'none', borderRadius: '15px', fontWeight: 'bold' }}>CONFIRM BOOKING</button>
        </form>
      )}
    </div>
  );
}
