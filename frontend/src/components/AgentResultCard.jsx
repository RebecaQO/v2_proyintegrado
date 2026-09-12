import React from 'react';
import { 
  Sparkles, 
  Cpu, 
  CheckCircle2, 
  AlertCircle, 
  ShieldCheck, 
  Target, 
  Zap,
  Eye
} from 'lucide-react';
import CssRobotAvatar from './CssRobotAvatar';

/**
 * AgentResultCard — Tarjeta de resultado con Robot Visual y Dictamen Estructurado
 */
export default function AgentResultCard({
  agentName = 'Agente Inteligente',
  role = 'Procesamiento de Datos',
  theme = 'green',
  status = 'completed',
  thinkingText = 'Resultado de procesamiento',
  model = '',
  phaseLabel = '',
  children,
  badgeText = '',
  image = '',
  justificacion = '',
  garantiaEtica = '',
  onViewPrev = null,   // callback → muestra resultado previo del agente
  prevLabel = 'Ver Ejecución Anterior',
}) {
  const themeStyles = {
    cyan: {
      border: 'rgba(0, 180, 216, 0.45)',
      bg: 'linear-gradient(135deg, rgba(11, 37, 69, 0.95) 0%, rgba(19, 64, 116, 0.85) 100%)',
      titleColor: '#00B4D8',
      glow: '0 12px 35px rgba(0, 180, 216, 0.25)',
      badgeClass: 'badge-blue',
      accent: '#00B4D8',
      glowShadow: '0 0 25px rgba(0, 180, 216, 0.5)'
    },
    blue: {
      border: 'rgba(2, 132, 199, 0.45)',
      bg: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.9) 100%)',
      titleColor: '#38BDF8',
      glow: '0 12px 35px rgba(2, 132, 199, 0.25)',
      badgeClass: 'badge-blue',
      accent: '#0284C7',
      glowShadow: '0 0 25px rgba(2, 132, 199, 0.5)'
    },
    green: {
      border: 'rgba(138, 201, 38, 0.45)',
      bg: 'linear-gradient(135deg, rgba(11, 37, 69, 0.95) 0%, rgba(15, 23, 42, 0.9) 100%)',
      titleColor: '#8AC926',
      glow: '0 12px 35px rgba(138, 201, 38, 0.25)',
      badgeClass: 'badge-green',
      accent: '#8AC926',
      glowShadow: '0 0 25px rgba(138, 201, 38, 0.5)'
    },
    gold: {
      border: 'rgba(244, 162, 97, 0.45)',
      bg: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.9) 100%)',
      titleColor: '#F4A261',
      glow: '0 12px 35px rgba(244, 162, 97, 0.25)',
      badgeClass: 'badge-gold',
      accent: '#F4A261',
      glowShadow: '0 0 25px rgba(244, 162, 97, 0.5)'
    },
    pink: {
      border: 'rgba(231, 111, 81, 0.45)',
      bg: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.9) 100%)',
      titleColor: '#E76F51',
      glow: '0 12px 35px rgba(231, 111, 81, 0.25)',
      badgeClass: 'badge-red',
      accent: '#E76F51',
      glowShadow: '0 0 25px rgba(231, 111, 81, 0.5)'
    },
    violet: {
      border: 'rgba(168, 85, 247, 0.45)',
      bg: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.9) 100%)',
      titleColor: '#a78bfa',
      glow: '0 12px 35px rgba(168, 85, 247, 0.25)',
      badgeClass: 'badge-violet',
      accent: '#a855f7',
      glowShadow: '0 0 25px rgba(168, 85, 247, 0.5)'
    },
    purple: {
      border: 'rgba(168, 85, 247, 0.45)',
      bg: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.9) 100%)',
      titleColor: '#c084fc',
      glow: '0 12px 35px rgba(168, 85, 247, 0.25)',
      badgeClass: 'badge-violet',
      accent: '#a855f7',
      glowShadow: '0 0 25px rgba(168, 85, 247, 0.5)'
    },
    emerald: {
      border: 'rgba(138, 201, 38, 0.45)',
      bg: 'linear-gradient(135deg, rgba(11, 37, 69, 0.95) 0%, rgba(15, 23, 42, 0.9) 100%)',
      titleColor: '#8AC926',
      glow: '0 12px 35px rgba(138, 201, 38, 0.25)',
      badgeClass: 'badge-green',
      accent: '#8AC926',
      glowShadow: '0 0 25px rgba(138, 201, 38, 0.5)'
    },
    amber: {
      border: 'rgba(244, 162, 97, 0.45)',
      bg: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.9) 100%)',
      titleColor: '#F4A261',
      glow: '0 12px 35px rgba(244, 162, 97, 0.25)',
      badgeClass: 'badge-gold',
      accent: '#F4A261',
      glowShadow: '0 0 25px rgba(244, 162, 97, 0.5)'
    },
    sky: {
      border: 'rgba(0, 180, 216, 0.45)',
      bg: 'linear-gradient(135deg, rgba(11, 37, 69, 0.95) 0%, rgba(19, 64, 116, 0.85) 100%)',
      titleColor: '#00B4D8',
      glow: '0 12px 35px rgba(0, 180, 216, 0.25)',
      badgeClass: 'badge-blue',
      accent: '#00B4D8',
      glowShadow: '0 0 25px rgba(0, 180, 216, 0.5)'
    },
    rose: {
      border: 'rgba(231, 111, 81, 0.45)',
      bg: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.9) 100%)',
      titleColor: '#E76F51',
      glow: '0 12px 35px rgba(231, 111, 81, 0.25)',
      badgeClass: 'badge-red',
      accent: '#E76F51',
      glowShadow: '0 0 25px rgba(231, 111, 81, 0.5)'
    },
    indigo: {
      border: 'rgba(2, 132, 199, 0.45)',
      bg: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.9) 100%)',
      titleColor: '#38BDF8',
      glow: '0 12px 35px rgba(2, 132, 199, 0.25)',
      badgeClass: 'badge-blue',
      accent: '#0284C7',
      glowShadow: '0 0 25px rgba(2, 132, 199, 0.5)'
    }
  };

  const ts = themeStyles[theme] || themeStyles.green;
  const isWorking = status === 'thinking' || status === 'working';
  const isDone = status === 'completed';

  return (
    <div style={{
      borderRadius: '24px',
      border: `2px solid ${ts.border}`,
      background: ts.bg,
      boxShadow: ts.glow,
      padding: '24px',
      marginBottom: '32px',
      transition: 'all 0.3s ease',
      backdropFilter: 'blur(16px)',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Background ambient lighting */}
      <div style={{
        position: 'absolute',
        top: '-80px',
        left: '-80px',
        width: '260px',
        height: '260px',
        borderRadius: '50%',
        background: ts.accent,
        filter: 'blur(100px)',
        opacity: 0.25,
        pointerEvents: 'none',
        zIndex: 0
      }} />

      {/* Main Split Layout: Lateral Robot Panel + Content Body */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(240px, 280px) 1fr',
        gap: '24px',
        position: 'relative',
        zIndex: 1,
        alignItems: 'start'
      }} className="agent-result-grid">

        {/* ── COLUMNA LATERAL: ROBOT DE GRAN IMPACTO VISUAL ── */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.7)',
          border: `1.5px solid ${ts.border}`,
          borderRadius: '20px',
          padding: '18px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4)',
          position: 'sticky',
          top: '20px'
        }}>
          {/* Header Tag / Phase */}
          <div style={{ display: 'flex', gap: '6px', marginBottom: '14px', flexWrap: 'wrap', justifyContent: 'center' }}>
            {phaseLabel && <span className={`badge ${ts.badgeClass}`} style={{ fontSize: '0.72rem' }}>{phaseLabel}</span>}
            {badgeText && <span className="badge badge-gold" style={{ fontSize: '0.72rem' }}>{badgeText}</span>}
          </div>

          {/* Imagen de Alto Impacto con marco brillante */}
          <div style={{
            position: 'relative',
            width: '100%',
            height: '230px',
            borderRadius: '16px',
            overflow: 'hidden',
            marginBottom: '16px',
            border: `2px solid ${ts.accent}`,
            boxShadow: isWorking ? ts.glowShadow : '0 10px 25px rgba(0,0,0,0.5)'
          }}>
            {image ? (
              <img
                src={image}
                alt={agentName}
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  filter: isWorking ? 'brightness(1.1) contrast(1.05)' : 'none',
                  transition: 'all 0.5s ease'
                }}
              />
            ) : (
              <div style={{
                width: '100%',
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'rgba(30, 41, 59, 0.8)'
              }}>
                <CssRobotAvatar
                  theme={theme}
                  status={status}
                  size="lg"
                  showBubble={isWorking}
                  thinkingText={thinkingText}
                />
              </div>
            )}

            {/* Checkmark overlay badge if completed */}
            {isDone && (
              <div style={{
                position: 'absolute',
                top: '10px',
                right: '10px',
                background: '#10b981',
                color: '#ffffff',
                borderRadius: '50%',
                width: '32px',
                height: '32px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 15px #10b981',
                border: '2px solid #ffffff'
              }}>
                <CheckCircle2 size={20} />
              </div>
            )}

            {/* Active processing pulse overlay */}
            {isWorking && (
              <div style={{
                position: 'absolute',
                bottom: '10px',
                left: '10px',
                right: '10px',
                background: 'rgba(0, 0, 0, 0.75)',
                backdropFilter: 'blur(6px)',
                borderRadius: '10px',
                padding: '6px 10px',
                color: '#fbbf24',
                fontSize: '0.75rem',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                justifyContent: 'center'
              }}>
                <Sparkles size={14} className="animate-spin" />
                <span>Analizando en Vivo...</span>
              </div>
            )}
          </div>

          {/* Nombre y Rol */}
          <h3 style={{
            fontSize: '1.25rem',
            fontWeight: 800,
            color: '#ffffff',
            letterSpacing: '-0.01em',
            margin: '0 0 4px 0',
            lineHeight: 1.2
          }}>
            {agentName}
          </h3>
          <div style={{
            fontSize: '0.82rem',
            color: ts.titleColor,
            fontWeight: 700,
            marginBottom: '12px'
          }}>
            {role}
          </div>

          {/* Status Badge con Check Prominente — paleta institucional */}
          <div style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            background: isWorking ? 'rgba(244, 162, 97, 0.2)' : 'rgba(138, 201, 38, 0.15)',
            border: `1.5px solid ${isWorking ? '#F4A261' : '#8AC926'}`,
            borderRadius: '12px',
            padding: '8px 12px',
            fontSize: '0.82rem',
            fontWeight: 800,
            color: isWorking ? '#F4A261' : '#8AC926',
            marginBottom: '16px',
            boxShadow: isDone ? '0 0 15px rgba(138,201,38,0.3)' : 'none'
          }}>
            {isWorking ? (
              <>
                <Zap size={16} className="animate-pulse" />
                <span>Procesando...</span>
              </>
            ) : (
              <>
                <CheckCircle2 size={18} color="#8AC926" />
                <span>Fase Ejecutada</span>
              </>
            )}
          </div>

          {/* Boton: Ver Ejecucion Anterior (siempre visible si hay callback configurado) */}
          {onViewPrev && (
            <button
              onClick={onViewPrev}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                padding: '8px 12px',
                borderRadius: '10px',
                background: 'rgba(0,180,216,0.12)',
                border: '1px solid rgba(0,180,216,0.5)',
                color: '#38BDF8',
                fontSize: '0.78rem',
                fontWeight: 700,
                cursor: 'pointer',
                marginBottom: '12px',
                transition: 'all 0.2s',
                fontFamily: 'Outfit, sans-serif',
                letterSpacing: '0.02em',
                boxShadow: '0 2px 8px rgba(0,180,216,0.15)'
              }}
              onMouseEnter={e => { e.currentTarget.style.background='rgba(0,180,216,0.25)'; e.currentTarget.style.borderColor='#00B4D8'; e.currentTarget.style.color='#FFFFFF'; }}
              onMouseLeave={e => { e.currentTarget.style.background='rgba(0,180,216,0.12)'; e.currentTarget.style.borderColor='rgba(0,180,216,0.5)'; e.currentTarget.style.color='#38BDF8'; }}
              title="Volver a visualizar los resultados de la ejecución"
            >
              <Eye size={14} />
              <span>{prevLabel}</span>
            </button>
          )}

          {/* ¿Por qué se realiza este paso? */}
          {justificacion && (
            <div style={{
              width: '100%',
              background: 'rgba(30, 41, 59, 0.85)',
              borderLeft: `4px solid ${ts.accent}`,
              borderRadius: '8px',
              padding: '10px 12px',
              textAlign: 'left',
              fontSize: '0.78rem',
              color: '#e2e8f0',
              lineHeight: 1.45,
              marginBottom: '12px'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontWeight: 700,
                color: ts.titleColor,
                marginBottom: '4px',
                fontSize: '0.76rem',
                textTransform: 'uppercase',
                letterSpacing: '0.04em'
              }}>
                <Target size={13} />
                <span>¿Por qué se realiza?</span>
              </div>
              <div>{justificacion}</div>
            </div>
          )}

        </div>

        {/* ── COLUMNA DERECHA: RESULTADOS Y DICTAMEN ESTRUCTURADO ── */}
        <div style={{ minWidth: 0 }}>
          {children}
        </div>

      </div>
    </div>
  );
}
