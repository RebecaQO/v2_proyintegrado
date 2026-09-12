import React from 'react';
import { 
  Building2, 
  FileText, 
  FolderArchive, 
  Scale, 
  Users, 
  Activity, 
  CheckCircle2,
  AlertTriangle,
  ShieldCheck
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, healthStatus }) {
  const isHealthy = healthStatus?.status === 'healthy';

  const navItems = [
    { id: 'mesa',        label: 'Mesa de Partes',          icon: FileText },
    { id: 'expedientes', label: 'Expedientes y Auditoria', icon: FolderArchive },
    { id: 'consistencia',label: 'Consistencia Normativa',  icon: Scale },
    { id: 'ciudadana',   label: 'Atencion Ciudadana',      icon: Users },
    { id: 'monitoreo',   label: 'Monitoreo de Agentes',    icon: Activity },
  ];

  return (
    <header style={{
      position: 'sticky',
      top: 0,
      zIndex: 50,
      background: 'linear-gradient(180deg, #071a35 0%, #0B2545 100%)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid rgba(0, 180, 216, 0.15)',
      boxShadow: '0 4px 24px rgba(0, 0, 0, 0.35)',
      padding: '0 28px',
    }}>
      <div style={{
        maxWidth: '1440px',
        margin: '0 auto',
        height: '72px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        {/* Brand & Emblem */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', cursor: 'pointer' }} onClick={() => setActiveTab('mesa')}>
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #0284C7 0%, #00B4D8 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 16px rgba(0, 180, 216, 0.4)',
            border: '1px solid rgba(255, 255, 255, 0.15)'
          }}>
            <Building2 size={24} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontFamily: 'Outfit', fontWeight: 800, fontSize: '1.22rem', color: '#ffffff', letterSpacing: '-0.01em' }}>
                SMA CONGRESO
              </span>
              <span style={{
                fontSize: '0.66rem', fontWeight: 700, padding: '2px 8px', borderRadius: '5px',
                background: 'rgba(0, 180, 216, 0.18)', border: '1px solid rgba(0, 180, 216, 0.35)',
                color: '#00B4D8', letterSpacing: '0.04em'
              }}>
                v2.0
              </span>
            </div>
            <span style={{ fontSize: '0.73rem', color: '#94A3B8', fontWeight: 500 }}>
              Sistema Multi-Agente de Registro y Auditoria Legislativa
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '7px',
                  padding: '8px 14px',
                  borderRadius: '10px',
                  border: isActive ? '1px solid rgba(0, 180, 216, 0.5)' : '1px solid transparent',
                  background: isActive ? 'rgba(0, 180, 216, 0.14)' : 'transparent',
                  color: isActive ? '#00B4D8' : '#94A3B8',
                  fontFamily: 'Outfit',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: '0.88rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  whiteSpace: 'nowrap'
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'rgba(0, 180, 216, 0.07)';
                    e.currentTarget.style.color = '#CBD5E1';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = '#94A3B8';
                  }
                }}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Estado del sistema */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '7px',
            background: 'rgba(11, 37, 69, 0.7)',
            padding: '6px 14px', borderRadius: '9999px',
            border: isHealthy ? '1px solid rgba(138, 201, 38, 0.3)' : '1px solid rgba(244, 162, 97, 0.3)',
            fontSize: '0.78rem',
          }}>
            <ShieldCheck size={14} color={isHealthy ? '#8AC926' : '#F4A261'} />
            <span style={{ color: '#94A3B8', fontWeight: 500 }}>Sistema</span>
            {isHealthy ? (
              <CheckCircle2 size={14} color="#8AC926" />
            ) : (
              <AlertTriangle size={14} color="#F4A261" />
            )}
            <span style={{ color: isHealthy ? '#8AC926' : '#F4A261', fontWeight: 700, fontSize: '0.75rem' }}>
              {isHealthy ? 'Operativo' : 'Verificando'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
