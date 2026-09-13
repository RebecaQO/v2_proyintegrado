import React from 'react';
import { 
  Building2, 
  FileText, 
  FolderArchive, 
  Scale, 
  Users, 
  Activity, 
  Database,
  CheckCircle2,
  AlertTriangle,
  Mic
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, healthStatus }) {
  const isHealthy = healthStatus?.status === 'healthy';

  const navItems = [
    { id: 'mesa', label: 'Mesa de Partes', icon: FileText },
    { id: 'expedientes', label: 'Expedientes y Auditoría', icon: FolderArchive },
    { id: 'consistencia', label: 'Consistencia Normativa', icon: Scale },
    { id: 'ciudadana', label: 'Atención Ciudadana', icon: Users },
    { id: 'voz', label: 'Asistente de Voz', icon: Mic },
    { id: 'monitoreo', label: 'Monitoreo y Agentes', icon: Activity },
  ];

  return (
    <header style={{
      position: 'sticky',
      top: 0,
      zIndex: 50,
      background: 'linear-gradient(180deg, #09111e 0%, #0d1728 100%)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
      boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
      padding: '0 24px',
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
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #10b981 0%, #047857 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(16, 185, 129, 0.4)',
            border: '1px solid rgba(255, 255, 255, 0.2)'
          }}>
            <Building2 size={24} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontFamily: 'Outfit', fontWeight: 800, fontSize: '1.25rem', color: '#ffffff', letterSpacing: '-0.01em' }}>
                SMA CONGRESO
              </span>
              <span className="badge badge-gold" style={{ fontSize: '0.68rem', padding: '2px 8px' }}>
                v2.0 FastAPI + React
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: '#6ee7b7', fontWeight: 500 }}>
              Sistema Multi-Agente de Registro y Auditoría Legislativa
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
                  gap: '8px',
                  padding: '9px 16px',
                  borderRadius: '10px',
                  border: isActive ? '1px solid rgba(52, 211, 153, 0.5)' : '1px solid transparent',
                  background: isActive ? 'rgba(16, 185, 129, 0.18)' : 'transparent',
                  color: isActive ? '#34d399' : '#a7f3d0',
                  fontFamily: 'Outfit',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) e.currentTarget.style.background = 'rgba(16, 185, 129, 0.08)';
                }}
                onMouseLeave={(e) => {
                  if (!isActive) e.currentTarget.style.background = 'transparent';
                }}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Health & DB Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(6, 40, 32, 0.6)',
            padding: '6px 12px',
            borderRadius: '9999px',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            fontSize: '0.8rem',
          }}>
            <Database size={14} color="#34d399" />
            <span style={{ color: '#a7f3d0', fontSize: '0.78rem' }}>Mongo + Neon</span>
            {isHealthy ? (
              <CheckCircle2 size={15} color="#34d399" />
            ) : (
              <AlertTriangle size={15} color="#f59e0b" />
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
