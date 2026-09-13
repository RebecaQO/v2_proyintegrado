import React, { useState, useEffect } from 'react';
import {
  X,
  Eye,
  CheckCircle2,
  Zap,
  Clock,
  AlertCircle,
  FileText,
  Search,
  Download,
  Building2,
  Scale,
  FileCheck,
  SendHorizontal,
  BookOpen,
  Merge,
  MessagesSquare,
  GitBranch,
  Gavel,
  Newspaper,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Shield
} from 'lucide-react';
import { AGENTS_DEFINITION } from './HorizontalAgentFlow';

const AGENT_ICONS = {
  distribuidor: FileText,
  comision: Building2,
  constitucional: Scale,
  consistencia: FileCheck,
  emisor: FileCheck,
  notificador: SendHorizontal,
  constitucion_fondo: BookOpen,
  concentrador_crew: Merge,
  secretario: MessagesSquare,
  bicameral: GitBranch,
  veto_promulgacion: Gavel,
  publicacion: Newspaper,
};

export default function AllAgentsResultsModal({
  isOpen,
  onClose,
  pipelineStep = 0,
  isProcessing = false,
  activeAgentDef = null,
  getAgentResultData = () => null,
  onInspectAgent = () => { }
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedAgentId, setExpandedAgentId] = useState(null);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Filtrado de agentes
  const filteredAgents = AGENTS_DEFINITION.filter((ag) => {
    const query = searchTerm.toLowerCase();
    return (
      ag.name.toLowerCase().includes(query) ||
      ag.shortName.toLowerCase().includes(query) ||
      ag.role.toLowerCase().includes(query) ||
      ag.phaseName.toLowerCase().includes(query)
    );
  });

  const completedTotal = AGENTS_DEFINITION.filter(a => pipelineStep >= a.doneAtStep).length;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 9999,
      background: 'rgba(7, 16, 33, 0.85)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '1080px',
        maxHeight: '90vh',
        background: 'linear-gradient(145deg, #0B2545 0%, #0F172A 100%)',
        border: '1.5px solid rgba(0, 180, 216, 0.4)',
        borderRadius: '20px',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 60px rgba(0, 0, 0, 0.7), 0 0 35px rgba(0, 180, 216, 0.25)',
        overflow: 'hidden'
      }}>
        {/* ── HEADER MODAL ── */}
        <div style={{
          padding: '20px 24px',
          background: 'rgba(15, 23, 42, 0.8)',
          borderBottom: '1px solid rgba(0, 180, 216, 0.25)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #0284C7, #00B4D8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFFFFF',
              boxShadow: '0 0 15px rgba(0, 180, 216, 0.5)'
            }}>
              <Eye size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{
                  margin: 0,
                  fontSize: '1.25rem',
                  fontWeight: 900,
                  color: '#FFFFFF',
                  fontFamily: 'Outfit, sans-serif',
                  letterSpacing: '-0.01em'
                }}>
                  Centro de Resultados Multi-Agente
                </h2>
                <span style={{
                  padding: '2px 8px',
                  borderRadius: '12px',
                  fontSize: '0.72rem',
                  fontWeight: 800,
                  background: 'rgba(138, 201, 38, 0.2)',
                  border: '1px solid rgba(138, 201, 38, 0.5)',
                  color: '#8AC926'
                }}>
                  {completedTotal} de {AGENTS_DEFINITION.length} completados
                </span>
              </div>
              <p style={{ margin: '3px 0 0 0', fontSize: '0.8rem', color: '#94A3B8' }}>
                Revise y compare los dictámenes de todos los agentes ejecutados, incluso mientras otro agente corre en segundo plano.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: '10px',
              padding: '8px',
              color: '#CBD5E1',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = '#ef4444'; e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = '#CBD5E1'; e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)'; }}
          >
            <X size={18} />
          </button>
        </div>

        {/* ── ALERTA DE EJECUCIÓN EN VIVO ── */}
        {isProcessing && (
          <div style={{
            background: 'linear-gradient(90deg, rgba(2, 132, 199, 0.25) 0%, rgba(0, 180, 216, 0.18) 100%)',
            borderBottom: '1px solid rgba(0, 180, 216, 0.35)',
            padding: '10px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Zap size={16} color="#00B4D8" className="animate-pulse" />
              <span style={{ fontSize: '0.82rem', color: '#E2E8F0', fontWeight: 600 }}>
                Ejecución activa en curso: <strong style={{ color: '#00B4D8' }}>{activeAgentDef?.name || 'Agente'}</strong>
              </span>
            </div>
            <span style={{
              fontSize: '0.72rem',
              color: '#38BDF8',
              background: 'rgba(0, 180, 216, 0.15)',
              padding: '2px 8px',
              borderRadius: '6px',
              border: '1px solid rgba(0, 180, 216, 0.3)'
            }}>
              Paso {pipelineStep} en progreso
            </span>
          </div>
        )}

        {/* ── BARRA DE BÚSQUEDA ── */}
        <div style={{ padding: '14px 24px', borderBottom: '1px solid rgba(0, 180, 216, 0.15)' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(0, 180, 216, 0.3)',
            borderRadius: '10px',
            padding: '8px 14px'
          }}>
            <Search size={16} color="#00B4D8" />
            <input
              type="text"
              placeholder="Buscar agente por nombre, rol o competencia..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                outline: 'none',
                color: '#FFFFFF',
                fontSize: '0.84rem',
                width: '100%',
                fontFamily: 'Outfit, sans-serif'
              }}
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', padding: 0 }}
              >
                <X size={14} />
              </button>
            )}
          </div>
        </div>

        {/* ── LISTADO SCROLLABLE DE AGENTES ── */}
        <div style={{
          padding: '16px 24px',
          overflowY: 'auto',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          {filteredAgents.map((agent) => {
            const isDone = pipelineStep >= agent.doneAtStep;
            const isActive = pipelineStep === agent.activeStep;
            const resultData = getAgentResultData(agent.id);
            const isExpanded = expandedAgentId === agent.id;
            const Icon = AGENT_ICONS[agent.id] || Shield;

            return (
              <div
                key={agent.id}
                style={{
                  background: isExpanded
                    ? 'rgba(19, 64, 116, 0.45)'
                    : isDone
                      ? 'rgba(11, 37, 69, 0.55)'
                      : 'rgba(15, 23, 42, 0.4)',
                  border: `1.5px solid ${isExpanded
                      ? '#00B4D8'
                      : isDone
                        ? 'rgba(138, 201, 38, 0.4)'
                        : isActive
                          ? '#00B4D8'
                          : 'rgba(100, 116, 139, 0.2)'
                    }`,
                  borderRadius: '14px',
                  padding: '14px 18px',
                  transition: 'all 0.25s ease',
                  boxShadow: isDone ? '0 4px 16px rgba(0, 0, 0, 0.25)' : 'none'
                }}
              >
                {/* Cabecera del Agente */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px',
                  flexWrap: 'wrap'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{
                      width: '38px',
                      height: '38px',
                      borderRadius: '10px',
                      background: isDone
                        ? 'rgba(138, 201, 38, 0.15)'
                        : isActive
                          ? 'rgba(0, 180, 216, 0.2)'
                          : 'rgba(100, 116, 139, 0.1)',
                      border: `1.5px solid ${isDone ? '#8AC926' : isActive ? '#00B4D8' : 'rgba(100, 116, 139, 0.3)'}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: isDone ? '#8AC926' : isActive ? '#00B4D8' : '#64748B'
                    }}>
                      <Icon size={18} />
                    </div>

                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span style={{
                          fontSize: '0.92rem',
                          fontWeight: 800,
                          color: '#FFFFFF',
                          fontFamily: 'Outfit, sans-serif'
                        }}>
                          {agent.name}
                        </span>
                        <span style={{
                          fontSize: '0.66rem',
                          fontFamily: 'monospace',
                          fontWeight: 800,
                          padding: '1px 6px',
                          borderRadius: '4px',
                          background: 'rgba(0, 180, 216, 0.15)',
                          color: '#00B4D8',
                          border: '1px solid rgba(0, 180, 216, 0.3)'
                        }}>
                          P{agent.stepNumber}
                        </span>
                        <span style={{ fontSize: '0.72rem', color: '#64748B' }}>
                          • {agent.phaseName}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.76rem', color: '#94A3B8', marginTop: '2px' }}>
                        {agent.role}
                      </div>
                    </div>
                  </div>

                  {/* Estado + Botones */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {isDone ? (
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        padding: '4px 10px',
                        borderRadius: '20px',
                        background: 'rgba(138, 201, 38, 0.15)',
                        color: '#8AC926',
                        border: '1px solid rgba(138, 201, 38, 0.4)',
                        fontSize: '0.74rem',
                        fontWeight: 800
                      }}>
                        <CheckCircle2 size={13} /> Ejecutado
                      </span>
                    ) : isActive ? (
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        padding: '4px 10px',
                        borderRadius: '20px',
                        background: 'rgba(0, 180, 216, 0.15)',
                        color: '#00B4D8',
                        border: '1px solid rgba(0, 180, 216, 0.4)',
                        fontSize: '0.74rem',
                        fontWeight: 800
                      }}>
                        <Zap size={13} className="animate-spin" /> En Proceso
                      </span>
                    ) : (
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        padding: '4px 10px',
                        borderRadius: '20px',
                        background: 'rgba(100, 116, 139, 0.15)',
                        color: '#64748B',
                        border: '1px solid rgba(100, 116, 139, 0.25)',
                        fontSize: '0.74rem',
                        fontWeight: 700
                      }}>
                        <Clock size={13} /> En Espera
                      </span>
                    )}

                    {/* Botón desplegar resultados */}
                    {resultData && (
                      <button
                        onClick={() => setExpandedAgentId(isExpanded ? null : agent.id)}
                        style={{
                          padding: '5px 12px',
                          fontSize: '0.74rem',
                          fontWeight: 700,
                          borderRadius: '8px',
                          background: isExpanded ? 'rgba(0, 180, 216, 0.25)' : 'rgba(0, 180, 216, 0.12)',
                          border: '1px solid rgba(0, 180, 216, 0.4)',
                          color: '#38BDF8',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px'
                        }}
                      >
                        <Eye size={13} />
                        <span>{isExpanded ? 'Ocultar' : 'Ver Resultado'}</span>
                        {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                      </button>
                    )}

                    {/* Botón inspección detallada */}
                    <button
                      onClick={() => {
                        onInspectAgent(agent);
                        onClose();
                      }}
                      title="Abrir en Panel Detallado"
                      style={{
                        padding: '5px 10px',
                        fontSize: '0.74rem',
                        fontWeight: 700,
                        borderRadius: '8px',
                        background: 'rgba(255, 255, 255, 0.06)',
                        border: '1px solid rgba(255, 255, 255, 0.18)',
                        color: '#E2E8F0',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px'
                      }}
                    >
                      <ExternalLink size={13} />
                      <span>Inspeccionar</span>
                    </button>
                  </div>
                </div>

                {/* Vista desplegada del resultado */}
                {isExpanded && resultData && (
                  <div style={{
                    marginTop: '14px',
                    paddingTop: '14px',
                    borderTop: '1px solid rgba(0, 180, 216, 0.2)'
                  }}>
                    <div style={{
                      background: 'rgba(10, 17, 30, 0.85)',
                      borderRadius: '10px',
                      padding: '12px 16px',
                      border: '1px solid rgba(0, 180, 216, 0.25)',
                      fontSize: '0.78rem',
                      lineHeight: 1.55,
                      color: '#CBD5E1'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ fontWeight: 800, color: '#38BDF8' }}>
                          Salida Estructurada — {agent.name}
                        </span>
                        {agent.model && (
                          <span style={{ fontSize: '0.7rem', color: '#64748B', fontFamily: 'monospace' }}>
                            Modelo: {agent.model}
                          </span>
                        )}
                      </div>

                      {/* Resumen específico por agente */}
                      {agent.id === 'distribuidor' && (
                        <div>
                          <div><strong>Tipo Documento:</strong> {resultData.tipo_documento || resultData.clasificacion || 'Legislativo'}</div>
                          <div><strong>Justificación:</strong> {resultData.justificacion || 'Ingreso válido por Mesa de Partes'}</div>
                        </div>
                      )}

                      {agent.id === 'comision' && (
                        <div>
                          <div><strong>Comisión Asignada:</strong> <span style={{ color: '#38BDF8', fontWeight: 800 }}>{resultData.comision_asignada || resultData.nombre_comision || 'Comisión de Constitución'}</span></div>
                          <div><strong>Materia:</strong> {resultData.materia_predominante || 'Legislativa'}</div>
                        </div>
                      )}

                      {agent.id === 'constitucional' && (
                        <div>
                          <div><strong>Dictamen CPE:</strong> <span style={{ color: resultData.valido ? '#8AC926' : '#F4A261', fontWeight: 800 }}>{resultData.valido ? 'ARTICULADO VÁLIDO' : 'CONTRADICCIONES DETECTADAS'}</span></div>
                          <div><strong>Artículos Analizados:</strong> {(resultData.articulos_consultados || []).join(', ') || 'Art. 1, 9, 14, 158'}</div>
                          {resultData.contradicciones && resultData.contradicciones.length > 0 && (
                            <div style={{ marginTop: '6px', color: '#F4A261' }}>
                              <strong>Contradicciones ({resultData.contradicciones.length}):</strong>
                              <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                                {resultData.contradicciones.slice(0, 3).map((c, i) => (
                                  <li key={i}>{c.articulo_constitucional || c.articulo}: {c.fundamento || c.razon}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}

                      {agent.id === 'consistencia' && (
                        <div>
                          <div><strong>Antinomias / Hallazgos:</strong> {(resultData.hallazgos || []).length} normas cotejadas</div>
                          <div><strong>Riesgo Global:</strong> {resultData.nivel_riesgo_global || 'OK'}</div>
                        </div>
                      )}

                      {agent.id === 'emisor' && (
                        <div>
                          <div><strong>Informe Oficial PDF:</strong> {resultData.filename || 'Generado'}</div>
                          {resultData.url && (
                            <a href={resultData.url} target="_blank" rel="noopener noreferrer" style={{ color: '#00B4D8', display: 'inline-flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}>
                              <Download size={13} /> Descargar PDF Oficial
                            </a>
                          )}
                        </div>
                      )}

                      {agent.id === 'notificador' && (
                        <div>
                          <div><strong>Despacho Notificación:</strong> {resultData.enviado ? 'Enviado con éxito' : 'Certificado para envío'}</div>
                          <div><strong>Destinatarios:</strong> {(resultData.destinatarios || []).join(', ') || 'Plenario'}</div>
                        </div>
                      )}

                      {agent.id === 'publicacion' && (
                        <div>
                          <div><strong>Número de Ley:</strong> <span style={{ color: '#8AC926', fontWeight: 900 }}>{resultData.numero_ley_str || resultData.numero_ley || (resultData.publicacion_oficial && resultData.publicacion_oficial.numero_ley_str) || 'Ley Publicada'}</span></div>
                          <div><strong>Fecha Vigencia:</strong> {resultData.fecha_vigencia || (resultData.publicacion_oficial && resultData.publicacion_oficial.fecha_vigencia) || 'Inmediata'}</div>
                          <div><strong>Hash SHA-256:</strong> <span style={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>{resultData.hash_texto || (resultData.publicacion_oficial && resultData.publicacion_oficial.hash_texto) || 'Verificado'}</span></div>
                          <div><strong>Boletín Oficial:</strong> {resultData.boletin_oficial || (resultData.publicacion_oficial && resultData.publicacion_oficial.boletin_oficial) || 'Gaceta Oficial'}</div>
                        </div>
                      )}

                      {agent.id === 'concentrador_crew' && (
                        <div>
                          <div><strong>Síntesis de Observaciones:</strong> {resultData.expediente_consolidado?.resumen_ejecutivo || 'Expediente consolidado con trazabilidad total.'}</div>
                          <div><strong>Total Observaciones Integradas:</strong> {(resultData.expediente_consolidado?.observaciones_integradas || []).length}</div>
                        </div>
                      )}

                      {/* Vista previa JSON detallada */}
                      <details style={{ marginTop: '8px', cursor: 'pointer' }}>
                        <summary style={{ color: '#64748B', fontSize: '0.72rem' }}>Ver JSON Completo</summary>
                        <pre style={{
                          margin: '6px 0 0 0',
                          padding: '8px',
                          background: '#070D18',
                          borderRadius: '6px',
                          fontFamily: 'monospace',
                          fontSize: '0.68rem',
                          maxHeight: '160px',
                          overflowY: 'auto',
                          color: '#94A3B8'
                        }}>
                          {typeof resultData === 'object' ? JSON.stringify(resultData, null, 2) : String(resultData)}
                        </pre>
                      </details>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* ── FOOTER MODAL ── */}
        <div style={{
          padding: '14px 24px',
          background: 'rgba(15, 23, 42, 0.95)',
          borderTop: '1px solid rgba(0, 180, 216, 0.25)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <span style={{ fontSize: '0.76rem', color: '#64748B' }}>
            Base de Datos: <strong style={{ color: '#94A3B8' }}>Neon PostgreSQL + pgvector + MongoDB Atlas</strong>
          </span>
          <button
            onClick={onClose}
            style={{
              padding: '6px 18px',
              fontSize: '0.82rem',
              fontWeight: 700,
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #0284C7, #00B4D8)',
              border: 'none',
              color: '#FFFFFF',
              cursor: 'pointer',
              boxShadow: '0 2px 10px rgba(0, 180, 216, 0.4)'
            }}
          >
            Entendido / Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
