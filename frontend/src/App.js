import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./components/Login";
import BookRide from "./components/BookRide";
import AdminDashboard from "./components/AdminDashboard";
import DriverDashboard from "./components/DriverDashboard";
import RegisterDriver from "./components/RegisterDriver";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" />} />
        <Route path="/login" element={<Login />} />
        <Route path="/book" element={<BookRide />} />
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/driver" element={<DriverDashboard />} />
        <Route path="/register-driver" element={<RegisterDriver />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;