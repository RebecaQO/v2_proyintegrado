import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import MesaPartes from './pages/MesaPartes';
import Expedientes from './pages/Expedientes';
import ConsistenciaNormativa from './pages/ConsistenciaNormativa';
import AtencionCiudadana from './pages/AtencionCiudadana';
import Monitoreo from './pages/Monitoreo';
import VoiceAssistantPage from './pages/VoiceAssistantPage';
import { api } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('mesa');
  const [healthStatus, setHealthStatus] = useState(null);

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

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        healthStatus={healthStatus}
      />

      <main style={{ flex: 1 }}>
        {activeTab === 'mesa' && <MesaPartes onNavigateExpedientes={() => setActiveTab('expedientes')} />}
        {activeTab === 'expedientes' && <Expedientes />}
        {activeTab === 'consistencia' && <ConsistenciaNormativa />}
        {activeTab === 'ciudadana' && <AtencionCiudadana />}
        {activeTab === 'voz' && <VoiceAssistantPage onNavigateTab={setActiveTab} />}
        {activeTab === 'monitoreo' && <Monitoreo />}
      </main>

      {/* Footer */}
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
    </div>
  );
}
