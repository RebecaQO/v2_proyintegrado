import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);

const STORAGE_KEY = 'sma_congreso_usuario';

// Roles que tienen acceso al panel interno completo (Mesa de Partes, Expedientes,
// Consistencia Normativa, Monitoreo). Todo lo que no sea 'Ciudadano' se trata
// como rol interno.
export function esRolInterno(rol) {
  return !!rol && rol !== 'Ciudadano';
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setUser(JSON.parse(raw));
    } catch (err) {
      console.error('Error leyendo sesión guardada:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const login = async (correo_electronico, contrasena) => {
    const res = await api.login(correo_electronico, contrasena);
    const usuario = res.data;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(usuario));
    setUser(usuario);
    return usuario;
  };

  const register = async (data) => {
    const res = await api.register(data);
    const usuario = res.data;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(usuario));
    setUser(usuario);
    return usuario;
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>');
  return ctx;
}
