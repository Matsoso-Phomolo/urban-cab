import React, { useState } from 'react';
import axios from 'axios';
import BackButton from "./BackButton";

export default function RegisterDriver() {
  const [form, setForm] = useState({ full_name: '', email: '', phone: '', password: '', license_no: '', vehicle_reg: '' });
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      // 🚀 Pointing to the specific Backend Route on Port 5000
      await axios.post('http://localhost:5000/api/admin/register-driver', form);
      alert("✅ Staff Enrolled: New Driver added to permanent fleet.");
      setForm({ full_name: '', email: '', phone: '', password: '', license_no: '', vehicle_reg: '' });
    } catch (err) {
      alert("❌ Enrollment Failed: " + (err.response?.data?.error || "Connection Error"));
    } finally { setLoading(false); }
  };

  const S = {
    container: { minHeight: "100vh", display: "flex", justifyContent: "center", alignItems: "center", background: "linear-gradient(135deg, #0a1628 0%, #1e4d8c 100%)", padding: "20px" },
    card: { width: "500px", padding: "40px", borderRadius: "30px", background: "rgba(255, 255, 255, 0.03)", backdropFilter: "blur(20px)", border: "1px solid rgba(255, 255, 255, 0.1)", boxShadow: "0 20px 50px rgba(0,0,0,0.5)", textAlign: "center" },
    grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px", marginBottom: "20px" },
    input: { width: "100%", padding: "14px", borderRadius: "12px", background: "rgba(15, 23, 42, 0.8)", color: "#fff", border: "1px solid rgba(255,255,255,0.1)", outline: "none", fontSize: "0.9rem" },
    btn: { width: "100%", padding: "16px", borderRadius: "15px", background: "#06b6d4", color: "#0a1628", fontWeight: "800", border: "none", cursor: "pointer" }
  };

  return (
    <div style={S.container}>
      <div style={{ position: 'absolute', top: '40px', left: '40px' }}><BackButton /></div>
      <form style={S.card} onSubmit={handleRegister}>
        <h2 style={{ color: "#fff", fontSize: "2rem" }}>Enroll New Staff</h2>
        <p style={{ color: "#94a3b8", marginBottom: "30px", fontSize: "0.85rem" }}>Permanent Driver Registration Terminal</p>

        <div style={S.grid}>
          <input style={S.input} placeholder="Full Name" required value={form.full_name} onChange={e => setForm({...form, full_name: e.target.value})} />
          <input style={S.input} placeholder="Email" type="email" required value={form.email} onChange={e => setForm({...form, email: e.target.value})} />
          <input style={S.input} placeholder="Phone" required value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} />
          <input style={S.input} placeholder="Password" type="password" required value={form.password} onChange={e => setForm({...form, password: e.target.value})} />
          <input style={S.input} placeholder="License No" required value={form.license_no} onChange={e => setForm({...form, license_no: e.target.value})} />
          <input style={S.input} placeholder="Vehicle Reg" required value={form.vehicle_reg} onChange={e => setForm({...form, vehicle_reg: e.target.value})} />
        </div>

        <button style={S.btn} disabled={loading}>{loading ? "ENROLLING..." : "ENROLL PERMANENT DRIVER"}</button>
      </form>
    </div>
  );
}
