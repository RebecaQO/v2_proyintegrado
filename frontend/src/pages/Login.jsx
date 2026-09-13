import React, { useState } from 'react';
import { LogIn, UserPlus, Mail, Lock, User, Phone, ArrowLeft, AlertTriangle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Login({ onBack }) {
  const { login, register } = useAuth();
  const [modo, setModo] = useState('login'); // 'login' | 'registro'
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Login
  const [correo, setCorreo] = useState('');
  const [contrasena, setContrasena] = useState('');

  // Registro (siempre crea rol Ciudadano)
  const [nombreCompleto, setNombreCompleto] = useState('');
  const [correoReg, setCorreoReg] = useState('');
  const [contrasenaReg, setContrasenaReg] = useState('');
  const [telefono, setTelefono] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await login(correo.trim(), contrasena);
      // Al loguear exitosamente, AuthContext actualiza `user` y App.jsx
      // redirige automáticamente según el rol.
    } catch (err) {
      setError(err.message || 'No se pudo iniciar sesión');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegistro = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await register({
        nombre_completo: nombreCompleto.trim(),
        correo_electronico: correoReg.trim(),
        contrasena: contrasenaReg,
        telefono: telefono.trim() || null,
      });
    } catch (err) {
      setError(err.message || 'No se pudo completar el registro');
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '12px 14px',
    borderRadius: '10px',
    background: 'rgba(15, 23, 42, 0.7)',
    border: '1px solid rgba(0, 180, 216, 0.3)',
    color: '#F1F5F9',
    outline: 'none',
    fontSize: '0.95rem',
  };

  const labelStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '0.85rem',
    color: '#94A3B8',
    marginBottom: '6px',
    fontWeight: 600,
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
      background: 'radial-gradient(circle at 50% 0%, rgba(0,180,216,0.12) 0%, transparent 60%)',
    }}>
      <div className="glass-card" style={{ width: '100%', maxWidth: '460px', padding: '36px' }}>
        {onBack && (
          <button
            onClick={onBack}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px', background: 'transparent',
              border: 'none', color: '#94A3B8', cursor: 'pointer', fontSize: '0.85rem',
              marginBottom: '18px', padding: 0,
            }}
          >
            <ArrowLeft size={16} /> Volver a Atención Ciudadana
          </button>
        )}

        <div style={{ textAlign: 'center', marginBottom: '26px' }}>
          <span className="badge badge-blue" style={{ marginBottom: '10px', display: 'inline-flex' }}>
            SMA Congreso
          </span>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#FFFFFF', margin: '10px 0 4px', fontFamily: 'Outfit, sans-serif' }}>
            {modo === 'login' ? 'Iniciar Sesión' : 'Crear Cuenta de Ciudadano'}
          </h1>
          <p style={{ color: '#94A3B8', fontSize: '0.88rem', margin: 0 }}>
            {modo === 'login'
              ? 'Accede con tu correo institucional o de ciudadano.'
              : 'El registro público crea una cuenta con rol Ciudadano.'}
          </p>
        </div>

        {/* Tabs Login / Registro */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', borderBottom: '1px solid rgba(0,180,216,0.2)', paddingBottom: '14px' }}>
          <button
            onClick={() => { setModo('login'); setError(''); }}
            className={modo === 'login' ? 'btn-primary' : 'btn-secondary'}
            style={{ flex: 1, justifyContent: 'center' }}
          >
            <LogIn size={16} /> <span>Ingresar</span>
          </button>
          <button
            onClick={() => { setModo('registro'); setError(''); }}
            className={modo === 'registro' ? 'btn-primary' : 'btn-secondary'}
            style={{ flex: 1, justifyContent: 'center' }}
          >
            <UserPlus size={16} /> <span>Soy Ciudadano, registrarme</span>
          </button>
        </div>

        {error && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            background: 'rgba(244,162,97,0.15)', border: '1px solid rgba(244,162,97,0.4)',
            borderRadius: '10px', padding: '10px 14px', marginBottom: '18px',
            color: '#F4A261', fontSize: '0.85rem',
          }}>
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
        )}

        {modo === 'login' ? (
          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}><Mail size={14} /> Correo electrónico</label>
              <input type="email" required value={correo} onChange={(e) => setCorreo(e.target.value)} style={inputStyle} placeholder="tu_correo@dominio.gob" />
            </div>
            <div style={{ marginBottom: '22px' }}>
              <label style={labelStyle}><Lock size={14} /> Contraseña</label>
              <input type="password" required value={contrasena} onChange={(e) => setContrasena(e.target.value)} style={inputStyle} placeholder="••••••••" />
            </div>
            <button type="submit" disabled={isSubmitting} className="btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
              {isSubmitting ? 'Ingresando...' : 'Iniciar Sesión'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegistro}>
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}><User size={14} /> Nombre completo</label>
              <input type="text" required value={nombreCompleto} onChange={(e) => setNombreCompleto(e.target.value)} style={inputStyle} placeholder="Ej: Juan Pérez" />
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}><Mail size={14} /> Correo electrónico</label>
              <input type="email" required value={correoReg} onChange={(e) => setCorreoReg(e.target.value)} style={inputStyle} placeholder="tu_correo@gmail.com" />
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}><Phone size={14} /> Teléfono (opcional)</label>
              <input type="text" value={telefono} onChange={(e) => setTelefono(e.target.value)} style={inputStyle} placeholder="758946" />
            </div>
            <div style={{ marginBottom: '22px' }}>
              <label style={labelStyle}><Lock size={14} /> Contraseña</label>
              <input type="password" required value={contrasenaReg} onChange={(e) => setContrasenaReg(e.target.value)} style={inputStyle} placeholder="••••••••" />
            </div>
            <button type="submit" disabled={isSubmitting} className="btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
              {isSubmitting ? 'Creando cuenta...' : 'Crear cuenta de Ciudadano'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
