import React from 'react';
import { useNavigate } from 'react-router-dom';
import logo from "../assets/logo.png";

export default function Home() {
  const navigate = useNavigate();

  const S = {
    container: { height: "100vh", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", background: "linear-gradient(135deg, #0a1628 0%, #1e4d8c 100%)", color: "#fff", fontFamily: "'Segoe UI', sans-serif" },
    btn: { width: "250px", padding: "18px", margin: "10px", borderRadius: "15px", border: "none", fontWeight: "800", cursor: "pointer", fontSize: "1rem", transition: "0.3s" },
    passengerBtn: { background: "#06b6d4", color: "#0a1628" },
    staffBtn: { background: "rgba(255, 255, 255, 0.05)", color: "#fff", border: "1px solid rgba(255, 255, 255, 0.2)" }
  };

  return (
    <div style={S.container}>
      <img src={logo} alt="Logo" style={{ width: '120px', marginBottom: '20px' }} />
      <h1 style={{ fontSize: '2.5rem', marginBottom: '10px' }}>MASERU URBAN CAB</h1>
      <p style={{ color: '#94a3b8', marginBottom: '40px' }}>Your premium dispatch service in the CBD</p>

      {/* 🚀 THE BOOK RIDE BUTTON */}
      <button 
        style={{...S.btn, ...S.passengerBtn}} 
        onClick={() => navigate('/book')}
      >
        BOOK A RIDE ➔
      </button>

      {/* 🚀 THE STAFF LOGIN BUTTON */}
      <button 
        style={{...S.btn, ...S.staffBtn}} 
        onClick={() => navigate('/login')}
      >
        STAFF PORTAL
      </button>
    </div>
  );
}
