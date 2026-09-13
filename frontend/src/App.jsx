import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import MesaPartes from './pages/MesaPartes';
import Expedientes from './pages/Expedientes';
import ConsistenciaNormativa from './pages/ConsistenciaNormativa';
import AtencionCiudadana from './pages/AtencionCiudadana';
import Monitoreo from './pages/Monitoreo';
import Login from './pages/Login';
import VoiceAssistantPage from './pages/VoiceAssistantPage';
import { api } from './services/api';
import { useAuth, esRolInterno } from './context/AuthContext';

const FOOTER = (
  <footer style={{
    background: '#ffffff',
    borderTop: '1px solid #e2e8f0',
    padding: '24px',
    textAlign: 'center',
    color: '#475569',
    fontSize: '0.85rem',
  }}>
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
      <div>
        <strong style={{ color: '#0f172a' }}>SMA Congreso</strong> — Sistema Multi-Agente de Registro, Clasificación y Auditoría Parlamentaria
      </div>
      <div style={{ display: 'flex', gap: '16px', fontSize: '0.78rem', color: '#64748b' }}>
        <span>FastAPI 0.110+</span>
        <span>•</span>
        <span>React + Vite</span>
        <span>•</span>
        <span>PostgreSQL Neon (pgvector)</span>
        <span>•</span>
        <span>MongoDB Atlas</span>
        <span>•</span>
        <span>NVIDIA NIM</span>
      </div>
    </div>
  </footer>
);

export default function App() {
  const { user, loading, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('mesa');
  const [healthStatus, setHealthStatus] = useState(null);
  const [mostrarLogin, setMostrarLogin] = useState(false);

  useEffect(() => {
    // Comprobar salud del backend periódicamente
    const checkHealth = async () => {
      try {
        const res = await api.getHealth();
        setHealthStatus(res);
      } catch (err) {
        setHealthStatus({ status: 'offline' });
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  // Al iniciar sesión exitosamente, cerrar la pantalla de login
  useEffect(() => {
    if (user) setMostrarLogin(false);
  }, [user]);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0B2545', color: '#94A3B8' }}>
        Cargando sesión...
      </div>
    );
  }

  // ── Sin sesión: vista ciudadana pública (por defecto), meramente informativa ──
  if (!user) {
    if (mostrarLogin) {
      return <Login onBack={() => setMostrarLogin(false)} />;
    }
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar
          activeTab="ciudadana"
          setActiveTab={() => { }}
          healthStatus={healthStatus}
          user={null}
          onLogout={null}
          simplified={true}
        />
        <main style={{ flex: 1 }}>
          <AtencionCiudadana isAuthenticated={false} onNavigateLogin={() => setMostrarLogin(true)} />
        </main>
        {FOOTER}
      </div>
    );
  }

  // ── Sesión Ciudadano: solo su vista interactiva (subir archivos, agente) ──
  if (!esRolInterno(user.rol)) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar
          activeTab="ciudadana"
          setActiveTab={() => { }}
          healthStatus={healthStatus}
          user={user}
          onLogout={logout}
          simplified={true}
        />
        <main style={{ flex: 1 }}>
          <AtencionCiudadana isAuthenticated={true} currentUser={user} />
        </main>
        {FOOTER}
      </div>
    );
  }

  // ── Roles internos (Senador, Diputado, Operador_Mesa_Partes, etc.): panel completo ──
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        healthStatus={healthStatus}
        user={user}
        onLogout={logout}
      />

      <main style={{ flex: 1 }}>
        {activeTab === 'mesa' && <MesaPartes onNavigateExpedientes={() => setActiveTab('expedientes')} currentUser={user} />}
        {activeTab === 'expedientes' && <Expedientes />}
        {activeTab === 'consistencia' && <ConsistenciaNormativa />}
        {activeTab === 'ciudadana' && <AtencionCiudadana isAuthenticated={true} currentUser={user} />}
        {activeTab === 'voz' && <VoiceAssistantPage onNavigateTab={setActiveTab} />}
        {activeTab === 'monitoreo' && <Monitoreo />}
      </main>

      {FOOTER}
    </div>
  );
}