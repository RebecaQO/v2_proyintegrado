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

// ── Formateo de los valores reales que devuelve el backend ─────────────────────
// Antes estos bloques usaban literales fijos ("Legislativo", "Comisión de
// Constitución", "Ingreso válido por Mesa de Partes") que se mostraban pase
// lo que devolviera la API, ocultando el dato real.

/** "AGENTE_GESTION_CORRESPONDENCIA" -> "Gestión de Correspondencia". */
const nombreLegible = (valor) => {
  const txt = String(valor ?? '').trim();
  if (!txt) return '';
  return txt
    .replace(/^AGENTE_/i, '')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
    .replace(/(^|\s)\p{L}/gu, (c) => c.toUpperCase());
};

/** `articulos_consultados` es una lista de objetos; `.join()` daba [object Object]. */
const formatearArticulos = (lista) => {
  if (!Array.isArray(lista) || lista.length === 0) return '';
  const items = lista.map((a) => {
    if (a && typeof a === 'object') {
      if (a.numero != null && a.numero !== '') return `Art. ${a.numero}`;
      if (a.articulo_constitucional != null) return String(a.articulo_constitucional);
      if (a.articulo != null) return String(a.articulo);
      if (a.titulo != null && a.titulo !== '') return String(a.titulo);
      return JSON.stringify(a);
    }
    return String(a);
  });
  if (items.length <= 20) return items.join(', ');
  return `${items.slice(0, 20).join(', ')} +${items.length - 20} más`;
};

const AGENT_LOGOS = {
  distribuidor:       '/robots/logos/agente_distribuidor.jpeg',
  comision:           '/robots/logos/agente_comision.jpeg',
  constitucional:     '/robots/logos/agente_constitucional.jpeg',
  consistencia:       '/robots/logos/agente_consistencia.jpeg',
  concentrador:       '/robots/logos/concentrador.jpeg',
  emisor:             '/robots/logos/agente_comodin.jpeg',
  notificador:        '/robots/logos/agente_comodin.jpeg',
  constitucion_fondo: '/robots/logos/agente_constitucional.jpeg',
  concentrador_crew:  '/robots/logos/concentrador.jpeg',
  secretario:         '/robots/logos/agente_secretario.jpeg',
  bicameral:          '/robots/logos/agente_bicamaral.jpeg',
  veto_promulgacion:  '/robots/logos/agente_veto.jpeg',
  publicacion:        '/robots/logos/agente_publicacion.jpeg',
  ciudadania:         '/robots/logos/agente_ciudadania.jpeg',
  comodin:            '/robots/logos/agente_comodin.jpeg',
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

  const completedTotal = AGENTS_DEFINITION.filter(a => getAgentResultData(a.id)).length;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 9999,
      background: 'rgba(19, 46, 69, 0.52)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '1080px',
        maxHeight: '90vh',
        background: '#F2F7FB',
        border: '1.5px solid #B8D3E3',
        borderRadius: '20px',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 24px 60px rgba(20, 55, 82, 0.28), 0 0 24px rgba(0, 132, 190, 0.12)',
        overflow: 'hidden'
      }}>
        {/* ── HEADER MODAL ── */}
        <div style={{
          padding: '20px 24px',
          background: '#FFFFFF',
          borderBottom: '1px solid #D8E5EE',
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
                  color: '#123B60',
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
                  background: '#EFF7E9',
                  border: '1px solid #C9DFAE',
                  color: '#4B7C18'
                }}>
                  {completedTotal} de {AGENTS_DEFINITION.length} completados
                </span>
              </div>
              <p style={{ margin: '3px 0 0 0', fontSize: '0.8rem', color: '#526E84' }}>
                Revise y compare los dictámenes de todos los agentes ejecutados, incluso mientras otro agente corre en segundo plano.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: '#F3F8FB',
              border: '1px solid #D1E0E9',
              borderRadius: '10px',
              padding: '8px',
              color: '#45657D',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = '#ef4444'; e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = '#45657D'; e.currentTarget.style.background = '#F3F8FB'; }}
          >
            <X size={18} />
          </button>
        </div>

        {/* ── ALERTA DE EJECUCIÓN EN VIVO ── */}
        {isProcessing && (
          <div style={{
            background: 'linear-gradient(90deg, #E8F4FA 0%, #F3FAFD 100%)',
            borderBottom: '1px solid #C5DFEC',
            padding: '10px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Zap size={16} color="#00B4D8" className="animate-pulse" />
              <span style={{ fontSize: '0.82rem', color: '#244863', fontWeight: 600 }}>
                Ejecución activa en curso: <strong style={{ color: '#00B4D8' }}>{activeAgentDef?.name || 'Agente'}</strong>
              </span>
            </div>
            <span style={{
              fontSize: '0.72rem',
              color: '#126596',
              background: '#E5F3FA',
              padding: '2px 8px',
              borderRadius: '6px',
              border: '1px solid #B7D8E9'
            }}>
              Paso {pipelineStep} en progreso
            </span>
          </div>
        )}

        {/* ── BARRA DE BÚSQUEDA ── */}
        <div style={{ padding: '14px 24px', borderBottom: '1px solid #D8E5EE', background: '#F2F7FB' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: '#FFFFFF',
            border: '1px solid #BFD8E7',
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
                color: '#183650',
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
          background: '#F1F6FA',
          overflowY: 'auto',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          {filteredAgents.map((agent) => {
            const resultData = getAgentResultData(agent.id);
            const isDone = !!resultData;
            const isActive = !isDone && pipelineStep >= agent.activeStep && pipelineStep < agent.doneAtStep;
            const isExpanded = expandedAgentId === agent.id;
            const Icon = AGENT_ICONS[agent.id] || Shield;

            return (
              <div
                key={agent.id}
                style={{
                  background: isExpanded
                    ? '#EAF5FB'
                    : isDone
                      ? '#FFFFFF'
                      : '#F8FBFD',
                  border: `1.5px solid ${isExpanded
                      ? '#68B9DB'
                      : isDone
                        ? '#C5DDB4'
                        : isActive
                          ? '#8BCDE5'
                          : '#DCE6ED'
                    }`,
                  borderRadius: '14px',
                  padding: '14px 18px',
                  transition: 'all 0.25s ease',
                  boxShadow: isDone ? '0 4px 14px rgba(24, 58, 86, 0.07)' : 'none'
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
                      width: '42px',
                      height: '42px',
                      borderRadius: '50%',
                      background: '#EAF2F7',
                      border: `2px solid ${isDone ? '#8AC926' : isActive ? '#00B4D8' : 'rgba(100, 116, 139, 0.4)'}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      overflow: 'hidden',
                      flexShrink: 0,
                      boxShadow: isDone ? '0 0 12px rgba(138,201,38,0.35)' : isActive ? '0 0 12px rgba(0,180,216,0.35)' : 'none'
                    }}>
                      {AGENT_LOGOS[agent.id] ? (
                        <img
                          src={AGENT_LOGOS[agent.id]}
                          alt={agent.name}
                          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        />
                      ) : (
                        <Icon size={18} color={isDone ? '#8AC926' : isActive ? '#00B4D8' : '#64748B'} />
                      )}
                    </div>

                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span style={{
                          fontSize: '0.92rem',
                          fontWeight: 800,
                          color: '#183F5D',
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
                        <span style={{ fontSize: '0.72rem', color: '#5B7489' }}>
                          • {agent.phaseName}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.76rem', color: '#536F85', marginTop: '2px' }}>
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
                        background: '#EFF7E9',
                        color: '#4B7C18',
                        border: '1px solid #C9DFAE',
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
                        background: '#E6F5FA',
                        color: '#087C9D',
                        border: '1px solid #AEDBEA',
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
                        color: '#536F85',
                        border: '1px solid #D3DFE7',
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
                          background: isExpanded ? '#D9EEF8' : '#EAF6FB',
                          border: '1px solid #9BCDE2',
                          color: '#126596',
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
                        background: '#F2F7FA',
                        border: '1px solid #D2E0E9',
                        color: '#35566E',
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
                    borderTop: '1px solid #D1E3ED'
                  }}>
                    <div style={{
                      background: '#FFFFFF',
                      borderRadius: '10px',
                      padding: '12px 16px',
                      border: '1px solid #D7E5ED',
                      fontSize: '0.78rem',
                      lineHeight: 1.55,
                      color: '#35566E'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ fontWeight: 800, color: '#126596' }}>
                          Salida Estructurada — {agent.name}
                        </span>
                        {(resultData.modelo_llm_usado || agent.model) && (
                          <span style={{ fontSize: '0.7rem', color: '#6A8295', fontFamily: 'monospace' }}>
                            Modelo: {resultData.modelo_llm_usado || agent.model}
                          </span>
                        )}
                      </div>

                      {/* Resumen específico por agente */}
                      {agent.id === 'distribuidor' && (
                        <div>
                          <div><strong>Tipo Documento:</strong> {resultData.tipo_documento || resultData.clasificacion || nombreLegible(resultData.categoria) || nombreLegible(resultData.tipo_entrada) || '—'}</div>
                          <div><strong>Destino institucional:</strong> {resultData.justificacion || (resultData.agente_destino_nombre ? `Turnado a ${nombreLegible(resultData.agente_destino_nombre)}` : '—')}</div>
                        </div>
                      )}

                      {agent.id === 'comision' && (
                        <div>
                          <div><strong>Comisión Asignada:</strong> <span style={{ color: '#38BDF8', fontWeight: 800 }}>{resultData.nombre_comision_display || resultData.comision_asignada || resultData.nombre_comision || nombreLegible(resultData.comision_principal) || '—'}</span></div>
                          <div><strong>Materia:</strong> {resultData.materia_predominante || (resultData.prioridad ? `Prioridad ${resultData.prioridad} · Complejidad ${resultData.complejidad || '—'}` : '—')}</div>
                        </div>
                      )}

                      {agent.id === 'constitucional' && (() => {
                        const numContradicciones = Array.isArray(resultData.contradicciones)
                          ? resultData.contradicciones.length
                          : (resultData.num_contradicciones || 0);
                        // Antes se declaraba "CONTRADICCIONES DETECTADAS" cuando
                        // `valido` era false aunque no hubiera ninguna (num=0).
                        const dictamen = numContradicciones > 0
                          ? 'CONTRADICCIONES DETECTADAS'
                          : (resultData.valido ? 'ARTICULADO VÁLIDO' : 'SIN CONTRADICCIONES DETECTADAS');
                        const colorDictamen = numContradicciones > 0 ? '#F4A261' : (resultData.valido ? '#8AC926' : '#6A8295');
                        const articulos = formatearArticulos(resultData.articulos_consultados);
                        return (
                          <div>
                            <div><strong>Dictamen CPE:</strong> <span style={{ color: colorDictamen, fontWeight: 800 }}>{dictamen}</span></div>
                            {articulos && (<div><strong>Artículos Analizados:</strong> {articulos}</div>)}
                            {numContradicciones > 0 && (
                              <div style={{ marginTop: '6px', color: '#F4A261' }}>
                                <strong>Contradicciones ({numContradicciones}):</strong>
                                <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                                  {resultData.contradicciones.slice(0, 3).map((c, i) => (
                                    <li key={i}>{c.articulo_constitucional || c.articulo}: {c.fundamento || c.razon}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        );
                      })()}

                      {agent.id === 'consistencia' && (
                        <div>
                          <div><strong>Antinomias / Hallazgos:</strong> {(resultData.hallazgos || []).length}{(resultData.pendientes_revision || []).length > 0 ? ` · ${resultData.pendientes_revision.length} pendientes de revisión` : ''}</div>
                          <div><strong>Riesgo Global:</strong> {resultData.nivel_riesgo_global || '—'}</div>
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
                        <summary style={{ color: '#42647D', fontSize: '0.72rem' }}>Ver JSON Completo</summary>
                        <pre style={{
                          margin: '6px 0 0 0',
                          padding: '8px',
                          background: '#F1F6F9',
                          borderRadius: '6px',
                          fontFamily: 'monospace',
                          fontSize: '0.68rem',
                          maxHeight: '160px',
                          overflowY: 'auto',
                          color: '#35566E',
                          border: '1px solid #D7E2E9'
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
          background: '#FFFFFF',
          borderTop: '1px solid #D8E5EE',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <span style={{ fontSize: '0.76rem', color: '#536F85' }}>
            Base de Datos: <strong style={{ color: '#35566E' }}>Neon PostgreSQL + pgvector + MongoDB Atlas</strong>
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
