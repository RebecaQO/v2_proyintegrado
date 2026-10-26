/**
 * AgentDetailPanel — Panel lateral deslizante de detalles del agente
 * Se abre desde la derecha cuando el usuario hace clic en un nodo circular.
 * Muestra: banner, nombre, estado, voz (sección prominente), descripción, logs, resultado.
 *
 * CAMBIO v2: Panel de Voz movido arriba y mostrado de forma prominente al abrir.
 *            El hook useLatinSpeech se instancia una sola vez por panel y se destruye al cerrar.
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
  Activity,
  Database,
  BookOpen,
  Eye,
  Radio,
  Mic,
} from 'lucide-react';
import { useLatinSpeech } from '../hooks/useLatinSpeech';
import AgentVoiceModule from './AgentVoiceModule';

// Mapeo de logos y banners institucionales
const AGENT_LOGO_MAP = {
  distribuidor: '/robots/logos/agente_distribuidor.jpeg',
  comision: '/robots/logos/agente_comision.jpeg',
  constitucional: '/robots/logos/agente_constitucional.jpeg',
  consistencia: '/robots/logos/agente_consistencia.jpeg',
  concentrador: '/robots/logos/concentrador.jpeg',
  emisor: '/robots/logos/agente_comodin.jpeg',
  notificador: '/robots/logos/agente_comodin.jpeg',
  constitucion_fondo: '/robots/logos/agente_constitucional.jpeg',
  concentrador_crew: '/robots/logos/concentrador.jpeg',
  secretario: '/robots/logos/agente_secretario.jpeg',
  bicameral: '/robots/logos/agente_bicamaral.jpeg',
  veto_promulgacion: '/robots/logos/agente_veto.jpeg',
  publicacion: '/robots/logos/agente_publicacion.jpeg',
  ciudadania: '/robots/logos/agente_ciudadania.jpeg',
  comodin: '/robots/logos/agente_comodin.jpeg',
};

const AGENT_BANNER_MAP = {
  distribuidor:       '/robots/banner/DISTRIBUIDOR.png',
  comision:           '/robots/banner/COMISION.png',
  constitucional:     '/robots/banner/CONSTITUCIONALIDAD.png',
  consistencia:       '/robots/banner/CONSISTENCIA.png',
  concentrador:       '/robots/banner/CONCENTRADOR.png',
  emisor:             '/robots/banner/CONCENTRADOR.png',
  notificador:        '/robots/banner/CONCENTRADOR.png',
  constitucion_fondo: '/robots/banner/CONSTITUCIONALIDAD.png',
  concentrador_crew:  '/robots/banner/CONCENTRADOR.png',
  secretario:         '/robots/banner/SECRETARIO.png',
  bicameral:          '/robots/banner/BICAMARAL.png',
  veto_promulgacion:  '/robots/banner/VETO.png',
  publicacion:        '/robots/banner/GACETAA.png',
  ciudadania:         '/robots/banner/DISTRIBUIDOR.png',
  comodin:            '/robots/banner/DISTRIBUIDOR.png',
};

// Color institucional por agente
const AGENT_THEME_COLORS = {
  distribuidor: { primary: '#00B4D8', glow: 'rgba(0, 180, 216, 0.45)', bg: 'rgba(0, 180, 216, 0.1)' },
  comision: { primary: '#38BDF8', glow: 'rgba(56, 189, 248, 0.45)', bg: 'rgba(56, 189, 248, 0.1)' },
  constitucional: { primary: '#2563EB', glow: 'rgba(37, 99, 235, 0.45)', bg: 'rgba(37, 99, 235, 0.1)' },
  consistencia: { primary: '#1D4ED8', glow: 'rgba(29, 78, 216, 0.45)', bg: 'rgba(29, 78, 216, 0.1)' },
  emisor: { primary: '#0284C7', glow: 'rgba(2, 132, 199, 0.45)', bg: 'rgba(2, 132, 199, 0.1)' },
  notificador: { primary: '#06B6D4', glow: 'rgba(6, 182, 212, 0.45)', bg: 'rgba(6, 182, 212, 0.1)' },
  constitucion_fondo: { primary: '#4338CA', glow: 'rgba(67, 56, 202, 0.45)', bg: 'rgba(67, 56, 202, 0.1)' },
  concentrador_crew: { primary: '#3B82F6', glow: 'rgba(59, 130, 246, 0.45)', bg: 'rgba(59, 130, 246, 0.1)' },
  secretario: { primary: '#1E40AF', glow: 'rgba(30, 64, 175, 0.45)', bg: 'rgba(30, 64, 175, 0.1)' },
  bicameral: { primary: '#7DD3FC', glow: 'rgba(125, 211, 252, 0.45)', bg: 'rgba(125, 211, 252, 0.1)' },
  veto_promulgacion: { primary: '#1E3A8A', glow: 'rgba(30, 58, 138, 0.5)', bg: 'rgba(30, 58, 138, 0.1)' },
  publicacion: { primary: '#00C2CB', glow: 'rgba(0, 194, 203, 0.45)', bg: 'rgba(0, 194, 203, 0.1)' },
};

function StatusBadge({ isActive, isDone, isError }) {
  if (isError) return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '4px 10px',
      borderRadius: '20px', background: 'rgba(231, 111, 81, 0.15)', color: '#E76F51',
      border: '1px solid rgba(231, 111, 81, 0.35)', fontSize: '0.75rem', fontWeight: 700
    }}>
      <AlertCircle size={12} /> Error
    </span>
  );
  if (isDone) return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '4px 10px',
      borderRadius: '20px', background: 'rgba(138, 201, 38, 0.15)', color: '#8AC926',
      border: '1px solid rgba(138, 201, 38, 0.35)', fontSize: '0.75rem', fontWeight: 700
    }}>
      <CheckCircle2 size={12} /> Completado
    </span>
  );
  if (isActive) return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '4px 10px',
      borderRadius: '20px', background: 'rgba(0, 180, 216, 0.15)', color: '#00B4D8',
      border: '1px solid rgba(0, 180, 216, 0.35)', fontSize: '0.75rem', fontWeight: 700,
      animation: 'pulse-inst 1.8s infinite ease-in-out'
    }}>
      <Zap size={12} /> En Proceso
    </span>
  );
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '4px 10px',
      borderRadius: '20px', background: 'rgba(100, 116, 139, 0.15)', color: '#64748B',
      border: '1px solid rgba(100, 116, 139, 0.25)', fontSize: '0.75rem', fontWeight: 700
    }}>
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

  // Hook de voz — una instancia única por agente en este panel
  const speechHook = useLatinSpeech();

  if (!agent) return null;

  const tc = AGENT_THEME_COLORS[agent.id] || AGENT_THEME_COLORS.distribuidor;
  const logoUrl = AGENT_LOGO_MAP[agent.id];
  const bannerUrl = AGENT_BANNER_MAP[agent.id];

  const isActive = pipelineStep === agent.activeStep;
  const isDone = !!resultData;
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
        <div style={{ position: 'relative', height: '130px', flexShrink: 0, overflow: 'hidden' }}>
          {bannerUrl ? (
            <img
              src={bannerUrl}
              alt={`Banner ${agent.name}`}
              style={{
                width: '100%', height: '100%', objectFit: 'cover',
                filter: 'brightness(0.45) saturate(0.7)'
              }}
            />
          ) : (
            <div style={{
              width: '100%', height: '100%',
              background: `linear-gradient(160deg, #0B2545 0%, ${tc.primary}22 100%)`
            }} />
          )}

          {/* Gradiente sobre el banner */}
          <div style={{
            position: 'absolute', inset: 0,
            background: 'linear-gradient(to bottom, rgba(11,37,69,0.2) 0%, rgba(11,37,69,0.92) 100%)'
          }} />

          {/* Botón cerrar */}
          <button
            onClick={onClose}
            style={{
              position: 'absolute', top: '10px', right: '10px',
              background: 'rgba(0, 0, 0, 0.55)', border: '1px solid rgba(255,255,255,0.2)',
              borderRadius: '50%', width: '30px', height: '30px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: '#e2e8f0', transition: 'all 0.2s'
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(231,111,81,0.6)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(0,0,0,0.55)'; }}
          >
            <X size={14} />
          </button>

          {/* Título del agente sobre el banner */}
          <div style={{ position: 'absolute', bottom: '10px', left: '14px', right: '50px' }}>
            <div style={{
              fontSize: '0.62rem', fontWeight: 700, color: tc.primary,
              letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '3px'
            }}>
              {agent.phaseName}
            </div>
            <h2 style={{
              fontSize: '1.05rem', fontWeight: 800, color: '#FFFFFF',
              lineHeight: 1.2, textShadow: '0 2px 8px rgba(0,0,0,0.5)', margin: 0
            }}>
              {agent.name}
            </h2>
          </div>
        </div>

        {/* ── LOGO + STATUS ROW ── */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '12px',
          padding: '12px 16px', borderBottom: `1px solid rgba(0,180,216,0.15)`,
          background: 'rgba(0, 0, 0, 0.25)', flexShrink: 0
        }}>

          {/* Logo circular */}
          <div style={{ position: 'relative', flexShrink: 0 }}>
            <div style={{
              width: '56px', height: '56px', borderRadius: '50%',
              border: `2.5px solid ${tc.primary}`,
              boxShadow: isActive ? `0 0 18px ${tc.glow}` : 'none',
              overflow: 'hidden', background: '#0F172A',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              {logoUrl ? (
                <img
                  src={logoUrl}
                  alt={agent.name}
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              ) : (
                <div style={{
                  width: '100%', height: '100%',
                  background: `linear-gradient(135deg, #0B2545, ${tc.primary}55)`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: tc.primary, fontWeight: 800, fontSize: '1.2rem'
                }}>
                  {agent.name?.charAt(0) || 'A'}
                </div>
              )}
            </div>
            {/* Anillo pulsante si activo */}
            {isActive && (
              <div style={{
                position: 'absolute', inset: '-4px', borderRadius: '50%',
                border: `2px dashed ${tc.primary}`, opacity: 0.7,
                animation: 'spin 4s linear infinite', pointerEvents: 'none'
              }} />
            )}
            {isDone && (
              <div style={{
                position: 'absolute', bottom: '0', right: '0',
                background: '#8AC926', borderRadius: '50%', width: '18px', height: '18px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                border: '2px solid #0B2545'
              }}>
                <CheckCircle2 size={11} color="#0B2545" />
              </div>
            )}
          </div>

          {/* Nombre + estado */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontSize: '0.9rem', fontWeight: 800, color: '#F1F5F9',
              marginBottom: '3px', fontFamily: 'Outfit, sans-serif',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
            }}>
              {agent.name}
            </div>
            <div style={{
              fontSize: '0.74rem', color: '#64748B', marginBottom: '6px',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
            }}>
              {agent.role}
            </div>
            <StatusBadge isActive={isActive} isDone={isDone} />
          </div>

          {/* Step badge */}
          <div style={{
            fontSize: '0.62rem', fontWeight: 800, color: tc.primary,
            background: tc.bg, border: `1px solid ${tc.primary}55`,
            borderRadius: '8px', padding: '3px 7px', fontFamily: 'monospace', flexShrink: 0
          }}>
            P{agent.stepNumber}
          </div>
        </div>

        {/* ── CUERPO SCROLLABLE ── */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>

          {/* ══════════════════════════════════════════════════════════ */}
          {/* SECCIÓN DE VOZ — PROMINENTE, PRIMERO QUE TODO */}
          {/* ══════════════════════════════════════════════════════════ */}
          <div style={{
            marginBottom: '16px',
            background: `linear-gradient(135deg, rgba(15,23,42,0.95), ${tc.primary}08)`,
            borderRadius: '14px',
            border: `1.5px solid ${tc.primary}30`,
            padding: '14px',
            boxShadow: `0 4px 20px ${tc.glow}20`
          }}>
            {/* Header de sección voz */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              marginBottom: '12px',
              paddingBottom: '10px',
              borderBottom: `1px solid ${tc.primary}20`
            }}>
              <div style={{
                width: '28px', height: '28px', borderRadius: '8px',
                background: `linear-gradient(135deg, ${tc.primary}30, ${tc.primary}10)`,
                border: `1px solid ${tc.primary}40`,
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <Mic size={14} color={tc.primary} />
              </div>
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 800, color: tc.primary, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                  Interacción por Voz
                </div>
                <div style={{ fontSize: '0.65rem', color: '#475569' }}>
                  Habla o escribe comandos para este agente
                </div>
              </div>
              {/* Indicador de modo STT activo */}
              {speechHook.isSTTSupported && (
                <div style={{
                  marginLeft: 'auto', fontSize: '0.62rem', fontWeight: 600,
                  color: '#10b981', background: 'rgba(16,185,129,0.1)',
                  border: '1px solid rgba(16,185,129,0.3)',
                  borderRadius: '6px', padding: '2px 7px',
                  display: 'flex', alignItems: 'center', gap: '4px'
                }}>
                  <Radio size={9} /> Web Speech API
                </div>
              )}
              {!speechHook.isSTTSupported && (
                <div style={{
                  marginLeft: 'auto', fontSize: '0.62rem', fontWeight: 600,
                  color: '#00f0ff', background: 'rgba(0,240,255,0.08)',
                  border: '1px solid rgba(0,240,255,0.25)',
                  borderRadius: '6px', padding: '2px 7px',
                  display: 'flex', alignItems: 'center', gap: '4px'
                }}>
                  <Radio size={9} /> Modo WAV Servidor
                </div>
              )}
            </div>

            <AgentVoiceModule
              agentId={agent.id}
              agentLabel={agent.name}
              primaryColor={tc.primary}
              sesionId={null}
              resultData={resultData}
              speechHook={speechHook}
              compact={false}
            />
          </div>

          {/* Modelo IA */}
          {(resultData?.modelo_llm_usado || agent.model) && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              marginBottom: '14px', padding: '7px 10px', borderRadius: '10px',
              background: 'rgba(2, 132, 199, 0.1)', border: '1px solid rgba(2, 132, 199, 0.25)'
            }}>
              <Cpu size={13} color="#38BDF8" />
              <span style={{ fontSize: '0.74rem', color: '#94A3B8', fontFamily: 'monospace' }}>
                Modelo: <strong style={{ color: '#38BDF8' }}>{resultData?.modelo_llm_usado || agent.model}</strong>
              </span>
              {agent.db && agent.db.length > 0 && (
                <>
                  <Database size={11} color="#64748B" style={{ marginLeft: '8px' }} />
                  <span style={{ fontSize: '0.68rem', color: '#64748B' }}>
                    {agent.db.join(', ')}
                  </span>
                </>
              )}
            </div>
          )}

          {/* Descripción */}
          <Section title="Responsabilidad" icon={<Target size={13} />} color={tc.primary}>
            <p style={{ fontSize: '0.83rem', color: '#CBD5E1', lineHeight: 1.6 }}>
              {agent.desc}
            </p>
          </Section>

          {/* Justificación */}
          {agent.justificacion && (
            <Section title="Fundamento Legal" icon={<BookOpen size={13} />} color={tc.primary}>
              <p style={{ fontSize: '0.79rem', color: '#94A3B8', lineHeight: 1.55 }}>
                {agent.justificacion}
              </p>
            </Section>
          )}

          {/* Garantía Ética */}
          {agent.garantiaEtica && (
            <Section title="Garantía Ética" icon={<ShieldCheck size={13} />} color="#8AC926">
              <p style={{ fontSize: '0.79rem', color: '#94A3B8', lineHeight: 1.55 }}>
                {agent.garantiaEtica}
              </p>
            </Section>
          )}

          {/* Logs / Webhooks */}
          {agentLogs.length > 0 && (
            <Section title={`Registro de Actividad (${agentLogs.length})`}
              icon={<Activity size={13} />} color="#F4A261">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                {agentLogs.map((log, i) => (
                  <div key={i} style={{
                    display: 'flex', gap: '8px', alignItems: 'flex-start',
                    padding: '6px 8px', borderRadius: '8px',
                    background: log.estado === 'ERROR' ? 'rgba(231,111,81,0.1)' :
                      log.estado === 'COMPLETADO' ? 'rgba(138,201,38,0.1)' :
                        'rgba(0,180,216,0.08)',
                    border: `1px solid ${log.estado === 'ERROR' ? 'rgba(231,111,81,0.25)' :
                      log.estado === 'COMPLETADO' ? 'rgba(138,201,38,0.25)' :
                        'rgba(0,180,216,0.2)'}`
                  }}>
                    <div style={{
                      fontSize: '0.6rem', color: '#64748B',
                      fontFamily: 'monospace', whiteSpace: 'nowrap', marginTop: '2px'
                    }}>
                      {log.ts}
                    </div>
                    <div style={{
                      fontSize: '0.74rem', color: '#CBD5E1', flex: 1,
                      lineHeight: 1.4
                    }}>
                      {log.msg}
                    </div>
                    <div style={{
                      fontSize: '0.6rem', fontWeight: 700,
                      color: log.estado === 'ERROR' ? '#E76F51' :
                        log.estado === 'COMPLETADO' ? '#8AC926' : '#00B4D8',
                      whiteSpace: 'nowrap'
                    }}>
                      {log.estado}
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Resultado del agente (si existe) */}
          {isDone && resultData && (
            <Section title="Resultado del Proceso" icon={<Eye size={13} />} color="#8AC926">
              <div style={{
                background: 'rgba(0, 0, 0, 0.3)', borderRadius: '10px',
                padding: '10px', fontFamily: 'monospace', fontSize: '0.69rem',
                color: '#94A3B8', lineHeight: 1.6, maxHeight: '180px', overflowY: 'auto',
                border: '1px solid rgba(138, 201, 38, 0.2)'
              }}>
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
            <div style={{
              textAlign: 'center', padding: '20px 14px',
              color: '#475569', fontSize: '0.82rem'
            }}>
              <Clock size={28} color="#334155" style={{ margin: '0 auto 10px' }} />
              <p>Este agente aún no ha sido ejecutado en esta sesión.</p>
            </div>
          )}
        </div>

        {/* ── FOOTER ── */}
        <div style={{
          padding: '12px 16px', borderTop: '1px solid rgba(0,180,216,0.15)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: 'rgba(0, 0, 0, 0.2)', flexShrink: 0
        }}>
          <span style={{ fontSize: '0.68rem', color: '#475569' }}>
            Paso {agent.stepNumber} · {agent.phaseName}
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(0, 180, 216, 0.12)', border: '1px solid rgba(0, 180, 216, 0.3)',
              color: '#00B4D8', padding: '5px 12px', borderRadius: '8px', cursor: 'pointer',
              fontSize: '0.74rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '5px',
              fontFamily: 'Outfit, sans-serif', transition: 'all 0.2s'
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,180,216,0.22)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(0,180,216,0.12)'}
          >
            <X size={12} /> Cerrar Panel
          </button>
        </div>
      </div>
    </>
  );
}

// ── Sub-componente de sección ──
function Section({ title, icon, color, children }) {
  return (
    <div style={{ marginBottom: '14px' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '7px',
        fontSize: '0.68rem', fontWeight: 800, color: color, textTransform: 'uppercase',
        letterSpacing: '0.06em'
      }}>
        <span style={{ color }}>{icon}</span>
        {title}
      </div>
      <div style={{ paddingLeft: '2px' }}>
        {children}
      </div>
    </div>
  );
}
