// MesaPartes v3.0 — Paleta Institucional GobernIA + Flujo Paralelo + Panel Lateral Deslizante
import React, { useState, useEffect, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Scale,
  Cpu,
  Building2,
  Users,
  Mail,
  RotateCcw,
  Check,
  ExternalLink,
  BookOpen,
  Download,
  FileCheck,
  Sparkles,
  Plus,
  X,
  Eye,
  EyeOff,
  Layers,
  Gavel,
  Newspaper,
  GitBranch,
  MessagesSquare,
  Merge,
  ShieldCheck,
  Database,
  Server,
  Terminal,
  Zap,
  Shield,
  Mic,
  Code,
  FileJson,
  Copy,
  Info,
} from 'lucide-react';
import { api as apiClient, BACKEND_BASE_URL } from '../services/api';
import { apiSoloLectura } from '../services/apiSoloLectura';
import AuditResultsNav from '../components/AuditResultsNav';
import CaseProcessingStatus from '../components/CaseProcessingStatus';
import { useCasosCompartidos } from '../hooks/useCasosCompartidos';
import { RevisionBicameralPanel, DecisionEjecutivaPanel } from '../components/RevisionLegislativa';
import HorizontalAgentFlow, { AGENTS_DEFINITION } from '../components/HorizontalAgentFlow';
import LateralAgentHero from '../components/LateralAgentHero';
import AgentResultCard from '../components/AgentResultCard';
import AgentDetailPanel from '../components/AgentDetailPanel';
import AllAgentsResultsModal from '../components/AllAgentsResultsModal';
import CorrecionesPanel from '../components/CorrecionesPanel';
import AgentVoiceModule from '../components/AgentVoiceModule';
import AgentChatPanel from '../components/AgentChatPanel';
import EmailDespachoDrawer from '../components/EmailDespachoDrawer';
import MensajeSenadoCrewPanel from '../components/MensajeSenadoCrewPanel';
import { GacetaCorreccionesSection, GacetaNotificacionEmailSection } from '../components/GacetaPublicacionSections';
import { useLatinSpeech } from '../hooks/useLatinSpeech';

// Mapeo de logos institucionales y colores de acento por agente
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

const AGENT_ACCENT_MAP = {
  distribuidor: '#00B4D8', // Celeste Neón Eléctrico
  comision: '#38BDF8', // Azul Cielo Radiante
  constitucional: '#2563EB', // Azul Zafiro Real
  consistencia: '#1D4ED8', // Azul Cobalto Profundo
  concentrador: '#0284C7', // Azul Océano Cerúleo
  emisor: '#0284C7', // Azul Océano Cerúleo
  notificador: '#06B6D4', // Turquesa Azulado
  constitucion_fondo: '#4338CA', // Azul Índigo Parlamentario
  concentrador_crew: '#3B82F6', // Azul Acero Técnico
  secretario: '#1E40AF', // Azul Marino Clásico
  bicameral: '#7DD3FC', // Azul Hielo Glaciar
  veto_promulgacion: '#1E3A8A', // Azul Medianoche Ultramar
  publicacion: '#00C2CB', // Azul Lapislázuli Brillante
};

const STORAGE_SESSIONS_KEY = 'sma_mesapartes_sessions_v2';
const STORAGE_ACTIVE_KEY = 'sma_mesapartes_active_session_id';

function createDefaultSession(index = 1) {
  return {
    id: `ses_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
    title: `Consulta #${index}`,
    inputMode: 'file', // 'file' | 'text'
    documentText: '',
    documentName: '',
    emailAutor: '',
    nombreAutor: '',
    tipoIniciativa: 'Senado',
    uploadStats: null,
    pipelineStep: 0,
    isProcessing: false,
    errorMessage: '',
    fase1Data: null,
    selectedCategory: '',
    comisionData: null,
    dictamenData: null,
    consistenciaData: null,
    pdfResult: null,
    notificadorData: null,
    showEmailPreview: false,
    customEmail: '',
    extraEmailMessage: '',
    customEmailSubject: '',
    votosBicameral: { dipFavor: 87, dipContra: 35, dipAbst: 8, senFavor: 25, senContra: 9, senAbst: 2, quorumConfirmado: true },
    remitidoPresidente: false,
    gacetaPdfData: null,
    showTextoConsolidadoModal: false,
    textoConsolidadoInfo: null,
    inspectedAgentId: null,
    createdAt: new Date().toISOString(),
    // CrewAI YAML extended pipeline
    constitucionFondoData: null,
    concentradorData: null,
    secretarioData: null,
    bicameralData: null,
    confirmacionBicameralData: null,
    vetoPromulgacionData: null,
    publicacionData: null,
    pipelineLog: []  // [{etapa, estado, msg, ts}]
  };
}

// ── Componente de Tarjeta Detallada para Artículos CPE A FAVOR ──
function CardArticuloAFavor({ art, idx }) {
  const [expanded, setExpanded] = useState(false);

  const analisis = art.analisis_profundo || {};
  const justificacion = art.justificacion_detallada || analisis.justificacion_por_que || art.fundamento;
  const parrafos = art.parrafos_evaluados || analisis.evaluacion_detallada_articulos_parrafos || (
    art.cita_proyecto ? [{ articulo_proyecto: 'Disposición analizada del proyecto', texto_parrafo: art.cita_proyecto, explicacion_concordancia: art.fundamento }] : []
  );
  const fortaleza = art.fortaleza_constitucional || analisis.fortaleza_constitucional || 'ALTA';
  const principios = art.principios || analisis.principios_constitucionales_aplicados || [];
  const blindaje = art.recomendacion_blindaje || analisis.recomendacion_blindaje;

  return (
    <div style={{
      background: 'rgba(6, 30, 20, 0.90)',
      border: '1px solid rgba(16, 185, 129, 0.35)',
      borderRadius: '14px',
      padding: '18px 20px',
      position: 'relative',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      gap: '12px',
      boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
      transition: 'all 0.2s ease',
    }}>
      {/* Indicador lateral verde esmeralda */}
      <div style={{ position: 'absolute', top: 0, left: 0, width: '4px', height: '100%', background: '#10b981', borderRadius: '14px 0 0 14px' }} />

      {/* Cabecera del Artículo */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#34d399', fontWeight: 800, fontSize: '1.05rem', letterSpacing: '0.02em' }}>
              Art. {art.numero}
            </span>
            <span style={{ background: 'rgba(16,185,129,0.18)', color: '#34d399', border: '1px solid rgba(16,185,129,0.4)', padding: '2px 10px', borderRadius: '20px', fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              A FAVOR
            </span>
            <span style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '2px 8px', borderRadius: '12px', fontSize: '0.68rem', fontWeight: 600 }}>
              Fortaleza: {fortaleza}
            </span>
          </div>
          {art.titulo && (
            <div style={{ color: '#a7f3d0', fontWeight: 600, fontSize: '0.86rem', marginTop: '4px' }}>
              {art.titulo}
            </div>
          )}
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            background: expanded ? 'rgba(16, 185, 129, 0.25)' : 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            color: '#a7f3d0',
            borderRadius: '8px',
            padding: '4px 10px',
            fontSize: '0.74rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontWeight: 600,
            transition: 'background 0.2s',
          }}
        >
          {expanded ? '▲ Contraer desglose' : `▼ Ver evaluación párrafo a párrafo (${parrafos.length})`}
        </button>
      </div>

      {/* Justificación Jurídica Principal (¿Por qué está a favor?) */}
      <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)', borderRadius: '10px', padding: '12px 14px' }}>
        <div style={{ fontSize: '0.72rem', color: '#34d399', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>⚖️ JUSTIFICACIÓN JURÍDICA (¿POR QUÉ RESPALDA A LA CPE?):</span>
        </div>
        <div style={{ color: '#d1fae5', fontSize: '0.84rem', lineHeight: 1.6, textAlign: 'justify' }}>
          {justificacion || 'El proyecto de ley materializa y desarrolla de forma conforme el precepto constitucional.'}
        </div>
      </div>

      {/* Evaluación Párrafo por Párrafo / Artículo por Artículo del Proyecto */}
      {parrafos.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ fontSize: '0.72rem', color: '#6ee7b7', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            🔍 ANÁLISIS ARTÍCULO POR ARTÍCULO Y PÁRRAFO POR PÁRRAFO DEL PROYECTO:
          </div>

          {(expanded ? parrafos : parrafos.slice(0, 1)).map((p, pIdx) => (
            <div key={pIdx} style={{
              background: 'rgba(0, 0, 0, 0.35)',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              borderRadius: '8px',
              padding: '10px 12px',
              fontSize: '0.8rem',
            }}>
              <div style={{ color: '#34d399', fontWeight: 700, fontSize: '0.76rem', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>📌 {p.articulo_proyecto || `Fragmento #${pIdx + 1} del Proyecto`}</span>
              </div>
              {p.texto_parrafo && (
                <div style={{ color: 'rgba(255, 255, 255, 0.82)', fontStyle: 'italic', background: 'rgba(0, 0, 0, 0.25)', padding: '6px 10px', borderRadius: '6px', marginBottom: '6px', lineHeight: 1.5, borderLeft: '2px solid #10b981' }}>
                  "{p.texto_parrafo}"
                </div>
              )}
              {p.explicacion_concordancia && (
                <div style={{ color: '#a7f3d0', fontSize: '0.78rem', lineHeight: 1.5 }}>
                  <strong style={{ color: '#6ee7b7' }}>✓ Concordancia: </strong>
                  {p.explicacion_concordancia}
                </div>
              )}
            </div>
          ))}

          {!expanded && parrafos.length > 1 && (
            <div
              onClick={() => setExpanded(true)}
              style={{ fontSize: '0.72rem', color: '#6ee7b7', fontStyle: 'italic', textAlign: 'center', cursor: 'pointer', padding: '4px 0', textDecoration: 'underline' }}
            >
              +{parrafos.length - 1} párrafo(s) analizado(s) adicional(es) — presiona para ver todo el desglose
            </div>
          )}
        </div>
      )}

      {/* Detalle complementario (Texto CPE, Principios y Blindaje) */}
      {expanded && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', borderTop: '1px solid rgba(16, 185, 129, 0.15)', paddingTop: '10px' }}>
          {art.extracto && (
            <div>
              <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
                📖 Precepto Constitucional (CPE 2009 - Art. {art.numero}):
              </div>
              <div style={{ color: 'rgba(255, 255, 255, 0.65)', fontSize: '0.78rem', lineHeight: 1.5, background: 'rgba(0, 0, 0, 0.25)', padding: '8px 10px', borderRadius: '6px' }}>
                {art.extracto}
              </div>
            </div>
          )}

          {principios.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.7rem', color: '#6ee7b7', fontWeight: 600 }}>Valores/Principios Constitucionales:</span>
              {principios.map((pr, prIdx) => (
                <span key={prIdx} style={{ background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#a7f3d0', borderRadius: '12px', padding: '1px 8px', fontSize: '0.68rem' }}>
                  {pr}
                </span>
              ))}
            </div>
          )}

          {blindaje && (
            <div style={{ background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: '8px', padding: '8px 12px' }}>
              <div style={{ fontSize: '0.7rem', color: '#38bdf8', fontWeight: 700, textTransform: 'uppercase', marginBottom: '3px' }}>
                🛡️ Recomendación de Blindaje Constitucional:
              </div>
              <div style={{ color: '#bae6fd', fontSize: '0.78rem', lineHeight: 1.5 }}>
                {blindaje}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function MesaPartes({ onNavigateExpedientes, onNavigateEjecutivo, currentUser, readOnly = false, initialCaseId = null, onActiveCaseChange }) {
  const api = readOnly ? apiSoloLectura(apiClient) : apiClient;
  const resultsRef = useRef(null);
  const [reanudandoCaso, setReanudandoCaso] = useState(false);
  const [errorReanudacion, setErrorReanudacion] = useState('');
  const [inboxSearch, setInboxSearch] = useState('');
  const [inboxDestination, setInboxDestination] = useState('Todas');
  const [downloadingOriginal, setDownloadingOriginal] = useState(false);
  const [originalDownloadError, setOriginalDownloadError] = useState('');
  // ── Multi-Session State Initialization ──
  const [sessions, setSessions] = useState(() => {
    if (readOnly) return [];
    try {
      const saved = localStorage.getItem(STORAGE_SESSIONS_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed.map(s => ({ ...s, isProcessing: false }));
        }
      }
    } catch (err) {
      console.warn('Error reading sessions from localStorage:', err);
    }
    return [createDefaultSession(1)];
  });

  const [activeSessionId, setActiveSessionId] = useState(() => {
    if (readOnly) return initialCaseId || "";
    try {
      const savedId = localStorage.getItem(STORAGE_ACTIVE_KEY);
      if (savedId) return savedId;
    } catch (err) {
      console.warn('Error reading active session ID:', err);
    }
    return sessions[0]?.id || '';
  });

  const fileInputRef = useRef(null);

  // ── Estado para Catálogo de Normativas y Carga con LLM ──
  const [normativasList, setNormativasList] = useState([]);
  const [isLoadingNormativas, setIsLoadingNormativas] = useState(false);
  const [showSubirNormativaModal, setShowSubirNormativaModal] = useState(false);
  const [normativaFile, setNormativaFile] = useState(null);
  const [normativaTexto, setNormativaTexto] = useState('');
  const [normativaNombre, setNormativaNombre] = useState('');
  const [normativaTipo, setNormativaTipo] = useState('Ley');
  const [normativaNumero, setNormativaNumero] = useState('');
  const [isUploadingNormativa, setIsUploadingNormativa] = useState(false);
  const [normativaUploadStatus, setNormativaUploadStatus] = useState(null);
  const [driveDownloadError, setDriveDownloadError] = useState('');

  // ── Pestañas técnicas para el Agente de Veto y Promulgación ──
  const [vetoActiveTab, setVetoActiveTab] = useState('dictamen');
  const [copiedVetoJson, setCopiedVetoJson] = useState(false);
  const [copiedDebateText, setCopiedDebateText] = useState(false);

  const cargarNormativas = async () => {
    setIsLoadingNormativas(true);
    try {
      const res = await api.getNormativasCatalogadas();
      if (res?.documentos) {
        setNormativasList(res.documentos);
      }
    } catch (err) {
      console.warn('Error cargando catálogo de normativas:', err);
    } finally {
      setIsLoadingNormativas(false);
    }
  };

  useEffect(() => {
    cargarNormativas();
  }, []);

  const handleSubirNormativa = async (e) => {
    if (readOnly) return;
    e.preventDefault();
    if (!normativaNombre.trim()) {
      alert('Por favor ingrese el nombre oficial de la normativa');
      return;
    }
    if (!normativaFile && !normativaTexto.trim()) {
      alert('Por favor seleccione un archivo PDF/TXT o pegue el texto de la normativa');
      return;
    }

    setIsUploadingNormativa(true);
    setNormativaUploadStatus(null);
    try {
      const formData = new FormData();
      formData.append('nombre', normativaNombre.trim());
      formData.append('tipo', normativaTipo);
      if (normativaNumero.trim()) formData.append('numero_norma', normativaNumero.trim());
      if (normativaFile) {
        formData.append('file', normativaFile);
      } else {
        formData.append('texto_directo', normativaTexto.trim());
      }

      const res = await api.subirNormativa(formData);
      if (res?.success) {
        setNormativaUploadStatus({
          success: true,
          msg: `Normativa "${res.documento}" procesada con LLM e indexada con éxito (${res.articulos_indexados} artículos).`,
          resumen: res.resumen
        });
        if (res.normativas) {
          setNormativasList(res.normativas);
        } else {
          cargarNormativas();
        }
        setNormativaFile(null);
        setNormativaTexto('');
        setNormativaNombre('');
        setNormativaNumero('');
      } else {
        setNormativaUploadStatus({ success: false, msg: res?.detail || 'Error procesando la normativa' });
      }
    } catch (err) {
      setNormativaUploadStatus({ success: false, msg: err.message || 'Error en la conexión al servidor' });
    } finally {
      setIsUploadingNormativa(false);
    }
  };

  const descargarRegistroNormativo = async (norma) => {
    setDriveDownloadError('');
    try {
      const blob = await apiClient.getDocumentoIngresado(norma.drive_upload_id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = norma.drive_filename || norma.documento || 'normativa-original';
      document.body.appendChild(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { setDriveDownloadError(err.message); }
  };

  // Active Session helper
  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0] || createDefaultSession(1);
  const shared = useCasosCompartidos(sessions, setSessions, s => ({ ...createDefaultSession(), ...s, createdAt: s.createdAt || s.updatedAt }), readOnly);
  const descargarDocumentoOriginal = async () => {
    setDownloadingOriginal(true);
    setOriginalDownloadError('');
    try {
      const blob = await apiClient.getCasoDocumento(activeSession.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = activeSession.documentPdf?.nombre || activeSession.uploadStats?.filename || activeSession.documentName || 'documento-original';
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { setOriginalDownloadError(err.message); }
    finally { setDownloadingOriginal(false); }
  };
  useEffect(() => {
    if (activeSession?.id && (activeSession._sharedVersion || activeSession.documentText || activeSession.fase1Data || activeSession.uploadStats?.saved_as)) {
      onActiveCaseChange?.(activeSession);
    }
  }, [activeSession?.id, activeSession?._sharedVersion, activeSession?.updatedAt, activeSession?.pipelineStep,
    activeSession?.estadoCompartido, activeSession?.isProcessing, activeSession?.title, activeSession?.documentName,
    activeSession?.documentText, activeSession?.uploadStats?.saved_as, onActiveCaseChange]);
  const reanudarAuditorias = async () => {
    if (reanudandoCaso) return;
    setReanudandoCaso(true); setErrorReanudacion('');
    try {
      // Acción explícita del autor; el servidor comprueba propiedad, rol y versión.
      await apiClient.reanudarCasoCiudadano(activeSession.id);
      await shared.refresh();
    } catch (err) { setErrorReanudacion(err.message); }
    finally { setReanudandoCaso(false); }
  };

  useEffect(() => {
    if (readOnly && initialCaseId) setActiveSessionId(initialCaseId);
  }, [readOnly, initialCaseId]);

  // Save to localStorage on change
  useEffect(() => {
    if (readOnly) return;
    try {
      // Don't store large files in localStorage; just metadata and text
      localStorage.setItem(STORAGE_SESSIONS_KEY, JSON.stringify(sessions));
      localStorage.setItem(STORAGE_ACTIVE_KEY, activeSessionId);
    } catch (err) {
      console.warn('Error saving sessions to localStorage:', err);
    }
  }, [sessions, activeSessionId, readOnly]);

  // Update current session helper
  const updateActiveSession = (patch) => {
    if (readOnly) {
      const vistas = new Set(['inspectedAgentId', 'showEmailPreview', 'showTextoConsolidadoModal', 'textoConsolidadoInfo']);
      patch = Object.fromEntries(Object.entries(patch).filter(([key]) => vistas.has(key)));
    }
    setSessions(prev => prev.map(s => {
      if (s.id === activeSession.id) {
        return { ...s, ...patch };
      }
      return s;
    }));
  };

  // Add new session tab
  const handleAddSession = () => {
    if (readOnly) return;
    const newSession = createDefaultSession(sessions.length + 1);
    setSessions(prev => [...prev, newSession]);
    setActiveSessionId(newSession.id);
  };

  // Remove session tab
  const handleRemoveSession = (e, sessionId) => {
    if (readOnly) return;
    e.stopPropagation();
    if (sessions.length <= 1) {
      // Reset the only remaining session instead of deleting
      const fresh = createDefaultSession(1);
      setSessions([fresh]);
      setActiveSessionId(fresh.id);
      return;
    }

    const filtered = sessions.filter(s => s.id !== sessionId);
    setSessions(filtered);
    if (activeSessionId === sessionId) {
      setActiveSessionId(filtered[0].id);
    }
  };

  // Destructure active session properties for clean local references
  const {
    inputMode,
    documentText,
    documentName,
    uploadStats,
    pipelineStep,
    isProcessing,
    errorMessage,
    fase1Data,
    selectedCategory,
    comisionData,
    dictamenData,
    consistenciaData,
    pdfResult,
    notificadorData,
    showEmailPreview,
    customEmail,
    extraEmailMessage,
    customEmailSubject,
    votosBicameral,
    remitidoPresidente,
    gacetaPdfData,
    showTextoConsolidadoModal,
    textoConsolidadoInfo,
    showDocumentoDebate = false,
    inspectedAgentId,
    // CrewAI extended pipeline
    constitucionFondoData,
    concentradorData,
    secretarioData,
    bicameralData,
    confirmacionBicameralData,
    vetoPromulgacionData,
    publicacionData,
    pipelineLog
  } = activeSession;

  // Helper to append a line to the pipeline log
  const appendLog = (etapa, estado, msg) => {
    const entry = { etapa, estado, msg, ts: new Date().toLocaleTimeString() };
    updateActiveSession({ pipelineLog: [...(activeSession.pipelineLog || []), entry] });
  };

  // Manejar Carga de Archivo
  const handleFileUpload = async (e) => {
    if (readOnly) return;
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    const shortName = selectedFile.name;
    const tabTitle = shortName.length > 22 ? shortName.substring(0, 19) + '...' : shortName;

    updateActiveSession({
      documentName: shortName,
      title: tabTitle,
      isProcessing: true,
      errorMessage: ''
    });

    try {
      const res = await api.uploadDocument(selectedFile);
      updateActiveSession({
        documentText: res.texto_completo,
          informeProfesionalData: res.analisis_profesional || null,
        uploadStats: {
          paginas: res.paginas,
          palabras: res.palabras,
          caracteres: res.caracteres,
          motor: res.motor,
          saved_as: res.saved_as,
          filename: res.filename,
          upload_id: res.upload_id,
          local_path: res.local_path,
          drive_link: res.drive_link,
          drive_file_id: res.drive_file_id,
          drive_status: res.drive_status,
        },
        driveLinkInicial: res.drive_link,
        isProcessing: false
      });
    } catch (err) {
      updateActiveSession({
        errorMessage: err.message || 'Error al procesar el archivo',
        isProcessing: false
      });
    }
  };

  // Iniciar Fase 1: Agente Distribuidor
  const handleIniciarFase1 = async () => {
    if (readOnly) return;
    if (!documentText.trim()) {
      updateActiveSession({ errorMessage: 'Por favor ingrese texto o suba un archivo.' });
      return;
    }

    updateActiveSession({
      isProcessing: true,
      errorMessage: '',
      pipelineStep: 1,
      inspectedAgentId: null
    });

    try {
      const res = await api.runPhase1({
        texto: documentText,
        nombre_archivo: documentName || (inputMode === 'file' ? 'documento.pdf' : 'texto_mesa_partes.txt'),
        tipo_entrada: inputMode === 'file' ? 'Archivo PDF/DOCX' : 'Texto Directo',
        metadata_extra: {
          palabras: uploadStats?.palabras || documentText.split(/\s+/).length,
          caracteres: documentText.length,
          email_autor: activeSession.emailAutor || null,
          nombre_autor: activeSession.nombreAutor || null,
          tipo_iniciativa: activeSession.tipoIniciativa || 'Senado',
          drive_link: activeSession.driveLinkInicial || uploadStats?.drive_link || null,
          drive_file_id: uploadStats?.drive_file_id || null,
        },
      });

      updateActiveSession({
        fase1Data: res.data,
        selectedCategory: res.data.categoria,
        pipelineStep: 2, // Pausa en Control Humano
        isProcessing: false
      });
    } catch (err) {
      updateActiveSession({
        errorMessage: err.message || 'Error durante la clasificación de Fase 1',
        pipelineStep: 0,
        isProcessing: false
      });
    }
  };

  const buildPayload = () => ({
    sesion_id: fase1Data?.sesion_id || '',
    task_id_inicial: fase1Data?.task_id_inicial || 'task_init',
    task_id_distribuidor: fase1Data?.task_id_distribuidor || 'task_dist',
    categoria: selectedCategory || fase1Data?.categoria || 'AGENTE_REGISTRO_LEGISLATIVO',
    agente_destino_nombre: (selectedCategory || fase1Data?.categoria) === 'AGENTE_REGISTRO_LEGISLATIVO'
      ? 'Agente_Comision_Legislativa'
      : (selectedCategory || fase1Data?.categoria) === 'AGENTE_ATENCION_CIUDADANA'
        ? 'Agente_Atencion_Ciudadana'
        : 'Agente_Gestion_Correspondencia',
    texto_documento: documentText || '',
    nombre_archivo: fase1Data?.nombre_archivo || documentName || 'documento.pdf',
    tipo_entrada: fase1Data?.tipo_entrada || 'Texto Directo',
    id_proyecto: fase1Data?.id_proyecto || null,
    solicitud_id: fase1Data?.solicitud_id || null,
    t_inicio_fase1: fase1Data?.t_inicio_fase1 || null,
    local_filepath: uploadStats?.local_path || null,
  });

  const handleEjecutarComision = async () => {
    if (readOnly) return;
    if (!fase1Data) return;
    updateActiveSession({
      isProcessing: true,
      errorMessage: '',
      pipelineStep: 3,
      inspectedAgentId: null
    });
    try {
      if (selectedCategory !== 'AGENTE_REGISTRO_LEGISLATIVO') {
        // Skip direct to end for non-legislative
        updateActiveSession({ pipelineStep: 6, isProcessing: false });
        return;
      }
      const res = await api.runAgentComision(buildPayload());
      updateActiveSession({
        comisionData: res.data,
        pipelineStep: 4,
        isProcessing: false
      });
    } catch (err) {
      updateActiveSession({
        errorMessage: err.message || 'Error en Asignación de Comisión',
        pipelineStep: 2,
        isProcessing: false
      });
    }
  };

  const handleEjecutarConstitucional = async () => {
    if (readOnly) return;
    updateActiveSession({
      isProcessing: true,
      errorMessage: '',
      inspectedAgentId: null
    });
    try {
      const res = await api.runAgentConstitucional(buildPayload());
      const totalPendientes = res.data?.total_pendientes || res.data?.pendientes_revision?.length || 0;
      updateActiveSession({
        dictamenData: res.data,
        pipelineStep: 5,
        isProcessing: false,
        errorMessage: res.data?.estado === 'PENDIENTE_REVISION'
          ? `Constitucional completado con ${totalPendientes} observaciones sujetas a revisión humana.`
          : ''
      });
    } catch (err) {
      updateActiveSession({
        errorMessage: err.message || 'Error en Verificación Constitucional',
        isProcessing: false
      });
    }
  };

  const handleEjecutarConsistencia = async () => {
    if (readOnly) return;
    if (!fase1Data) {
      updateActiveSession({ errorMessage: 'Registra primero el documento en Mesa de Entradas.' });
      return;
    }
    updateActiveSession({
      isProcessing: true,
      errorMessage: '',
      inspectedAgentId: null,
      agentesEnProceso: ['consistencia']
    });
    try {
      const res = await api.runAgentConsistencia(buildPayload());
      if (!res.success || !res.data) {
        throw new Error(res.error || 'Respuesta incompleta del Agente de Consistencia Normativa');
      }
      updateActiveSession({
        consistenciaData: res.data,
        pipelineStep: Math.max(activeSession.pipelineStep || 0, 6),
        isProcessing: false,
        agentesEnProceso: []
      });
      if (res.data.estado === 'PENDIENTE_REVISION') {
        appendLog('Consistencia', 'PENDIENTE_REVISION', `${res.data.total_pendientes || 1} cotejos normativos con observaciones / pendientes de revisión.`);
      } else {
        appendLog('Consistencia', 'COMPLETADO', `Consistencia normativa completada: ${(res.data.hallazgos || []).length} hallazgos.`);
      }
    } catch (err) {
      updateActiveSession({
        errorMessage: err.message || 'Error en Consistencia Normativa',
        isProcessing: false,
        agentesEnProceso: []
      });
      appendLog('Consistencia', 'ERROR', err.message);
    }
  };

  const handleEmitPDF = async () => {
    if (readOnly) return;
    updateActiveSession({
      isProcessing: true,
      errorMessage: '',
      inspectedAgentId: null
    });
    try {
      const res = await api.emitPdf({
        sesion_id: fase1Data.sesion_id,
        datos_constitucionales: dictamenData || { valido: true },
        datos_consistencia: consistenciaData || {}
      });
      updateActiveSession({
        pdfResult: res.data,
        pipelineStep: 7,
        isProcessing: false
      });
    } catch (err) {
      updateActiveSession({
        errorMessage: err.message || 'Error al emitir el reporte PDF',
        isProcessing: false
      });
    }
  };

  const handleNotificar = async () => {
    if (readOnly) return;
    updateActiveSession({
      isProcessing: true,
      errorMessage: '',
      inspectedAgentId: null
    });
    try {
      const res = await api.runAgentNotificador({
        sesion_id: fase1Data.sesion_id,
        id_proyecto: fase1Data.id_proyecto || null,
        datos_comision: comisionData || {},
        datos_constitucionales: dictamenData || {},
        datos_consistencia: consistenciaData || {},
        pdf_filename: pdfResult?.filename || null,
        destinatario_extra: customEmail || null,
        mensaje_extra: extraEmailMessage || null,
        asunto_personalizado: customEmailSubject || null,
      });
      updateActiveSession({
        notificadorData: res.data,
        showEmailPreview: true,
        pipelineStep: 8,
        isProcessing: false
      });
    } catch (err) {
      updateActiveSession({
        errorMessage: err.message || 'Error en Agente Notificador',
        isProcessing: false
      });
    }
  };

  // ── HANDLERS CREWAI — ETAPAS 3-8 ──────────────────────────────────────

  /** Construye proyecto_info desde fase1Data para los agentes CrewAI */
  const buildProyectoInfo = () => ({
    id: fase1Data?.id_proyecto || 1,
    id_proyecto: fase1Data?.id_proyecto || 1,
    titulo: (fase1Data?.titulo && !fase1Data.titulo.toLowerCase().endsWith('.pdf') ? fase1Data.titulo : null)
      || concentradorData?.expediente_consolidado?.titulo
      || (documentName ? documentName.replace(/\.(pdf|docx|txt)$/i, '') : 'Proyecto de Ley'),
    sesion_id: fase1Data?.sesion_id,
    texto_documento: documentText,
  });

  /** Construye lista de observaciones previas para el Concentrador */
  const buildObservaciones = () => {
    const obs = [];
    if (dictamenData?.contradicciones) {
      obs.push({ tipo: 'CONSTITUCIONAL', agente_origen: 'Verificador Constitucional', contenido: JSON.stringify(dictamenData.contradicciones), riesgo: dictamenData.severidad_maxima || 'BAJO' });
    }
    if (consistenciaData?.hallazgos) {
      (consistenciaData.hallazgos || []).forEach(h => obs.push({ tipo: 'CONSISTENCIA', agente_origen: 'Consistencia Normativa', contenido: h.descripcion || '', riesgo: h.nivel_riesgo || 'BAJO' }));
    }
    if (comisionData?.comision_principal) {
      obs.push({ tipo: 'COMISION', agente_origen: 'Comision Legislativa', contenido: `Comision asignada: ${comisionData.comision_principal}`, riesgo: 'BAJO' });
    }
    if (constitucionFondoData?.dictamen_fondo) {
      const df = constitucionFondoData.dictamen_fondo;
      obs.push({ tipo: 'DICTAMEN_FONDO', agente_origen: 'Comision Constitucion Fondo', contenido: df.recomendaciones || '', riesgo: df.riesgo_constitucional || 'BAJO' });
    }
    return obs;
  };

  const handleConstitucionFondo = async () => {
    if (readOnly) return;
    if (!fase1Data) return;
    updateActiveSession({ isProcessing: true, errorMessage: '', pipelineStep: 9, inspectedAgentId: null });
    appendLog('Constitucion_Fondo', 'EN_PROCESO', 'Iniciando analisis hermeneutico constitucional de fondo...');
    try {
      const res = await api.runAgentConstitucionFondo({
        proyecto_info: buildProyectoInfo(),
        texto_proyecto: documentText,
        obs_formales: [],
        id_proyecto: fase1Data?.id_proyecto
      });
      updateActiveSession({ constitucionFondoData: res.data, pipelineStep: 10, isProcessing: false });
      appendLog('Constitucion_Fondo', 'COMPLETADO', `Viabilidad: ${res.data?.dictamen_fondo?.viabilidad_fondo || 'N/A'}`);
    } catch (err) {
      updateActiveSession({ errorMessage: err.message || 'Error en Constitucion Fondo', pipelineStep: 9, isProcessing: false });
      appendLog('Constitucion_Fondo', 'ERROR', err.message);
    }
  };

  const handleConcentrador = async () => {
    if (readOnly) return;
    if (isProcessing) return;
    const tieneCpe = Boolean(
      dictamenData &&
      !dictamenData.error &&
      (dictamenData.analisis || dictamenData.articulos_consultados || dictamenData.estado === 'COMPLETADO' || dictamenData.estado === 'PENDIENTE_REVISION' || dictamenData.dictamen_global || dictamenData.valido !== undefined)
    );
    const tieneNormas = Boolean(
      consistenciaData &&
      !consistenciaData.error &&
      (consistenciaData.hallazgos || consistenciaData.pendientes_revision || consistenciaData.total_hallazgos !== undefined || consistenciaData.estado === 'COMPLETADO' || consistenciaData.estado === 'PENDIENTE_REVISION')
    );
    if (!tieneCpe || !tieneNormas) {
      updateActiveSession({ errorMessage: 'Completa las auditorias constitucional y normativa antes de consolidar.' });
      return;
    }
    if (!fase1Data) return;
    updateActiveSession({ isProcessing: true, errorMessage: '', pipelineStep: 6, inspectedAgentId: null });
    appendLog('Concentrador', 'EN_PROCESO', 'Consolidando todas las observaciones, emitiendo dictamen formal PDF y despachando notificación...');
    try {
      const res = await api.runAgentConcentrador({
        sesion_id: fase1Data?.sesion_id,
        id_proyecto: fase1Data?.id_proyecto,
        proyecto_info: buildProyectoInfo(),
        observaciones: buildObservaciones(),
        datos_constitucionales: dictamenData || {},
        datos_consistencia: consistenciaData || {},
        datos_fondo: constitucionFondoData || {},
        datos_comision: comisionData || {},
        datos_tecnicos: activeSession?.tecnicoData || activeSession?.especialistaTecnicoData || null,
        datos_presupuesto: activeSession?.presupuestoData || activeSession?.planificacionPresupuestoData || null,
        texto_proyecto: documentText,
        titulo_proyecto: documentName,
        notificar: true,
        destinatario_extra: customEmail || null,
        mensaje_extra: extraEmailMessage || null,
        asunto_personalizado: customEmailSubject || null
      });
      const concentradorRes = res.data || {};
      const exp = concentradorRes.expediente_consolidado || {};
      const pdfRes = concentradorRes.pdf || { filename: concentradorRes.pdf_filename };
      const notifRes = concentradorRes.notificacion_comision || {};

      updateActiveSession({
        concentradorData: concentradorRes,
        pdfResult: pdfRes,
        notificadorData: notifRes,
        pipelineStep: 11,
        isProcessing: false
      });
      appendLog('Concentrador', 'COMPLETADO', `Riesgo: ${exp.nivel_riesgo_general || 'MEDIO'} | Dictamen formal PDF emitido y notificado a la comisión`);
    } catch (err) {
      updateActiveSession({ errorMessage: err.message || 'Error en Agente Concentrador, Emisor y Notificador', pipelineStep: 6, isProcessing: false });
      appendLog('Concentrador', 'ERROR', err.message);
    }
  };

  const handleSecretario = async () => {
    if (readOnly) return;
    if (isProcessing || !(concentradorData)) {
      updateActiveSession({ errorMessage: 'Completa el concentrador antes de ejecutar al secretario.' });
      return;
    }
    if (!fase1Data) return;
    updateActiveSession({ isProcessing: true, errorMessage: '', pipelineStep: 11, inspectedAgentId: null });
    appendLog('Secretario', 'EN_PROCESO', 'Registrando debate parlamentario y votaciones...');
    try {
      const res = await api.runAgentSecretario({
        proyecto_info: buildProyectoInfo(),
        debate_data: { expediente_previo: concentradorData?.expediente_consolidado || {}, proyecto_titulo: documentName },
        id_proyecto: fase1Data?.id_proyecto
      });
      updateActiveSession({ secretarioData: res.data, pipelineStep: 12, isProcessing: false });
      const acta = res.data?.acta_debate || {};
      appendLog('Secretario', 'COMPLETADO', `Sesion #${acta.sesion_numero || 1} | ${(acta.votaciones || []).length} votaciones`);
    } catch (err) {
      updateActiveSession({ errorMessage: err.message || 'Error en Secretario', pipelineStep: 11, isProcessing: false });
      appendLog('Secretario', 'ERROR', err.message);
    }
  };

  const handleBicameral = async () => {
    if (readOnly) return;
    if (isProcessing || !(secretarioData)) {
      updateActiveSession({ errorMessage: 'Completa el acta del secretario antes del tramite bicameral.' });
      return;
    }
    if (!fase1Data) return;
    updateActiveSession({ isProcessing: true, errorMessage: '', pipelineStep: 12, inspectedAgentId: null });
    appendLog('Bicameral', 'EN_PROCESO', 'Comparando versiones entre camaras legislativas...');
    try {
      const acta = secretarioData?.acta_debate || {};
      const res = await api.runAgentBicameral({
        proyecto_info: buildProyectoInfo(),
        // Version real del proyecto tal como ingreso (Camara de Origen).
        version_original: { articulos: [documentText], sesion_origen: acta.sesion_numero || 1 },
        // Aun no existe una etapa de edicion real por la Camara Revisora en
        // este sistema; se usa el mismo texto mas los acuerdos del debate,
        // que es lo unico que refleja cambios sugeridos hasta ahora.
        version_retornada: { articulos: [documentText], acuerdos_debate: acta.acuerdos || [], sesion_revision: (acta.sesion_numero || 1) + 1 },
        id_proyecto: fase1Data?.id_proyecto
      });
      updateActiveSession({ bicameralData: res.data, pipelineStep: 13, isProcessing: false });
      const ciclo = res.data?.ciclo_bicameral || {};
      appendLog('Bicameral', 'COMPLETADO', `Cambios: ${ciclo.clasificacion_cambios || 'N/A'} | Ruta: ${ciclo.ruta_siguiente || 'N/A'}`);
    } catch (err) {
      updateActiveSession({ errorMessage: err.message || 'Error en Bicameral', pipelineStep: 12, isProcessing: false });
      appendLog('Bicameral', 'ERROR', err.message);
    }
  };

  /**
   * Confirmación de Aprobación — Trámite Bicameral.
   * La disponible solo para usuarios con rol 'Senador' o 'Diputado'. Al confirmar,
   * se notifica por correo (con el PDF del proyecto y el informe de constitucionalidad
   * y consistencia adjuntos) a todos los usuarios de la cámara opuesta.
   */
  const handleConfirmarAprobacionBicameral = async () => {
    if (readOnly) return;
    if (!fase1Data) return;
    const rol = currentUser?.rol;
    if (rol !== 'Senador' && rol !== 'Diputado') return;

    updateActiveSession({ isProcessing: true, errorMessage: '', inspectedAgentId: null });
    appendLog('Confirmacion_Bicameral', 'EN_PROCESO', `Confirmando aprobacion como ${rol} y notificando a la camara opuesta...`);
    try {
      const res = await api.confirmarAprobacionBicameral({
        rol_remitente: rol,
        titulo_proyecto: documentName || fase1Data?.nombre_archivo || 'Proyecto de Ley',
        sesion_id: fase1Data.sesion_id,
        id_proyecto: fase1Data?.id_proyecto || null,
        nombre_remitente: currentUser?.nombre_completo || null,
        datos_constitucionales: dictamenData || {},
        datos_consistencia: consistenciaData || {},
        pdf_proyecto_filename: uploadStats?.saved_as || null,
        pdf_informe_filename: pdfResult?.filename || null,
      });
      if (!res.success || !res.data) throw new Error(res.error || 'Respuesta de envío incompleta');
      updateActiveSession({ confirmacionBicameralData: {
        ...res.data, id_revision: bicameralData?.ciclo_bicameral?.id_revision,
      }, isProcessing: false });
      if (res.data.status === 'sin_destinatarios') {
        updateActiveSession({ errorMessage: res.data.mensaje });
        appendLog('Confirmacion_Bicameral', 'SIN_DESTINATARIOS', res.data.mensaje);
        return;
      }
      const destino = res.data?.camara_destino || 'la camara opuesta';
      const total = res.data?.total_destinatarios ?? 0;
      appendLog('Confirmacion_Bicameral', 'COMPLETADO', `Notificados ${total} usuario(s) de la Camara de ${destino}s`);
    } catch (err) {
      updateActiveSession({ confirmacionBicameralData: { status: 'error', mensaje: err.message } });
      updateActiveSession({ errorMessage: err.message || 'Error al confirmar la aprobacion bicameral', isProcessing: false });
      appendLog('Confirmacion_Bicameral', 'ERROR', err.message);
    }
  };

  const handleActualizarBicameral = async () => {
    updateActiveSession({ isProcessing: true, errorMessage: '' });
    try {
      const res = await api.getRevisionBicameral(fase1Data.id_proyecto);
      if (!res.success || !res.data?.ciclo_bicameral) throw new Error('Revision bicameral incompleta');
      updateActiveSession({ bicameralData: res.data });
    } catch (err) {
      updateActiveSession({ errorMessage: err.message });
    } finally {
      updateActiveSession({ isProcessing: false });
    }
  };

  const handleResolverBicameral = async (accion, motivo, confirmado) => {
    if (readOnly) return;
    if (isProcessing) return;
    updateActiveSession({ isProcessing: true, errorMessage: '' });
    try {
      const ciclo = bicameralData.ciclo_bicameral;
      await api.decidirBicameral({
        id_proyecto: fase1Data.id_proyecto,
        id_revision: ciclo.id_revision || bicameralData.id_revision,
        version_revision: ciclo.version_revision,
        accion, motivo, confirmacion_exigencias: confirmado,
      });
      const res = await api.getRevisionBicameral(fase1Data.id_proyecto);
      if (!res.success || !res.data?.ciclo_bicameral) throw new Error('No se pudo verificar la decision guardada');
      updateActiveSession({ bicameralData: res.data, pipelineStep: 13 });
      appendLog('Bicameral', 'DECISION_REGISTRADA', accion);
      if (accion === 'APROBAR' && res.data.ciclo_bicameral.aprobacion_humana?.accion === 'APROBAR'
          && !(confirmacionBicameralData?.status === 'notificado'
          && confirmacionBicameralData.id_revision === ciclo.id_revision)) {
        await handleConfirmarAprobacionBicameral();
      }
    } catch (err) {
      updateActiveSession({ errorMessage: err.message });
    } finally {
      updateActiveSession({ isProcessing: false });
    }
  };

  const handleRemitirAlEjecutivo = () => {
    const casoEjecutivo = {
      ...activeSession,
      pipelineStep: 14,
      updatedAt: new Date().toISOString(),
    };
    updateActiveSession({ pipelineStep: 14, updatedAt: casoEjecutivo.updatedAt });
    onActiveCaseChange?.(casoEjecutivo);
    onNavigateEjecutivo?.();
  };

  const handleDevolverComision = async (motivo) => {
    if (isProcessing) return;
    updateActiveSession({ isProcessing: true, errorMessage: '' });
    try {
      const idProyecto = fase1Data?.id_proyecto || activeSession?.proyectoId || 1;
      await api.devolverComision({
        id_proyecto: idProyecto,
        motivo: motivo || 'Devuelto por contradicciones detectadas en trámite bicameral',
        sesion_id: activeSession?.id
      });
      appendLog('Bicameral', 'BUCLE_DEVOLUCION_COMISION', motivo);
      // Regresar visualmente al paso de Comisión / Concentrador (Step 11) con notificación
      updateActiveSession({
        pipelineStep: 11,
        inspectedAgentId: 'concentrador_crew',
        errorMessage: `↩️ Expediente devuelto formalmente a Comisión: "${motivo.substring(0, 120)}..."`,
        isProcessing: false
      });
    } catch (err) {
      updateActiveSession({ errorMessage: err.message, isProcessing: false });
    }
  };

  const handlePublicacion = async () => {
    if (readOnly) return;
    if (isProcessing || vetoPromulgacionData?.evaluacion_veto?.decision !== 'PROMULGAR' || pipelineStep < 14) {
      updateActiveSession({ errorMessage: 'Completa Veto y Promulgacion antes de publicar.' });
      return;
    }
    updateActiveSession({ isProcessing: true, errorMessage: '', pipelineStep: 14, inspectedAgentId: null });
    appendLog('Publicacion', 'EN_PROCESO', 'Registrando publicacion oficial...');
    try {
      const numPersonalizado =
        vetoPromulgacionData?.numero_ley_personalizado ||
        vetoPromulgacionData?.evaluacion_veto?.numero_ley_personalizado ||
        (vetoPromulgacionData?.evaluacion_veto?.referencia_decision?.replace(/\D/g, '') || null) ||
        (vetoPromulgacionData?.referencia_decision?.replace(/\D/g, '') || null);

      const res = await api.runAgentPublicacion({
        proyecto_info: buildProyectoInfo(),
        evaluacion_veto: vetoPromulgacionData,
        id_proyecto: fase1Data?.id_proyecto,
        numero_ley_personalizado: numPersonalizado
      });
      if (!res?.success || !res.data?.publicacion_oficial?.numero_ley || res.data.error) {
        throw new Error(res?.data?.publicacion_oficial?.razon || res?.data?.error || res?.error || 'Publicacion incompleta');
      }
      updateActiveSession({ publicacionData: res.data, pipelineStep: 15, isProcessing: false });
      appendLog('Publicacion', 'COMPLETADO', res.data.publicacion_oficial.numero_ley || 'Publicacion registrada');
    } catch (err) {
      updateActiveSession({ errorMessage: err.message, pipelineStep: 14, isProcessing: false });
      appendLog('Publicacion', 'ERROR', err.message);
    }
  };

  const handleReset = () => {
    if (readOnly) return;
    updateActiveSession({
      documentText: '',
      documentName: '',
      title: `Consulta #${sessions.indexOf(activeSession) + 1}`,
      uploadStats: null,
      fase1Data: null,
      comisionData: null,
      dictamenData: null,
      consistenciaData: null,
      pdfResult: null,
      notificadorData: null,
      showEmailPreview: false,
      customEmail: '',
      pipelineStep: 0,
      errorMessage: '',
      inspectedAgentId: null,
      isProcessing: false,
      constitucionFondoData: null,
      concentradorData: null,
      secretarioData: null,
      bicameralData: null,
      confirmacionBicameralData: null,
      vetoPromulgacionData: null,
      publicacionData: null,
      pipelineLog: []
    });
  };

  // ── Estado del panel lateral deslizante y modal de todos los resultados ──
  const [detailPanelAgent, setDetailPanelAgent] = useState(null);
  const [showAllResultsModal, setShowAllResultsModal] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [chatTab, setChatTab] = useState('sistema'); // 'sistema' | 'agente'
  const [showVozEnChat, setShowVozEnChat] = useState(false);

  // Al seleccionar un agente para inspeccionar, cambiar la pestaña al agente automáticamente
  useEffect(() => {
    if (inspectedAgentId) {
      setChatTab('agente');
    }
  }, [inspectedAgentId]);


  // ── Panel de Correcciones & Actualizaciones Normativas: drawer lateral derecho ──
  const [showCorreccionesDrawer, setShowCorreccionesDrawer] = useState(false);

  // ── Drawer Despacho Institucional (editar correo + mensaje extra + enviar) ──
  const [showEmailDrawer, setShowEmailDrawer] = useState(false);

  // Hook de voz compartido en toda la Mesa de Partes
  const speechHook = useLatinSpeech();

  // Dictado por voz: añade el texto dictado al campo del documento (Distribuidor)
  const handleDictadoVoz = (textoDict) => {
    if (readOnly) return;
    if (!textoDict) return;
    updateActiveSession({
      documentText: (documentText ? documentText + ' ' : '') + textoDict,
    });
  };

  // Acciones ejecutables que el chatbot orquestador puede disparar por voz/texto.
  // Las acciones "leer_*" no necesitan handler: el chat las responde con TTS
  // usando los datos de contexto del agente.
  const CHAT_ACTION_HANDLERS = {
    ejecutar_fase_1_clasificacion: handleIniciarFase1,
    cancelar_pipeline: handleReset,
    asignar_comision: handleEjecutarComision,
    ejecutar_verificacion_constitucional: handleEjecutarConstitucional,
    ejecutar_consistencia_normativa: handleEjecutarConsistencia,
    generar_dictamen_pdf: handleEmitPDF,
    enviar_notificacion_comision: handleNotificar,
    notificar_correcciones_autor: handleNotificar,
    evaluar_fondo_constitucional: handleConstitucionFondo,
    sintetizar_expediente: handleConcentrador,
    firmar_acta_debate: handleSecretario,
    registrar_aprobacion_grande: handleSecretario,
    registrar_aprobacion_detalle: handleSecretario,
    iniciar_ciclo_bicameral: handleBicameral,
    confirmar_aprobacion_bicameral: handleConfirmarAprobacionBicameral,
    evaluar_veto_promulgacion: () => onNavigateEjecutivo?.(),
    autorizar_promulgacion: () => onNavigateEjecutivo?.(),
    registrar_veto: () => onNavigateEjecutivo?.(),
    publicar_gaceta_oficial: handlePublicacion,
    asignar_numero_ley: handlePublicacion,
  };

  // Callback del AgentChatPanel: ejecuta el paso del pipeline decidido por el orquestador
  const handleChatAccion = (accion, agenteDestino) => {
    if (readOnly) return;
    const handler = CHAT_ACTION_HANDLERS[accion];
    const origen = inspectedAgentId || 'orquestador';
    if (handler) {
      appendLog(origen, 'CHAT', `Acción desde chat: ${accion} → ${agenteDestino}`);
      handler();
    } else {
      appendLog(origen, 'CHAT', `Acción informativa (sin paso ejecutable): ${accion} → ${agenteDestino}`);
    }
  };

  // Obtener resultado del agente para mostrarlo en el panel
  const getAgentResultData = (agentId) => {
    const map = {
      distribuidor: fase1Data,
      comision: comisionData,
      constitucional: dictamenData,
      consistencia: consistenciaData,
      emisor: pdfResult,
      notificador: notificadorData,
      constitucion_fondo: constitucionFondoData,
      concentrador: concentradorData,
      concentrador_crew: concentradorData,
      secretario: secretarioData,
      bicameral: bicameralData,
      veto_promulgacion: vetoPromulgacionData,
      publicacion: publicacionData,
    };
    return map[agentId] || null;
  };

  // Agent Selection — abre el panel lateral Y también actualiza inspección
  const handleSelectAgent = (agent) => {
    if (!readOnly && !getAgentResultData(agent.id)) {
      setDetailPanelAgent(agent);
      return;
    }
    setDetailPanelAgent(null);
    updateActiveSession({ inspectedAgentId: agent.id });
  };

  const handleCloseDetailPanel = () => {
    setDetailPanelAgent(null);
  };

  // ── AUDITORÍA PARALELA MULTIHILO: Constitucionalidad CPE y Consistencia Normativa ──
  const handleEjecutarAuditoriaParalela = async () => {
    if (readOnly) return;
    if (!fase1Data) return;
    updateActiveSession({
      isProcessing: true,
      errorMessage: '',
      pipelineStep: 4,
      inspectedAgentId: null,
      agentesEnProceso: ['constitucional', 'consistencia']
    });
    appendLog('Auditoria_Paralela', 'EN_PROCESO', 'Iniciando auditorías paralelas: Constitucionalidad CPE y Consistencia Normativa.');
    try {
      const payload = buildPayload();
      const ejecutar = async (nombre, campo, llamada, presupuestoSegundos = 240) => {
        try {
          const res = await llamada({ ...payload, presupuesto_segundos: presupuestoSegundos });
          if (!res.success || !res.data || res.data.error) {
            throw new Error(`${nombre}: ${res.data?.error || res.error || 'Respuesta incompleta'}`);
          }
          updateActiveSession({ [campo]: res.data });
          if (res.data.estado === 'PENDIENTE_REVISION') {
            appendLog(nombre, 'PENDIENTE_REVISION', `${res.data.total_pendientes || 1} cotejos sin completar`);
          } else {
            appendLog(nombre, 'COMPLETADO', 'Análisis terminado. Resultado disponible.');
          }
          return res.data;
        } catch (e) {
          const detalle = e.message || `Error en ${nombre}`;
          const fallback = {
            estado: 'PENDIENTE_REVISION',
            error: detalle,
            confianza: 0,
            pendientes_revision: [{ motivo: detalle }]
          };
          updateActiveSession({ [campo]: fallback });
          appendLog(nombre, 'ERROR', detalle);
          return fallback;
        }
      };

      const [cpeData, normasData] = await Promise.all([
        ejecutar('Constitucional', 'dictamenData', api.runAgentConstitucional, 240),
        ejecutar('Consistencia', 'consistenciaData', api.runAgentConsistencia, 240)
      ]);

      updateActiveSession({
        dictamenData: cpeData,
        consistenciaData: normasData,
        pipelineStep: 6,
        isProcessing: false,
        agentesEnProceso: []
      });
      appendLog('Auditoria_Paralela', 'COMPLETADO', 'Ambas auditorías concluidas.');
    } catch (err) {
      updateActiveSession({
        errorMessage: err.message || 'Error en auditorías paralelas',
        pipelineStep: 4,
        isProcessing: false,
        agentesEnProceso: []
      });
      appendLog('Auditoria_Paralela', 'ERROR', err.message);
    }
  };

  // Active agent object determination (preciso para los 9 agentes del pipeline)
  const getActiveAgentDef = () => {
    if (readOnly && !inspectedAgentId && activeSession.agentesEnProceso?.length) {
      return AGENTS_DEFINITION.find(a => a.id === activeSession.agentesEnProceso[0]) || AGENTS_DEFINITION[0];
    }
    if (inspectedAgentId) return AGENTS_DEFINITION.find(a => a.id === inspectedAgentId) || AGENTS_DEFINITION[0];
    if (isProcessing && pipelineStep >= 11 && pipelineStep <= 14) {
      const id = { 11: 'secretario', 12: 'bicameral', 13: 'bicameral', 14: 'publicacion' }[pipelineStep];
      return AGENTS_DEFINITION.find(a => a.id === id);
    }
    if (pipelineStep <= 2) return AGENTS_DEFINITION.find(a => a.id === 'distribuidor') || AGENTS_DEFINITION[0];
    if (pipelineStep <= 4) return AGENTS_DEFINITION.find(a => a.id === 'comision') || AGENTS_DEFINITION[1];
    if (pipelineStep === 5) return AGENTS_DEFINITION.find(a => a.id === 'constitucional') || AGENTS_DEFINITION[2];
    if (pipelineStep === 6 && !isProcessing) return AGENTS_DEFINITION.find(a => a.id === 'consistencia') || AGENTS_DEFINITION[3];
    if (pipelineStep === 7 || pipelineStep === 8 || pipelineStep === 11 || (pipelineStep === 6 && isProcessing)) {
      return AGENTS_DEFINITION.find(a => a.id === 'concentrador') || AGENTS_DEFINITION[4];
    }
    if (pipelineStep <= 10) return AGENTS_DEFINITION.find(a => a.id === 'constitucional') || AGENTS_DEFINITION[2];
    if (pipelineStep === 12) return AGENTS_DEFINITION.find(a => a.id === 'secretario') || AGENTS_DEFINITION[5];
    if (pipelineStep === 13) return AGENTS_DEFINITION.find(a => a.id === 'bicameral') || AGENTS_DEFINITION[6];
    if (pipelineStep === 14) return AGENTS_DEFINITION.find(a => a.id === 'publicacion') || AGENTS_DEFINITION[7];
    return AGENTS_DEFINITION.find(a => a.id === 'publicacion') || AGENTS_DEFINITION[7];
  };
  const activeAgentDef = getActiveAgentDef();
  const activeLogoUrl = AGENT_LOGO_MAP[activeAgentDef?.id] || '/robots/logos/agente_distribuidor.jpeg';
  const activeAccent = AGENT_ACCENT_MAP[activeAgentDef?.id] || '#00B4D8';

  // ── Renderiza el contenedor superior dedicado (RECUADRO ROJO): Logo más grande (104px) + Nombre del agente destacado ──
  const renderAgentHeaderContainer = () => {
    const isAgentDone = !!getAgentResultData(activeAgentDef?.id);

    return (
      <div style={{
        background: 'linear-gradient(135deg, #ffffff 0%, #f2f8fc 58%, #eaf4fa 100%)',
        border: `1.5px solid ${isAgentDone ? '#8AC92688' : `${activeAccent}66`}`,
        borderRadius: '20px',
        padding: 'clamp(14px, 2.5vw, 22px) clamp(16px, 3vw, 28px)',
        boxShadow: isAgentDone
          ? `0 8px 24px rgba(24,58,86,0.08), 0 0 20px rgba(138,201,38,0.16)`
          : `0 8px 24px rgba(24,58,86,0.08), 0 0 20px ${activeAccent}22`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '20px',
        position: 'relative',
        overflow: 'hidden',
        backdropFilter: 'blur(16px)',
        flexWrap: 'wrap'
      }}>
        {/* Línea superior iluminada */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '3px',
          background: isAgentDone
            ? 'linear-gradient(90deg, transparent 0%, #8AC926 50%, transparent 100%)'
            : `linear-gradient(90deg, transparent 0%, ${activeAccent} 50%, transparent 100%)`
        }} />

        {/* Lado izquierdo: Fase, Nombre en grande, Rol */}
        <div style={{ flex: 1, minWidth: 'min(100%, 260px)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(14,116,176,.08)',
              border: '1px solid #b7d5e5',
              borderRadius: '6px',
              padding: '4px 12px',
              fontSize: '0.72rem',
              fontWeight: 800,
              color: '#176b9b',
              letterSpacing: '0.09em',
              textTransform: 'uppercase'
            }}>
              <Shield size={12} />
              <span>{activeAgentDef?.phaseName || 'Fase 1: Admisión'}</span>
            </div>

            {/* Checkmark de flujo ajustado y completado */}
            {isAgentDone && (
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                background: 'rgba(138, 201, 38, 0.18)',
                border: '1px solid rgba(138, 201, 38, 0.5)',
                borderRadius: '6px',
                padding: '4px 10px',
                fontSize: '0.72rem',
                fontWeight: 800,
                color: '#8AC926',
                letterSpacing: '0.05em'
              }}>
                <CheckCircle2 size={13} color="#8AC926" strokeWidth={2.5} />
                <span>Flujo Ajustado y Completado</span>
              </div>
            )}
          </div>

          <h2 style={{
            fontSize: 'clamp(1.3rem, 3.2vw, 2.1rem)',
            fontWeight: 900,
            color: '#123B60',
            fontFamily: 'Outfit, sans-serif',
            lineHeight: 1.15,
            margin: '0 0 6px 0',
            letterSpacing: '0.01em',
            textShadow: 'none'
          }}>
            {activeAgentDef?.name}
          </h2>

          <div style={{
            fontSize: '0.9rem',
            color: '#4B6B84',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <span style={{ color: '#1592ca', fontWeight: 800 }}>•</span>
            <span>{activeAgentDef?.role}</span>
          </div>
        </div>

        {/* Lado derecho: Logo circular adaptativo con aro institucional */}
        <div style={{ position: 'relative', flexShrink: 0 }}>
          {/* Anillo de resplandor orbital */}
          <div style={{
            position: 'absolute',
            inset: '-6px',
            borderRadius: '50%',
            border: `2px dashed ${isAgentDone ? '#8AC92677' : `${activeAccent}77`}`,
            animation: isProcessing ? 'spin 4s linear infinite' : 'none',
            pointerEvents: 'none'
          }} />

          <div style={{
            width: 'clamp(68px, 9vw, 104px)',
            height: 'clamp(68px, 9vw, 104px)',
            borderRadius: '50%',
            border: `3.5px solid ${isAgentDone ? '#8AC926' : activeAccent}`,
            boxShadow: isAgentDone
              ? `0 0 32px rgba(138,201,38,0.5), 0 8px 26px rgba(0,0,0,0.65)`
              : `0 0 32px ${activeAccent}77, 0 8px 26px rgba(0,0,0,0.65)`,
            overflow: 'hidden',
            background: '#0B2545',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative'
          }}>
            <img
              src={activeLogoUrl}
              alt={activeAgentDef?.name}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                filter: 'brightness(1.05)'
              }}
            />
          </div>

          {/* Badge con Check sobre el logo cuando ya se ejecutó/ajustó */}
          {isAgentDone && (
            <div style={{
              position: 'absolute',
              bottom: '2px',
              right: '2px',
              background: '#8AC926',
              borderRadius: '50%',
              width: '28px',
              height: '28px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '2.5px solid #0B2545',
              boxShadow: '0 0 12px rgba(138,201,38,0.85)',
              zIndex: 6
            }}>
              <CheckCircle2 size={16} color="#0B2545" strokeWidth={3} />
            </div>
          )}
        </div>
      </div>
    );
  };

  // Inspection step map (extended — con fusión de Concentrador, Emisor y Notificador)
  const inspectStepMap = {
    distribuidor: 2, comision: 4, constitucional: 5, consistencia: 6,
    emisor: 11, notificador: 11, concentrador: 11, concentrador_crew: 11,
    constitucion_fondo: 5, secretario: 12, bicameral: 13, veto_promulgacion: 14, publicacion: 15
  };
  const effectiveViewStep = inspectedAgentId ? (inspectStepMap[inspectedAgentId] || pipelineStep) : pipelineStep;
  useEffect(() => {
    if (!inspectedAgentId) return;
    const frame = requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    return () => cancelAnimationFrame(frame);
  }, [inspectedAgentId, activeSession.id]);

  return (
    <div className="mesa-page" style={{ maxWidth: '1720px', width: '96%', margin: '0 auto', padding: 'clamp(12px, 2vw, 24px) clamp(12px, 2vw, 24px) 80px' }}>
      {/* ── MODAL GLOBAL DE TODOS LOS RESULTADOS DE AGENTES ── */}
      <AllAgentsResultsModal
        isOpen={showAllResultsModal}
        onClose={() => setShowAllResultsModal(false)}
        pipelineStep={pipelineStep}
        isProcessing={isProcessing}
        activeAgentDef={activeAgentDef}
        getAgentResultData={getAgentResultData}
        onInspectAgent={(agent) => {
          handleSelectAgent(agent);
          setShowAllResultsModal(false);
        }}
      />

      {/* ── PANEL LATERAL DESLIZANTE ── */}
      {detailPanelAgent && (
        <AgentDetailPanel
          agent={detailPanelAgent}
          pipelineStep={pipelineStep}
          resultData={getAgentResultData(detailPanelAgent.id)}
          pipelineLog={pipelineLog || []}
          onClose={handleCloseDetailPanel}
        />
      )}

      {/* ── HEADER INSTITUCIONAL ── */}
      <div className="mesa-institutional-header" style={{
        marginBottom: '20px',
        background: 'rgba(11,37,69,0.7)',
        border: '1px solid rgba(0,180,216,0.2)',
        borderRadius: '18px',
        padding: '22px 28px',
        backdropFilter: 'blur(12px)',
        position: 'relative',
        overflow: 'hidden'
      }}>
        {/* Ambient glow */}
        <div style={{
          position: 'absolute', top: '-40px', right: '-40px', width: '200px', height: '200px',
          borderRadius: '50%', background: 'rgba(0,180,216,0.08)', filter: 'blur(60px)', pointerEvents: 'none'
        }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px', flexWrap: 'wrap' }}>
          <span className="badge badge-blue" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Shield size={12} /> Mesa de Partes Virtual
          </span>
          <span className="badge badge-gold" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Zap size={12} /> Flujo Multi-Agente · Paralelo
          </span>
          <span className="badge badge-green" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <CheckCircle2 size={12} /> Persistencia Automática
          </span>

          {/* Botón destacado en el header para ver todos los resultados */}
          <button
            onClick={() => setShowAllResultsModal(true)}
            style={{
              marginLeft: 'auto',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #0284C7 0%, #00B4D8 100%)',
              border: '1px solid rgba(0, 180, 216, 0.6)',
              color: '#FFFFFF',
              fontWeight: 800,
              fontSize: '0.78rem',
              cursor: 'pointer',
              boxShadow: '0 2px 12px rgba(0, 180, 216, 0.4)',
              transition: 'all 0.2s ease',
              fontFamily: 'Outfit, sans-serif'
            }}
            title="Visualizar en cualquier momento los resultados de todos los agentes ejecutados"
          >
            <Eye size={15} />
            <span>Ver Todos los Resultados ({AGENTS_DEFINITION.filter(a => getAgentResultData(a.id)).length})</span>
          </button>
        </div>
        <h1 style={{
          fontSize: '1.9rem', fontWeight: 800, color: '#FFFFFF', marginBottom: '6px',
          letterSpacing: '-0.02em', fontFamily: 'Outfit, sans-serif',
          textShadow: '0 2px 12px rgba(0,180,216,0.3)'
        }}>
          Auditoría Automática de Documentos Legislativos
        </h1>
        <p style={{ color: '#94A3B8', fontSize: '0.92rem', maxWidth: '800px', lineHeight: 1.55, margin: 0 }}>
          Procese múltiples expedientes en simultáneo con flujo paralelo. Los agentes de Verificación Constitucional y Consistencia Normativa ejecutan de forma simultánea. Haga clic en cualquier agente para ver su detalle.
        </p>
      </div>

      {/* Bandeja y comandos compactos al lado; flujo y resultados en el área central. */}
      <div className="mesa-sidebar-workspace">
        <aside className="mesa-process-sidebar" aria-label="Bandeja de ingreso y comandos">
          <div className="command-panel-heading"><span>Mesa de comandos</span><span className="command-stage">Etapa {pipelineStep}</span></div>
          <label htmlFor="active-process-select">Expediente activo</label>
          <select id="active-process-select" value={activeSession.id} onChange={e => setActiveSessionId(e.target.value)}>
            {sessions.map((ses, idx) => <option key={ses.id} value={ses.id}>{ses.title || ses.documentName || `Consulta #${idx + 1}`} · {ses.camaraDestino || ses.tipoIniciativa || 'Sin destino'}</option>)}
          </select>
          {!readOnly && <button type="button" onClick={handleAddSession} className="sidebar-new-case"><Plus size={15} />Nuevo expediente</button>}
          {!readOnly && (() => {
            const inbox = sessions.filter(s => s._sharedVersion && (s.documentText || s.fase1Data));
            const filtered = inbox.filter(s => {
              const q = inboxSearch.trim().toLocaleLowerCase();
              const target = s.camaraDestino || s.tipoIniciativa || 'Ambas';
              return (!q || [s.id, s.title, s.documentName, s.autorCaso, s.nombreAutor].some(v => String(v || '').toLocaleLowerCase().includes(q)))
                && (inboxDestination === 'Todas' || target === inboxDestination || target === 'Ambas');
            }).sort((a, b) => new Date(b.updatedAt || b.createdAt || 0) - new Date(a.updatedAt || a.createdAt || 0));
            const isActive = s => Boolean(s.isProcessing || s._sharedProcessing);
            const needsReview = s => Boolean(s.errorMessage || s.estadoCompartido === 'REQUIERE_REVISION');
            return <details className="sidebar-inbox">
              <summary>Solicitudes entrantes <span className="inbox-total">{inbox.length}</span><small>{inbox.filter(isActive).length} activas · {inbox.filter(needsReview).length} por revisar</small></summary>
              <div className="sidebar-inbox-counts"><span>{inbox.filter(isActive).length} en ejecución</span><span>{inbox.filter(needsReview).length} por revisar</span></div>
              <input aria-label="Buscar solicitudes entrantes" value={inboxSearch} onChange={e => setInboxSearch(e.target.value)} placeholder="Buscar expediente o solicitante" />
              <select aria-label="Filtrar solicitudes por cámara" value={inboxDestination} onChange={e => setInboxDestination(e.target.value)}><option>Todas</option><option>Diputados</option><option>Senadores</option></select>
              <div className="sidebar-inbox-list">
                {filtered.slice(0, 8).map(s => <button type="button" key={s.id} className={`sidebar-inbox-item ${s.id === activeSession.id ? 'selected' : ''}`} onClick={() => setActiveSessionId(s.id)}>
                  <strong>{s.title || s.documentName || 'Sin título'}</strong><small>{s.id} · {s.camaraDestino || s.tipoIniciativa || 'Sin destino'}</small><span>{needsReview(s) ? 'Requiere revisión' : isActive(s) ? 'En ejecución' : s.estadoCompartido || (s.fase1Data ? 'En seguimiento' : 'Recibido')}</span>
                </button>)}
                {!filtered.length && <p className="sidebar-inbox-empty">{shared.ready ? 'No hay solicitudes que coincidan.' : 'Cargando solicitudes registradas…'}</p>}
                {filtered.length > 8 && <small className="sidebar-inbox-more">Mostrando 8 de {filtered.length}; busca para localizar otro expediente.</small>}
              </div>
              <button type="button" className="sidebar-refresh" onClick={shared.refresh}>Actualizar bandeja</button>
              {shared.error && <p role="alert" className="sidebar-error">{shared.error}</p>}
            </details>;
          })()}
          <details className="revision-panel command-status-panel sidebar-sync-panel" aria-live="polite">
            <summary>Sincronización y estado</summary>
            <strong>{readOnly ? 'Seguimiento ciudadano' : 'Casos compartidos'}</strong>
            <CaseProcessingStatus caso={activeSession} onReanudar={reanudarAuditorias} reanudando={reanudandoCaso} />
            {errorReanudacion && <p role="alert">{errorReanudacion}</p>}
            {readOnly && <p>El seguimiento se actualiza automáticamente; la continuación corresponde al diputado o senador.</p>}
            {readOnly && activeSession.agentesEnProceso?.length > 0 && <p role="status">En acción: {activeSession.agentesEnProceso.map(id => AGENTS_DEFINITION.find(a => a.id === id)?.name || id).join(' y ')}</p>}
            {readOnly && activeSession.errorMessage && <p role="alert">{activeSession.errorMessage}</p>}
            {readOnly && activeSession.avisos?.map((aviso, i) => <p role="status" key={i}>{aviso}</p>)}
            {readOnly && inspectedAgentId && !getAgentResultData(inspectedAgentId) && <p role="status">Este agente todavía no tiene un resultado disponible.</p>}
            <p>{shared.error || (shared.saving ? 'Guardando en el servidor…' : shared.ready ? 'Casos sincronizados en el servidor.' : 'Conectando al servidor de casos…')}</p>
            <button type="button" className="sidebar-refresh" onClick={shared.refresh}>Actualizar casos</button>
          </details>
          <button type="button" className="sidebar-results-button" onClick={() => setShowAllResultsModal(true)}><Eye size={15} />Ver todos los resultados ({AGENTS_DEFINITION.filter(a => getAgentResultData(a.id)).length})</button>
        </aside>
        <main className="mesa-workbench-main">
          <HorizontalAgentFlow
            activeAgentIds={activeSession._sharedProcessing ? activeSession.agentesEnProceso : undefined}
            completedAgentIds={readOnly ? AGENTS_DEFINITION.filter(a => getAgentResultData(a.id)).map(a => a.id) : undefined}
            pipelineStep={pipelineStep}
            inspectedAgentId={inspectedAgentId}
            onSelectAgent={handleSelectAgent}
            onOpenAllResults={() => setShowAllResultsModal(true)}
          />
          {(fase1Data || dictamenData || consistenciaData) && <AuditResultsNav
            constitucional={dictamenData} consistencia={consistenciaData} selected={inspectedAgentId}
            onSelect={id => handleSelectAgent(AGENTS_DEFINITION.find(agent => agent.id === id))} />}
      {/* ── INSPECTION BANNER ── */}
      {inspectedAgentId && (
        <div style={{
          background: 'linear-gradient(90deg, rgba(11,37,69,0.9) 0%, rgba(15,23,42,0.95) 100%)',
          border: '1.5px solid rgba(0,180,216,0.4)',
          borderRadius: '14px',
          padding: '12px 20px',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          boxShadow: '0 4px 18px rgba(0,180,216,0.2)',
          backdropFilter: 'blur(8px)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Eye size={18} color="#00B4D8" />
            <div>
              <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#F1F5F9' }}>
                Modo Inspección: <strong style={{ color: '#00B4D8' }}>{activeAgentDef.name}</strong>
              </div>
              <div style={{ fontSize: '0.74rem', color: '#64748B' }}>
                Paso actual: {pipelineStep}. Revise los resultados de agentes anteriores sin perder el progreso.
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => { setShowChat(true); setChatTab('agente'); }}
              style={{
                padding: '6px 12px', fontSize: '0.78rem', borderRadius: '8px',
                background: 'rgba(0,180,216,0.15)', border: '1px solid rgba(0,180,216,0.35)',
                color: '#00B4D8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px',
                fontFamily: 'Outfit, sans-serif', fontWeight: 600
              }}
              title="Abrir chat emergente con este agente"
            >
              <MessagesSquare size={13} /> Chat Agente
            </button>
            <button
              onClick={() => setDetailPanelAgent(activeAgentDef)}
              style={{
                padding: '6px 12px', fontSize: '0.78rem', borderRadius: '8px',
                background: 'rgba(0,180,216,0.15)', border: '1px solid rgba(0,180,216,0.35)',
                color: '#00B4D8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px',
                fontFamily: 'Outfit, sans-serif', fontWeight: 600
              }}
            >
              <Eye size={13} /> Ver Detalle
            </button>
            <button
              onClick={() => updateActiveSession({ inspectedAgentId: null })}
              style={{
                padding: '6px 12px', fontSize: '0.78rem', borderRadius: '8px',
                background: 'rgba(2,132,199,0.2)', border: '1px solid rgba(2,132,199,0.4)',
                color: '#38BDF8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px',
                fontFamily: 'Outfit, sans-serif', fontWeight: 600
              }}
            >
              <EyeOff size={13} /> Volver
            </button>
          </div>
        </div>
      )}

      <div ref={resultsRef} style={{ scrollMarginTop: 100 }} />
      {/* ── ERROR ALERT ── */}
      {errorMessage && (
        <div className="glass-card" style={{
          padding: '16px 20px',
          background: '#fef2f2',
          border: '1px solid #fecaca',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          color: '#991b1b'
        }}>
          <AlertTriangle size={22} color="#dc2626" />
          <div style={{ flex: 1, fontSize: '0.95rem', fontWeight: 600 }}>{errorMessage}</div>
          <button className="btn-secondary" onClick={() => updateActiveSession({ errorMessage: '' })} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
            Descartar
          </button>
        </div>
      )}

      {/* ── STEP 0: DOCUMENT UPLOAD & INPUT ── */}
      {effectiveViewStep === 0 && !readOnly && (
        <div className="mesa-layout-grid">
          {/* Columna Izquierda: Banner Nítido sin recuadros */}
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={isProcessing}
            />
          </div>

          {/* Columna Derecha */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* ── CONTENEDOR SUPERIOR DEDICADO: LOGO MÁS GRANDE (104px) Y NOMBRE EN GRANDE ── */}
            {renderAgentHeaderContainer()}

            {/* Formulario de Carga y Entrada de Texto */}
            <div className="glass-card" style={{ padding: '32px' }}>
              <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', borderBottom: '1px solid rgba(0, 180, 216, 0.2)', paddingBottom: '16px' }}>
                <button
                  onClick={() => updateActiveSession({ inputMode: 'file' })}
                  className={inputMode === 'file' ? 'btn-primary' : 'btn-secondary'}
                >
                  <UploadCloud size={18} />
                  <span>Subir Archivo (PDF / DOCX)</span>
                </button>
                <button
                  onClick={() => updateActiveSession({ inputMode: 'text' })}
                  className={inputMode === 'text' ? 'btn-primary' : 'btn-secondary'}
                >
                  <FileText size={18} />
                  <span>Pegar Texto Directo</span>
                </button>
              </div>

              {inputMode === 'file' ? (
                <div>
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    accept=".pdf,.docx,.doc,.txt"
                    style={{ display: 'none' }}
                  />
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    style={{
                      border: '2px dashed rgba(0, 180, 216, 0.4)',
                      borderRadius: '16px',
                      padding: '44px 24px',
                      textAlign: 'center',
                      cursor: 'pointer',
                      background: 'rgba(11, 37, 69, 0.6)',
                      transition: 'all 0.25s ease',
                      marginBottom: '20px',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = '#00B4D8';
                      e.currentTarget.style.background = 'rgba(19, 64, 116, 0.5)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(0, 180, 216, 0.4)';
                      e.currentTarget.style.background = 'rgba(11, 37, 69, 0.6)';
                    }}
                  >
                    <UploadCloud size={46} color="#00B4D8" style={{ margin: '0 auto 14px' }} />
                    <h3 style={{ color: '#F1F5F9', fontSize: '1.2rem', fontWeight: 700, marginBottom: '6px' }}>
                      {documentName || 'Haz clic aquí para seleccionar tu archivo'}
                    </h3>
                    <p style={{ color: '#94A3B8', fontSize: '0.88rem' }}>
                      Soporta formatos PDF, DOCX o archivos de texto plano (.txt)
                    </p>
                  </div>

                  {uploadStats && (
                    <div style={{
                      display: 'flex',
                      gap: '20px',
                      background: 'rgba(15, 23, 42, 0.7)',
                      padding: '16px 20px',
                      borderRadius: '12px',
                      border: '1px solid rgba(0, 180, 216, 0.25)',
                      marginBottom: '24px',
                      flexWrap: 'wrap'
                    }}>
                      <div>
                        <span style={{ fontSize: '0.75rem', color: '#94A3B8', textTransform: 'uppercase', fontWeight: 600 }}>Páginas:</span>
                        <strong style={{ display: 'block', color: '#F8FAFC', fontSize: '1.15rem' }}>{uploadStats.paginas}</strong>
                      </div>
                      <div>
                        <span style={{ fontSize: '0.75rem', color: '#94A3B8', textTransform: 'uppercase', fontWeight: 600 }}>Palabras:</span>
                        <strong style={{ display: 'block', color: '#F8FAFC', fontSize: '1.15rem' }}>{uploadStats.palabras.toLocaleString()}</strong>
                      </div>
                      <div>
                        <span style={{ fontSize: '0.75rem', color: '#94A3B8', textTransform: 'uppercase', fontWeight: 600 }}>Caracteres:</span>
                        <strong style={{ display: 'block', color: '#F8FAFC', fontSize: '1.15rem' }}>{uploadStats.caracteres.toLocaleString()}</strong>
                      </div>
                      <div>
                        <span style={{ fontSize: '0.75rem', color: '#94A3B8', textTransform: 'uppercase', fontWeight: 600 }}>Motor:</span>
                        <strong style={{ display: 'block', color: '#8AC926', fontSize: '1.15rem' }}>{uploadStats.motor}</strong>
                      </div>
                      {uploadStats.drive_link && (
                        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
                          <a
                            href={uploadStats.drive_link}
                            target="_blank"
                            rel="noreferrer"
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              background: 'rgba(16, 185, 129, 0.2)',
                              border: '1px solid rgba(16, 185, 129, 0.45)',
                              color: '#34d399',
                              padding: '8px 14px',
                              borderRadius: '8px',
                              fontSize: '0.82rem',
                              fontWeight: 700,
                              textDecoration: 'none'
                            }}
                          >
                            <ExternalLink size={15} />
                            <span>Guardado en Google Drive</span>
                          </a>
                        </div>
                      )}
                    </div>
                  )}
                  {activeSession.informeProfesionalData && <div style={{ padding: 14, marginTop: 12, border: '1px solid #38bdf8', borderRadius: 10 }}>
                    <strong>Facetas profesionales del documento</strong>
                    <p>{activeSession.informeProfesionalData.profesiones?.join(' · ') ||
                      (activeSession.informeProfesionalData.estado === 'NO_APLICA' ? 'No requiere las especialidades del catálogo.' : 'Revisión pendiente.')}</p>
                    {activeSession.informeProfesionalData.cobertura_parcial && <p>Se revisó una muestra distribuida del documento por su extensión.</p>}
                    {activeSession.informeProfesionalData.error && <p role="status">{activeSession.informeProfesionalData.error}</p>}
                    {activeSession.informeProfesionalData.facetas?.map(f => <details key={f.profesion}>
                      <summary>{f.profesion} · {f.estado === 'COMPLETADO' ? 'Aporte disponible' : 'Revisión pendiente'}</summary>
                      <p>{f.motivo}</p><p style={{ whiteSpace: 'pre-wrap' }}>{f.informe || f.error}</p>
                      <ul>{f.fuentes?.map(s => <li key={s.referencia}>[{s.referencia}] {s.titulo}, página PDF {s.pagina}</li>)}</ul>
                    </details>)}
                  </div>}
                </div>
              ) : (
                <div style={{ marginBottom: '24px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <label style={{ color: '#94A3B8', fontSize: '0.92rem', fontWeight: 600 }}>
                      Contenido del Documento o Proyecto:
                    </label>
                    <div style={{ fontSize: '0.78rem', color: '#00B4D8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Mic size={14} />
                      <span>Dictado por voz habilitado</span>
                    </div>
                  </div>

                  {/* Asistente de Voz: Dictado de Documento */}
                  <div style={{ marginBottom: '14px' }}>
                    {!readOnly && (<AgentVoiceModule
                      agentId="distribuidor"
                      agentLabel="Agente Distribuidor"
                      primaryColor="#00B4D8"
                      sesionId={fase1Data?.sesion_id || null}
                      speechHook={speechHook}
                      onDictadoText={handleDictadoVoz}
                      compact={true}
                    />)}
                  </div>
                  <textarea
                    value={documentText}
                    onChange={(e) => updateActiveSession({ documentText: e.target.value })}
                    placeholder="Pegue aquí el texto completo del proyecto de ley o solicitud..."
                    rows={9}
                    style={{
                      width: '100%',
                      background: 'rgba(15, 23, 42, 0.8)',
                      border: '1px solid rgba(0, 180, 216, 0.3)',
                      borderRadius: '12px',
                      padding: '16px',
                      color: '#F1F5F9',
                      fontFamily: 'monospace',
                      fontSize: '0.9rem',
                      lineHeight: 1.5,
                      outline: 'none',
                    }}
                  />
                </div>
              )}

              {/* Datos del Autor / Iniciativa Legislativa */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '16px',
                background: 'rgba(15, 23, 42, 0.6)',
                padding: '16px',
                borderRadius: '12px',
                border: '1px solid rgba(0, 180, 216, 0.2)',
                marginBottom: '24px'
              }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '6px', color: '#94A3B8', fontSize: '0.8rem', fontWeight: 600 }}>
                    Email del Autor (Notificaciones):
                  </label>
                  <input
                    type="email"
                    placeholder="autor@senado.gob.bo"
                    value={activeSession.emailAutor || ''}
                    onChange={(e) => updateActiveSession({ emailAutor: e.target.value })}
                    style={{
                      width: '100%',
                      background: 'rgba(11, 37, 69, 0.8)',
                      border: '1px solid rgba(0, 180, 216, 0.3)',
                      borderRadius: '8px',
                      padding: '8px 12px',
                      color: '#F1F5F9',
                      fontSize: '0.85rem',
                      outline: 'none',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '6px', color: '#94A3B8', fontSize: '0.8rem', fontWeight: 600 }}>
                    Nombre del Presentante:
                  </label>
                  <input
                    type="text"
                    placeholder="Sen. Mario Choque"
                    value={activeSession.nombreAutor || ''}
                    onChange={(e) => updateActiveSession({ nombreAutor: e.target.value })}
                    style={{
                      width: '100%',
                      background: 'rgba(11, 37, 69, 0.8)',
                      border: '1px solid rgba(0, 180, 216, 0.3)',
                      borderRadius: '8px',
                      padding: '8px 12px',
                      color: '#F1F5F9',
                      fontSize: '0.85rem',
                      outline: 'none',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '6px', color: '#94A3B8', fontSize: '0.8rem', fontWeight: 600 }}>
                    Origen / Tipo de Iniciativa:
                  </label>
                  <select
                    value={activeSession.tipoIniciativa || 'Senado'}
                    onChange={(e) => updateActiveSession({ tipoIniciativa: e.target.value })}
                    style={{
                      width: '100%',
                      background: 'rgba(11, 37, 69, 0.8)',
                      border: '1px solid rgba(0, 180, 216, 0.3)',
                      borderRadius: '8px',
                      padding: '8px 12px',
                      color: '#F1F5F9',
                      fontSize: '0.85rem',
                      outline: 'none',
                    }}
                  >
                    <option value="Senado">Cámara de Senadores</option>
                    <option value="Diputados">Cámara de Diputados</option>
                    <option value="Ejecutivo">Órgano Ejecutivo</option>
                    <option value="Ciudadana">Iniciativa Ciudadana</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button
                  onClick={handleIniciarFase1}
                  disabled={readOnly || isProcessing || !documentText.trim()}
                  className="btn-primary"
                  style={{ fontSize: '1rem', padding: '14px 28px' }}
                >
                  {isProcessing ? (
                    <>
                      <Cpu size={20} className="pulse-active" />
                      <span>Analizando con Agente Distribuidor...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles size={20} />
                      <span>Iniciar Clasificación (Fase 1)</span>
                      <ArrowRight size={18} />
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── STEP 1: FASE 1 EN EJECUCIÓN ── */}
      {effectiveViewStep === 1 && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={true}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <div className="glass-card" style={{ padding: '48px', textAlign: 'center' }}>
              <Cpu size={56} color="#00f0ff" className="pulse-active" style={{ margin: '0 auto 20px' }} />
              <h2 style={{ fontSize: '1.5rem', color: '#ffffff', marginBottom: '8px' }}>
                Fase 1: Agente Distribuidor en Ejecución
              </h2>
              <p style={{ color: '#a7f3d0', fontSize: '0.95rem', maxWidth: '600px', margin: '0 auto' }}>
                Analizando la materia institucional, el petitorio y la estructura del documento para determinar la categoría correspondiente...
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── STEP 2: CONTROL HUMANO / 🛑 BOTÓN DE ALTO ── */}
      {effectiveViewStep === 2 && fase1Data && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={isProcessing}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <AgentResultCard
              agentName="Agente Distribuidor"
              role="Clasificación Institucional del Documento"
              theme="cyan"
              status="completed"
              phaseLabel="Fase 1: Clasificación"
              badgeText="Control Humano Requerido"
              thinkingText="Clasificación inicial completada con éxito"
              image="/robots/logos/agente_distribuidor.jpeg"
              justificacion="Principio de orden y debido proceso parlamentario: cada expediente debe canalizarse por su vía procedimental correcta (Registro Legislativo, Atención Ciudadana o Correspondencia Oficial)."
              onViewPrev={() => updateActiveSession({ pipelineStep: 2, inspectedAgentId: 'distribuidor' })}
              prevLabel="Ver Clasificación del Distribuidor"
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                <div style={{
                  background: 'rgba(244, 162, 97, 0.15)',
                  border: '1px solid rgba(244,162,97,0.5)',
                  borderRadius: '50%',
                  width: '40px',
                  height: '40px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <AlertTriangle size={22} color="#F4A261" />
                </div>
                <div>
                  <h4 style={{ fontSize: '1.25rem', color: '#F4A261', fontWeight: 800, margin: 0 }}>
                    PUNTO DE CONTROL HUMANO
                  </h4>
                  <p style={{ color: '#CBD5E1', fontSize: '0.85rem', margin: 0 }}>
                    El Agente Distribuidor ha emitido su recomendación. Puede confirmar la categoría sugerida o reasignarla manualmente antes de activar la Fase 2.
                  </p>
                </div>
              </div>


              <div style={{
                background: 'rgba(11, 37, 69, 0.75)',
                padding: '24px',
                borderRadius: '14px',
                border: '1.5px solid rgba(0, 180, 216, 0.35)',
                marginBottom: '24px',
              }}>
                <div style={{ fontSize: '0.85rem', color: '#38BDF8', marginBottom: '8px' }}>Categoría Sugerida por el Agente:</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                  <span className="badge badge-blue" style={{ fontSize: '1rem', padding: '6px 14px' }}>
                    {fase1Data.categoria}
                  </span>
                  <span style={{ fontSize: '0.85rem', color: '#CBD5E1' }}>
                    Agente Destino: <strong style={{ color: '#00B4D8' }}>{fase1Data.agente_destino_nombre}</strong>
                  </span>
                </div>

                <div style={{ fontSize: '0.85rem', color: '#38BDF8', marginBottom: '8px' }}>
                  Ajustar Categoría si es necesario:
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                  {[
                    { id: 'AGENTE_REGISTRO_LEGISLATIVO', label: 'Registro Legislativo (Proyecto de Ley)', icon: Scale, logo: '/robots/logos/agente_distribuidor.jpeg' },
                    { id: 'AGENTE_ATENCION_CIUDADANA', label: 'Atención Ciudadana (Petición/Reclamo)', icon: Users, logo: '/robots/logos/agente_ciudadania.jpeg' },
                    { id: 'AGENTE_GESTION_CORRESPONDENCIA', label: 'Gestión de Correspondencia (Oficio)', icon: Mail, logo: '/robots/logos/agente_comodin.jpeg' },
                  ].map((cat) => {
                    const Icon = cat.icon;
                    const isSel = selectedCategory === cat.id;
                    return (
                      <button
                        key={cat.id}
                        onClick={() => updateActiveSession({ selectedCategory: cat.id })}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                          padding: '10px 18px',
                          borderRadius: '12px',
                          border: isSel ? '2px solid #00B4D8' : '1px solid rgba(0, 180, 216, 0.25)',
                          background: isSel ? 'rgba(0, 180, 216, 0.22)' : 'rgba(11, 37, 69, 0.65)',
                          color: isSel ? '#FFFFFF' : '#CBD5E1',
                          boxShadow: isSel ? '0 0 16px rgba(0, 180, 216, 0.35)' : 'none',
                          cursor: 'pointer',
                          fontWeight: isSel ? 700 : 500,
                          transition: 'all 0.2s',
                        }}
                      >
                        <div style={{
                          width: '28px',
                          height: '28px',
                          borderRadius: '50%',
                          overflow: 'hidden',
                          border: `1.5px solid ${isSel ? '#00B4D8' : 'rgba(148, 163, 184, 0.3)'}`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                          background: '#0B2545'
                        }}>
                          {cat.logo ? (
                            <img src={cat.logo} alt={cat.label} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                          ) : (
                            <Icon size={16} color={isSel ? '#00B4D8' : '#94A3B8'} />
                          )}
                        </div>
                        <span>{cat.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Módulo de voz: Agente Distribuidor (Lectura y conversación) */}
              <div style={{ marginBottom: '20px' }}>
                {!readOnly && (<AgentVoiceModule
                  agentId="distribuidor"
                  agentLabel="Agente Distribuidor"
                  primaryColor="#00B4D8"
                  sesionId={fase1Data?.sesion_id || null}
                  resultData={fase1Data}
                  speechHook={speechHook}
                />)}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
                <button className="btn-secondary" onClick={handleReset}>
                  <RotateCcw size={16} />
                  <span>Cancelar y Reiniciar</span>
                </button>

                <button
                  onClick={handleEjecutarComision}
                  disabled={readOnly || isProcessing}
                  className="btn-primary"
                  style={{ fontSize: '1rem', padding: '14px 28px' }}
                >
                  <Check size={20} />
                  <span>Confirmar y Ejecutar Comisión</span>
                  <ArrowRight size={18} />
                </button>
              </div>
            </AgentResultCard>
          </div>
        </div>
      )}

      {/* ── STEP 3: FASE COMISIÓN EN EJECUCIÓN ── */}
      {effectiveViewStep === 3 && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={true}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <div className="glass-card" style={{ padding: '48px', textAlign: 'center' }}>
              <Sparkles size={56} color="#3b82f6" className="pulse-active" style={{ margin: '0 auto 20px' }} />
              <h2 style={{ fontSize: '1.5rem', color: '#ffffff', marginBottom: '8px' }}>
                Agente de Comisión en Ejecución
              </h2>
              <p style={{ color: '#bfdbfe', fontSize: '0.95rem', maxWidth: '650px', margin: '0 auto 20px' }}>
                Asignando comisión parlamentaria según materia y distribuyendo a sus miembros legislativos...
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── STEP 4: RESULTADO COMISIÓN ── */}
      {effectiveViewStep === 4 && comisionData && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={isProcessing}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <AgentResultCard
              agentName="Agente Comisión Legislativa"
              role="Asignación Temática & Miembros Parlamentarios"
              theme="blue"
              status="completed"
              phaseLabel="Fase 2: Asignación"
              thinkingText="Dictamen de comisión parlamentaria emitido"
              image="/robots/logos/agente_comision.jpeg"
              justificacion="Art. 158 CPE y Reglamento Camaral: Distribución por competencia y especialidad temática a las comisiones parlamentarias y a sus autoridades para su tratamiento de mérito."
              onViewPrev={() => updateActiveSession({ inspectedAgentId: 'distribuidor' })}
              prevLabel="Ver Clasificación (Distribuidor)"
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Building2 size={32} color="#1d4f91" />
              <h3 style={{ fontSize: '1.4rem', color: '#123B60', fontWeight: 800, margin: 0 }}>Comisión Parlamentaria Asignada</h3>
                </div>
                <button className="btn-secondary" onClick={handleReset}>
                  <RotateCcw size={16} />
                  <span>Nuevo Trámite</span>
                </button>
              </div>

              <div style={{
                background: '#edf5ff',
                padding: '20px',
                borderRadius: '14px',
                border: '1px solid #c7dbf3',
                marginBottom: '24px'
              }}>
                <div style={{ fontSize: '0.9rem', color: '#49677f', marginBottom: '4px' }}>Comisión Principal Recomendada:</div>
                <div style={{ fontSize: '1.4rem', color: '#1d4f91', fontWeight: 800, marginBottom: '6px' }}>
                  {comisionData.comision_principal}
                </div>
                {comisionData.comision_secundaria && (
                  <div style={{ fontSize: '0.9rem', color: '#49677f' }}>
                    Comisión Secundaria: <strong style={{ color: '#183650' }}>{comisionData.comision_secundaria}</strong>
                  </div>
                )}
                <div style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
                  <span className="badge badge-gold">Prioridad: {comisionData.prioridad || 'Media'}</span>
                  <span className="badge badge-blue">Complejidad: {comisionData.complejidad || 'Media'}</span>
                </div>
              </div>

              {comisionData.resumen && (
                <div style={{
                  background: '#edf8f2',
                  padding: '20px',
                  borderRadius: '14px',
                  border: '1px solid #c7e5d3',
                  marginBottom: '24px',
                }}>
                  <h4 style={{ fontSize: '1rem', color: '#187448', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                    <BookOpen size={18} />
                    Resumen Ejecutivo del Bot
                  </h4>
                  <p style={{ color: '#345b48', fontSize: '0.92rem', lineHeight: 1.6, marginTop: '8px', marginBottom: 0 }}>{comisionData.resumen}</p>
                </div>
              )}

              {/* Miembros de la Comisión Asignada */}
              <div style={{
                background: '#f4f8fb',
                padding: '20px',
                borderRadius: '14px',
                border: '1px solid #d5e3ed',
                marginBottom: '24px'
              }}>
                <h4 style={{ fontSize: '1.05rem', color: '#175d88', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                  <Users size={20} />
                  Miembros Parlamentarios Asignados (Destinatarios Oficiales)
                </h4>
                {comisionData.miembros && comisionData.miembros.length > 0 ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px', marginTop: '12px' }}>
                    {comisionData.miembros.map((m, idx) => (
                      <div key={idx} style={{
                        background: '#ffffff',
                        padding: '12px 16px',
                        borderRadius: '10px',
                        border: '1px solid #dce7ee'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span style={{ color: '#183650', fontWeight: 700, fontSize: '0.92rem' }}>{m.nombre_completo}</span>
                          <span className="badge badge-gold">{m.cargo}</span>
                        </div>
                        <div style={{ fontSize: '0.82rem', color: '#627d92', marginBottom: '4px' }}>
                          Cámara: <strong style={{ color: '#35566e' }}>{m.tipo_camara}</strong> {m.partido_politico ? `| ${m.partido_politico}` : ''}
                        </div>
                        {m.email && (
                          <div style={{ fontSize: '0.82rem', color: '#087db8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <Mail size={14} />
                            <span>{m.email}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '0.88rem', color: '#627d92', fontStyle: 'italic', marginTop: '8px' }}>
                    No hay parlamentarios registrados aún para esta comisión.
                  </div>
                )}
              </div>

              {/* Módulo de voz: Agente Comisión Legislativa */}
              <div style={{ marginTop: '20px', marginBottom: '20px' }}>
                {!readOnly && (<AgentVoiceModule
                  agentId="comision"
                  agentLabel="Agente Comisión Legislativa"
                  primaryColor="#38BDF8"
                  sesionId={fase1Data?.sesion_id || null}
                  resultData={comisionData}
                  speechHook={speechHook}
                />)}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '24px', gap: '14px', alignItems: 'center' }}>
                <span style={{ fontSize: '0.85rem', color: '#94A3B8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Zap size={14} color="#00B4D8" /> Constitucionalidad por artículo → Consistencia · máx. 4 min
                </span>
                <button
                  onClick={handleEjecutarAuditoriaParalela}
                  disabled={readOnly || isProcessing}
                  className="btn-primary"
                  style={{
                    fontSize: '1.05rem',
                    padding: '14px 28px',
                    background: 'linear-gradient(135deg, #00B4D8 0%, #134074 100%)',
                    boxShadow: '0 4px 18px rgba(0, 180, 216, 0.4)',
                    border: '1px solid rgba(0, 180, 216, 0.6)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px'
                  }}
                >
                  {isProcessing ? (
                    <>
                      <Cpu size={22} className="pulse-active" />
                      <span>Verificando CPE por artículo y luego consistencia...</span>
                    </>
                  ) : (
                    <>
                      <Zap size={20} color="#8AC926" />
                      <span>Iniciar auditoría secuencial (máx. 4 min)</span>
                      <ArrowRight size={18} />
                    </>
                  )}
                </button>
              </div>
            </AgentResultCard>
          </div>
        </div>
      )}

      {/* ── STEP 5: VERIFICACIÓN CONSTITUCIONAL CPE ── */}
      {effectiveViewStep === 5 && dictamenData && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={isProcessing}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <AgentResultCard
              agentName="Agente Verificador Constitucional"
              role="Auditoría de Conformidad contra la CPE Bolivia 2009"
              theme="green"
              status="completed"
              phaseLabel="Fase 2: CPE Bolivia"
              thinkingText="Dictamen Constitucional emitido"
              badgeText={dictamenData.valido ? 'CPE Conforme' : 'CPE Observado'}
              image="/robots/logos/agente_constitucional.jpeg"
              justificacion="Art. 410 CPE: Principio de Supremacía Constitucional. El proyecto debe cotejarse exhaustivamente con los mandatos de la CPE 2009 para impedir normas contrarias a los derechos y garantías constitucionales."
              onViewPrev={() => updateActiveSession({ inspectedAgentId: 'comision' })}
              prevLabel="Ver Asignación de Comisión"
            >
              <div style={{
                background: dictamenData.valido
                  ? 'linear-gradient(135deg, rgba(6,78,59,0.9), rgba(4,120,87,0.7))'
                  : 'linear-gradient(135deg, rgba(127,29,29,0.9), rgba(185,28,28,0.7))',
                padding: '24px 28px',
                borderRadius: '16px',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px',
                marginBottom: '24px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '50%', padding: '12px', display: 'flex' }}>
                    <Scale size={36} color={dictamenData.valido ? '#34d399' : '#f87171'} />
                  </div>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.6)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '4px' }}>
                      Resultado de Auditoría Constitucional
                    </div>
                    <h2 style={{ fontSize: '1.4rem', color: '#ffffff', fontWeight: 800, margin: 0 }}>
                      {dictamenData.valido ? '✅ CONFORME CON LA CONSTITUCIÓN' : '⚠️ OBSERVACIONES CONSTITUCIONALES'}
                    </h2>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px 18px', borderRadius: '10px', textAlign: 'center' }}>
                    <div style={{ fontSize: '1.6rem', fontWeight: 800, color: dictamenData.valido ? '#34d399' : '#fbbf24' }}>
                      {dictamenData.confianza ?? 0}%
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.6)', textTransform: 'uppercase' }}>Confianza</div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px 18px', borderRadius: '10px', textAlign: 'center' }}>
                    <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#f87171' }}>
                      {dictamenData.num_contradicciones || dictamenData.contradicciones?.length || 0}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.6)', textTransform: 'uppercase' }}>Obs. CPE</div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px 18px', borderRadius: '10px', textAlign: 'center' }}>
                    <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#34d399' }}>
                      {(dictamenData.articulos_a_favor?.length || dictamenData.articulos_consultados?.length || 0)}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.6)', textTransform: 'uppercase' }}>Normas Revisadas</div>
                  </div>
                </div>
              </div>

              {dictamenData.evaluaciones_por_articulo?.length > 0 && (
                <section className="cpe-analysis-results" aria-label="Dictamen binario por artículo del proyecto">
                  <header className="cpe-analysis-heading">
                    <div><span>DICTAMEN POR ARTÍCULO DEL PROYECTO</span><h3>Clasificación y justificación técnica</h3><p>Cada artículo recibe una de dos etiquetas. La evidencia insuficiente se indica como limitación, sin crear una tercera etiqueta.</p></div>
                    <div className="cpe-analysis-metrics"><strong>{dictamenData.evaluaciones_por_articulo.length}<small>Artículos clasificados</small></strong><strong>{dictamenData.limitaciones_revision?.length || 0}<small>Limitaciones de evidencia</small></strong></div>
                  </header>
                  <div className="cpe-analysis-list">
                    {dictamenData.evaluaciones_por_articulo.map((item, idx) => (
                      <article className={`cpe-analysis-item ${item.clasificacion === 'EN_CONTRA' ? 'cpe-contradiccion' : 'cpe-complementario'}`} key={`${item.articulo_proyecto}-${idx}`}>
                        <div className="cpe-analysis-item-heading"><div><strong>{item.articulo_proyecto}</strong><span>{item.base_decision === 'COMPATIBILIDAD_PROVISIONAL_SIN_INCOMPATIBILIDAD_ACREDITADA' ? 'Compatibilidad provisional; sin apoyo constitucional expreso acreditado' : item.base_decision === 'INCOMPATIBILIDAD_DIRECTA_VERIFICADA' ? 'Colisión directa verificada' : 'Compatibilidad constitucional identificada'}</span></div><span className="cpe-analysis-label">{item.clasificacion}</span></div>
                        <p className="cpe-analysis-justification">{item.justificacion_tecnica}</p>
                        {item.comentario_analitico && <p><strong>Comentario analítico:</strong> {item.comentario_analitico}</p>}
                        {item.sugerencia && <p><strong>Sugerencia:</strong> {item.sugerencia}</p>}
                        {item.citas?.length > 0 && <details><summary>Ver citas y fragmentos cotejados ({item.citas.length})</summary>{item.citas.map((cita, citaIdx) => <div className="cpe-quote-grid" key={`${cita.articulo}-${citaIdx}`}><div><small>Artículo CPE: {cita.articulo || 'referencia no disponible'}</small><p>{cita.texto || 'Texto constitucional no disponible.'}</p></div><div><small>Fragmento del proyecto</small><p>{cita.cita_proyecto || 'Fragmento no disponible.'}</p></div></div>)}</details>}
                        {item.articulos_relacionados?.length > 0 && <div style={{ marginTop: '14px' }}><strong>Artículos CPE relacionados ({item.total_articulos_relacionados || item.articulos_relacionados.length})</strong><div className="cpe-analysis-list" style={{ marginTop: '8px' }}>{item.articulos_relacionados.map((rel, relIdx) => <article className="cpe-analysis-item" key={`${item.articulo_proyecto}-cpe-${rel.numero}-${relIdx}`}><div className="cpe-analysis-item-heading"><div><strong>Art. {rel.numero}{rel.titulo ? ` · ${rel.titulo}` : ''}</strong><span>{rel.estado_cotejo === 'COTEJADO' ? 'Cotejado individualmente; dictamen binario visible arriba' : 'Relacionado por búsqueda; no cotejado individualmente'}</span></div><span className="cpe-analysis-label">{rel.estado_cotejo === 'COTEJADO' ? 'COTEJADO' : 'RELACIONADO'}</span></div><p>{rel.texto || rel.fundamento_relacion}</p><p><strong>Clasificación:</strong> {rel.clasificacion_cotejo}</p><p><strong>Comentario analítico:</strong> {rel.comentario_analitico}</p><p><strong>Sugerencia:</strong> {rel.sugerencia}</p></article>)}</div></div>}
                        {item.limitaciones?.length > 0 && <details><summary>Limitaciones del cotejo ({item.limitaciones.length})</summary>{item.limitaciones.map((lim, limIdx) => <p key={limIdx}>{lim.motivo || lim.fase || 'Evidencia incompleta'}</p>)}</details>}
                      </article>
                    ))}
                  </div>
                </section>
              )}

              {dictamenData.analisis?.some((fila) => fila.tipo_relacion !== 'pendiente_revision') && (
                <section className="cpe-analysis-results">
                  <header className="cpe-analysis-heading">
                    <div><span>ANÁLISIS DETALLADO</span><h3>Cotejo párrafo por párrafo con la Constitución</h3><p>Cada bloque del proyecto se contrasta con los artículos pertinentes de la CPE 2009.</p></div>
                    <div className="cpe-analysis-metrics"><strong>{dictamenData.total_parrafos_evaluados || 0}<small>Párrafos</small></strong><strong>{dictamenData.total_cotejos || dictamenData.analisis.length}<small>Cotejos CPE</small></strong><strong>{dictamenData.nivel_riesgo_global || dictamenData.resumen_ejecutivo?.nivel_riesgo || '—'}<small>Riesgo global</small></strong></div>
                  </header>
                  <div className="cpe-analysis-list">
                    {dictamenData.analisis.filter((fila) => fila.tipo_relacion !== 'pendiente_revision').map((fila, idx) => {
                      const labels = { contradiccion: 'Contradicción', complementario: 'Compatible', requiere_analisis_de_fondo: 'Requiere análisis de fondo', sin_relacion: 'Sin colisión detectada', pendiente_revision: 'Pendiente de revisión' };
                      return <article className={`cpe-analysis-item cpe-${fila.tipo_relacion || 'sin_relacion'}`} key={`${fila.articulo_proyecto}-${fila.parrafo_proyecto}-${fila.numero_articulo}-${idx}`}>
                        <div className="cpe-analysis-item-heading"><div><strong>{fila.articulo_proyecto} · {fila.parrafo_proyecto}</strong><span>{fila.articulo_constitucional}{fila.similitud > 0 && ` · ${Math.round((fila.similitud <= 1 ? fila.similitud : fila.similitud / 100) * 100)}% de relevancia`}</span></div><span className="cpe-analysis-label">{fila.clasificacion}</span></div>
                        <div className="cpe-quote-grid"><div><small>Fragmento del proyecto</small><p>{fila.cita_proyecto || fila.texto_parrafo || 'Fragmento no disponible.'}</p></div><div><small>Artículo de la Constitución</small><p>{fila.cita_constitucional || fila.texto_constitucional_verificado || 'Texto constitucional no disponible.'}</p></div></div>
                        <p className="cpe-analysis-justification">{fila.justificacion || 'Sin observación jurídica adicional.'}</p>
                        {fila.comentario_analitico && <p><strong>Comentario analítico:</strong> {fila.comentario_analitico}</p>}
                        {fila.sugerencia && <details><summary>Ver recomendación y fundamento</summary><p>{fila.sugerencia}</p>{fila.analisis_profundo?.redaccion_corregida && <p><strong>Redacción sugerida:</strong> {fila.analisis_profundo.redaccion_corregida}</p>}{fila.analisis_profundo?.precedentes_tcp && <p><strong>Precedente TCP:</strong> {fila.analisis_profundo.precedentes_tcp}</p>}</details>}
                      </article>;
                    })}
                  </div>
                </section>
              )}

              <div>
                {/* Severidad */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px' }}>
                  <span style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.6)' }}>Severidad Máxima:</span>
                  <span className={`badge ${dictamenData.severidad_maxima === 'bloqueante' ? 'badge-red' :
                      dictamenData.severidad_maxima === 'grave' ? 'badge-gold' :
                        dictamenData.severidad_maxima === 'leve' ? 'badge-blue' : 'badge-green'
                    }`} style={{ fontSize: '0.85rem', padding: '5px 14px' }}>
                    {dictamenData.severidad_maxima || 'ninguna'}
                  </span>
                </div>

                {/* ── SECCIÓN A FAVOR ── */}
                {(() => {
                  const aFavor = dictamenData.articulos_a_favor || [];
                  return aFavor.length > 0 && (
                    <div style={{ marginBottom: '32px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid rgba(16,185,129,0.25)' }}>
                        <div style={{ width: '4px', height: '24px', background: '#10b981', borderRadius: '2px' }} />
                        <h3 style={{ fontSize: '1.05rem', color: '#34d399', margin: 0, fontWeight: 700 }}>
                          Artículos CPE — APOYO CONSTITUCIONAL IDENTIFICADO ({aFavor.length})
                        </h3>
                        <span style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
                          Fuente: public.articulos_constitucion
                        </span>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '16px' }}>
                        {aFavor.map((art, idx) => (
                          <CardArticuloAFavor key={idx} art={art} idx={idx} />
                        ))}
                      </div>
                    </div>
                  );
                })()}

                {/* ── SECCIÓN EN CONTRA ── */}
                <div style={{ marginBottom: '24px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid rgba(239,68,68,0.25)' }}>
                    <div style={{ width: '4px', height: '24px', background: '#ef4444', borderRadius: '2px' }} />
                    <h3 style={{ fontSize: '1.05rem', color: '#f87171', margin: 0, fontWeight: 700 }}>
                      Párrafos Observados — INFRINGEN LA CPE ({dictamenData.contradicciones?.length || 0})
                    </h3>
                  </div>

                  {dictamenData.contradicciones?.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                      {dictamenData.contradicciones.map((c, idx) => (
                        <div key={idx} style={{
                          background: 'rgba(30, 5, 5, 0.8)',
                          border: '1px solid rgba(239, 68, 68, 0.4)',
                          borderRadius: '14px',
                          overflow: 'hidden',
                        }}>
                          <div style={{ background: 'rgba(239,68,68,0.15)', padding: '12px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(239,68,68,0.2)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <ShieldAlert size={18} color="#f87171" />
                              <span style={{ fontWeight: 700, color: '#fca5a5', fontSize: '0.92rem' }}>
                                OBSERVACIÓN #{idx + 1} — Párrafo del Proyecto: {c.articulo_proyecto}
                              </span>
                            </div>
                            <span className={`badge ${c.severidad === 'bloqueante' ? 'badge-red' : c.severidad === 'grave' ? 'badge-gold' : 'badge-blue'}`}>
                              {c.severidad || 'bloqueante'}
                            </span>
                          </div>

                          <div style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                            {c.fragmento_proyecto && (
                              <div>
                                <div style={{ fontSize: '0.72rem', color: '#f87171', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '6px', fontWeight: 600 }}>
                                  📄 Texto del Proyecto que Genera la Contradicción:
                                </div>
                                <div style={{ background: 'rgba(0,0,0,0.4)', padding: '12px 16px', borderRadius: '8px', color: '#fed7aa', fontSize: '0.87rem', fontStyle: 'italic', lineHeight: 1.6, borderLeft: '3px solid #ef4444' }}>
                                  "{c.fragmento_proyecto}"
                                </div>
                              </div>
                            )}

                            <div>
                              <div style={{ fontSize: '0.72rem', color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '6px', fontWeight: 600 }}>
                                ⚖️ Norma Constitucional Infringida (CPE):
                              </div>
                              <div style={{ background: 'rgba(15, 30, 60, 0.7)', padding: '12px 16px', borderRadius: '8px', borderLeft: '3px solid #38bdf8' }}>
                                <div style={{ color: '#38bdf8', fontWeight: 700, fontSize: '0.9rem', marginBottom: '6px' }}>
                                  {c.articulo_constitucional}
                                </div>
                                {c.texto_constitucional_verificado && (
                                  <div style={{ color: '#e2e8f0', fontSize: '0.84rem', lineHeight: 1.6 }}>
                                    {c.texto_constitucional_verificado}
                                  </div>
                                )}
                              </div>
                            </div>

                            {c.fundamento && (
                              <div>
                                <div style={{ fontSize: '0.72rem', color: '#fbbf24', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '6px', fontWeight: 600 }}>
                                  📋 Fundamentación Jurídica:
                                </div>
                                <div style={{ color: '#fef3c7', fontSize: '0.87rem', lineHeight: 1.65 }}>
                                  {c.fundamento}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{
                      background: 'rgba(6, 78, 59, 0.25)',
                      border: '1px solid rgba(16,185,129,0.3)',
                      borderRadius: '12px',
                      padding: '20px 24px',
                      display: 'flex', alignItems: 'center', gap: '14px'
                    }}>
                      <CheckCircle2 size={28} color="#34d399" />
                      <div>
                        <div style={{ color: '#34d399', fontWeight: 700, fontSize: '0.95rem' }}>
                          Sin contradicciones constitucionales detectadas
                        </div>
                        <div style={{ color: 'rgba(167,243,208,0.7)', fontSize: '0.83rem', marginTop: '4px' }}>
                          El proyecto es plenamente compatible con la Constitución Política del Estado.
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Botón continuar */}
                {/* Módulo de voz: Lectura de Observaciones Constitucionales */}

                <div style={{ marginTop: '24px', marginBottom: '16px' }}>

                  {!readOnly && (<AgentVoiceModule

                    agentId="constitucional"

                    agentLabel="Agente Verificador Constitucional"

                    primaryColor="#2563EB"

                    sesionId={fase1Data?.sesion_id || null}

                    resultData={dictamenData}

                    speechHook={speechHook}

                  />)}

                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '28px' }}>
                  <button
                    onClick={handleEjecutarConsistencia}
                    disabled={readOnly || isProcessing}
                    className="btn-primary"
                    style={{ fontSize: '1.05rem', padding: '14px 30px' }}
                  >
                    {isProcessing ? (
                      <>
                        <Cpu size={20} className="pulse-active" />
                        <span>Ejecutando Agente de Consistencia...</span>
                      </>
                    ) : (
                      <>
                        <Check size={20} />
                        <span>Continuar: Consistencia Normativa</span>
                        <ArrowRight size={18} />
                      </>
                    )}
                  </button>
                </div>
              </div>
            </AgentResultCard>
          </div>
        </div>
      )}

      {/* ── STEP 6: CONSISTENCIA NORMATIVA ── */}
      {effectiveViewStep === 6 && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={isProcessing}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <AgentResultCard
              agentName="Agente de Consistencia Normativa"
              role="Auditoría Semántica Vectorial (pgvector)"
              theme="gold"
              status="completed"
              phaseLabel="Fase 2: Consistencia Vectorial"
              thinkingText="Auditoría semántica de leyes vigentes emitida"
              image="/robots/logos/agente_consistencia.jpeg"
              justificacion="Seguridad Jurídica y Principio de No Contradicción: Búsqueda vectorial semántica pgvector contra leyes y códigos vigentes para prevenir derogaciones tácitas y antinomias normativas."
              onViewPrev={() => updateActiveSession({ inspectedAgentId: 'constitucional' })}
              prevLabel="Ver Dictamen Constitucional"
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '50%', padding: '12px', display: 'flex' }}>
                      <BookOpen size={32} color="#fbbf24" />
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '4px' }}>
                        Agente de Consistencia Normativa — Leyes Vigentes Bolivia
                      </div>
                      <h3 style={{ fontSize: '1.4rem', color: '#ffffff', fontWeight: 800, margin: 0 }}>
                        Auditoría contra el Ordenamiento Legal Vigente
                      </h3>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 16px', borderRadius: '10px', textAlign: 'center' }}>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#fbbf24' }}>
                        {consistenciaData?.total_hallazgos || consistenciaData?.analisis?.length || 0}
                      </div>
                      <div style={{ fontSize: '0.68rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase' }}>Hallazgos</div>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 16px', borderRadius: '10px', textAlign: 'center' }}>
                      <div style={{
                        fontSize: '1.1rem', fontWeight: 800, color:
                          consistenciaData?.nivel_riesgo_global === 'ALTO' ? '#ef4444' :
                            consistenciaData?.nivel_riesgo_global === 'MEDIO' ? '#f59e0b' :
                              '#34d399'
                      }}>
                        {consistenciaData?.nivel_riesgo_global || 'OK'}
                      </div>
                      <div style={{ fontSize: '0.68rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase' }}>Riesgo Global</div>
                    </div>
                  </div>
                </div>

                <div>
                  {/* Resumen por tipo */}
                  {consistenciaData?.resumen_por_tipo && Object.keys(consistenciaData.resumen_por_tipo).length > 0 && (
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '24px', padding: '14px 18px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', border: '1px solid rgba(251,191,36,0.15)' }}>
                      <span style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.5)', alignSelf: 'center', marginRight: '4px' }}>Clasificación:</span>
                      {Object.entries(consistenciaData.resumen_por_tipo).map(([tipo, count]) => (
                        <span key={tipo} style={{
                          padding: '4px 12px', borderRadius: '20px', fontSize: '0.78rem', fontWeight: 700,
                          background: tipo === 'contradiccion' ? 'rgba(239,68,68,0.2)' : tipo === 'repeticion' ? 'rgba(251,191,36,0.15)' : 'rgba(16,185,129,0.15)',
                          color: tipo === 'contradiccion' ? '#f87171' : tipo === 'repeticion' ? '#fbbf24' : '#34d399',
                          border: `1px solid ${tipo === 'contradiccion' ? 'rgba(239,68,68,0.3)' : tipo === 'repeticion' ? 'rgba(251,191,36,0.25)' : 'rgba(16,185,129,0.25)'}`,
                        }}>
                          {tipo.replace('_', ' ').toUpperCase()}: {count}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Hallazgos detallados */}
                  {consistenciaData?.analisis?.length > 0 ? (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid rgba(251,191,36,0.2)' }}>
                        <div style={{ width: '4px', height: '20px', background: '#fbbf24', borderRadius: '2px' }} />
                        <h4 style={{ fontSize: '1rem', color: '#fbbf24', margin: 0, fontWeight: 700 }}>
                          Hallazgos con Leyes Vigentes ({consistenciaData.analisis.length})
                        </h4>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                        {consistenciaData.analisis.map((item, idx) => {
                          const esContradiccion = item.tipo_relacion === 'contradiccion';
                          const esRepeticion = item.tipo_relacion === 'repeticion';
                          const borde = esContradiccion ? '#ef4444' : esRepeticion ? '#f59e0b' : '#10b981';
                          const bgCard = esContradiccion ? 'rgba(30,5,5,0.75)' : esRepeticion ? 'rgba(30,20,0,0.75)' : 'rgba(4,20,14,0.75)';
                          const badgeClass = esContradiccion ? 'badge-red' : esRepeticion ? 'badge-gold' : 'badge-green';
                          return (
                            <div key={idx} style={{
                              background: bgCard,
                              border: `1px solid ${borde}40`,
                              borderRadius: '14px',
                              overflow: 'hidden',
                            }}>
                              <div style={{ background: `${borde}18`, padding: '12px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: `1px solid ${borde}25` }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <span style={{ color: borde, fontWeight: 700, fontSize: '0.9rem' }}>
                                    📜 {item.norma}
                                  </span>
                                  <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.82rem' }}>
                                    Art. {item.numero_articulo}
                                  </span>
                                </div>
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                  <span className={`badge ${badgeClass}`} style={{ fontSize: '0.75rem' }}>
                                    {item.tipo_relacion?.replace('_', ' ')?.toUpperCase()}
                                  </span>
                                  <span style={{ background: 'rgba(56,189,248,0.1)', color: '#38bdf8', border: '1px solid rgba(56,189,248,0.25)', padding: '2px 8px', borderRadius: '20px', fontSize: '0.72rem', fontWeight: 600 }}>
                                    {Math.round(item.similitud * 100)}% similitud
                                  </span>
                                </div>
                              </div>

                              <div style={{ padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                <div>
                                  <div style={{ fontSize: '0.7rem', color: '#fbbf24', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '4px', fontWeight: 600 }}>
                                    Análisis Jurídico:
                                  </div>
                                  <div style={{ color: '#fef3c7', fontSize: '0.85rem', lineHeight: 1.6 }}>
                                    {item.justificacion}
                                  </div>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div style={{
                      background: 'rgba(6, 30, 10, 0.5)',
                      border: '1px solid rgba(16,185,129,0.25)',
                      borderRadius: '12px',
                      padding: '20px',
                      display: 'flex', alignItems: 'center', gap: '14px'
                    }}>
                      <CheckCircle2 size={28} color="#8AC926" />
                      <div>
                        <div style={{ color: '#8AC926', fontWeight: 700, fontSize: '0.95rem' }}>
                          Sin incompatibilidades normativas graves detectadas
                        </div>
                        <div style={{ color: 'rgba(203, 213, 225, 0.75)', fontSize: '0.82rem', marginTop: '2px' }}>
                          El corpus normativo vigente no registra conflictos con el proyecto analizado.
                        </div>
                      </div>
                    </div>
                  )}

                  {/* ── CATÁLOGO DE NORMATIVAS VIGENTES INDEXADAS (NEON PGVECTOR) ── */}
                  <div style={{
                    marginTop: '32px',
                    background: 'linear-gradient(145deg, rgba(13, 27, 42, 0.95) 0%, rgba(20, 35, 60, 0.90) 100%)',
                    border: '1.5px solid rgba(251, 191, 36, 0.35)',
                    borderRadius: '16px',
                    padding: '22px',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.45)'
                  }}>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: '14px',
                      marginBottom: '18px',
                      borderBottom: '1px solid rgba(251, 191, 36, 0.2)',
                      paddingBottom: '14px'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ background: 'rgba(251, 191, 36, 0.15)', borderRadius: '10px', padding: '10px', display: 'flex' }}>
                          <Database size={24} color="#fbbf24" />
                        </div>
                        <div>
                          <h4 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: '#ffffff' }}>
                            Corpus Normativo Vigente Indexado en la Base de Datos
                          </h4>
                          <p style={{ margin: '3px 0 0', fontSize: '0.82rem', color: '#94a3b8' }}>
                            Normas bolivianas cargadas con embeddings (2048 dimensiones) para auditoría de antinomias.
                          </p>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.82rem', color: '#fbbf24', background: 'rgba(251, 191, 36, 0.12)', border: '1px solid rgba(251, 191, 36, 0.3)', padding: '5px 12px', borderRadius: '20px', fontWeight: 700 }}>
                          {normativasList.length} Normativas en Neon
                        </span>
                        <button
                          type="button"
                          onClick={() => setShowSubirNormativaModal(!showSubirNormativaModal)}
                          style={{
                            background: showSubirNormativaModal ? 'rgba(239, 68, 68, 0.2)' : 'linear-gradient(135deg, #fbbf24 0%, #d97706 100%)',
                            color: showSubirNormativaModal ? '#fca5a5' : '#0B2545',
                            border: showSubirNormativaModal ? '1px solid #ef4444' : 'none',
                            padding: '8px 16px',
                            borderRadius: '10px',
                            fontWeight: 800,
                            fontSize: '0.86rem',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            boxShadow: '0 4px 14px rgba(251, 191, 36, 0.35)',
                            transition: 'all 0.2s ease'
                          }}
                        >
                          {showSubirNormativaModal ? <X size={16} /> : <Plus size={16} />}
                          <span>{showSubirNormativaModal ? 'Cerrar Formulario' : 'Subir Otra Normativa'}</span>
                        </button>
                      </div>
                    </div>

                    {/* Formulario Expandible para Subir y Procesar con LLM */}
                    {showSubirNormativaModal && (
                      <form onSubmit={handleSubirNormativa} style={{
                        background: 'rgba(15, 23, 42, 0.95)',
                        border: '1.5px solid rgba(56, 189, 248, 0.4)',
                        borderRadius: '14px',
                        padding: '20px',
                        marginBottom: '22px'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                          <Sparkles size={20} color="#38bdf8" />
                          <h5 style={{ margin: 0, fontSize: '1rem', fontWeight: 800, color: '#38bdf8' }}>
                            Cargar Nueva Normativa y Procesar con LLM (NVIDIA NIM)
                          </h5>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px', marginBottom: '14px' }}>
                          <div>
                            <label style={{ display: 'block', fontSize: '0.78rem', color: '#7dd3fc', fontWeight: 700, marginBottom: '6px' }}>
                              Nombre Oficial de la Norma *:
                            </label>
                            <input
                              type="text"
                              required
                              placeholder="Ej: Ley N° 348 Integral para Mujeres / Ley 1333"
                              value={normativaNombre}
                              onChange={(e) => setNormativaNombre(e.target.value)}
                              style={{
                                width: '100%',
                                padding: '9px 12px',
                                borderRadius: '8px',
                                background: 'rgba(15, 23, 42, 0.9)',
                                border: '1px solid rgba(56, 189, 248, 0.35)',
                                color: '#ffffff',
                                fontSize: '0.84rem',
                                outline: 'none',
                                boxSizing: 'border-box'
                              }}
                            />
                          </div>

                          <div>
                            <label style={{ display: 'block', fontSize: '0.78rem', color: '#7dd3fc', fontWeight: 700, marginBottom: '6px' }}>
                              Tipo de Norma:
                            </label>
                            <select
                              value={normativaTipo}
                              onChange={(e) => setNormativaTipo(e.target.value)}
                              style={{
                                width: '100%',
                                padding: '9px 12px',
                                borderRadius: '8px',
                                background: '#0F172A',
                                border: '1px solid rgba(56, 189, 248, 0.35)',
                                color: '#ffffff',
                                fontSize: '0.84rem',
                                outline: 'none',
                                boxSizing: 'border-box'
                              }}
                            >
                              <option value="Ley">Ley Nacional</option>
                              <option value="Código">Código Orgánico / Sustantivo</option>
                              <option value="Decreto Supremo">Decreto Supremo</option>
                              <option value="Resolución">Resolución Ministerial / Administrativa</option>
                            </select>
                          </div>

                          <div>
                            <label style={{ display: 'block', fontSize: '0.78rem', color: '#7dd3fc', fontWeight: 700, marginBottom: '6px' }}>
                              Número de Norma (Opcional):
                            </label>
                            <input
                              type="text"
                              placeholder="Ej: 348 / 1333"
                              value={normativaNumero}
                              onChange={(e) => setNormativaNumero(e.target.value)}
                              style={{
                                width: '100%',
                                padding: '9px 12px',
                                borderRadius: '8px',
                                background: 'rgba(15, 23, 42, 0.9)',
                                border: '1px solid rgba(56, 189, 248, 0.35)',
                                color: '#ffffff',
                                fontSize: '0.84rem',
                                outline: 'none',
                                boxSizing: 'border-box'
                              }}
                            />
                          </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px', marginBottom: '16px' }}>
                          <div>
                            <label style={{ display: 'block', fontSize: '0.78rem', color: '#fbbf24', fontWeight: 700, marginBottom: '6px' }}>
                              📁 Adjuntar Archivo (PDF o TXT):
                            </label>
                            <input
                              type="file"
                              accept=".pdf,.txt,.docx"
                              onChange={(e) => setNormativaFile(e.target.files?.[0] || null)}
                              style={{
                                width: '100%',
                                padding: '8px',
                                borderRadius: '8px',
                                background: 'rgba(15, 23, 42, 0.85)',
                                border: '1px solid rgba(251, 191, 36, 0.35)',
                                color: '#e2e8f0',
                                fontSize: '0.82rem',
                                boxSizing: 'border-box'
                              }}
                            />
                          </div>

                          <div>
                            <label style={{ display: 'block', fontSize: '0.78rem', color: '#fbbf24', fontWeight: 700, marginBottom: '6px' }}>
                              O pegar texto de artículos directamente:
                            </label>
                            <textarea
                              rows={2}
                              placeholder="ARTÍCULO 1.- (OBJETO)..."
                              value={normativaTexto}
                              onChange={(e) => setNormativaTexto(e.target.value)}
                              style={{
                                width: '100%',
                                padding: '8px 12px',
                                borderRadius: '8px',
                                background: 'rgba(15, 23, 42, 0.9)',
                                border: '1px solid rgba(251, 191, 36, 0.35)',
                                color: '#ffffff',
                                fontSize: '0.82rem',
                                outline: 'none',
                                boxSizing: 'border-box'
                              }}
                            />
                          </div>
                        </div>

                        {normativaUploadStatus && (
                          <div style={{
                            padding: '12px 16px',
                            borderRadius: '10px',
                            marginBottom: '16px',
                            background: normativaUploadStatus.success ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                            border: `1px solid ${normativaUploadStatus.success ? '#10b981' : '#ef4444'}`,
                            color: normativaUploadStatus.success ? '#34d399' : '#f87171',
                            fontSize: '0.84rem'
                          }}>
                            <div><strong>{normativaUploadStatus.success ? '✅ Éxito:' : '❌ Error:'}</strong> {normativaUploadStatus.msg}</div>
                            {normativaUploadStatus.resumen && (
                              <div style={{ marginTop: '6px', fontSize: '0.8rem', color: '#e2e8f0' }}>
                                <em>Resumen IA:</em> {normativaUploadStatus.resumen}
                              </div>
                            )}
                          </div>
                        )}

                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                          <button
                            type="button"
                            onClick={() => setShowSubirNormativaModal(false)}
                            className="btn-secondary"
                            style={{ padding: '9px 18px', fontSize: '0.85rem' }}
                          >
                            Cancelar
                          </button>
                          <button
                            type="submit"
                            disabled={isUploadingNormativa}
                            className="btn-primary"
                            style={{ padding: '9px 24px', fontSize: '0.88rem' }}
                          >
                            {isUploadingNormativa ? (
                              <>
                                <Cpu size={16} className="pulse-active" />
                                <span>Procesando con LLM & Indexando...</span>
                              </>
                            ) : (
                              <>
                                <Sparkles size={16} />
                                <span>⚡ Procesar con LLM y Registrar en BD</span>
                              </>
                            )}
                          </button>
                        </div>
                      </form>
                    )}

                    {driveDownloadError && <p role="alert" style={{ color: '#fca5a5', fontSize: '0.78rem' }}>{driveDownloadError}</p>}
                    {/* Grid de Normativas Cargadas */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
                      {normativasList.length === 0 ? (
                        <div style={{ color: '#94a3b8', fontSize: '0.85rem', padding: '16px', textAlign: 'center', gridColumn: '1 / -1' }}>
                          {isLoadingNormativas ? 'Cargando catálogo normativo desde Neon...' : 'No hay normativas registradas en la base de datos.'}
                        </div>
                      ) : (
                        normativasList.map((norma, idx) => (
                          <div key={idx} style={{
                            background: 'rgba(15, 23, 42, 0.85)',
                            border: '1px solid rgba(148, 163, 184, 0.22)',
                            borderRadius: '12px',
                            padding: '16px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            gap: '12px'
                          }}>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '10px', marginBottom: '8px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <span style={{ fontSize: '1.2rem' }}>📜</span>
                                  <h5 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 800, color: '#ffffff' }}>
                                    {norma.documento}
                                  </h5>
                                </div>
                                <span style={{
                                  background: 'rgba(56, 189, 248, 0.15)',
                                  color: '#38bdf8',
                                  border: '1px solid rgba(56, 189, 248, 0.3)',
                                  borderRadius: '20px',
                                  padding: '2px 8px',
                                  fontSize: '0.72rem',
                                  fontWeight: 700,
                                  whiteSpace: 'nowrap'
                                }}>
                                  {norma.num_articulos} artículos
                                </span>
                              </div>

                              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '10px' }}>
                                <span style={{ fontSize: '0.7rem', padding: '2px 7px', borderRadius: '4px', background: 'rgba(251, 191, 36, 0.12)', color: '#fbbf24', fontWeight: 600 }}>
                                  {norma.tipo_documento?.toUpperCase()} {norma.numero_norma ? `#${norma.numero_norma}` : ''}
                                </span>
                                {norma.materia && (
                                  <span style={{ fontSize: '0.7rem', padding: '2px 7px', borderRadius: '4px', background: 'rgba(16, 185, 129, 0.12)', color: '#34d399', fontWeight: 600 }}>
                                    {norma.materia}
                                  </span>
                                )}
                              </div>

                              {/* Resumen IA */}
                              <div style={{
                                background: 'rgba(0, 0, 0, 0.35)',
                                border: '1px solid rgba(255, 255, 255, 0.08)',
                                borderRadius: '8px',
                                padding: '10px 12px',
                                fontSize: '0.82rem',
                                color: '#e2e8f0',
                                lineHeight: 1.55
                              }}>
                                <div style={{ fontSize: '0.68rem', color: '#38bdf8', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <Sparkles size={11} /> Resumen Generado por IA (LLM):
                                </div>
                                {norma.resumen}
                              </div>
                            </div>

                            <div style={{ fontSize: '0.7rem', color: '#64748b', display: 'flex', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '8px' }}>
                              <span>Estado: Vigente en BD</span>
                              <span>{norma.ultima_actualizacion ? new Date(norma.ultima_actualizacion).toLocaleDateString('es-BO') : 'Indexada'}</span>
                            </div>
                            {norma.drive_upload_id && <button type="button" onClick={() => descargarRegistroNormativo(norma)} className="download-original-button"><Download size={14}/> Descargar original</button>}
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Botón Acción Siguiente: FUSIONADO EN CONCENTRADOR, EMISOR Y NOTIFICADOR */}
                  {selectedCategory === 'AGENTE_REGISTRO_LEGISLATIVO' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '28px' }}>
                      {/* Módulo de voz: Lectura de Hallazgos Normativos */}
                      <div style={{ width: '100%' }}>
                        {!readOnly && (<AgentVoiceModule
                          agentId="consistencia"
                          agentLabel="Agente de Consistencia Normativa"
                          primaryColor="#fbbf24"
                          sesionId={fase1Data?.sesion_id || null}
                          resultData={consistenciaData}
                          speechHook={speechHook}
                        />)}
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '14px', flexWrap: 'wrap' }}>
                        <button
                          onClick={handleConcentrador}
                          disabled={readOnly || isProcessing}
                          className="btn-primary"
                          style={{ fontSize: '1.05rem', padding: '14px 30px' }}
                        >
                          {isProcessing ? (
                            <>
                              <Cpu size={20} className="pulse-active" />
                              <span>Consolidando, Emitiendo PDF & Despachando...</span>
                            </>
                          ) : (
                            <>
                              <Merge size={20} />
                              <span>Consolidar Expediente, Emitir Dictamen PDF y Notificar</span>
                              <ArrowRight size={18} />
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </AgentResultCard>
          </div>
        </div>
      )}

      {/* ── STEP 7: RESULTADO FINAL PDF ── */}
      {effectiveViewStep === 7 && pdfResult && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={isProcessing}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <AgentResultCard
              agentName="Agente Concentrador y Emisor"
              role="Compilación de Dictámenes & Generación PDF Oficial"
              theme="blue"
              status="completed"
              phaseLabel="Fase 3: Redacción & PDF"
              thinkingText="Informe consolidado de auditoría generado en PDF"
              image="/robots/logos/concentrador.jpeg"
              justificacion="Publicidad, transparencia y rigor técnico: Consolida y sintetiza todos los dictámenes en un informe oficial y formaliza el reporte PDF para el plenario de la Asamblea."
              onViewPrev={() => updateActiveSession({ inspectedAgentId: 'consistencia' })}
              prevLabel="Ver Consistencia Normativa"
            >
              <FileCheck size={56} color="#00B4D8" style={{ margin: '0 auto 16px', display: 'block' }} />
              <h3 style={{ fontSize: '1.6rem', color: '#ffffff', fontWeight: 800, marginBottom: '12px', textAlign: 'center' }}>
                Informe Consolidado Generado
              </h3>
              <p style={{ color: '#94A3B8', fontSize: '1rem', maxWidth: '700px', margin: '0 auto 24px', textAlign: 'center' }}>
                El Agente Emisor ha generado el dictamen técnico-jurídico formal. Ahora puede notificar a los miembros parlamentarios de la comisión.
              </p>

              {/* ── SECCIÓN DE DESPACHO A GMAIL / CÁMARAS CON MENSAJE EXTRA (VOZ/TECLADO) ── */}
              <div style={{
                maxWidth: '680px',
                margin: '0 auto 24px auto',
                background: 'linear-gradient(145deg, rgba(13, 27, 42, 0.95) 0%, rgba(27, 42, 74, 0.90) 100%)',
                border: '1.5px solid rgba(56, 189, 248, 0.35)',
                borderRadius: '16px',
                padding: '20px',
                boxShadow: '0 8px 30px rgba(0,0,0,0.35)',
                textAlign: 'left'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px', borderBottom: '1px solid rgba(148,163,184,0.15)', paddingBottom: '10px' }}>
                  <Mail size={22} color="#38bdf8" />
                  <div>
                    <h4 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 800, color: '#ffffff' }}>
                      Despacho Institucional a Gmail / Comisión con Mensaje Extra
                    </h4>
                    <p style={{ margin: 0, fontSize: '0.78rem', color: '#94a3b8' }}>
                      Escriba o dicte por voz observaciones que se incrustarán de manera destacada en el correo formal para las autoridades.
                    </p>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px', marginBottom: '14px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.78rem', color: '#7dd3fc', fontWeight: 700, marginBottom: '6px' }}>
                      ✉️ Correo Destino / Gmail (Opcional):
                    </label>
                    <input
                      type="email"
                      placeholder="ejemplo: comision.constitucion@gmail.com"
                      value={customEmail || ''}
                      onChange={(e) => updateActiveSession({ customEmail: e.target.value })}
                      style={{
                        width: '100%',
                        padding: '9px 12px',
                        borderRadius: '8px',
                        background: 'rgba(15, 23, 42, 0.85)',
                        border: '1px solid rgba(56, 189, 248, 0.35)',
                        color: '#ffffff',
                        fontSize: '0.84rem',
                        outline: 'none',
                        boxSizing: 'border-box'
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.78rem', color: '#7dd3fc', fontWeight: 700, marginBottom: '6px' }}>
                      📌 Asunto Institucional:
                    </label>
                    <input
                      type="text"
                      placeholder="Asunto formal del dictamen..."
                      value={customEmailSubject || ''}
                      onChange={(e) => updateActiveSession({ customEmailSubject: e.target.value })}
                      style={{
                        width: '100%',
                        padding: '9px 12px',
                        borderRadius: '8px',
                        background: 'rgba(15, 23, 42, 0.85)',
                        border: '1px solid rgba(56, 189, 248, 0.35)',
                        color: '#ffffff',
                        fontSize: '0.84rem',
                        outline: 'none',
                        boxSizing: 'border-box'
                      }}
                    />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <label style={{ fontSize: '0.78rem', color: '#fbbf24', fontWeight: 700 }}>
                      📝 Mensaje Extra / Observaciones del Remitente:
                    </label>
                    <button
                      type="button"
                      onClick={() => {
                        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                          alert('Reconocimiento de voz no disponible en este navegador.');
                          return;
                        }
                        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                        const rec = new SR();
                        rec.lang = 'es-BO';
                        rec.onresult = (ev) => {
                          const text = ev.results[0][0].transcript;
                          updateActiveSession({
                            extraEmailMessage: (extraEmailMessage ? extraEmailMessage + ' ' : '') + text
                          });
                        };
                        rec.start();
                      }}
                      style={{
                        background: 'rgba(245, 158, 11, 0.18)',
                        border: '1px solid rgba(245, 158, 11, 0.4)',
                        borderRadius: '6px',
                        color: '#fbbf24',
                        padding: '4px 10px',
                        fontSize: '0.74rem',
                        fontWeight: 700,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      <Mic size={13} />
                      <span>Dictar por Voz (Audio a Texto)</span>
                    </button>
                  </div>

                  <textarea
                    rows={3}
                    placeholder="Escriba mediante teclado o dicte con el micrófono observaciones adicionales para los miembros de la comisión y cámaras..."
                    value={extraEmailMessage || ''}
                    onChange={(e) => updateActiveSession({ extraEmailMessage: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '9px 12px',
                      borderRadius: '8px',
                      background: 'rgba(15, 23, 42, 0.9)',
                      border: '1px solid rgba(245, 158, 11, 0.35)',
                      color: '#ffffff',
                      fontSize: '0.84rem',
                      outline: 'none',
                      resize: 'vertical',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
              </div>

              {/* Módulo de voz: Lectura de Informe y Dictado de Observaciones para Notificar */}


              <div style={{ maxWidth: '640px', margin: '0 auto 24px auto' }}>


                {!readOnly && (<AgentVoiceModule


                  agentId="emisor"


                  agentLabel="Agente Concentrador y Emisor"


                  primaryColor="#0284C7"


                  sesionId={fase1Data?.sesion_id || null}


                  resultData={pdfResult}


                  speechHook={speechHook}


                  emailDestino={customEmail || activeSession.emailAutor}


                  onVoiceAction={(action) => {


                    if (action?.type === 'notificacion_enviada') {


                      appendLog('emisor', 'VOZ', `Observación enviada por voz: "${(action.texto || '').substring(0, 80)}"`);


                    }


                  }}


                />)}


              </div>


              <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', flexWrap: 'wrap' }}>
                <a
                  href={`${BACKEND_BASE_URL}/uploaded_files/informes/${pdfResult.filename}`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-secondary"
                  style={{ fontSize: '1rem', padding: '13px 24px', textDecoration: 'none' }}
                >
                  <Download size={20} />
                  <span>Descargar PDF</span>
                </a>
                {pdfResult?.drive_link && (
                  <a
                    href={pdfResult.drive_link}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-success"
                    style={{ fontSize: '1rem', padding: '13px 24px', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '8px' }}
                  >
                    <ExternalLink size={20} />
                    <span>Ver en Google Drive</span>
                  </a>
                )}
                <button
                  onClick={handleNotificar}
                  disabled={readOnly || isProcessing}
                  className="btn-primary"
                  style={{ fontSize: '1rem', padding: '13px 26px' }}
                >
                  {isProcessing ? (
                    <><Cpu size={20} className="pulse-active" /><span>Redactando y Enviando...</span></>
                  ) : (
                    <><Mail size={20} /><span>Notificar a Comisión (5to Agente)</span><ArrowRight size={18} /></>
                  )}
                </button>
                <button className="btn-secondary" onClick={handleReset} style={{ fontSize: '1rem', padding: '13px 24px' }}>
                  <RotateCcw size={20} />
                  <span>Nuevo Análisis</span>
                </button>
              </div>
            </AgentResultCard>
          </div>
        </div>
      )}

      {/* ── STEP 8: NOTIFICADOR DE COMISIÓN ── */}
      {effectiveViewStep === 8 && notificadorData && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={isProcessing}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <AgentResultCard
              agentName="Agente Notificador de Comisión"
              role="Despachador de Correo HTML Institucional"
              theme="violet"
              status="completed"
              phaseLabel="Fase 3: Notificación Oficial"
              thinkingText="Correo electrónico HTML despachado con éxito"
              image="/robots/logos/agente_comodin.jpeg"
              justificacion="Debida notificación y publicidad parlamentaria: Despacha la comunicación oficial en formato HTML formal a los correos electrónicos institucionales de los miembros asignados."
              onViewPrev={() => updateActiveSession({ inspectedAgentId: 'emisor' })}
              prevLabel="Ver PDF Generado (Emisor)"
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <Mail size={32} color="#a78bfa" />
                    <h3 style={{ fontSize: '1.45rem', color: '#ffffff', fontWeight: 800, margin: 0 }}>
                      📨 Correo HTML Formal Generado
                    </h3>
                  </div>
                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    <div style={{ background: 'rgba(0,0,0,0.35)', padding: '8px 14px', borderRadius: '10px', textAlign: 'center' }}>
                      <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#a78bfa' }}>
                        {notificadorData.total_destinatarios || 0}
                      </div>
                      <div style={{ fontSize: '0.68rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase' }}>Destinatarios</div>
                    </div>
                  </div>
                </div>

                {/* Metadatos del despacho */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px', marginBottom: '24px' }}>
                  <div className="process-step completed">
                    <div className="process-step-number">✓</div>
                    <div>
                      <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.45)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Comisión Notificada</div>
                      <div style={{ fontWeight: 700, color: '#e8edf5', fontSize: '0.95rem', marginTop: '2px' }}>
                        {notificadorData.comision || 'Comisión Legislativa'}
                      </div>
                    </div>
                  </div>
                  <div className="process-step completed">
                    <div className="process-step-number">✓</div>
                    <div>
                      <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.45)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Asunto del Correo</div>
                      <div style={{ fontWeight: 600, color: '#94a3b8', fontSize: '0.84rem', marginTop: '2px', lineHeight: 1.4 }}>
                        {notificadorData.asunto}
                      </div>
                    </div>
                  </div>
                  <div className="process-step completed">
                    <div className="process-step-number">✓</div>
                    <div>
                      <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.45)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Fecha de Despacho</div>
                      <div style={{ fontWeight: 700, color: '#e8edf5', fontSize: '0.9rem', marginTop: '2px' }}>
                        {notificadorData.fecha_despacho ? new Date(notificadorData.fecha_despacho).toLocaleString('es-BO') : '—'}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Destinatarios */}
                {notificadorData.miembros_notificados?.length > 0 && (
                  <div style={{ marginBottom: '24px' }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>
                      👥 Miembros Destinatarios
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {notificadorData.miembros_notificados.map((m, i) => (
                        <div key={i} style={{
                          display: 'flex', alignItems: 'center', gap: '8px',
                          background: 'rgba(14,19,32,0.85)', padding: '8px 14px', borderRadius: '10px',
                          border: '1px solid rgba(168,85,247,0.22)'
                        }}>
                          <div style={{ width: 30, height: 30, borderRadius: '50%', background: 'rgba(168,85,247,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.85rem', flexShrink: 0 }}>
                            👤
                          </div>
                          <div>
                            <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#e8edf5' }}>{m.nombre_completo}</div>
                            <div style={{ fontSize: '0.72rem', color: '#a78bfa' }}>{m.cargo} · {m.tipo_camara}</div>
                            {m.email && <div style={{ fontSize: '0.7rem', color: '#64748b', fontFamily: 'monospace' }}>{m.email}</div>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Vista previa del correo HTML */}
                <div style={{ marginBottom: '24px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                      📧 Vista Previa del Correo HTML Institucional
                    </div>
                    <button
                      onClick={() => updateActiveSession({ showEmailPreview: !showEmailPreview })}
                      className="btn-secondary"
                      style={{ padding: '6px 14px', fontSize: '0.8rem' }}
                    >
                      {showEmailPreview ? 'Ocultar Vista Previa' : 'Mostrar Vista Previa'}
                    </button>
                  </div>
                  {showEmailPreview && notificadorData.html_preview && (
                    <div className="email-preview-frame" style={{ maxHeight: '600px', overflowY: 'auto' }}>
                      <iframe
                        srcDoc={notificadorData.html_preview}
                        title="Vista previa del correo institucional"
                        style={{ width: '100%', height: '580px', border: 'none', display: 'block' }}
                        sandbox="allow-same-origin"
                      />
                    </div>
                  )}
                </div>

                {/* Acciones finales */}
                <div className="glow-divider" />
                <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', flexWrap: 'wrap' }}>
                  {/* Botón para avanzar a la siguiente etapa legislativa: Comisión Constitución Fondo */}
                  <button
                    onClick={handleConstitucionFondo}
                    disabled={readOnly || isProcessing}
                    className="btn-primary"
                    style={{
                      fontSize: '1rem',
                      padding: '13px 26px'
                    }}
                  >
                    {isProcessing ? (
                      <><Cpu size={20} className="pulse-active" /><span>Iniciando Análisis de Fondo...</span></>
                    ) : (
                      <><BookOpen size={20} /><span>Continuar: Comisión Constitución (Fondo)</span><ArrowRight size={18} /></>
                    )}
                  </button>

                  {pdfResult?.filename && (
                    <a
                      href={`${BACKEND_BASE_URL}/uploaded_files/informes/${pdfResult.filename}`}
                      target="_blank" rel="noreferrer"
                      className="btn-secondary"
                      style={{ fontSize: '1rem', padding: '13px 24px', textDecoration: 'none' }}
                    >
                      <Download size={20} />
                      <span>Descargar PDF</span>
                    </a>
                  )}
                  {onNavigateExpedientes && (
                    <button className="btn-success" onClick={onNavigateExpedientes}
                      style={{ fontSize: '1rem', padding: '13px 24px' }}>
                      <ExternalLink size={20} />
                      <span>Ver Expedientes</span>
                    </button>
                  )}
                  <button className="btn-secondary" onClick={handleReset} style={{ fontSize: '1rem', padding: '13px 24px' }}>
                    <RotateCcw size={20} />
                    <span>Nuevo Análisis</span>
                  </button>
                </div>
              </div>
            </AgentResultCard>
          </div>
        </div>
      )}

      {/* ── STEP 09: PROCESANDO CONSTITUCIÓN FONDO ── */}
      {effectiveViewStep === 9 && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={true}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <div className="glass-card" style={{ padding: '48px', textAlign: 'center' }}>
              <Sparkles size={56} color="#a855f7" className="pulse-active" style={{ margin: '0 auto 20px' }} />
              <h2 style={{ fontSize: '1.5rem', color: '#ffffff', marginBottom: '8px' }}>
                Comisión de Constitución (Fondo) en Ejecución
              </h2>
              <p style={{ color: '#e9d5ff', fontSize: '0.95rem', maxWidth: '650px', margin: '0 auto 20px' }}>
                Aplicando interpretación sistemática, ponderación de derechos y jurisprudencia del Tribunal Constitucional Plurinacional...
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── STEP 10: RESULTADO CONSTITUCIÓN FONDO ── */}
      {effectiveViewStep === 10 && constitucionFondoData && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={isProcessing}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <AgentResultCard
              agentName="Comisión Constitución (Fondo)"
              role="Análisis Hermenéutico y Viabilidad Sustantiva"
              theme="purple"
              status="completed"
              phaseLabel="Fase 4: Fondo CPE"
              thinkingText="Dictamen sustantivo de constitucionalidad emitido"
              image="/robots/logos/agente_constitucional.jpeg"
              justificacion="Art. 196 CPE: Control de constitucionalidad de fondo, precedentes del TCP y ponderación proporcional de derechos fundamentales."
              onViewPrev={() => updateActiveSession({ inspectedAgentId: 'notificador' })}
              prevLabel="Ver Notificación de Comisión"
            >
              {(() => {
                const df = constitucionFondoData.dictamen_fondo || {};
                const herm = df.analisis_hermeneutico || {};
                return (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                        <div style={{ background: 'rgba(168,85,247,0.2)', borderRadius: '50%', padding: '12px' }}>
                          <BookOpen size={32} color="#c084fc" />
                        </div>
                        <div>
                          <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                            Etapa 3 · Dictamen de Mérito Constitucional
                          </div>
                          <h3 style={{ fontSize: '1.4rem', color: '#ffffff', fontWeight: 800, margin: 0 }}>
                            Viabilidad Constitucional Sustantiva
                          </h3>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                        <span className="badge" style={{ background: 'rgba(168,85,247,0.25)', color: '#d8b4fe', border: '1px solid #a855f7' }}>
                          {df.viabilidad_fondo || 'VIABLE'}
                        </span>
                        <span className="badge" style={{
                          background: df.riesgo_constitucional === 'ALTO' ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)',
                          color: df.riesgo_constitucional === 'ALTO' ? '#f87171' : '#34d399',
                          border: `1px solid ${df.riesgo_constitucional === 'ALTO' ? '#ef4444' : '#10b981'}`
                        }}>
                          Riesgo: {df.riesgo_constitucional || 'BAJO'}
                        </span>
                      </div>
                    </div>

                    {/* Precedentes TC y Principios */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginBottom: '20px' }}>
                      <div style={{ background: 'rgba(14,19,32,0.85)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(168,85,247,0.25)' }}>
                        <h4 style={{ color: '#c084fc', fontSize: '0.9rem', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          ⚖️ Principios Constitucionales
                        </h4>
                        <ul style={{ margin: 0, paddingLeft: '18px', color: '#e2e8f0', fontSize: '0.85rem', lineHeight: 1.6 }}>
                          {(herm.principios_aplicables || []).map((p, i) => <li key={i}>{p}</li>)}
                        </ul>
                      </div>

                      <div style={{ background: 'rgba(14,19,32,0.85)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(168,85,247,0.25)' }}>
                        <h4 style={{ color: '#c084fc', fontSize: '0.9rem', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          🏛️ Precedentes TCP Relevantes
                        </h4>
                        <ul style={{ margin: 0, paddingLeft: '18px', color: '#e2e8f0', fontSize: '0.85rem', lineHeight: 1.6 }}>
                          {(herm.precedentes_relevantes || []).map((p, i) => <li key={i}>{p}</li>)}
                        </ul>
                      </div>
                    </div>

                    {/* Interpretación Sistemática */}
                    {herm.interpretacion_sistematica && (
                      <div style={{ background: 'rgba(88,28,135,0.2)', border: '1px solid rgba(168,85,247,0.3)', padding: '16px', borderRadius: '12px', marginBottom: '20px' }}>
                        <div style={{ fontSize: '0.75rem', color: '#c084fc', textTransform: 'uppercase', fontWeight: 700, marginBottom: '4px' }}>
                          Interpretación Sistemática del Bloque Constitucional
                        </div>
                        <p style={{ color: '#f3e8ff', fontSize: '0.88rem', lineHeight: 1.6, margin: 0 }}>
                          {herm.interpretacion_sistematica}
                        </p>
                      </div>
                    )}

                    {/* Recomendación */}
                    {df.recomendaciones && (
                      <div style={{ background: 'rgba(14,22,42,0.7)', border: '1px solid rgba(251,191,36,0.3)', padding: '14px 18px', borderRadius: '12px', marginBottom: '24px' }}>
                        <span style={{ color: '#fbbf24', fontWeight: 700, fontSize: '0.85rem' }}>💡 Recomendaciones de Técnica Legislativa: </span>
                        <span style={{ color: '#fef3c7', fontSize: '0.85rem' }}>{df.recomendaciones}</span>
                      </div>
                    )}

                    {/* Acción Siguiente */}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '14px' }}>
                      <button
                        onClick={handleConcentrador}
                        disabled={readOnly || isProcessing}
                        className="btn-primary"
                        style={{ fontSize: '1.05rem', padding: '14px 30px' }}
                      >
                        {isProcessing ? (
                          <><Cpu size={20} className="pulse-active" /><span>Consolidando...</span></>
                        ) : (
                          <><Merge size={20} /><span>Continuar: Concentrador y Emisor (CrewAI)</span><ArrowRight size={18} /></>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })()}
            </AgentResultCard>
          </div>
        </div>
      )}

      {/* ── STEP 11: RESULTADO CONCENTRADOR (CREWAI) ── */}
      {effectiveViewStep === 11 && concentradorData && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={isProcessing}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <AgentResultCard
              agentName="Agente Concentrador, Emisor y Notificador"
              role="Síntesis de Expediente, Dictamen Formal en PDF & Despacho a Comisión"
              theme="blue"
              status="completed"
              phaseLabel="Fase 3: Síntesis, Dictamen PDF & Despacho"
              thinkingText="Expediente unificado consolidado, PDF formal generado y notificación despachada"
              image="/robots/logos/concentrador.jpeg"
              justificacion="Fe pública y debido proceso parlamentario: Consolida los dictámenes constitucionales y normativos, emite el reporte oficial con letra negra formal y despacha la notificación a los miembros de la comisión."
              onViewPrev={() => updateActiveSession({ inspectedAgentId: 'consistencia' })}
              prevLabel="Ver Consistencia Normativa"
            >
              {(() => {
                const exp = concentradorData.expediente_consolidado || {};
                const obsList = exp.observaciones_integradas || [];
                const pdfFilename = pdfResult?.filename || concentradorData?.pdf?.filename || concentradorData?.pdf_filename || '';
                const notifInfo = notificadorData || concentradorData?.notificacion_comision || {};
                return (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                        <div style={{ background: 'rgba(0,180,216,0.15)', borderRadius: '50%', padding: '12px' }}>
                          <Merge size={32} color="#00B4D8" />
                        </div>
                        <div>
                          <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                            Etapa 5 · Expediente Consolidado, Dictamen PDF & Notificación
                          </div>
                          <h3 style={{ fontSize: '1.4rem', color: '#ffffff', fontWeight: 800, margin: 0 }}>
                            Expediente Unificado y Despacho Formal
                          </h3>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '10px' }}>
                        <span className="badge" style={{ background: 'rgba(0,180,216,0.15)', color: '#00B4D8', border: '1px solid #00B4D8' }}>
                          {obsList.length} Observaciones
                        </span>
                        <span className="badge" style={{ background: 'rgba(56,189,248,0.15)', color: '#38bdf8', border: '1px solid #38bdf8' }}>
                          Riesgo: {exp.nivel_riesgo_general || 'MEDIO'}
                        </span>
                      </div>
                    </div>

                    {concentradorData.informe_profesional && concentradorData.informe_profesional.estado !== 'NO_APLICA' && (
                      <section style={{ padding: 18, border: '1px solid #38bdf8', borderRadius: 12, marginBottom: 20 }}>
                        <h4 style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                          <img src="/robots/logos/asistente_profesional.jpg" alt="" style={{ width: 38, height: 38, borderRadius: '50%', objectFit: 'cover' }} />
                          Agente multifacético · Informe profesional
                        </h4>
                        <p>{concentradorData.informe_profesional.profesiones?.join(' · ')}</p>
                        <p style={{ whiteSpace: 'pre-wrap' }}>{concentradorData.informe_profesional.informe || 'Revisión profesional pendiente.'}</p>
                        {concentradorData.informe_profesional.error && <p role="status">{concentradorData.informe_profesional.error}</p>}
                        <small>Orientación complementaria a las auditorías constitucional y normativa.</small>
                        {concentradorData.informe_profesional.fuentes?.length > 0 && <details>
                          <summary>Reglamentos y páginas consultados</summary>
                          <ul>{concentradorData.informe_profesional.fuentes.map(f => (
                            <li key={f.referencia}>[{f.referencia}] {f.titulo} — {f.archivo}, página PDF {f.pagina}</li>
                          ))}</ul>
                        </details>}
                      </section>
                    )}
                    {/* Resumen Ejecutivo */}
                    <div style={{ background: 'rgba(11,37,69,0.6)', border: '1px solid rgba(0,180,216,0.3)', padding: '18px', borderRadius: '12px', marginBottom: '20px' }}>
                      <h4 style={{ color: '#00B4D8', fontSize: '0.9rem', marginBottom: '6px' }}>📋 Resumen Ejecutivo Consolidado</h4>
                      <p style={{ color: '#d1fae5', fontSize: '0.88rem', lineHeight: 1.6, margin: 0 }}>
                        {exp.resumen_ejecutivo || 'Expediente consolidado con observaciones integradas de todos los agentes.'}
                      </p>
                    </div>

                    {/* ── BLOQUE DE DICTAMEN FORMAL EN PDF (EMISOR INTEGRADO) ── */}
                    {pdfFilename && (
                      <div style={{
                        background: 'linear-gradient(145deg, rgba(15,23,42,0.9) 0%, rgba(20,35,60,0.85) 100%)',
                        border: '1.5px solid rgba(56,189,248,0.35)',
                        borderRadius: '12px',
                        padding: '16px 20px',
                        marginBottom: '20px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        flexWrap: 'wrap',
                        gap: '14px'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <FileCheck size={28} color="#38bdf8" />
                          <div>
                            <div style={{ fontSize: '0.75rem', color: '#7dd3fc', fontWeight: 700, textTransform: 'uppercase' }}>
                              Dictamen Formal Institucional Emitido (PDF Letra Negra)
                            </div>
                            <div style={{ color: '#ffffff', fontWeight: 700, fontSize: '0.9rem', marginTop: '2px' }}>
                              {pdfFilename}
                            </div>
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                          <a
                            href={`${BACKEND_BASE_URL}/uploaded_files/informes/${pdfFilename}`}
                            target="_blank"
                            rel="noreferrer"
                            className="btn-secondary"
                            style={{ fontSize: '0.88rem', padding: '9px 18px', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '8px' }}
                          >
                            <Download size={16} />
                            <span>Descargar Dictamen Formal (PDF)</span>
                          </a>
                          {(concentradorData?.pdf_informe?.drive_link || pdfResult?.drive_link) && (
                            <a
                              href={concentradorData?.pdf_informe?.drive_link || pdfResult?.drive_link}
                              target="_blank"
                              rel="noreferrer"
                              style={{
                                fontSize: '0.88rem',
                                padding: '9px 18px',
                                textDecoration: 'none',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                background: 'rgba(16,185,129,0.18)',
                                border: '1px solid rgba(16,185,129,0.45)',
                                color: '#34d399',
                                borderRadius: '8px',
                                fontWeight: 700
                              }}
                            >
                              <ExternalLink size={16} />
                              <span>Google Drive</span>
                            </a>
                          )}
                        </div>
                      </div>
                    )}

                    {/* ── BLOQUE DE DESPACHO / NOTIFICACIÓN A COMISIÓN (NOTIFICADOR INTEGRADO) ── */}
                    {notifInfo && (
                      <div style={{
                        background: 'rgba(15,23,42,0.7)',
                        border: '1px solid rgba(168,85,247,0.3)',
                        borderRadius: '12px',
                        padding: '16px 20px',
                        marginBottom: '20px'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '10px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <Mail size={22} color="#a78bfa" />
                            <div>
                              <div style={{ color: '#ffffff', fontWeight: 800, fontSize: '0.92rem' }}>
                                Notificación Oficial Despachada a la Comisión
                              </div>
                              <div style={{ color: '#94a3b8', fontSize: '0.78rem' }}>
                                {notifInfo.comision || comisionData?.comision_principal || 'Comisión Asignada'} · {notifInfo.total_destinatarios || (notifInfo.miembros_notificados?.length) || 1} destinatarios notificados
                              </div>
                            </div>
                          </div>
                          {notifInfo.html_preview && (
                            <button
                              type="button"
                              onClick={() => updateActiveSession({ showEmailPreview: !showEmailPreview })}
                              className="btn-secondary"
                              style={{ padding: '6px 14px', fontSize: '0.78rem' }}
                            >
                              {showEmailPreview ? 'Ocultar Correo' : 'Ver Vista Previa del Correo'}
                            </button>
                          )}
                        </div>
                        {showEmailPreview && notifInfo.html_preview && (
                          <div style={{ marginTop: '12px', maxHeight: '420px', overflowY: 'auto', borderRadius: '8px', border: '1px solid rgba(148,163,184,0.2)' }}>
                            <iframe
                              srcDoc={notifInfo.html_preview}
                              title="Vista previa del correo de comisión"
                              style={{ width: '100%', height: '400px', border: 'none', display: 'block' }}
                              sandbox="allow-same-origin"
                            />
                          </div>
                        )}
                      </div>
                    )}

                    {/* Lista de Observaciones Integradas */}
                    {obsList.length > 0 && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '24px' }}>
                        <div style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase' }}>
                          Observaciones Integradas con Trazabilidad:
                        </div>
                        {obsList.map((o, idx) => {
                          const artLabel = o.articulo_afectado || o.articulo || '';
                          const textoObs = o.cita_original || (typeof o.contenido === 'string' ? o.contenido : o.fundamento || (o.contenido ? JSON.stringify(o.contenido) : 'Observación técnica'));
                          const fuenteLabel = o.agente_origen || o.fuente || (Array.isArray(o.fuentes) ? o.fuentes.join(', ') : 'Agente');
                          return (
                            <div key={idx} style={{
                              background: 'rgba(15,23,42,0.7)',
                              border: '1px solid rgba(148,163,184,0.2)',
                              padding: '12px 16px',
                              borderRadius: '10px',
                              display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px'
                            }}>
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
                                  <span style={{ fontWeight: 700, color: '#38bdf8', fontSize: '0.85rem' }}>
                                    [{o.tipo || 'OBS'}]
                                  </span>
                                  {artLabel && artLabel !== 'N/A' && (
                                    <span style={{ fontWeight: 600, color: '#e2e8f0', fontSize: '0.82rem' }}>
                                      {artLabel}
                                    </span>
                                  )}
                                  {o.riesgo && (
                                    <span className="badge" style={{
                                      fontSize: '0.65rem', padding: '1px 6px',
                                      background: (o.riesgo === 'bloqueante' || o.riesgo === 'grave') ? 'rgba(239,68,68,0.2)' : 'rgba(234,179,8,0.2)',
                                      color: (o.riesgo === 'bloqueante' || o.riesgo === 'grave') ? '#f87171' : '#facc15'
                                    }}>
                                      {o.riesgo}
                                    </span>
                                  )}
                                </div>
                                <div style={{ color: '#94a3b8', fontSize: '0.82rem', lineHeight: 1.4 }}>
                                  {String(textoObs).slice(0, 200)}{String(textoObs).length > 200 ? '...' : ''}
                                </div>
                              </div>
                              <span className="badge" style={{ fontSize: '0.7rem', padding: '2px 8px', background: 'rgba(56,189,248,0.15)', color: '#38bdf8', flexShrink: 0 }}>
                                {fuenteLabel}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Acción Siguiente */}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '14px' }}>
                      <button
                        onClick={handleSecretario}
                        disabled={readOnly || isProcessing}
                        className="btn-primary"
                        style={{ fontSize: '1.05rem', padding: '14px 30px' }}
                      >
                        {isProcessing ? (
                          <><Cpu size={20} className="pulse-active" /><span>Registrando debate...</span></>
                        ) : (
                          <><MessagesSquare size={20} /><span>Continuar: Debate Parlamentario (Secretario)</span><ArrowRight size={18} /></>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })()}
            </AgentResultCard>
          </div>
        </div>
      )}

      {/* ── STEP 12: RESULTADO SECRETARIO DE CÁMARA (DEBATE) ── */}
      {effectiveViewStep === 12 && secretarioData && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={isProcessing}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <AgentResultCard
              agentName="Agente Secretario de Cámara"
              role="Registro de Actas de Debate Parlamentario y Votaciones"
              theme="blue"
              status="completed"
              phaseLabel="Fase 4: Debate Plenario"
              thinkingText="Acta parlamentaria y votaciones nominales registradas"
              image="/robots/logos/agente_secretario.jpeg"
              justificacion="Transparencia y publicidad legislativa: Registro fidedigno de intervenciones de legisladores, votaciones en grande y detalle, y acuerdos tomados en plenario."
              onViewPrev={() => updateActiveSession({ inspectedAgentId: 'concentrador_crew' })}
              prevLabel="Ver Expediente Concentrador"
            >
              {(() => {
                const acta = secretarioData.acta_debate || {};
                const votaciones = acta.votaciones || [];
                return (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                        <div style={{ background: 'rgba(0,180,216,0.15)', borderRadius: '50%', padding: '12px' }}>
                          <MessagesSquare size={32} color="#00B4D8" />
                        </div>
                        <div>
                          <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                            Etapa 5 · Acta de Debate Parlamentario
                          </div>
                          <h3 style={{ fontSize: '1.4rem', color: '#ffffff', fontWeight: 800, margin: 0 }}>
                            {acta.camara || 'Cámara de Diputados'} — Sesión #{acta.sesion_numero || 1}
                          </h3>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '10px' }}>
                        <span className="badge badge-blue">
                          Fecha: {acta.fecha || new Date().toISOString().split('T')[0]}
                        </span>
                        <span className="badge badge-green">
                          Estado: {acta.estado_siguiente || 'EN_TRAMITE_BICAMERAL'}
                        </span>
                      </div>
                    </div>

                    {/* TÍTULO DE LA NORMATIVA EN TRATAMIENTO Y VISOR DEL DOCUMENTO ANALIZADO */}
                    <div style={{
                      background: 'linear-gradient(135deg, rgba(30,58,138,0.3) 0%, rgba(15,23,42,0.85) 100%)',
                      border: '1px solid rgba(56,189,248,0.35)',
                      padding: '16px 20px',
                      borderRadius: '12px',
                      marginBottom: '16px'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                        <div style={{ flex: 1, minWidth: '280px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <span style={{ fontSize: '0.72rem', color: '#7dd3fc', fontWeight: 700, letterSpacing: '0.05em' }}>
                              NORMATIVA EN DEBATE PLENARIO:
                            </span>
                            <span style={{ background: 'rgba(56,189,248,0.15)', color: '#38bdf8', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600 }}>
                              Expediente: {fase1Data?.numero_expediente || `PL-${fase1Data?.id_proyecto || 136}/2026`}
                            </span>
                          </div>
                          <h4 style={{ margin: '4px 0 8px 0', color: '#ffffff', fontSize: '1.1rem', fontWeight: 700, lineHeight: 1.4 }}>
                            {acta.normativa_titulo || fase1Data?.nombre_archivo || 'Proyecto de Ley en Plenaria'}
                          </h4>
                          <div style={{ display: 'flex', gap: '16px', fontSize: '0.8rem', color: '#94a3b8', flexWrap: 'wrap' }}>
                            <span>Archivo Base: <strong style={{ color: '#e2e8f0' }}>{fase1Data?.nombre_archivo || 'PL-CS-010-2023-2024.pdf'}</strong></span>
                            <span>Artículos en Votación: <strong style={{ color: '#86efac' }}>{(acta.votacion_en_detalle || []).length} artículos registrados</strong></span>
                          </div>
                        </div>

                        {/* Botones de acción del documento */}
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                          <button
                            type="button"
                            onClick={() => updateActiveSession({ showDocumentoDebate: !showDocumentoDebate })}
                            className="btn-secondary"
                            style={{
                              padding: '8px 16px',
                              fontSize: '0.82rem',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px',
                              background: showDocumentoDebate ? 'rgba(56,189,248,0.25)' : 'rgba(30,41,59,0.85)',
                              borderColor: showDocumentoDebate ? '#38bdf8' : 'rgba(148,163,184,0.3)',
                              color: showDocumentoDebate ? '#38bdf8' : '#ffffff',
                              fontWeight: 600,
                              cursor: 'pointer'
                            }}
                          >
                            <BookOpen size={16} />
                            <span>{showDocumentoDebate ? 'Ocultar Documento Analizado' : 'Ver Documento Analizado'}</span>
                          </button>

                          {fase1Data?.archivo_pdf && (
                            <a
                              href={`/uploaded_files/${fase1Data.archivo_pdf}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn-secondary"
                              style={{
                                padding: '8px 14px',
                                fontSize: '0.82rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                textDecoration: 'none',
                                color: '#e2e8f0',
                                background: 'rgba(30,41,59,0.7)',
                                border: '1px solid rgba(148,163,184,0.25)',
                                borderRadius: '8px'
                              }}
                              title="Abrir el PDF original en nueva pestaña"
                            >
                              <ExternalLink size={15} />
                              <span>PDF Original</span>
                            </a>
                          )}
                        </div>
                      </div>

                      {/* Visor interactivo del texto analizado */}
                      {showDocumentoDebate && (
                        <div style={{
                          marginTop: '16px',
                          background: 'rgba(15,23,42,0.95)',
                          border: '1px solid rgba(56,189,248,0.3)',
                          borderRadius: '10px',
                          padding: '16px'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <FileText size={18} color="#38bdf8" />
                              <span style={{ fontSize: '0.82rem', color: '#38bdf8', fontWeight: 700, letterSpacing: '0.04em' }}>
                                CONTENIDO ÍNTEGRO DEL DOCUMENTO NORMATIVO ANALIZADO:
                              </span>
                            </div>
                            <button
                              type="button"
                              onClick={() => {
                                const texto = acta.texto_documento || acta.texto_aprobado || documentText || '';
                                navigator.clipboard.writeText(texto);
                                setCopiedDebateText(true);
                                setTimeout(() => setCopiedDebateText(false), 2000);
                              }}
                              className="btn-secondary"
                              style={{ padding: '5px 12px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}
                            >
                              {copiedDebateText ? <Check size={14} color="#86efac" /> : <Copy size={14} />}
                              <span>{copiedDebateText ? '¡Copiado al portapapeles!' : 'Copiar Texto Completo'}</span>
                            </button>
                          </div>

                          <div style={{
                            maxHeight: '450px',
                            overflowY: 'auto',
                            background: 'rgba(2,6,23,0.75)',
                            padding: '16px 18px',
                            borderRadius: '8px',
                            fontSize: '0.84rem',
                            color: '#e2e8f0',
                            lineHeight: 1.65,
                            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                            whiteSpace: 'pre-wrap',
                            border: '1px solid rgba(148,163,184,0.15)'
                          }}>
                            {acta.texto_documento || acta.texto_aprobado || documentText || 'No hay texto disponible para este documento.'}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* 1. RESULTADOS DEL ANÁLISIS EN GRANDE */}
                    {acta.votacion_en_grande && (
                      <div style={{ background: 'rgba(15,23,42,0.85)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(0,180,216,0.3)', marginBottom: '16px' }}>
                        <h4 style={{ color: '#00B4D8', fontSize: '0.95rem', margin: '0 0 12px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          🟦 Resultados del análisis en grande (Votación General)
                        </h4>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(clamp(110px, 20vw, 150px), 1fr))', gap: '10px' }}>
                          <div style={{ background: 'rgba(30,41,59,0.7)', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>A Favor</span>
                            <div style={{ color: '#8AC926', fontSize: '1.25rem', fontWeight: 800 }}>{acta.votacion_en_grande.favor ?? 0}</div>
                          </div>
                          <div style={{ background: 'rgba(30,41,59,0.7)', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>En Contra</span>
                            <div style={{ color: '#f87171', fontSize: '1.25rem', fontWeight: 800 }}>{acta.votacion_en_grande.contra ?? 0}</div>
                          </div>
                          <div style={{ background: 'rgba(30,41,59,0.7)', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Abstenciones</span>
                            <div style={{ color: '#F4A261', fontSize: '1.25rem', fontWeight: 800 }}>{acta.votacion_en_grande.abstenciones ?? 0}</div>
                          </div>
                          <div style={{ background: 'rgba(30,41,59,0.7)', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Resultado</span>
                            <div style={{ color: acta.votacion_en_grande.resultado === 'APROBADO' ? '#8AC926' : '#f87171', fontSize: '1rem', fontWeight: 800 }}>
                              {acta.votacion_en_grande.resultado || 'APROBADO'}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 2. RESULTADOS DEL ANÁLISIS EN DETALLE */}
                    <div style={{ background: 'rgba(15,23,42,0.85)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(134,239,172,0.25)', marginBottom: '16px' }}>
                      <h4 style={{ color: '#86efac', fontSize: '0.95rem', margin: '0 0 12px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        🟩 Resultados del análisis en detalle (artículo por artículo)
                      </h4>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(clamp(200px, 28vw, 280px), 1fr))', gap: '12px' }}>
                        {(acta.votacion_en_detalle && acta.votacion_en_detalle.length > 0 ? acta.votacion_en_detalle : votaciones).map((v, idx) => (
                          <div key={idx} style={{
                            background: 'rgba(30,41,59,0.7)',
                            padding: '12px 14px',
                            borderRadius: '10px',
                            border: '1px solid rgba(148,163,184,0.2)'
                          }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                              <span style={{ color: '#ffffff', fontWeight: 700, fontSize: '0.9rem' }}>
                                {v.etiqueta || (v.articulo ? (String(v.articulo).toLowerCase().startsWith('disposicion') ? v.articulo : `Art. ${v.articulo}`) : `Art. ${idx + 1}`)}
                              </span>
                              <span className={v.resultado === 'APROBADO' ? 'badge badge-green' : v.resultado === 'RECHAZADO' ? 'badge badge-red' : 'badge badge-yellow'}>{v.resultado || v.votacion || 'APROBADO'}</span>
                            </div>
                            {v.epigrafe && !(v.etiqueta && v.etiqueta.includes(v.epigrafe)) && (
                              <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginBottom: '6px' }}>
                                {v.epigrafe}
                              </div>
                            )}
                            <div style={{ display: 'flex', gap: '12px', fontSize: '0.82rem', color: '#cbd5e1', flexWrap: 'wrap' }}>
                              <span>A favor: <strong style={{ color: '#8AC926' }}>{v.favor ?? 0}</strong></span>
                              <span>En contra: <strong style={{ color: '#f87171' }}>{v.contra ?? 0}</strong></span>
                              <span>Abstención: <strong style={{ color: '#F4A261' }}>{v.abstenciones ?? 0}</strong></span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* ANTECEDENTES DE COMISIÓN CONSOLIDADOS */}
                    {acta.antecedentes_comision_consolidados && (
                      <div style={{ background: 'rgba(15,23,42,0.7)', padding: '12px 16px', borderRadius: '8px', border: '1px solid rgba(56,189,248,0.2)', marginBottom: '16px', fontSize: '0.82rem', color: '#cbd5e1' }}>
                        <span style={{ color: '#7dd3fc', fontWeight: 700 }}>Antecedentes Consolidados de Comisión:</span>{' '}
                        Comisión de origen: <strong>{acta.antecedentes_comision_consolidados.comision_origen || 'Comisión Ordinaria'}</strong>.
                        Se integraron las observaciones técnicas y constitucionales previas para la versión final remitida al Pleno.
                      </div>
                    )}


                    {/* Acuerdos */}
                    {acta.acuerdos && acta.acuerdos.length > 0 && (
                      <div style={{ background: 'rgba(14,22,42,0.7)', padding: '14px 18px', borderRadius: '12px', border: '1px solid rgba(56,189,248,0.25)', marginBottom: '24px' }}>
                        <div style={{ fontSize: '0.8rem', color: '#38bdf8', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>
                          Acuerdos del Plenario:
                        </div>
                        <ul style={{ margin: 0, paddingLeft: '18px', color: '#e2e8f0', fontSize: '0.85rem' }}>
                          {acta.acuerdos.map((a, i) => <li key={i}>{a}</li>)}
                        </ul>
                      </div>
                    )}

                    {/* Módulo de voz independiente: Secretario de Cámara */}
                    {!readOnly && (
                      <div style={{ marginBottom: '20px', width: '100%' }}>
                        <AgentVoiceModule
                          agentId="secretario"
                          agentLabel="Agente Secretario de Cámara"
                          primaryColor="#1E40AF"
                          sesionId={fase1Data?.sesion_id || null}
                          resultData={secretarioData}
                          speechHook={speechHook}
                          onAgregarCorreccion={(corr) => {
                            appendLog('secretario', 'CORRECCION', `Corrección registrada para ${corr.articulo}: ${corr.texto}`);
                          }}
                        />
                      </div>
                    )}

                    {/* Acción Siguiente: Botonera con clase responsiva dedicada */}
                    <div className="secretario-actions-row">
                      <button
                        type="button"
                        onClick={handleSecretario}
                        disabled={isProcessing}
                        className="btn-secondary btn-action-secretario"
                        title="Re-ejecutar Secretario para recargar todos los artículos extraídos del documento"
                      >
                        <RotateCcw size={18} />
                        <span>Re-procesar Acta con Artículos Reales</span>
                      </button>

                      <button
                        onClick={handleBicameral}
                        disabled={readOnly || isProcessing}
                        className="btn-primary btn-action-secretario btn-action-primary"
                      >
                        {isProcessing ? (
                          <><Cpu size={20} className="pulse-active" /><span>Comparando cámaras...</span></>
                        ) : (
                          <><GitBranch size={20} /><span>Continuar: Trámite Bicameral</span><ArrowRight size={18} /></>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })()}
            </AgentResultCard>
          </div>
        </div>
      )}

      {/* ── STEP 13: RESULTADO COMUNICACIÓN BICAMERAL ── */}
      {effectiveViewStep === 13 && bicameralData && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={isProcessing}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <AgentResultCard
              agentName="Agente Comunicación Bicameral"
              role="Coordinación y Reconciliación entre Cámaras Legislativas"
              theme="sky"
              status="completed"
              phaseLabel="Fase 5: Bicameral"
              thinkingText="Cotejo de versiones entre Cámaras completado"
              image="/robots/logos/agente_bicamaral.jpeg"
              justificacion="Art. 163 CPE: Reconciliación del trámite bicameral entre la Cámara de Origen y la Cámara Revisora para sanción legislativa."
              onViewPrev={() => updateActiveSession({ inspectedAgentId: 'secretario' })}
              prevLabel="Ver Acta de Debate (Secretario)"
            >
              <RevisionBicameralPanel
                key={bicameralData.ciclo_bicameral?.version_revision}
                ciclo={bicameralData.ciclo_bicameral || {}}
                usuario={currentUser}
                procesando={readOnly || isProcessing}
                onDecision={handleResolverBicameral}
                onActualizar={handleActualizarBicameral}
                onContinuar={handleRemitirAlEjecutivo}
                onDevolverComision={handleDevolverComision}
                onCorregir={() => updateActiveSession({ pipelineStep: 11, inspectedAgentId: null })}
              />
              {bicameralData.ciclo_bicameral?.aprobacion_humana?.accion === 'APROBAR' && (
                <section className="revision-panel" aria-live="polite">
                  <h3>Correo a la otra cámara</h3>
                  {confirmacionBicameralData?.status === 'notificado' ? (
                    <p>Correo enviado a {confirmacionBicameralData.camara_destino}: {(confirmacionBicameralData.destinatarios || []).join(', ')}.</p>
                  ) : (
                    <>
                      <p>{confirmacionBicameralData?.mensaje || 'La aprobación está registrada. El envío de correo está pendiente.'}</p>
                      <button type="button" className="btn-secondary" disabled={readOnly || isProcessing}
                        onClick={handleConfirmarAprobacionBicameral}>
                        {isProcessing ? 'Enviando...' : 'Enviar correo a la otra cámara'}
                      </button>
                    </>
                  )}
                </section>
              )}
            </AgentResultCard>
          </div>
        </div>
      )}

      {/* ── ETAPA EJECUTIVA TRASLADADA A SU PESTAÑA ── */}
      {effectiveViewStep === 14 && (
        <section className="executive-move-card">
            <span className="executive-kicker">ETAPA POST BICAMERAL</span>
            <h2>Despacho Ejecutivo</h2>
            <p>La evaluación de veto y promulgación, el informe del Asistente de Presidencia y la decisión humana se gestionan en su espacio propio. El expediente y los dictámenes anteriores se conservan.</p>
            <button type="button" className="btn-primary" onClick={() => onNavigateEjecutivo?.()}>Abrir Despacho Ejecutivo <ArrowRight size={17}/></button>
        </section>
      )}
      {/* ── STEP 15: RESULTADO PUBLICACIÓN OFICIAL (FIN DEL PIPELINE) ── */}
      {effectiveViewStep === 15 && (
        <div className="mesa-layout-grid">
          <div className="mesa-banner-col" style={{ position: 'sticky', top: '20px' }}>
            <LateralAgentHero
              agent={activeAgentDef}
              isProcessing={isProcessing}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderAgentHeaderContainer()}
            <AgentResultCard
              agentName="Agente de Publicación Oficial"
              role="Registro Oficial y Promulgación en Gaceta / Boletín"
              theme="blue"
              status="completed"
              phaseLabel="Fase 5: Promulgación & Vigencia"
              thinkingText="Ley formalmente promulgada y registrada en el Boletín Oficial"
              image="/robots/logos/agente_publicacion.jpeg"
              justificacion="Art. 164 CPE: Las leyes serán de cumplimiento obligatorio desde el día de su publicación en la Gaceta Oficial del Estado Plurinacional."
              onViewPrev={() => onNavigateEjecutivo?.()}
              prevLabel="Ver Evaluación de Veto/Promulgación"
            >
              {(() => {
                const pub = publicacionData?.publicacion_oficial || {
                  numero_ley: 'Ley N° 1582 de Protección y Desarrollo Integral',
                  boletin_oficial: 'GAC-2026-BOL',
                  fecha_promulgacion: new Date().toISOString().slice(0, 10),
                  fecha_vigencia: 'Al día siguiente de su publicación',
                  estado_siguiente: 'LEY_VIGENTE',
                  titulo: fase1Data?.titulo || 'Proyecto de Ley Sancionado'
                };
                return (
                  <div>
                    {/* Banner de Éxito Legislativo */}
                    <div style={{
                      background: 'linear-gradient(135deg, rgba(11,37,69,0.95), rgba(19,64,116,0.85))',
                      border: '2px solid rgba(0,180,216,0.5)',
                      padding: '28px',
                      borderRadius: '16px',
                      textAlign: 'center',
                      marginBottom: '24px',
                      boxShadow: '0 0 35px rgba(0,180,216,0.25)'
                    }}>
                      <Sparkles size={52} color="#00B4D8" style={{ margin: '0 auto 12px' }} />
                      <div style={{ fontSize: '0.85rem', color: '#7dd3fc', letterSpacing: '0.15em', textTransform: 'uppercase', fontWeight: 700 }}>
                        Estado Plurinacional de Bolivia — Proceso Legislativo Concluido
                      </div>
                      <h2 style={{ fontSize: '2.2rem', color: '#ffffff', fontWeight: 900, margin: '8px 0 12px 0' }}>
                        {pub.numero_ley_str || (pub.numero_ley ? (String(pub.numero_ley).toLowerCase().includes('ley') ? pub.numero_ley : `Ley N° ${pub.numero_ley}`) : 'Ley Sancionada y Promulgada')}
                      </h2>
                      <p style={{ color: '#e0e7ff', fontSize: '1.05rem', maxWidth: '750px', margin: '0 auto' }}>
                        {String(pub.titulo || 'Proyecto de Ley').replace(/\.(pdf|docx|txt)$/i, '')}
                      </p>
                    </div>

                    {/* Metadatos de la Ley Promulgada */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '24px' }}>
                      <div style={{ background: 'rgba(15,23,42,0.85)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(0,180,216,0.3)' }}>
                        <div style={{ fontSize: '0.72rem', color: '#00B4D8', textTransform: 'uppercase', fontWeight: 700 }}>Boletín / Gaceta</div>
                        <div style={{ fontSize: '1.15rem', color: '#ffffff', fontWeight: 800, marginTop: '4px' }}>{pub.boletin_oficial || 'BOL-OFICIAL'}</div>
                      </div>

                      <div style={{ background: 'rgba(15,23,42,0.85)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(138,201,38,0.3)' }}>
                        <div style={{ fontSize: '0.72rem', color: '#8AC926', textTransform: 'uppercase', fontWeight: 700 }}>Fecha Promulgación</div>
                        <div style={{ fontSize: '1.15rem', color: '#ffffff', fontWeight: 800, marginTop: '4px' }}>{pub.fecha_promulgacion || '2026-09-05'}</div>
                      </div>

                      <div style={{ background: 'rgba(15,23,42,0.85)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(244,162,97,0.3)' }}>
                        <div style={{ fontSize: '0.72rem', color: '#F4A261', textTransform: 'uppercase', fontWeight: 700 }}>Entrada en Vigencia</div>
                        <div style={{ fontSize: '1.15rem', color: '#ffffff', fontWeight: 800, marginTop: '4px' }}>{pub.fecha_vigencia || 'Al día siguiente'}</div>
                      </div>

                      <div style={{ background: 'rgba(15,23,42,0.85)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(56,189,248,0.3)' }}>
                        <div style={{ fontSize: '0.72rem', color: '#38bdf8', textTransform: 'uppercase', fontWeight: 700 }}>Estado Normativo</div>
                        <div style={{ fontSize: '1.15rem', color: '#ffffff', fontWeight: 800, marginTop: '4px' }}>{pub.estado_siguiente || 'LEY_VIGENTE'}</div>
                      </div>
                    </div>

                    {/* ── TARJETA: TEXTO FINAL CORREGIDO Y GACETA OFICIAL ── */}
                    <div style={{
                      background: 'linear-gradient(145deg, rgba(13, 27, 42, 0.95) 0%, rgba(27, 42, 74, 0.90) 100%)',
                      border: '1.5px solid rgba(0, 194, 203, 0.4)',
                      borderRadius: '16px',
                      padding: '20px',
                      marginBottom: '24px',
                      boxShadow: '0 8px 30px rgba(0,0,0,0.35)',
                      textAlign: 'left'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', marginBottom: '14px', borderBottom: '1px solid rgba(148,163,184,0.15)', paddingBottom: '10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <FileCheck size={22} color="#00C2CB" />
                          <div>
                            <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 800, color: '#ffffff' }}>
                              Gaceta Oficial: Ley Final Sancionada con Observaciones Resueltas
                            </h4>
                            <p style={{ margin: 0, fontSize: '0.78rem', color: '#94a3b8' }}>
                              Texto legal definitivo que incorpora todas las enmiendas aplicadas por los agentes y el usuario.
                            </p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={async () => {
                            try {
                              const res = await api.getTextoConsolidado(fase1Data?.id_proyecto || 104);
                              updateActiveSession({
                                textoConsolidadoInfo: res,
                                showTextoConsolidadoModal: true
                              });
                            } catch (e) {
                              alert('Error al obtener texto consolidado: ' + e.message);
                            }
                          }}
                          style={{
                            background: 'rgba(0, 194, 203, 0.15)',
                            border: '1px solid rgba(0, 194, 203, 0.4)',
                            borderRadius: '8px',
                            color: '#00C2CB',
                            padding: '6px 14px',
                            fontSize: '0.8rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                          }}
                        >
                          <Eye size={15} />
                          <span>Ver Texto Final Corregido</span>
                        </button>
                      </div>

                      {/* ── BOTONES DE ACCIÓN DE GACETA OFICIAL ── */}
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        flexWrap: 'wrap',
                        gap: '14px',
                        background: 'rgba(15, 23, 42, 0.7)',
                        padding: '16px 20px',
                        borderRadius: '12px',
                        border: '1px solid rgba(0, 194, 203, 0.3)'
                      }}>
                        <div style={{ flex: '1 1 300px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <span style={{
                              background: 'rgba(16, 185, 129, 0.2)',
                              border: '1px solid rgba(16, 185, 129, 0.5)',
                              color: '#34d399',
                              fontWeight: 800,
                              fontSize: '0.72rem',
                              padding: '2px 8px',
                              borderRadius: '6px'
                            }}>
                              ✓ PUBLICACIÓN OFICIAL ACTIVA
                            </span>
                            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                              Edición: <strong>{pub.boletin_oficial || 'GAC-2026-BOL'}</strong>
                            </span>
                          </div>
                          <div style={{ fontSize: '0.82rem', color: '#cbd5e1' }}>
                            Texto legal auténtico registrado con sello protocolar y fuerza obligatoria según el Art. 164 CPE.
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                          {/* BOTÓN DESTACADO: PUBLICAR EN LA GACETA OFICIAL */}
                          <button
                            type="button"
                            onClick={async () => {
                              await handlePublicacion();
                            }}
                            disabled={readOnly || isProcessing}
                            className="btn-gaceta-oficial"
                            style={{
                              background: 'linear-gradient(135deg, #0284C7 0%, #00C2CB 100%)',
                              border: '1.5px solid rgba(56, 189, 248, 0.8)',
                              boxShadow: '0 0 25px rgba(0, 194, 203, 0.5)',
                              padding: '12px 24px',
                              fontSize: '0.92rem',
                              fontWeight: 900
                            }}
                          >
                            {isProcessing ? (
                              <>
                                <Cpu size={18} style={{ animation: 'spin 1s linear infinite' }} />
                                <span>Sellando y Publicando en Gaceta...</span>
                              </>
                            ) : (
                              <>
                                <Newspaper size={18} />
                                <span>🏛️ Publicar Ley en la Gaceta Oficial</span>
                              </>
                            )}
                          </button>

                          {/* BOTÓN DESCARGAR PDF */}
                          <button
                            type="button"
                            onClick={async () => {
                              try {
                                const res = await api.generarPdfGaceta(fase1Data?.id_proyecto || 104);
                                if (res.data) {
                                  updateActiveSession({ gacetaPdfData: res.data });
                                  window.open(res.data.url_descarga, '_blank');
                                }
                              } catch (e) {
                                alert('Error generando PDF de Gaceta: ' + e.message);
                              }
                            }}
                            style={{
                              background: 'linear-gradient(135deg, #0d9488 0%, #0f766e 100%)',
                              border: 'none',
                              borderRadius: '10px',
                              color: '#ffffff',
                              padding: '12px 20px',
                              fontSize: '0.86rem',
                              fontWeight: 800,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px',
                              boxShadow: '0 4px 16px rgba(13, 148, 136, 0.35)'
                            }}
                          >
                            <Download size={16} />
                            <span>Descargar PDF Gaceta</span>
                          </button>
                          {gacetaPdfData?.drive_link && (
                            <a
                              href={gacetaPdfData.drive_link}
                              target="_blank"
                              rel="noreferrer"
                              style={{
                                background: 'rgba(16,185,129,0.2)',
                                border: '1px solid rgba(16,185,129,0.5)',
                                borderRadius: '10px',
                                color: '#34d399',
                                padding: '12px 18px',
                                fontSize: '0.86rem',
                                fontWeight: 800,
                                textDecoration: 'none',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                              }}
                            >
                              <ExternalLink size={16} />
                              <span>Ver en Google Drive</span>
                            </a>
                          )}
                        </div>
                      </div>

                      {gacetaPdfData && (
                        <div style={{ marginTop: '12px', padding: '10px 16px', background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.4)', borderRadius: '8px', fontSize: '0.82rem', color: '#34d399', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                          <span>✓ Documento oficial de Gaceta generado: <strong>{gacetaPdfData.filename}</strong></span>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                            <a href={gacetaPdfData.url_descarga} target="_blank" rel="noreferrer" style={{ color: '#38bdf8', fontWeight: 700, textDecoration: 'underline' }}>Abrir Documento Digital</a>
                            {gacetaPdfData.drive_link && (
                              <a href={gacetaPdfData.drive_link} target="_blank" rel="noreferrer" style={{ color: '#10b981', fontWeight: 800, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                📁 Guardado en Drive
                              </a>
                            )}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* ── PANEL DE VOZ: LEER LEY FINAL ── */}
                    <div style={{
                      marginBottom: '24px',
                      background: 'linear-gradient(135deg, rgba(0,194,203,0.12), rgba(0,194,203,0.04))',
                      border: '2px solid rgba(0,194,203,0.35)',
                      borderRadius: '16px',
                      padding: '18px',
                      boxShadow: '0 4px 24px rgba(0,194,203,0.15)',
                    }}>
                      <div style={{ fontSize: '0.72rem', fontWeight: 800, color: '#00C2CB', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Newspaper size={13} /> Asistente de Voz — Gaceta Oficial
                      </div>
                      {!readOnly && (<AgentVoiceModule
                        agentId="publicacion"
                        agentLabel="Publicación Oficial — Gaceta"
                        primaryColor="#00C2CB"
                        sesionId={fase1Data?.sesion_id || null}
                        resultData={publicacionData}
                        speechHook={speechHook}
                        compact={false}
                      />)}
                    </div>

                    {/* ── MÓDULO INTERACTIVO CON AGENTE CREWAI: MENSAJE AL PRESIDENTE DEL SENADO ── */}
                    {!readOnly && (<MensajeSenadoCrewPanel
                      idProyecto={fase1Data?.id_proyecto || 104}
                      sesionId={fase1Data?.sesion_id}
                      numeroLey={pub.numero_ley || 'Ley Sancionada y Promulgada'}
                      tituloProyecto={pub.titulo || fase1Data?.titulo || 'Proyecto de Ley'}
                      boletinOficial={pub.boletin_oficial || 'GAC-2026-BOL'}
                      defaultEmail={activeSession?.emailAutor || 'rebalicbecky2@gmail.com'}
                      onSent={() => appendLog('Mensaje_Senado_Crew', 'COMPLETADO', 'Oficio remitido al Presidente del Senado con Token de Google')}
                    />)}

                    {/* ── CORRECCIONES FINALES DE LA GACETA (Secretario / Usuario) ── */}
                    {!readOnly && (<GacetaCorreccionesSection
                      idProyecto={fase1Data?.id_proyecto}
                      sesionId={activeSession?.id}
                      onCorreccionActualizada={() => appendLog('Gaceta_Correcciones', 'ACTUALIZADO', 'Corrección registrada en Gaceta')}
                    />)}

                    {/* ── ENVÍO DE CORREOS VALIDADO — PUBLICACIÓN EN GACETA ── */}
                    {!readOnly && (<GacetaNotificacionEmailSection
                      fase1Data={fase1Data}
                      pub={pub}
                      defaultEmail={activeSession?.emailAutor || 'rebalicbecky2@gmail.com'}
                      onSent={(dest) => appendLog('Publicacion_Correo', 'COMPLETADO', `Correos de Gaceta enviados a: ${dest.join(', ')}`)}
                    />)}

                    {/* Acciones Finales */}
                    <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', flexWrap: 'wrap' }}>
                      {pdfResult?.filename && (
                        <a
                          href={`${BACKEND_BASE_URL}/uploaded_files/informes/${pdfResult.filename}`}
                          target="_blank" rel="noreferrer"
                          className="btn-secondary"
                          style={{ fontSize: '1rem', padding: '13px 24px', textDecoration: 'none' }}
                        >
                          <Download size={20} />
                          <span>Descargar Expediente PDF</span>
                        </a>
                      )}
                      {onNavigateExpedientes && (
                        <button className="btn-success" onClick={onNavigateExpedientes}
                          style={{ fontSize: '1rem', padding: '13px 24px' }}>
                          <ExternalLink size={20} />
                          <span>Ver Expedientes Registrados</span>
                        </button>
                      )}
                      <button className="btn-secondary" onClick={handleReset} style={{ fontSize: '1rem', padding: '13px 24px' }}>
                        <RotateCcw size={20} />
                        <span>Iniciar Nuevo Trámite</span>
                      </button>

                    </div>
                  </div>
                );

              })()}
            </AgentResultCard>
          </div>
        </div>
      )}

      {/* ── BITÁCORA DEL PIPELINE (PIPELINE LOG) ── */}
      {pipelineLog && pipelineLog.length > 0 && (
        <div style={{
          marginTop: '32px',
          background: 'rgba(11, 15, 25, 0.85)',
          borderRadius: '16px',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          padding: '20px 24px',
          boxShadow: '0 8px 30px rgba(0,0,0,0.4)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Terminal size={20} color="#38bdf8" />
              <h4 style={{ color: '#ffffff', fontSize: '1rem', fontWeight: 800, margin: 0 }}>
                Bitácora Transaccional del Pipeline Multi-Agente
              </h4>
            </div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <span className="badge" style={{ background: 'rgba(99,102,241,0.2)', color: '#818cf8', border: '1px solid #6366f1', fontSize: '0.72rem' }}>
                🐘 Neon PostgreSQL Conectado
              </span>
              <span className="badge" style={{ background: 'rgba(16,185,129,0.2)', color: '#34d399', border: '1px solid #10b981', fontSize: '0.72rem' }}>
                🍃 MongoDB Atlas Conectado
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '240px', overflowY: 'auto' }}>
            {pipelineLog.map((log, idx) => {
              const color = log.estado === 'COMPLETADO' ? '#34d399' : log.estado === 'ERROR' ? '#f87171' : log.estado === 'OMITIDA' ? '#94a3b8' : '#fbbf24';
              return (
                <div key={idx} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  background: 'rgba(15,23,42,0.6)',
                  border: '1px solid rgba(148,163,184,0.15)',
                  fontSize: '0.82rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ color: '#64748b', fontFamily: 'monospace' }}>[{log.ts}]</span>
                    <span style={{ color: '#e2e8f0', fontWeight: 700 }}>{log.etapa}</span>
                    <span style={{ color: '#cbd5e1' }}>{log.msg}</span>
                  </div>
                  <span style={{
                    color,
                    fontWeight: 700,
                    fontSize: '0.72rem',
                    textTransform: 'uppercase',
                    padding: '2px 8px',
                    borderRadius: '6px',
                    background: `${color}18`,
                    border: `1px solid ${color}40`
                  }}>
                    {log.estado}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}



      {/* ── BOTÓN FLOTANTE PERMANENTE: VER RESULTADOS DE AGENTES (ACCESIBLE EN TODO MOMENTO) ── */}
      <button
        onClick={() => setShowAllResultsModal(true)}
        className="fab-results-btn"
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 999,
          background: 'linear-gradient(135deg, #0284C7 0%, #00B4D8 100%)',
          color: '#FFFFFF',
          border: '1.5px solid rgba(255, 255, 255, 0.4)',
          borderRadius: '50px',
          padding: '11px 22px',
          display: 'flex',
          alignItems: 'center',
          gap: '9px',
          fontWeight: 800,
          fontSize: '0.86rem',
          fontFamily: 'Outfit, sans-serif',
          cursor: 'pointer',
          boxShadow: '0 8px 25px rgba(0, 180, 216, 0.5), 0 2px 10px rgba(0, 0, 0, 0.5)',
          transition: 'all 0.25s ease'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-3px) scale(1.04)';
          e.currentTarget.style.boxShadow = '0 12px 32px rgba(0, 180, 216, 0.75)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0) scale(1)';
          e.currentTarget.style.boxShadow = '0 8px 25px rgba(0, 180, 216, 0.5), 0 2px 10px rgba(0, 0, 0, 0.5)';
        }}
        title="Ver resultados ejecutados de todos los agentes en cualquier momento, incluso mientras se ejecuta otro"
      >
        <Eye size={18} />
        <span>Ver Resultados de Agentes</span>
        <span style={{
          background: '#8AC926',
          color: '#0B2545',
          borderRadius: '10px',
          padding: '2px 8px',
          fontSize: '0.74rem',
          fontWeight: 900
        }}>
          {AGENTS_DEFINITION.filter(a => getAgentResultData(a.id)).length}
        </span>
      </button>

      {/* ── BOTÓN FLOTANTE: CHAT EMERGENTE (audio ↔ texto, abre y cierra) ── */}
      <button
        onClick={() => setShowChat(v => !v)}
        className="fab-chat-btn"
        style={{
          position: 'fixed',
          bottom: '24px',
          left: '24px',
          zIndex: 1001,
          background: showChat
            ? 'linear-gradient(135deg, #1E293B 0%, #0F172A 100%)'
            : 'linear-gradient(135deg, #0B2545 0%, #134074 100%)',
          color: '#FFFFFF',
          border: showChat
            ? '1.5px solid rgba(239, 68, 68, 0.5)'
            : '1.5px solid rgba(0, 180, 216, 0.6)',
          borderRadius: '50px',
          padding: '11px 22px',
          display: 'flex',
          alignItems: 'center',
          gap: '9px',
          fontWeight: 800,
          fontSize: '0.86rem',
          fontFamily: 'Outfit, sans-serif',
          cursor: 'pointer',
          boxShadow: showChat
            ? '0 8px 25px rgba(239, 68, 68, 0.25), 0 2px 10px rgba(0, 0, 0, 0.5)'
            : '0 8px 25px rgba(0, 180, 216, 0.35), 0 2px 10px rgba(0, 0, 0, 0.5)',
          transition: 'all 0.25s ease'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-3px) scale(1.04)';
          e.currentTarget.style.boxShadow = showChat
            ? '0 12px 32px rgba(239, 68, 68, 0.45)'
            : '0 12px 32px rgba(0, 180, 216, 0.55)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0) scale(1)';
          e.currentTarget.style.boxShadow = showChat
            ? '0 8px 25px rgba(239, 68, 68, 0.25), 0 2px 10px rgba(0, 0, 0, 0.5)'
            : '0 8px 25px rgba(0, 180, 216, 0.35), 0 2px 10px rgba(0, 0, 0, 0.5)';
        }}
        title={showChat ? "Cerrar chat emergente" : "Abrir chat emergente: habla con los agentes por voz o texto"}
      >
        {showChat ? (
          <>
            <X size={18} color="#F87171" />
            <span style={{ color: '#FCA5A5' }}>Cerrar Chat</span>
          </>
        ) : (
          <>
            <MessagesSquare size={18} color="#00B4D8" />
            <span>{inspectedAgentId ? `Chat: ${activeAgentDef?.name || 'Agente'}` : 'Chat del Sistema'}</span>
            <span style={{
              width: '8px', height: '8px', borderRadius: '50%',
              background: '#10B981', boxShadow: '0 0 8px #10B981',
              display: 'inline-block'
            }} />
          </>
        )}
      </button>

      {/* ── VENTANA EMERGENTE DEL CHAT (se abre y cierra) ── */}
      {showChat && (
        <div style={{
          position: 'fixed',
          bottom: '84px',
          left: '24px',
          zIndex: 1000,
          width: 'min(430px, calc(100vw - 48px))',
          boxShadow: '0 16px 50px rgba(0, 0, 0, 0.8), 0 0 30px rgba(0, 180, 216, 0.25)',
          borderRadius: '16px',
          animation: 'chatPopIn 0.22s cubic-bezier(0.16, 1, 0.3, 1)',
        }}>
          {/* Pestañas: Chat del Sistema / Chat del agente inspeccionado + Botón Cerrar */}
          {inspectedAgentId && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              marginBottom: '8px',
              background: 'rgba(15, 23, 42, 0.92)',
              padding: '4px',
              borderRadius: '12px',
              border: '1px solid rgba(148, 163, 184, 0.2)',
              backdropFilter: 'blur(12px)',
            }}>
              <button
                onClick={() => setChatTab('sistema')}
                style={{
                  flex: 1, padding: '7px 10px', borderRadius: '8px', cursor: 'pointer',
                  fontSize: '0.75rem', fontWeight: 700, fontFamily: 'Outfit, sans-serif',
                  background: chatTab === 'sistema' ? 'rgba(0,180,216,0.25)' : 'transparent',
                  border: `1px solid ${chatTab === 'sistema' ? '#00B4D8' : 'transparent'}`,
                  color: chatTab === 'sistema' ? '#00B4D8' : '#94A3B8',
                  transition: 'all 0.2s',
                }}
              >
                💬 Sistema
              </button>
              <button
                onClick={() => setChatTab('agente')}
                style={{
                  flex: 2, padding: '7px 10px', borderRadius: '8px', cursor: 'pointer',
                  fontSize: '0.75rem', fontWeight: 700, fontFamily: 'Outfit, sans-serif',
                  background: chatTab === 'agente' ? `${AGENT_ACCENT_MAP[inspectedAgentId] || '#00B4D8'}30` : 'transparent',
                  border: `1px solid ${chatTab === 'agente' ? (AGENT_ACCENT_MAP[inspectedAgentId] || '#00B4D8') : 'transparent'}`,
                  color: chatTab === 'agente' ? '#FFFFFF' : '#94A3B8',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  transition: 'all 0.2s',
                }}
              >
                🤖 {activeAgentDef?.name || inspectedAgentId}
              </button>
              <button
                onClick={() => setShowChat(false)}
                title="Cerrar chat emergente"
                style={{
                  padding: '6px 8px', borderRadius: '8px', cursor: 'pointer',
                  background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#F87171', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.35)';
                  e.currentTarget.style.color = '#FFFFFF';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)';
                  e.currentTarget.style.color = '#F87171';
                }}
              >
                <X size={14} />
              </button>
            </div>
          )}

          {(!inspectedAgentId || chatTab === 'sistema') ? (
            !readOnly && (<AgentChatPanel
              agentId="orquestador"
              agentLabel="Chat del Sistema — Mesa de Partes"
              sesionId={fase1Data?.sesion_id || null}
              datosContexto={getAgentResultData(inspectedAgentId) || fase1Data}
              speechHook={speechHook}
              compact={false}
              onAccion={handleChatAccion}
              onClose={() => setShowChat(false)}
            />)
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {!readOnly && (<AgentChatPanel
                key={inspectedAgentId}
                agentId={inspectedAgentId}
                agentLabel={activeAgentDef?.name}
                primaryColor={AGENT_ACCENT_MAP[inspectedAgentId] || '#00B4D8'}
                sesionId={fase1Data?.sesion_id || null}
                datosContexto={getAgentResultData(inspectedAgentId)}
                speechHook={speechHook}
                compact={true}
                emailDestino={activeSession?.emailAutor || null}
                onAccion={handleChatAccion}
                onClose={() => setShowChat(false)}
              />)}
              {/* Control de voz contextual del agente (antes barra inline superior) */}
              <div style={{
                background: 'rgba(15,23,42,0.9)',
                border: `1px solid ${(AGENT_ACCENT_MAP[inspectedAgentId] || '#00B4D8')}40`,
                borderRadius: '12px',
                overflow: 'hidden',
              }}>
                <div
                  onClick={() => setShowVozEnChat(v => !v)}
                  style={{
                    padding: '8px 12px', cursor: 'pointer', display: 'flex',
                    alignItems: 'center', gap: '8px', fontSize: '0.72rem',
                    fontWeight: 700, color: '#94A3B8',
                  }}
                >
                  <Mic size={13} color={AGENT_ACCENT_MAP[inspectedAgentId] || '#00B4D8'} />
                  🎤 Control de Voz — {activeAgentDef?.name || inspectedAgentId}
                  <span style={{ marginLeft: 'auto', color: AGENT_ACCENT_MAP[inspectedAgentId] || '#00B4D8' }}>
                    {showVozEnChat ? '▲' : '▼'}
                  </span>
                </div>
                {showVozEnChat && (
                  <div style={{ padding: '0 10px 10px' }}>
                    {!readOnly && (<AgentVoiceModule
                      agentId={inspectedAgentId}
                      agentLabel={activeAgentDef?.name}
                      primaryColor={AGENT_ACCENT_MAP[inspectedAgentId] || '#00B4D8'}
                      sesionId={fase1Data?.sesion_id || null}
                      resultData={getAgentResultData(inspectedAgentId)}
                      speechHook={speechHook}
                      compact={true}
                      onDictadoText={inspectedAgentId === 'distribuidor' ? handleDictadoVoz : null}
                      emailDestino={activeSession?.emailAutor || null}
                      onVoiceAction={(action) => {
                        if (action?.type === 'notificacion_enviada') {
                          appendLog(inspectedAgentId, 'VOZ', `Notificación enviada: "${(action.texto || '').substring(0, 60)}"`);
                        }
                      }}
                    />)}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
      {/* ── DRAWER LATERAL DERECHO: Actualizar información del proyecto de ley ── */}
      {fase1Data?.id_proyecto && (
        <button
          onClick={() => setShowCorreccionesDrawer(v => !v)}
          style={{
            position: 'fixed',
            bottom: '88px',
            right: '24px',
            zIndex: 999,
            background: 'linear-gradient(135deg, #134074 0%, #0B2545 100%)',
            color: '#FFFFFF',
            border: '1.5px solid rgba(138, 201, 38, 0.55)',
            borderRadius: '50px',
            padding: '10px 20px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontWeight: 800,
            fontSize: '0.82rem',
            fontFamily: 'Outfit, sans-serif',
            cursor: 'pointer',
            boxShadow: '0 8px 25px rgba(138, 201, 38, 0.3), 0 2px 10px rgba(0, 0, 0, 0.5)',
          }}
          title="Actualizar la información del proyecto de ley (correcciones y observaciones)"
        >
          <FileCheck size={17} />
          <span>Actualizar Proyecto de Ley</span>
        </button>
      )}

      {/* ── BOTÓN FLOTANTE: DESPACHO DE CORREO ── */}
      <button
        onClick={() => setShowEmailDrawer(v => !v)}
        style={{
          position: 'fixed',
          bottom: '152px',
          right: '24px',
          zIndex: 999,
          background: 'linear-gradient(135deg, #1e3a5f 0%, #0D1B2A 100%)',
          color: '#FFFFFF',
          border: '1.5px solid rgba(56,189,248,0.55)',
          borderRadius: '50px',
          padding: '10px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontWeight: 800,
          fontSize: '0.82rem',
          fontFamily: 'Outfit, sans-serif',
          cursor: 'pointer',
          boxShadow: '0 8px 25px rgba(56,189,248,0.3), 0 2px 10px rgba(0,0,0,0.5)',
          transition: 'all 0.25s ease',
        }}
        onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-3px)'; e.currentTarget.style.boxShadow = '0 12px 32px rgba(56,189,248,0.55)'; }}
        onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 8px 25px rgba(56,189,248,0.3), 0 2px 10px rgba(0,0,0,0.5)'; }}
        title="Despacho Institucional: editar y enviar correo con observaciones adicionales"
      >
        <Mail size={17} />
        <span>Despacho / Correo</span>
      </button>

      {/* ── EMAIL DESPACHO DRAWER ── */}
      {!readOnly && (<EmailDespachoDrawer
        isOpen={showEmailDrawer}
        onClose={() => setShowEmailDrawer(false)}
        defaultEmail={customEmail || activeSession?.emailAutor || ''}
        defaultSubject={customEmailSubject || ''}
        defaultMensaje={extraEmailMessage || ''}
        sesionId={fase1Data?.sesion_id || null}
        idProyecto={fase1Data?.id_proyecto || null}
        onChange={(patch) => {
          if (patch.email !== undefined) updateActiveSession({ customEmail: patch.email });
          if (patch.subject !== undefined) updateActiveSession({ customEmailSubject: patch.subject });
          if (patch.mensaje !== undefined) updateActiveSession({ extraEmailMessage: patch.mensaje });
        }}
        onSent={(info) => {
          appendLog('Despacho_Correo', 'COMPLETADO', `Correo enviado a: ${info.email}`);
        }}
      />)}

      {showCorreccionesDrawer && fase1Data?.id_proyecto && (
        <div style={{
          position: 'fixed',
          top: '90px',
          right: '24px',
          bottom: '150px',
          width: 'min(400px, calc(100vw - 48px))',
          zIndex: 1000,
          background: 'rgba(11, 37, 69, 0.97)',
          border: '1.5px solid rgba(138, 201, 38, 0.4)',
          borderRadius: '16px',
          boxShadow: '0 12px 40px rgba(0, 0, 0, 0.65)',
          backdropFilter: 'blur(14px)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '12px 16px', borderBottom: '1px solid rgba(138,201,38,0.25)',
          }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 800, color: '#8AC926', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileCheck size={16} /> Actualizar Proyecto de Ley
            </div>
            <button
              onClick={() => setShowCorreccionesDrawer(false)}
              style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', padding: 4 }}
              title="Cerrar panel"
            >
              <X size={16} />
            </button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
            {!readOnly && (<CorrecionesPanel
              idProyecto={fase1Data.id_proyecto}
              sesionId={activeSession?.id}
            />)}
          </div>
        </div>
      )}

      {/* ── MODAL DE TEXTO CONSOLIDADO Y CORREGIDO (GACETA OFICIAL) ── */}
      {showTextoConsolidadoModal && textoConsolidadoInfo && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(8px)',
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div style={{
            background: '#0d1b2a',
            border: '1.5px solid rgba(0, 194, 203, 0.4)',
            borderRadius: '20px',
            width: '100%',
            maxWidth: '850px',
            maxHeight: '90vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            boxShadow: '0 20px 50px rgba(0,0,0,0.6)'
          }}>
            {/* Header del Modal */}
            <div style={{
              padding: '18px 24px',
              borderBottom: '1px solid rgba(148, 163, 184, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(15, 23, 42, 0.9)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileText size={22} color="#00C2CB" />
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 800, color: '#ffffff' }}>
                    Texto Final Corregido — Gaceta Oficial de Bolivia
                  </h3>
                  <p style={{ margin: 0, fontSize: '0.78rem', color: '#94a3b8' }}>
                    Proyecto #{textoConsolidadoInfo.id_proyecto} · {textoConsolidadoInfo.total_aplicadas} enmiendas y observaciones incorporadas
                  </p>
                </div>
              </div>
              <button
                onClick={() => updateActiveSession({ showTextoConsolidadoModal: false })}
                style={{
                  background: 'rgba(255,255,255,0.1)',
                  border: 'none',
                  borderRadius: '50%',
                  width: '32px',
                  height: '32px',
                  color: '#cbd5e1',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Contenido del texto de la Ley */}
            <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
              <div style={{
                background: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid rgba(56, 189, 248, 0.2)',
                borderRadius: '12px',
                padding: '20px',
                fontFamily: 'serif',
                fontSize: '0.95rem',
                lineHeight: 1.7,
                color: '#e2e8f0',
                whiteSpace: 'pre-wrap'
              }}>
                {textoConsolidadoInfo.texto_consolidado}
              </div>
            </div>

            {/* Footer del Modal */}
            <div style={{
              padding: '16px 24px',
              borderTop: '1px solid rgba(148, 163, 184, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(15, 23, 42, 0.9)'
            }}>
              <span style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: 700 }}>
                ✓ Texto armonizado con la CPE y catálogo legislativo
              </span>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={() => updateActiveSession({ showTextoConsolidadoModal: false })}
                  style={{
                    background: 'rgba(30, 41, 59, 0.8)',
                    border: '1px solid rgba(148, 163, 184, 0.25)',
                    borderRadius: '8px',
                    color: '#cbd5e1',
                    padding: '8px 18px',
                    fontSize: '0.84rem',
                    cursor: 'pointer'
                  }}
                >
                  Cerrar
                </button>
                <button
                  onClick={async () => {
                    try {
                      const res = await api.generarPdfGaceta(textoConsolidadoInfo.id_proyecto);
                      if (res.data) {
                        updateActiveSession({ gacetaPdfData: res.data });
                        window.open(res.data.url_descarga, '_blank');
                      }
                    } catch (e) {
                      alert('Error generando PDF de Gaceta: ' + e.message);
                    }
                  }}
                  style={{
                    background: 'linear-gradient(135deg, #0d9488 0%, #0f766e 100%)',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#ffffff',
                    padding: '8px 20px',
                    fontSize: '0.84rem',
                    fontWeight: 800,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <Download size={14} />
                  <span>Descargar PDF Gaceta</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
        </main>
        <aside className="mesa-case-sidebar" aria-label="Resumen del expediente seleccionado">
          <section className="mesa-project-summary">
            <div className="command-panel-heading"><span>Expediente seleccionado</span><span className="command-stage">{activeSession.estadoCompartido || (activeSession._sharedProcessing ? 'En ejecución' : `Etapa ${pipelineStep}`)}</span></div>
            {activeSession.documentText || fase1Data || comisionData ? <>
              <h2>{fase1Data?.titulo_proyecto || fase1Data?.titulo || activeSession.documentName || activeSession.title || 'Expediente seleccionado'}</h2>
              <div className="summary-label">{fase1Data?.resumen_ejecutivo || concentradorData?.expediente_consolidado?.resumen_ejecutivo ? 'Resumen ejecutivo' : 'Vista previa del documento'}</div>
              <p>{fase1Data?.resumen_ejecutivo || concentradorData?.expediente_consolidado?.resumen_ejecutivo || comisionData?.resumen || activeSession.documentText?.slice(0, 360) || 'El resumen estará disponible cuando el expediente tenga contenido.'}</p>
              <dl><div><dt>Destino</dt><dd>{activeSession.camaraDestino || fase1Data?.camara_destino || activeSession.tipoIniciativa || 'Pendiente de asignación'}</dd></div><div><dt>Estado</dt><dd>{activeSession.estadoCompartido || (activeSession._sharedProcessing ? 'En ejecución' : pipelineStep ? 'En seguimiento' : 'Recibido')}</dd></div><div><dt>Documento</dt><dd>{activeSession.uploadStats?.drive_status === 'GUARDADO' || activeSession.documentPdf?.drive_file_id ? 'Registrado en Google Drive' : activeSession.documentText ? 'Texto registrado' : 'Pendiente'}</dd></div></dl>
              {activeSession.uploadStats?.drive_link && <a href={activeSession.uploadStats.drive_link} target="_blank" rel="noreferrer" className="drive-record-link">Ver documento registrado en Drive <ExternalLink size={14}/></a>}
              {(activeSession.uploadStats?.saved_as || activeSession.documentPdf?.saved_as) && <button type="button" onClick={descargarDocumentoOriginal} disabled={downloadingOriginal} className="download-original-button"><Download size={14}/>{downloadingOriginal ? 'Preparando descarga…' : 'Descargar original'}</button>}
              {originalDownloadError && <p role="alert" className="original-download-error">{originalDownloadError}</p>}
            </> : <div className="empty-project-summary"><FileText size={22}/><p>Selecciona un expediente con documento registrado para ver aquí su nombre, resumen y estado.</p></div>}
            {(activeSession.uploadStats?.drive_file_id || activeSession.documentPdf?.drive_file_id) && <div className="drive-confirmation"><CheckCircle2 size={14}/> Copia confirmada en Google Drive</div>}
          </section>
        </aside>
      </div>
    </div>
  );
}
