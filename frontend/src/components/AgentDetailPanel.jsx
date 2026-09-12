/**
 * AgentDetailPanel — Panel lateral deslizante de detalles del agente
 * Se abre desde la derecha cuando el usuario hace clic en un nodo circular.
 * Muestra: logo + banner, nombre, estado, descripción, webhook/logs, resultado.
 */
import React, { useEffect, useRef } from 'react';
import {
  X,
  CheckCircle2,
  Clock,
  AlertCircle,
  Zap,
  Target,
  ShieldCheck,
  Cpu,
  ChevronRight,
  Activity,
  Database,
  BookOpen,
} from 'lucide-react';

// Mapeo de logos y banners institucionales
const AGENT_LOGO_MAP = {
  distribuidor:       '/robots/logos/distribuidor.jpg',
  comision:           '/robots/logos/verificadorconstitucional.jpg',
  constitucional:     '/robots/logos/verificadorconstitucional.jpg',
  consistencia:       '/robots/logos/consistencianormativa.jpg',
  emisor:             '/robots/logos/distribuidor.jpg',
  notificador:        '/robots/logos/consistencianormativa.jpg',
  constitucion_fondo: '/robots/logos/verificadorconstitucional.jpg',
  concentrador_crew:  '/robots/logos/distribuidor.jpg',
  secretario:         '/robots/logos/verificadorconstitucional.jpg',
  bicameral:          '/robots/logos/consistencianormativa.jpg',
  veto_promulgacion:  '/robots/logos/distribuidor.jpg',
  publicacion:        '/robots/logos/verificadorconstitucional.jpg',
};

const AGENT_BANNER_MAP = {
  distribuidor:       '/robots/banner/disribuidor.png',
  comision:           '/robots/banner/normativa.png',
  constitucional:     '/robots/banner/normativa.png',
  consistencia:       '/robots/banner/consistencia.png',
  emisor:             '/robots/banner/emisor.png',
  notificador:        '/robots/banner/emisor.png',
  constitucion_fondo: '/robots/banner/normativa.png',
  concentrador_crew:  '/robots/banner/emisor.png',
  secretario:         '/robots/banner/normativa.png',
  bicameral:          '/robots/banner/normativa.png',
  veto_promulgacion:  '/robots/banner/normativa.png',
  publicacion:        '/robots/banner/emisor.png',
};

// Color institucional por agente (Opción 6 — Tono Ejecutivo Moderno)
const AGENT_THEME_COLORS = {
  distribuidor:       { primary: '#00B4D8', glow: 'rgba(0, 180, 216, 0.4)',   bg: 'rgba(0, 180, 216, 0.08)' },
  comision:           { primary: '#38BDF8', glow: 'rgba(56, 189, 248, 0.4)',  bg: 'rgba(56, 189, 248, 0.08)' },
  constitucional:     { primary: '#8AC926', glow: 'rgba(138, 201, 38, 0.4)',  bg: 'rgba(138, 201, 38, 0.08)' },
  consistencia:       { primary: '#F4A261', glow: 'rgba(244, 162, 97, 0.4)',  bg: 'rgba(244, 162, 97, 0.08)' },
  emisor:             { primary: '#A78BFA', glow: 'rgba(167, 139, 250, 0.4)', bg: 'rgba(167, 139, 250, 0.08)' },
  notificador:        { primary: '#38BDF8', glow: 'rgba(56, 189, 248, 0.4)',  bg: 'rgba(56, 189, 248, 0.08)' },
  constitucion_fondo: { primary: '#8AC926', glow: 'rgba(138, 201, 38, 0.4)',  bg: 'rgba(138, 201, 38, 0.08)' },
  concentrador_crew:  { primary: '#00B4D8', glow: 'rgba(0, 180, 216, 0.4)',   bg: 'rgba(0, 180, 216, 0.08)' },
  secretario:         { primary: '#F4A261', glow: 'rgba(244, 162, 97, 0.4)',  bg: 'rgba(244, 162, 97, 0.08)' },
  bicameral:          { primary: '#38BDF8', glow: 'rgba(56, 189, 248, 0.4)',  bg: 'rgba(56, 189, 248, 0.08)' },
  veto_promulgacion:  { primary: '#E76F51', glow: 'rgba(231, 111, 81, 0.4)',  bg: 'rgba(231, 111, 81, 0.08)' },
  publicacion:        { primary: '#8AC926', glow: 'rgba(138, 201, 38, 0.4)',  bg: 'rgba(138, 201, 38, 0.08)' },
};

function StatusBadge({ isActive, isDone, isError }) {
  if (isError) return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '4px 10px',
      borderRadius: '20px', background: 'rgba(231, 111, 81, 0.15)', color: '#E76F51',
      border: '1px solid rgba(231, 111, 81, 0.35)', fontSize: '0.75rem', fontWeight: 700 }}>
      <AlertCircle size={12} /> Error
    </span>
  );
  if (isDone) return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '4px 10px',
      borderRadius: '20px', background: 'rgba(138, 201, 38, 0.15)', color: '#8AC926',
      border: '1px solid rgba(138, 201, 38, 0.35)', fontSize: '0.75rem', fontWeight: 700 }}>
      <CheckCircle2 size={12} /> Completado
    </span>
  );
  if (isActive) return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '4px 10px',
      borderRadius: '20px', background: 'rgba(0, 180, 216, 0.15)', color: '#00B4D8',
      border: '1px solid rgba(0, 180, 216, 0.35)', fontSize: '0.75rem', fontWeight: 700,
      animation: 'pulse-inst 1.8s infinite ease-in-out' }}>
      <Zap size={12} /> En Proceso
    </span>
  );
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '4px 10px',
      borderRadius: '20px', background: 'rgba(100, 116, 139, 0.15)', color: '#64748B',
      border: '1px solid rgba(100, 116, 139, 0.25)', fontSize: '0.75rem', fontWeight: 700 }}>
      <Clock size={12} /> En Espera
    </span>
  );
}

export default function AgentDetailPanel({
  agent,
  pipelineStep = 0,
  resultData = null,
  pipelineLog = [],
  onClose
}) {
  const panelRef = useRef(null);

  // Cerrar con Escape
  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  if (!agent) return null;

  const tc = AGENT_THEME_COLORS[agent.id] || AGENT_THEME_COLORS.distribuidor;
  const logoUrl = AGENT_LOGO_MAP[agent.id];
  const bannerUrl = AGENT_BANNER_MAP[agent.id];

  const isActive = pipelineStep === agent.activeStep;
  const isDone   = pipelineStep >= agent.doneAtStep;
  const agentLogs = pipelineLog.filter(l =>
    l.etapa?.toLowerCase().includes(agent.id?.toLowerCase().replace('_', '')) ||
    l.etapa?.toLowerCase().includes(agent.shortName?.toLowerCase())
  );

  return (
    <>
      {/* Overlay semi-transparente */}
      <div
        className="agent-detail-panel-overlay"
        onClick={onClose}
      />

      {/* Panel principal */}
      <div className="agent-detail-panel" ref={panelRef}>

        {/* ── BANNER SUPERIOR ── */}
        <div style={{ position: 'relative', height: '160px', flexShrink: 0, overflow: 'hidden' }}>
          {bannerUrl ? (
            <img
              src={bannerUrl}
              alt={`Banner ${agent.name}`}
              style={{ width: '100%', height: '100%', objectFit: 'cover',
                filter: 'brightness(0.55) saturate(0.8)' }}
            />
          ) : (
            <div style={{ width: '100%', height: '100%',
              background: `linear-gradient(160deg, #0B2545 0%, ${tc.primary}22 100%)` }} />
          )}

          {/* Gradiente sobre el banner */}
          <div style={{ position: 'absolute', inset: 0,
            background: 'linear-gradient(to bottom, rgba(11,37,69,0.2) 0%, rgba(11,37,69,0.85) 100%)' }} />

          {/* Botón cerrar */}
          <button
            onClick={onClose}
            style={{ position: 'absolute', top: '12px', right: '12px',
              background: 'rgba(0, 0, 0, 0.5)', border: '1px solid rgba(255,255,255,0.2)',
              borderRadius: '50%', width: '32px', height: '32px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: '#e2e8f0', transition: 'all 0.2s' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(231,111,81,0.6)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(0,0,0,0.5)'; }}
          >
            <X size={16} />
          </button>

          {/* Título del agente sobre el banner */}
          <div style={{ position: 'absolute', bottom: '12px', left: '16px', right: '60px' }}>
            <div style={{ fontSize: '0.68rem', fontWeight: 700, color: tc.primary,
              letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '4px' }}>
              {agent.phaseName}
            </div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#FFFFFF',
              lineHeight: 1.2, textShadow: '0 2px 8px rgba(0,0,0,0.5)' }}>
              {agent.name}
            </h2>
          </div>
        </div>

        {/* ── LOGO + STATUS ROW ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px',
          padding: '16px 20px', borderBottom: `1px solid rgba(0,180,216,0.15)`,
          background: 'rgba(0, 0, 0, 0.2)', flexShrink: 0 }}>

          {/* Logo circular */}
          <div style={{ position: 'relative', flexShrink: 0 }}>
            <div style={{ width: '68px', height: '68px', borderRadius: '50%',
              border: `2.5px solid ${tc.primary}`,
              boxShadow: isActive ? `0 0 18px ${tc.glow}` : 'none',
              overflow: 'hidden', background: '#0F172A',
              display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {logoUrl ? (
                <img
                  src={logoUrl}
                  alt={agent.name}
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              ) : (
                <div style={{
                  width: '100%',
                  height: '100%',
                  background: `linear-gradient(135deg, #0B2545, ${tc.primary}55)`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: tc.primary,
                  fontWeight: 800,
                  fontSize: '1.4rem'
                }}>
                  {agent.name?.charAt(0) || 'A'}
                </div>
              )}
            </div>
            {/* Anillo pulsante si activo */}
            {isActive && (
              <div style={{ position: 'absolute', inset: '-4px', borderRadius: '50%',
                border: `2px dashed ${tc.primary}`, opacity: 0.7,
                animation: 'spin 4s linear infinite', pointerEvents: 'none' }} />
            )}
            {isDone && (
              <div style={{ position: 'absolute', bottom: '0', right: '0',
                background: '#8AC926', borderRadius: '50%', width: '20px', height: '20px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                border: '2px solid #0B2545' }}>
                <CheckCircle2 size={12} color="#0B2545" />
              </div>
            )}
          </div>

          {/* Nombre + estado */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#F1F5F9',
              marginBottom: '4px', fontFamily: 'Outfit, sans-serif',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {agent.name}
            </div>
            <div style={{ fontSize: '0.78rem', color: '#64748B', marginBottom: '8px',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {agent.role}
            </div>
            <StatusBadge isActive={isActive} isDone={isDone} />
          </div>

          {/* Step badge */}
          <div style={{ fontSize: '0.65rem', fontWeight: 800, color: tc.primary,
            background: tc.bg, border: `1px solid ${tc.primary}55`,
            borderRadius: '8px', padding: '3px 8px', fontFamily: 'monospace', flexShrink: 0 }}>
            P{agent.stepNumber}
          </div>
        </div>

        {/* ── CUERPO SCROLLABLE ── */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>

          {/* Modelo IA */}
          {agent.model && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px',
              marginBottom: '16px', padding: '8px 12px', borderRadius: '10px',
              background: 'rgba(2, 132, 199, 0.1)', border: '1px solid rgba(2, 132, 199, 0.25)' }}>
              <Cpu size={14} color="#38BDF8" />
              <span style={{ fontSize: '0.78rem', color: '#94A3B8', fontFamily: 'monospace' }}>
                Modelo: <strong style={{ color: '#38BDF8' }}>{agent.model}</strong>
              </span>
              {agent.db && agent.db.length > 0 && (
                <>
                  <Database size={12} color="#64748B" style={{ marginLeft: '8px' }} />
                  <span style={{ fontSize: '0.72rem', color: '#64748B' }}>
                    {agent.db.join(', ')}
                  </span>
                </>
              )}
            </div>
          )}

          {/* Descripción */}
          <Section title="Responsabilidad" icon={<Target size={14} />} color={tc.primary}>
            <p style={{ fontSize: '0.85rem', color: '#CBD5E1', lineHeight: 1.6 }}>
              {agent.desc}
            </p>
          </Section>

          {/* Justificación */}
          {agent.justificacion && (
            <Section title="Fundamento Legal" icon={<BookOpen size={14} />} color={tc.primary}>
              <p style={{ fontSize: '0.82rem', color: '#94A3B8', lineHeight: 1.55 }}>
                {agent.justificacion}
              </p>
            </Section>
          )}

          {/* Garantía Ética */}
          {agent.garantiaEtica && (
            <Section title="Garantía Ética" icon={<ShieldCheck size={14} />} color="#8AC926">
              <p style={{ fontSize: '0.82rem', color: '#94A3B8', lineHeight: 1.55 }}>
                {agent.garantiaEtica}
              </p>
            </Section>
          )}

          {/* Logs / Webhooks */}
          {agentLogs.length > 0 && (
            <Section title={`Registro de Actividad (${agentLogs.length})`}
              icon={<Activity size={14} />} color="#F4A261">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {agentLogs.map((log, i) => (
                  <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start',
                    padding: '7px 10px', borderRadius: '8px',
                    background: log.estado === 'ERROR' ? 'rgba(231,111,81,0.1)' :
                      log.estado === 'COMPLETADO' ? 'rgba(138,201,38,0.1)' :
                      'rgba(0,180,216,0.08)',
                    border: `1px solid ${log.estado === 'ERROR' ? 'rgba(231,111,81,0.25)' :
                      log.estado === 'COMPLETADO' ? 'rgba(138,201,38,0.25)' :
                      'rgba(0,180,216,0.2)'}` }}>
                    <div style={{ fontSize: '0.62rem', color: '#64748B',
                      fontFamily: 'monospace', whiteSpace: 'nowrap', marginTop: '2px' }}>
                      {log.ts}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#CBD5E1', flex: 1,
                      lineHeight: 1.4 }}>
                      {log.msg}
                    </div>
                    <div style={{ fontSize: '0.62rem', fontWeight: 700,
                      color: log.estado === 'ERROR' ? '#E76F51' :
                        log.estado === 'COMPLETADO' ? '#8AC926' : '#00B4D8',
                      whiteSpace: 'nowrap' }}>
                      {log.estado}
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Resultado del agente (si existe) */}
          {isDone && resultData && (
            <Section title="Resultado del Proceso" icon={<Eye size={14} />} color="#8AC926">
              <div style={{ background: 'rgba(0, 0, 0, 0.3)', borderRadius: '10px',
                padding: '12px', fontFamily: 'monospace', fontSize: '0.72rem',
                color: '#94A3B8', lineHeight: 1.6, maxHeight: '200px', overflowY: 'auto',
                border: '1px solid rgba(138, 201, 38, 0.2)' }}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {typeof resultData === 'string'
                    ? resultData
                    : JSON.stringify(resultData, null, 2)}
                </pre>
              </div>
            </Section>
          )}

          {/* Estado vacío si no hay datos */}
          {!isDone && !isActive && (
            <div style={{ textAlign: 'center', padding: '24px 16px',
              color: '#475569', fontSize: '0.85rem' }}>
              <Clock size={32} color="#334155" style={{ margin: '0 auto 10px' }} />
              <p>Este agente aún no ha sido ejecutado en esta sesión.</p>
            </div>
          )}
        </div>

        {/* ── FOOTER ── */}
        <div style={{ padding: '14px 20px', borderTop: '1px solid rgba(0,180,216,0.15)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: 'rgba(0, 0, 0, 0.2)', flexShrink: 0 }}>
          <span style={{ fontSize: '0.72rem', color: '#475569' }}>
            Paso {agent.stepNumber} · {agent.phaseName}
          </span>
          <button
            onClick={onClose}
            style={{ background: 'rgba(0, 180, 216, 0.12)', border: '1px solid rgba(0, 180, 216, 0.3)',
              color: '#00B4D8', padding: '6px 14px', borderRadius: '8px', cursor: 'pointer',
              fontSize: '0.78rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '5px',
              fontFamily: 'Outfit, sans-serif', transition: 'all 0.2s' }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,180,216,0.22)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(0,180,216,0.12)'}
          >
            <X size={13} /> Cerrar Panel
          </button>
        </div>
      </div>
    </>
  );
}

// ── Sub-componente de sección ──
function Section({ title, icon, color, children }) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px',
        fontSize: '0.72rem', fontWeight: 800, color: color, textTransform: 'uppercase',
        letterSpacing: '0.06em' }}>
        <span style={{ color }}>{icon}</span>
        {title}
      </div>
      <div style={{ paddingLeft: '2px' }}>
        {children}
      </div>
    </div>
  );
}
