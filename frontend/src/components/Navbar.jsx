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
  Mic,
  ShieldCheck,
  LogOut,
  UserCircle2
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, healthStatus, user, onLogout, simplified = false }) {
  const isHealthy = healthStatus?.status === 'healthy';

  const navItems = [
    { id: 'mesa', label: 'Mesa de Partes', icon: FileText },
    { id: 'ejecutivo', label: 'Despacho Ejecutivo', icon: Building2 },
    { id: 'expedientes', label: 'Expedientes y Auditoría', icon: FolderArchive },
    { id: 'consistencia', label: 'Consistencia Normativa', icon: Scale },
    { id: 'ciudadana', label: 'Atención Ciudadana', icon: Users },
    { id: 'voz', label: 'Asistente de Voz', icon: Mic },
    { id: 'monitoreo', label: 'Monitoreo y Agentes', icon: Activity },
  ];

  return (
    <header className="navbar-header" style={{
      position: 'sticky',
      top: 0,
      zIndex: 50,
      background: simplified ? 'linear-gradient(115deg, #123b60 0%, #245a84 100%)' : 'linear-gradient(180deg, #ffffff 0%, #f3f8fc 100%)',
      backdropFilter: 'blur(16px)',
      borderBottom: simplified ? '1px solid #0d3152' : '1px solid #d5e3ed',
      boxShadow: simplified ? '0 5px 18px rgba(18,59,96,.22)' : '0 4px 20px rgba(24, 58, 86, 0.08)',
      padding: '0 clamp(10px, 2vw, 24px)',
    }}>
      <div style={{
        maxWidth: '1720px',
        width: '96%',
        margin: '0 auto',
        minHeight: simplified ? '76px' : '68px',
        gap: 'clamp(8px, 1.5vw, 18px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        {/* Brand & Emblem */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', cursor: simplified ? 'default' : 'pointer' }} onClick={() => !simplified && setActiveTab('mesa')}>
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
                <span style={{ fontFamily: 'Outfit', fontWeight: 800, fontSize: '1.22rem', color: simplified ? '#ffffff' : '#123b60', letterSpacing: '-0.01em' }}>
                SMA CONGRESO
              </span>
              <span style={{
                fontSize: '0.66rem', fontWeight: 700, padding: '2px 8px', borderRadius: '5px',
                background: simplified ? 'rgba(255,255,255,.14)' : '#e4f3fb', border: simplified ? '1px solid rgba(255,255,255,.25)' : '1px solid #b7d9eb',
                color: simplified ? '#e5f4ff' : '#087db8', letterSpacing: '0.04em'
              }}>
                v2.0
              </span>
            </div>
            <span className="navbar-brand-subtitle" style={{ fontSize: '0.73rem', color: simplified ? '#d2e6f3' : '#627d92', fontWeight: 500 }}>
              Sistema Multi-Agente de Registro y Auditoria Legislativa
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="navbar-nav-strip" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {!simplified && navItems.map((item) => {
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
                  border: isActive ? '1px solid #acd2e7' : '1px solid transparent',
                  background: isActive ? '#eaf5fb' : 'transparent',
                  color: isActive ? '#126596' : '#58758b',
                  fontFamily: 'Outfit',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: '0.88rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  whiteSpace: 'nowrap'
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = '#f0f7fb';
                    e.currentTarget.style.color = '#244863';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = '#58758b';
                  }
                }}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Estado del sistema + Usuario */}
        <div className="navbar-user-actions" style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '7px',
            background: simplified ? 'rgba(255,255,255,.12)' : 'rgba(11, 37, 69, 0.7)',
            padding: '6px 14px', borderRadius: '9999px',
            border: isHealthy ? '1px solid rgba(16,185,129,.45)' : '1px solid rgba(244, 162, 97, 0.3)',
            fontSize: '0.78rem',
          }}>
            <ShieldCheck size={14} color={isHealthy ? '#6ee7b7' : '#F4A261'} />
            <span className="navbar-status-label" style={{ color: '#e2edf5', fontWeight: 600 }}>Sistema</span>
            {isHealthy ? (
              <CheckCircle2 size={14} color="#6ee7b7" />
            ) : (
              <AlertTriangle size={14} color="#F4A261" />
            )}
            <span style={{ color: isHealthy ? '#a7f3d0' : '#ffd2a8', fontWeight: 800, fontSize: '0.75rem' }}>
              {isHealthy ? 'Operativo' : 'Verificando'}
            </span>
          </div>

          {user && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              background: 'rgba(11, 37, 69, 0.7)',
              padding: '6px 8px 6px 14px', borderRadius: '9999px',
              border: '1px solid rgba(0, 180, 216, 0.25)',
              fontSize: '0.78rem',
            }}>
              <UserCircle2 size={16} color="#00B4D8" />
              <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.1 }}>
                <span style={{ color: '#F1F5F9', fontWeight: 700, fontSize: '0.78rem' }}>{user.nombre_completo}</span>
                <span style={{ color: '#00B4D8', fontWeight: 600, fontSize: '0.68rem' }}>{user.rol}</span>
              </div>
              <button
                onClick={onLogout}
                title="Cerrar sesión"
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  width: '28px', height: '28px', borderRadius: '50%',
                  background: 'rgba(231, 111, 81, 0.15)', border: '1px solid rgba(231, 111, 81, 0.35)',
                  color: '#E76F51', cursor: 'pointer',
                }}
              >
                <LogOut size={14} />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
