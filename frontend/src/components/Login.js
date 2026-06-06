import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

export default function Login() {
  const [form, setForm] = useState({ identifier: '', password: '' });
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post('http://localhost:5000/api/auth/login', form);
      localStorage.setItem("username", res.data.username);
      navigate(res.data.role === 'admin' ? '/admin' : '/driver');
    } catch (err) { alert("Access Denied: Check Credentials"); }
  };

  const S = {
    container: { height: "100vh", display: "flex", justifyContent: "center", alignItems: "center", background: "linear-gradient(135deg, #0a1628 0%, #1e4d8c 100%)" },
    card: { width: "400px", padding: "40px", borderRadius: "28px", background: "rgba(255, 255, 255, 0.03)", backdropFilter: "blur(20px)", border: "1px solid rgba(255, 255, 255, 0.1)", textAlign: "center" },
    input: { width: "100%", padding: "15px", margin: "10px 0", borderRadius: "14px", background: "rgba(15, 23, 42, 0.6)", color: "#fff", border: "none", boxSizing: "border-box" }
  };

  return (
    <div style={S.container}>
      <form style={S.card} onSubmit={handleLogin}>
        <h2 style={{ color: "#fff" }}>STAFF LOGIN</h2>
        <input style={S.input} placeholder="Employee No (EN-101)" required onChange={(e) => setForm({ ...form, identifier: e.target.value })} />
        <input style={S.input} type="password" placeholder="Password" required onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <button style={{ width: "100%", padding: "16px", background: "#06b6d4", color: "#0a1628", fontWeight: "800", border: "none", borderRadius: "14px", cursor: "pointer" }}>SECURE LOGIN</button>
      </form>
    </div>
  );
}
