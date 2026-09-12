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
  Shield
} from 'lucide-react';
import { api } from '../services/api';
import HorizontalAgentFlow, { AGENTS_DEFINITION } from '../components/HorizontalAgentFlow';
import LateralAgentHero from '../components/LateralAgentHero';
import AgentResultCard from '../components/AgentResultCard';
import AgentDetailPanel from '../components/AgentDetailPanel';

// Mapeo de logos institucionales y colores de acento por agente
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

const AGENT_ACCENT_MAP = {
  distribuidor:       '#00B4D8', // Celeste Neón Eléctrico
  comision:           '#38BDF8', // Azul Cielo Radiante
  constitucional:     '#2563EB', // Azul Zafiro Real
  consistencia:       '#1D4ED8', // Azul Cobalto Profundo
  emisor:             '#0284C7', // Azul Océano Cerúleo
  notificador:        '#06B6D4', // Turquesa Azulado
  constitucion_fondo: '#4338CA', // Azul Índigo Parlamentario
  concentrador_crew:  '#3B82F6', // Azul Acero Técnico
  secretario:         '#1E40AF', // Azul Marino Clásico
  bicameral:          '#7DD3FC', // Azul Hielo Glaciar
  veto_promulgacion:  '#1E3A8A', // Azul Medianoche Ultramar
  publicacion:        '#00C2CB', // Azul Lapislázuli Brillante
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
    inspectedAgentId: null,
    createdAt: new Date().toISOString(),
    // CrewAI YAML extended pipeline
    constitucionFondoData: null,
    concentradorData: null,
    secretarioData: null,
    bicameralData: null,
    vetoPromulgacionData: null,
    publicacionData: null,
    pipelineLog: []  // [{etapa, estado, msg, ts}]
  };
}

export default function MesaPartes({ onNavigateExpedientes }) {
  // ── Multi-Session State Initialization ──
  const [sessions, setSessions] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_SESSIONS_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch (err) {
      console.warn('Error reading sessions from localStorage:', err);
    }
    return [createDefaultSession(1)];
  });

  const [activeSessionId, setActiveSessionId] = useState(() => {
    try {
      const savedId = localStorage.getItem(STORAGE_ACTIVE_KEY);
      if (savedId) return savedId;
    } catch (err) {
      console.warn('Error reading active session ID:', err);
    }
    return sessions[0]?.id || '';
  });

  const fileInputRef = useRef(null);

  // Active Session helper
  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0] || createDefaultSession(1);

  // Save to localStorage on change
  useEffect(() => {
    try {
      // Don't store large files in localStorage; just metadata and text
      localStorage.setItem(STORAGE_SESSIONS_KEY, JSON.stringify(sessions));
      localStorage.setItem(STORAGE_ACTIVE_KEY, activeSessionId);
    } catch (err) {
      console.warn('Error saving sessions to localStorage:', err);
    }
  }, [sessions, activeSessionId]);

  // Update current session helper
  const updateActiveSession = (patch) => {
    setSessions(prev => prev.map(s => {
      if (s.id === activeSession.id) {
        return { ...s, ...patch };
      }
      return s;
    }));
  };

  // Add new session tab
  const handleAddSession = () => {
    const newSession = createDefaultSession(sessions.length + 1);
    setSessions(prev => [...prev, newSession]);
    setActiveSessionId(newSession.id);
  };

  // Remove session tab
  const handleRemoveSession = (e, sessionId) => {
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
    inspectedAgentId,
    // CrewAI extended pipeline
    constitucionFondoData,
    concentradorData,
    secretarioData,
    bicameralData,
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
        uploadStats: {
          paginas: res.paginas,
          palabras: res.palabras,
          caracteres: res.caracteres,
          motor: res.motor,
          saved_as: res.saved_as,
          local_path: res.local_path,
        },
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
    sesion_id: fase1Data.sesion_id,
    task_id_inicial: fase1Data.task_id_inicial,
    task_id_distribuidor: fase1Data.task_id_distribuidor,
    categoria: selectedCategory,
    agente_destino_nombre: selectedCategory === 'AGENTE_REGISTRO_LEGISLATIVO'
      ? 'Agente_Comision_Legislativa'
      : selectedCategory === 'AGENTE_ATENCION_CIUDADANA'
      ? 'Agente_Atencion_Ciudadana'
      : 'Agente_Gestion_Correspondencia',
    texto_documento: documentText,
    nombre_archivo: fase1Data.nombre_archivo,
    tipo_entrada: fase1Data.tipo_entrada,
    id_proyecto: fase1Data.id_proyecto,
    solicitud_id: fase1Data.solicitud_id,
    t_inicio_fase1: fase1Data.t_inicio_fase1,
    local_filepath: uploadStats?.local_path || null,
  });

  const handleEjecutarComision = async () => {
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
    updateActiveSession({
      isProcessing: true,
      errorMessage: '',
      inspectedAgentId: null
    });
    try {
      const res = await api.runAgentConstitucional(buildPayload());
      updateActiveSession({
        dictamenData: res.data,
        pipelineStep: 5,
        isProcessing: false
      });
    } catch (err) {
      updateActiveSession({
        errorMessage: err.message || 'Error en Verificación Constitucional',
        isProcessing: false
      });
    }
  };

  const handleEjecutarConsistencia = async () => {
    updateActiveSession({
      isProcessing: true,
      errorMessage: '',
      inspectedAgentId: null
    });
    try {
      const res = await api.runAgentConsistencia(buildPayload());
      updateActiveSession({
        consistenciaData: res.data,
        pipelineStep: 6,
        isProcessing: false
      });
    } catch (err) {
      updateActiveSession({
        errorMessage: err.message || 'Error en Consistencia Normativa',
        isProcessing: false
      });
    }
  };

  const handleEmitPDF = async () => {
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
    titulo: documentName || fase1Data?.nombre_archivo || 'Proyecto de Ley',
    sesion_id: fase1Data?.sesion_id
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
    if (!fase1Data) return;
    updateActiveSession({ isProcessing: true, errorMessage: '', pipelineStep: 10, inspectedAgentId: null });
    appendLog('Concentrador', 'EN_PROCESO', 'Consolidando todas las observaciones en expediente unificado...');
    try {
      const res = await api.runAgentConcentrador({
        proyecto_info: buildProyectoInfo(),
        observaciones: buildObservaciones(),
        id_proyecto: fase1Data?.id_proyecto
      });
      updateActiveSession({ concentradorData: res.data, pipelineStep: 11, isProcessing: false });
      const exp = res.data?.expediente_consolidado || {};
      appendLog('Concentrador', 'COMPLETADO', `Riesgo: ${exp.nivel_riesgo_general || 'N/A'} | Obs: ${(exp.observaciones_integradas || []).length}`);
    } catch (err) {
      updateActiveSession({ errorMessage: err.message || 'Error en Concentrador', pipelineStep: 10, isProcessing: false });
      appendLog('Concentrador', 'ERROR', err.message);
    }
  };

  const handleSecretario = async () => {
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
    if (!fase1Data) return;
    updateActiveSession({ isProcessing: true, errorMessage: '', pipelineStep: 12, inspectedAgentId: null });
    appendLog('Bicameral', 'EN_PROCESO', 'Comparando versiones entre camaras legislativas...');
    try {
      const res = await api.runAgentBicameral({
        proyecto_info: buildProyectoInfo(),
        version_original: { articulos: ['Version original de la Camara de Origen'] },
        version_retornada: { articulos: ['Version revisada por la Camara Revisora'] },
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

  const handleVetoPromulgacion = async () => {
    if (!fase1Data) return;
    updateActiveSession({ isProcessing: true, errorMessage: '', pipelineStep: 13, inspectedAgentId: null });
    appendLog('Veto_Promulgacion', 'EN_PROCESO', 'Evaluacion estrategica multicriterio en curso...');
    try {
      const res = await api.runAgentVetoPromulgacion({
        proyecto_info: buildProyectoInfo(),
        expediente: concentradorData?.expediente_consolidado || {},
        id_proyecto: fase1Data?.id_proyecto
      });
      updateActiveSession({ vetoPromulgacionData: res.data, pipelineStep: 14, isProcessing: false });
      const ev = res.data?.evaluacion_veto || {};
      appendLog('Veto_Promulgacion', 'COMPLETADO', `Decision: ${ev.decision || 'N/A'} | Score: ${ev.score_final || 'N/A'}`);
    } catch (err) {
      updateActiveSession({ errorMessage: err.message || 'Error en Veto/Promulgacion', pipelineStep: 13, isProcessing: false });
      appendLog('Veto_Promulgacion', 'ERROR', err.message);
    }
  };

  const handlePublicacion = async () => {
    if (!fase1Data) return;
    const decision = vetoPromulgacionData?.evaluacion_veto?.decision;
    if (decision && decision !== 'PROMULGAR') {
      appendLog('Publicacion', 'OMITIDA', `No procede publicacion. Decision: ${decision}`);
      updateActiveSession({ pipelineStep: 15 });
      return;
    }
    updateActiveSession({ isProcessing: true, errorMessage: '', pipelineStep: 14, inspectedAgentId: null });
    appendLog('Publicacion', 'EN_PROCESO', 'Asignando numero de ley y registrando en Boletin Oficial...');
    try {
      const res = await api.runAgentPublicacion({
        proyecto_info: buildProyectoInfo(),
        evaluacion_veto: vetoPromulgacionData || { evaluacion_veto: { decision: 'PROMULGAR' } },
        id_proyecto: fase1Data?.id_proyecto
      });
      updateActiveSession({ publicacionData: res.data, pipelineStep: 15, isProcessing: false });
      const pub = res.data?.publicacion_oficial || {};
      appendLog('Publicacion', 'COMPLETADO', `${pub.numero_ley || 'N/A'} | Boletin: ${pub.boletin_oficial || 'N/A'}`);
    } catch (err) {
      updateActiveSession({ errorMessage: err.message || 'Error en Publicacion Oficial', pipelineStep: 14, isProcessing: false });
      appendLog('Publicacion', 'ERROR', err.message);
    }
  };

  const handleReset = () => {
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
      vetoPromulgacionData: null,
      publicacionData: null,
      pipelineLog: []
    });
  };

  // ── Estado del panel lateral deslizante ──
  const [detailPanelAgent, setDetailPanelAgent] = useState(null);

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
    setDetailPanelAgent(agent);
    if (inspectedAgentId === agent.id) {
      updateActiveSession({ inspectedAgentId: null });
    } else {
      updateActiveSession({ inspectedAgentId: agent.id });
    }
  };

  const handleCloseDetailPanel = () => {
    setDetailPanelAgent(null);
  };

  // ── EJECUCIÓN PARALELA: Constitucional + Consistencia simultáneamente ──
  const handleEjecutarAuditoriaParalela = async () => {
    if (!fase1Data) return;
    updateActiveSession({ isProcessing: true, errorMessage: '', pipelineStep: 4, inspectedAgentId: null });
    appendLog('Auditoria_Paralela', 'EN_PROCESO', 'Iniciando Verificador Constitucional y Consistencia Normativa en paralelo...');
    try {
      const payload = buildPayload();
      const [resConstitucional, resConsistencia] = await Promise.all([
        api.runAgentConstitucional(payload),
        api.runAgentConsistencia(payload)
      ]);
      updateActiveSession({
        dictamenData: resConstitucional.data,
        consistenciaData: resConsistencia.data,
        pipelineStep: 6,
        isProcessing: false
      });
      appendLog('Constitucional', 'COMPLETADO', `Resultado constitucional: ${resConstitucional.data?.valido ? 'VÁLIDO' : 'CON OBSERVACIONES'}`);
      appendLog('Consistencia', 'COMPLETADO', `Hallazgos: ${(resConsistencia.data?.hallazgos || []).length} detectados`);
    } catch (err) {
      updateActiveSession({
        errorMessage: err.message || 'Error en auditoría paralela',
        pipelineStep: 4,
        isProcessing: false
      });
      appendLog('Auditoria_Paralela', 'ERROR', err.message);
    }
  };

  // Active agent object determination (extended to 12 agents)
  const getActiveAgentDef = () => {
    if (inspectedAgentId) return AGENTS_DEFINITION.find(a => a.id === inspectedAgentId) || AGENTS_DEFINITION[0];
    if (pipelineStep <= 2) return AGENTS_DEFINITION[0];
    if (pipelineStep <= 4) return AGENTS_DEFINITION[1];
    if (pipelineStep === 5) return AGENTS_DEFINITION[2];
    if (pipelineStep === 6) return AGENTS_DEFINITION[3];
    if (pipelineStep === 7) return AGENTS_DEFINITION[4];
    if (pipelineStep === 8) return AGENTS_DEFINITION[5];
    if (pipelineStep <= 10) return AGENTS_DEFINITION.find(a => a.id === 'constitucion_fondo') || AGENTS_DEFINITION[6];
    if (pipelineStep === 11) return AGENTS_DEFINITION.find(a => a.id === 'concentrador_crew') || AGENTS_DEFINITION[7];
    if (pipelineStep === 12) return AGENTS_DEFINITION.find(a => a.id === 'secretario') || AGENTS_DEFINITION[8];
    if (pipelineStep === 13) return AGENTS_DEFINITION.find(a => a.id === 'bicameral') || AGENTS_DEFINITION[9];
    if (pipelineStep === 14) return AGENTS_DEFINITION.find(a => a.id === 'veto_promulgacion') || AGENTS_DEFINITION[10];
    return AGENTS_DEFINITION.find(a => a.id === 'publicacion') || AGENTS_DEFINITION[11];
  };
  const activeAgentDef = getActiveAgentDef();
  const activeLogoUrl = AGENT_LOGO_MAP[activeAgentDef?.id] || '/robots/logos/distribuidor.jpg';
  const activeAccent = AGENT_ACCENT_MAP[activeAgentDef?.id] || '#00B4D8';

  // ── Renderiza el contenedor superior dedicado (RECUADRO ROJO): Logo más grande (104px) + Nombre del agente destacado ──
  const renderAgentHeaderContainer = () => {
    const isAgentDone = pipelineStep >= (activeAgentDef?.doneAtStep || 99);

    return (
      <div style={{
        background: 'linear-gradient(135deg, rgba(11, 37, 69, 0.94) 0%, rgba(19, 64, 116, 0.75) 50%, rgba(15, 23, 42, 0.94) 100%)',
        border: `1.5px solid ${isAgentDone ? '#8AC92688' : `${activeAccent}66`}`,
        borderRadius: '20px',
        padding: '20px 28px',
        boxShadow: isAgentDone
          ? `0 10px 32px rgba(0,0,0,0.45), 0 0 28px rgba(138,201,38,0.3)`
          : `0 10px 32px rgba(0,0,0,0.45), 0 0 28px ${activeAccent}33`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '24px',
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
        <div style={{ flex: 1, minWidth: '240px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: `${activeAccent}22`,
              border: `1px solid ${activeAccent}66`,
              borderRadius: '6px',
              padding: '4px 12px',
              fontSize: '0.72rem',
              fontWeight: 800,
              color: activeAccent,
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
            fontSize: '2.1rem',
            fontWeight: 900,
            color: '#FFFFFF',
            fontFamily: 'Outfit, sans-serif',
            lineHeight: 1.15,
            margin: '0 0 6px 0',
            letterSpacing: '0.01em',
            textShadow: `0 2px 18px ${activeAccent}55`
          }}>
            {activeAgentDef?.name}
          </h2>

          <div style={{
            fontSize: '0.9rem',
            color: '#CBD5E1',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <span style={{ color: activeAccent, fontWeight: 800 }}>•</span>
            <span>{activeAgentDef?.role}</span>
          </div>
        </div>

        {/* Lado derecho: Logo circular MÁS GRANDE (104px) con aro institucional */}
        <div style={{ position: 'relative', flexShrink: 0 }}>
          {/* Anillo de resplandor orbital */}
          <div style={{
            position: 'absolute',
            inset: '-7px',
            borderRadius: '50%',
            border: `2px dashed ${isAgentDone ? '#8AC92677' : `${activeAccent}77`}`,
            animation: isProcessing ? 'spin 4s linear infinite' : 'none',
            pointerEvents: 'none'
          }} />

          <div style={{
            width: '104px',
            height: '104px',
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

  // Inspection step map (extended)
  const inspectStepMap = {
    distribuidor: 2, comision: 4, constitucional: 5, consistencia: 6, emisor: 7, notificador: 8,
    constitucion_fondo: 10, concentrador_crew: 11, secretario: 12, bicameral: 13, veto_promulgacion: 14, publicacion: 15
  };
  const effectiveViewStep = inspectedAgentId ? (inspectStepMap[inspectedAgentId] || pipelineStep) : pipelineStep;

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '24px 24px 48px 24px' }}>

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
      <div style={{
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
        <div style={{ position: 'absolute', top: '-40px', right: '-40px', width: '200px', height: '200px',
          borderRadius: '50%', background: 'rgba(0,180,216,0.08)', filter: 'blur(60px)', pointerEvents: 'none' }} />
        
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
        </div>
        <h1 style={{ fontSize: '1.9rem', fontWeight: 800, color: '#FFFFFF', marginBottom: '6px',
          letterSpacing: '-0.02em', fontFamily: 'Outfit, sans-serif',
          textShadow: '0 2px 12px rgba(0,180,216,0.3)' }}>
          Auditoría Automática de Documentos Legislativos
        </h1>
        <p style={{ color: '#94A3B8', fontSize: '0.92rem', maxWidth: '800px', lineHeight: 1.55, margin: 0 }}>
          Procese múltiples expedientes en simultáneo con flujo paralelo. Los agentes de Verificación Constitucional y Consistencia Normativa ejecutan de forma simultánea. Haga clic en cualquier agente para ver su detalle.
        </p>
      </div>

      {/* ── MULTI-QUERY SESSIONS TABS ── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        marginBottom: '20px',
        overflowX: 'auto',
        paddingBottom: '4px',
        borderBottom: '1px solid rgba(0,180,216,0.2)'
      }}>
        {sessions.map((ses, idx) => {
          const isCurrent = ses.id === activeSession.id;
          const isDone = ses.pipelineStep >= 7;
          const isWorking = ses.pipelineStep > 0 && ses.pipelineStep < 7;

          return (
            <div
              key={ses.id}
              onClick={() => setActiveSessionId(ses.id)}
              className={`session-tab ${isCurrent ? 'active' : 'inactive'}`}
            >
              {/* Status indicator dot */}
              <span style={{
                width: '7px', height: '7px', borderRadius: '50%', flexShrink: 0,
                background: isDone ? '#8AC926' : isWorking ? '#F4A261' : 'rgba(100,116,139,0.5)',
                boxShadow: isWorking ? '0 0 6px #F4A261' : isDone ? '0 0 6px #8AC926' : 'none'
              }} />

              <span style={{ fontSize: '0.84rem', whiteSpace: 'nowrap' }}>
                {ses.title || `Consulta #${idx + 1}`}
              </span>

              {/* Step indicator pill */}
              <span style={{
                fontSize: '0.66rem',
                padding: '2px 6px',
                borderRadius: '5px',
                background: isCurrent ? 'rgba(0,180,216,0.15)' : 'rgba(100,116,139,0.1)',
                color: isCurrent ? '#00B4D8' : '#64748B',
                fontWeight: 700
              }}>
                {ses.pipelineStep === 0 ? 'Inicio' : `Paso ${ses.pipelineStep}`}
              </span>

              {/* Close tab button */}
              <button
                onClick={(e) => handleRemoveSession(e, ses.id)}
                title="Cerrar esta consulta"
                style={{
                  border: 'none',
                  background: 'transparent',
                  padding: '2px',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  cursor: 'pointer',
                  color: '#94a3b8',
                  transition: 'color 0.2s'
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = '#ef4444'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = '#94a3b8'; }}
              >
                <X size={14} />
              </button>
            </div>
          );
        })}

        {/* Add New Session Button */}
        <button
          onClick={handleAddSession}
          className="btn-secondary"
          style={{
            padding: '6px 14px',
            fontSize: '0.82rem',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            borderRadius: '10px',
            height: '34px',
            whiteSpace: 'nowrap',
            background: 'rgba(19, 64, 116, 0.4)',
            border: '1px dashed rgba(0, 180, 216, 0.6)',
            color: '#00B4D8',
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(0, 180, 216, 0.15)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(19, 64, 116, 0.4)'; }}
        >
          <Plus size={15} />
          <span>Nueva Consulta</span>
        </button>
      </div>

      {/* ── TOP HORIZONTAL AGENT FLOW (Screenshot 1: 6 Robots in One Single Line) ── */}
      <HorizontalAgentFlow
        pipelineStep={pipelineStep}
        inspectedAgentId={inspectedAgentId}
        onSelectAgent={handleSelectAgent}
      />

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
              onClick={() => setDetailPanelAgent(activeAgentDef)}
              style={{ padding: '6px 12px', fontSize: '0.78rem', borderRadius: '8px',
                background: 'rgba(0,180,216,0.15)', border: '1px solid rgba(0,180,216,0.35)',
                color: '#00B4D8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px',
                fontFamily: 'Outfit, sans-serif', fontWeight: 600 }}
            >
              <Eye size={13} /> Ver Detalle
            </button>
            <button
              onClick={() => updateActiveSession({ inspectedAgentId: null })}
              style={{ padding: '6px 12px', fontSize: '0.78rem', borderRadius: '8px',
                background: 'rgba(2,132,199,0.2)', border: '1px solid rgba(2,132,199,0.4)',
                color: '#38BDF8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px',
                fontFamily: 'Outfit, sans-serif', fontWeight: 600 }}
            >
              <EyeOff size={13} /> Volver
            </button>
          </div>
        </div>
      )}

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
      {effectiveViewStep === 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(320px, 360px) 1fr',
          gap: '24px',
          alignItems: 'start'
        }}>
          {/* Columna Izquierda: Banner Nítido sin recuadros */}
          <div style={{ position: 'sticky', top: '20px' }}>
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
                  </div>
                )}
              </div>
            ) : (
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '8px', color: '#94A3B8', fontSize: '0.92rem', fontWeight: 600 }}>
                  Contenido del Documento o Proyecto:
                </label>
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

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                onClick={handleIniciarFase1}
                disabled={isProcessing || !documentText.trim()}
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
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(320px, 360px) 1fr',
          gap: '24px',
          alignItems: 'start'
        }}>
          <div style={{ position: 'sticky', top: '20px' }}>
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
        <AgentResultCard
          agentName="Agente Distribuidor"
          role="Clasificación Institucional del Documento"
          theme="cyan"
          status="completed"
          phaseLabel="Fase 1: Clasificación"
          badgeText="Control Humano Requerido"
          model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
          thinkingText="Clasificación inicial completada con éxito"
          image="/robots/robot_distribuidor_hi.jpg"
          justificacion="Principio de orden y debido proceso parlamentario: cada expediente debe canalizarse por su vía procedimental correcta (Registro Legislativo, Atención Ciudadana o Correspondencia Oficial)."
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <div style={{
              background: 'rgba(251, 191, 36, 0.2)',
              border: '1px solid #fbbf24',
              borderRadius: '50%',
              width: '40px',
              height: '40px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <AlertTriangle size={22} color="#fbbf24" />
            </div>
            <div>
              <h4 style={{ fontSize: '1.25rem', color: '#fbbf24', fontWeight: 800, margin: 0 }}>
                🛑 PUNTO DE CONTROL HUMANO (Alto del Pipeline)
              </h4>
              <p style={{ color: '#fef3c7', fontSize: '0.85rem', margin: 0 }}>
                El Agente Distribuidor ha emitido su recomendación. Puede confirmar la categoría sugerida o reasignarla manualmente antes de activar la Fase 2.
              </p>
            </div>
          </div>

          <div style={{
            background: 'rgba(6, 40, 32, 0.8)',
            padding: '24px',
            borderRadius: '14px',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            marginBottom: '24px',
          }}>
            <div style={{ fontSize: '0.85rem', color: '#a7f3d0', marginBottom: '8px' }}>Categoría Sugerida por el Bot:</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <span className="badge badge-green" style={{ fontSize: '1rem', padding: '6px 14px' }}>
                {fase1Data.categoria}
              </span>
              <span style={{ fontSize: '0.85rem', color: '#6ee7b7' }}>
                → Agente Destino: <strong>{fase1Data.agente_destino_nombre}</strong>
              </span>
            </div>

            <div style={{ fontSize: '0.85rem', color: '#a7f3d0', marginBottom: '8px' }}>
              Ajustar Categoría si es necesario:
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
              {[
                { id: 'AGENTE_REGISTRO_LEGISLATIVO', label: 'Registro Legislativo (Proyecto de Ley)', icon: Scale },
                { id: 'AGENTE_ATENCION_CIUDADANA', label: 'Atención Ciudadana (Petición/Reclamo)', icon: Users },
                { id: 'AGENTE_GESTION_CORRESPONDENCIA', label: 'Gestión de Correspondencia (Oficio)', icon: Mail },
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
                      gap: '10px',
                      padding: '12px 20px',
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
                    <Icon size={18} color={isSel ? '#00B4D8' : '#94A3B8'} />
                    <span>{cat.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
            <button className="btn-secondary" onClick={handleReset}>
              <RotateCcw size={16} />
              <span>Cancelar y Reiniciar</span>
            </button>

            <button
              onClick={handleEjecutarComision}
              disabled={isProcessing}
              className="btn-primary"
              style={{ fontSize: '1rem', padding: '14px 28px' }}
            >
              <Check size={20} />
              <span>Confirmar y Ejecutar Comisión</span>
              <ArrowRight size={18} />
            </button>
          </div>
        </AgentResultCard>
      )}

      {/* ── STEP 3: FASE COMISIÓN EN EJECUCIÓN ── */}
      {effectiveViewStep === 3 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(320px, 360px) 1fr',
          gap: '24px',
          alignItems: 'start'
        }}>
          <div style={{ position: 'sticky', top: '20px' }}>
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
        <AgentResultCard
          agentName="Agente Comisión Legislativa"
          role="Asignación Temática & Miembros Parlamentarios"
          theme="blue"
          status="completed"
          phaseLabel="Fase 2: Asignación"
          model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
          thinkingText="Dictamen de comisión parlamentaria emitido"
          image="/robots/robot_ciudadano_hi.jpg"
          justificacion="Art. 158 CPE y Reglamento Camaral: Distribución por competencia y especialidad temática a las comisiones parlamentarias y a sus autoridades para su tratamiento de mérito."
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Building2 size={32} color="#60a5fa" />
              <h3 style={{ fontSize: '1.4rem', color: '#ffffff', fontWeight: 800, margin: 0 }}>Comisión Parlamentaria Asignada</h3>
            </div>
            <button className="btn-secondary" onClick={handleReset}>
              <RotateCcw size={16} />
              <span>Nuevo Trámite</span>
            </button>
          </div>

          <div style={{
            background: 'rgba(29, 78, 216, 0.2)',
            padding: '20px',
            borderRadius: '14px',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            marginBottom: '24px'
          }}>
            <div style={{ fontSize: '0.9rem', color: '#bfdbfe', marginBottom: '4px' }}>Comisión Principal Recomendada:</div>
            <div style={{ fontSize: '1.4rem', color: '#60a5fa', fontWeight: 800, marginBottom: '6px' }}>
              {comisionData.comision_principal}
            </div>
            {comisionData.comision_secundaria && (
              <div style={{ fontSize: '0.9rem', color: '#bfdbfe' }}>
                Comisión Secundaria: <strong style={{ color: '#ffffff' }}>{comisionData.comision_secundaria}</strong>
              </div>
            )}
            <div style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
              <span className="badge badge-gold">Prioridad: {comisionData.prioridad || 'Media'}</span>
              <span className="badge badge-blue">Complejidad: {comisionData.complejidad || 'Media'}</span>
            </div>
          </div>

          {comisionData.resumen && (
            <div style={{
              background: 'rgba(3, 20, 16, 0.6)',
              padding: '20px',
              borderRadius: '14px',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              marginBottom: '24px',
            }}>
              <h4 style={{ fontSize: '1rem', color: '#34d399', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                <BookOpen size={18} />
                Resumen Ejecutivo del Bot
              </h4>
              <p style={{ color: '#f0fdf4', fontSize: '0.92rem', lineHeight: 1.6, marginTop: '8px', marginBottom: 0 }}>{comisionData.resumen}</p>
            </div>
          )}

          {/* Miembros de la Comisión Asignada */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.6)',
            padding: '20px',
            borderRadius: '14px',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            marginBottom: '24px'
          }}>
            <h4 style={{ fontSize: '1.05rem', color: '#60a5fa', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
              <Users size={20} />
              Miembros Parlamentarios Asignados (Destinatarios Oficiales)
            </h4>
            {comisionData.miembros && comisionData.miembros.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px', marginTop: '12px' }}>
                {comisionData.miembros.map((m, idx) => (
                  <div key={idx} style={{
                    background: 'rgba(30, 41, 59, 0.7)',
                    padding: '12px 16px',
                    borderRadius: '10px',
                    border: '1px solid rgba(148, 163, 184, 0.2)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ color: '#ffffff', fontWeight: 700, fontSize: '0.92rem' }}>{m.nombre_completo}</span>
                      <span className="badge badge-gold">{m.cargo}</span>
                    </div>
                    <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '4px' }}>
                      Cámara: <strong style={{ color: '#cbd5e1' }}>{m.tipo_camara}</strong> {m.partido_politico ? `| ${m.partido_politico}` : ''}
                    </div>
                    {m.email && (
                      <div style={{ fontSize: '0.82rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Mail size={14} />
                        <span>{m.email}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: '0.88rem', color: '#94a3b8', fontStyle: 'italic', marginTop: '8px' }}>
                No hay parlamentarios registrados aún para esta comisión.
              </div>
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '24px', gap: '14px', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: '#94A3B8', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Zap size={14} color="#00B4D8" /> Ejecución simultánea en paralelo
            </span>
            <button
              onClick={handleEjecutarAuditoriaParalela}
              disabled={isProcessing}
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
                  <span>Ejecutando Auditoría Paralela (CPE + Leyes)...</span>
                </>
              ) : (
                <>
                  <Zap size={20} color="#8AC926" />
                  <span>Iniciar Auditoría Paralela (CPE + Leyes)</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </div>
        </AgentResultCard>
      )}

      {/* ── STEP 5: VERIFICACIÓN CONSTITUCIONAL CPE ── */}
      {effectiveViewStep === 5 && dictamenData && (
        <AgentResultCard
          agentName="Agente Verificador Constitucional"
          role="Auditoría de Conformidad contra la CPE Bolivia 2009"
          theme="green"
          status="completed"
          phaseLabel="Fase 2: CPE Bolivia"
          model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
          thinkingText="Dictamen Constitucional emitido"
          badgeText={dictamenData.valido ? '✅ CPE Conforme' : '⚠️ CPE Observado'}
          image="/robots/robot_constitucional_hi.jpg"
          justificacion="Art. 410 CPE: Principio de Supremacía Constitucional. El proyecto debe cotejarse exhaustivamente con los mandatos de la CPE 2009 para impedir normas contrarias a los derechos y garantías constitucionales."
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
                  {dictamenData.confianza || 95}%
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

          <div>
            {/* Severidad */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px' }}>
              <span style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.6)' }}>Severidad Máxima:</span>
              <span className={`badge ${
                dictamenData.severidad_maxima === 'bloqueante' ? 'badge-red' :
                dictamenData.severidad_maxima === 'grave' ? 'badge-gold' :
                dictamenData.severidad_maxima === 'leve' ? 'badge-blue' : 'badge-green'
              }`} style={{ fontSize: '0.85rem', padding: '5px 14px' }}>
                {dictamenData.severidad_maxima || 'ninguna'}
              </span>
            </div>

            {/* ── SECCIÓN A FAVOR ── */}
            {(() => {
              const aFavor = dictamenData.articulos_a_favor?.length > 0
                ? dictamenData.articulos_a_favor
                : (dictamenData.articulos_consultados || []);
              return aFavor.length > 0 && (
                <div style={{ marginBottom: '32px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid rgba(16,185,129,0.25)' }}>
                    <div style={{ width: '4px', height: '24px', background: '#10b981', borderRadius: '2px' }} />
                    <h3 style={{ fontSize: '1.05rem', color: '#34d399', margin: 0, fontWeight: 700 }}>
                      Artículos CPE — RESPALDO A FAVOR ({aFavor.length})
                    </h3>
                    <span style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
                      Fuente: public.articulos_constitucion
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '14px' }}>
                    {aFavor.map((art, idx) => (
                      <div key={idx} style={{
                        background: 'rgba(6, 30, 20, 0.85)',
                        border: '1px solid rgba(16, 185, 129, 0.3)',
                        borderRadius: '12px',
                        padding: '16px',
                        position: 'relative',
                        overflow: 'hidden'
                      }}>
                        <div style={{ position: 'absolute', top: 0, left: 0, width: '3px', height: '100%', background: '#10b981', borderRadius: '12px 0 0 12px' }} />
                        <div style={{ paddingLeft: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                            <span style={{ color: '#34d399', fontWeight: 700, fontSize: '0.92rem' }}>
                              Art. {art.numero}
                            </span>
                            <span style={{ background: 'rgba(16,185,129,0.15)', color: '#34d399', border: '1px solid rgba(16,185,129,0.3)', padding: '2px 10px', borderRadius: '20px', fontSize: '0.72rem', fontWeight: 700 }}>
                              A FAVOR
                            </span>
                          </div>
                          {art.titulo && (
                            <div style={{ color: '#a7f3d0', fontWeight: 600, fontSize: '0.82rem', marginBottom: '6px' }}>
                              {art.titulo}
                            </div>
                          )}
                          <div style={{ color: 'rgba(167,243,208,0.75)', fontSize: '0.8rem', lineHeight: 1.55, borderTop: '1px solid rgba(16,185,129,0.1)', paddingTop: '8px' }}>
                            {art.extracto || art.fundamento || 'Artículo de la CPE verificado como conforme.'}
                          </div>
                        </div>
                      </div>
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
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '28px' }}>
              <button
                onClick={handleEjecutarConsistencia}
                disabled={isProcessing}
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
      )}

      {/* ── STEP 6: CONSISTENCIA NORMATIVA ── */}
      {effectiveViewStep === 6 && (
        <AgentResultCard
          agentName="Agente de Consistencia Normativa"
          role="Auditoría Semántica Vectorial pgvector (2048 dims)"
          theme="gold"
          status="completed"
          phaseLabel="Fase 2: Consistencia Vectorial"
          model="nvidia/nemotron-3-embed-1b"
          thinkingText="Auditoría semántica de leyes vigente emitida"
          image="/robots/robot_consistencia_hi.jpg"
          justificacion="Seguridad Jurídica y Principio de No Contradicción: Búsqueda vectorial semántica pgvector contra leyes y códigos vigentes para prevenir derogaciones tácitas y antinomias normativas."
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
                  <div style={{ fontSize: '1.1rem', fontWeight: 800, color:
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

              {/* Botón PDF */}
              {selectedCategory === 'AGENTE_REGISTRO_LEGISLATIVO' && (
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '24px' }}>
                  <button
                    onClick={handleEmitPDF}
                    disabled={isProcessing}
                    className="btn-primary"
                    style={{ fontSize: '1.05rem', padding: '14px 30px' }}
                  >
                    {isProcessing ? (
                      <>
                        <Cpu size={20} className="pulse-active" />
                        <span>Generando Informe PDF...</span>
                      </>
                    ) : (
                      <>
                        <FileCheck size={20} />
                        <span>Generar Informe de Auditoría PDF</span>
                        <ArrowRight size={18} />
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        </AgentResultCard>
      )}

      {/* ── STEP 7: RESULTADO FINAL PDF ── */}
      {effectiveViewStep === 7 && pdfResult && (
        <AgentResultCard
          agentName="Agente Concentrador y Emisor"
          role="Compilación de Dictámenes & Generación PDF Oficial"
          theme="blue"
          status="completed"
          phaseLabel="Fase 3: Redacción & PDF"
          model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
          thinkingText="Informe consolidado de auditoría generado en PDF"
          image="/robots/robot_concentrador_hi.jpg"
          justificacion="Publicidad, transparencia y rigor técnico: Consolida y sintetiza todos los dictámenes en un informe oficial y formaliza el reporte PDF para el plenario de la Asamblea."
        >
          <FileCheck size={56} color="#00B4D8" style={{ margin: '0 auto 16px', display: 'block' }} />
          <h3 style={{ fontSize: '1.6rem', color: '#ffffff', fontWeight: 800, marginBottom: '12px', textAlign: 'center' }}>
            Informe Consolidado Generado
          </h3>
          <p style={{ color: '#94A3B8', fontSize: '1rem', maxWidth: '700px', margin: '0 auto 24px', textAlign: 'center' }}>
            El Agente Emisor ha generado el dictamen técnico-jurídico formal. Ahora puede notificar a los miembros parlamentarios de la comisión.
          </p>
          
          <div style={{ maxWidth: '480px', margin: '0 auto 24px auto' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', color: '#7dd3fc', fontWeight: 600, marginBottom: '8px' }}>
              ✉️ Enviar copia directa a correo / Gmail (Opcional):
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="email"
                placeholder="ejemplo: tu_correo@gmail.com"
                value={customEmail}
                onChange={(e) => updateActiveSession({ customEmail: e.target.value })}
                style={{
                  flex: 1,
                  padding: '10px 14px',
                  borderRadius: '10px',
                  background: 'rgba(14, 22, 42, 0.9)',
                  border: '1px solid rgba(56, 189, 248, 0.4)',
                  color: '#ffffff',
                  fontSize: '0.9rem',
                  outline: 'none',
                }}
              />
            </div>
          </div>
          
          <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <a 
              href={`http://127.0.0.1:8085/uploaded_files/informes/${pdfResult.filename}`}
              target="_blank" 
              rel="noreferrer"
              className="btn-secondary"
              style={{ fontSize: '1rem', padding: '13px 24px', textDecoration: 'none' }}
            >
              <Download size={20} />
              <span>Descargar PDF</span>
            </a>
            <button
              onClick={handleNotificar}
              disabled={isProcessing}
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
      )}

      {/* ── STEP 8: NOTIFICADOR DE COMISIÓN ── */}
      {effectiveViewStep === 8 && notificadorData && (
        <AgentResultCard
          agentName="Agente Notificador de Comisión"
          role="Despachador de Correo HTML Institucional"
          theme="violet"
          status="completed"
          phaseLabel="Fase 3: Notificación Oficial"
          model="SMA/notificador-v1"
          thinkingText="Correo electrónico HTML despachado con éxito"
          image="/robots/robot_notificador_hi.jpg"
          justificacion="Debida notificación y publicidad parlamentaria: Despacha la comunicación oficial en formato HTML formal a los correos electrónicos institucionales de los miembros asignados."
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
                disabled={isProcessing}
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
                  href={`http://127.0.0.1:8085/uploaded_files/informes/${pdfResult.filename}`}
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
      )}

      {/* ── STEP 09: PROCESANDO CONSTITUCIÓN FONDO ── */}
      {effectiveViewStep === 9 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(320px, 360px) 1fr',
          gap: '24px',
          alignItems: 'start'
        }}>
          <div style={{ position: 'sticky', top: '20px' }}>
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
        <AgentResultCard
          agentName="Comisión Constitución (Fondo)"
          role="Análisis Hermenéutico y Viabilidad Sustantiva"
          theme="purple"
          status="completed"
          phaseLabel="Fase 4: Fondo CPE"
          model="Nemotron-70B (CrewAI)"
          thinkingText="Dictamen sustantivo de constitucionalidad emitido"
          image="/robots/robot_constitucional_hi.jpg"
          justificacion="Art. 196 CPE: Control de constitucionalidad de fondo, precedentes del TCP y ponderación proporcional de derechos fundamentales."
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
                    disabled={isProcessing}
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
      )}

      {/* ── STEP 11: RESULTADO CONCENTRADOR (CREWAI) ── */}
      {effectiveViewStep === 11 && concentradorData && (
        <AgentResultCard
          agentName="Agente Concentrador y Emisor (CrewAI)"
          role="Consolidación y Síntesis de Observaciones Multi-Agente"
          theme="blue"
          status="completed"
          phaseLabel="Fase 4: Síntesis"
          model="Nemotron-70B (CrewAI)"
          thinkingText="Expediente unificado consolidado con trazabilidad de origen"
          image="/robots/robot_concentrador_hi.jpg"
          justificacion="Rigor y Trazabilidad Parlamentaria: Consolida todas las observaciones de auditoría constitucional, normativa y de comisión en un expediente único."
        >
          {(() => {
            const exp = concentradorData.expediente_consolidado || {};
            const obsList = exp.observaciones_integradas || [];
            return (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <div style={{ background: 'rgba(0,180,216,0.15)', borderRadius: '50%', padding: '12px' }}>
                      <Merge size={32} color="#00B4D8" />
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                        Etapa 4 · Expediente Unificado
                      </div>
                      <h3 style={{ fontSize: '1.4rem', color: '#ffffff', fontWeight: 800, margin: 0 }}>
                        Expediente Consolidado Multi-Agente
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

                {/* Resumen Ejecutivo */}
                <div style={{ background: 'rgba(11,37,69,0.6)', border: '1px solid rgba(0,180,216,0.3)', padding: '18px', borderRadius: '12px', marginBottom: '20px' }}>
                  <h4 style={{ color: '#00B4D8', fontSize: '0.9rem', marginBottom: '6px' }}>📋 Resumen Ejecutivo Consolidado</h4>
                  <p style={{ color: '#d1fae5', fontSize: '0.88rem', lineHeight: 1.6, margin: 0 }}>
                    {exp.resumen_ejecutivo || 'Expediente consolidado con observaciones integradas de todos los agentes.'}
                  </p>
                </div>

                {/* Lista de Observaciones Integradas */}
                {obsList.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '24px' }}>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase' }}>
                      Observaciones Integradas con Trazabilidad:
                    </div>
                    {obsList.map((o, idx) => (
                      <div key={idx} style={{
                        background: 'rgba(15,23,42,0.7)',
                        border: '1px solid rgba(148,163,184,0.2)',
                        padding: '12px 16px',
                        borderRadius: '10px',
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px'
                      }}>
                        <div>
                          <span style={{ fontWeight: 700, color: '#e2e8f0', fontSize: '0.85rem', marginRight: '8px' }}>
                            [{o.tipo || 'OBS'}]
                          </span>
                          <span style={{ color: '#94a3b8', fontSize: '0.82rem' }}>
                            {typeof o.contenido === 'string' ? o.contenido.slice(0, 140) : JSON.stringify(o.contenido || {}).slice(0, 140)}...
                          </span>
                        </div>
                        <span className="badge" style={{ fontSize: '0.7rem', padding: '2px 8px', background: 'rgba(56,189,248,0.15)', color: '#38bdf8', flexShrink: 0 }}>
                          {o.agente_origen || 'Agente'}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Acción Siguiente */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '14px' }}>
                  <button
                    onClick={handleSecretario}
                    disabled={isProcessing}
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
      )}

      {/* ── STEP 12: RESULTADO SECRETARIO DE CÁMARA (DEBATE) ── */}
      {effectiveViewStep === 12 && secretarioData && (
        <AgentResultCard
          agentName="Agente Secretario de Cámara"
          role="Registro de Actas de Debate Parlamentario y Votaciones"
          theme="blue"
          status="completed"
          phaseLabel="Fase 4: Debate Plenario"
          model="Nemotron-70B (CrewAI)"
          thinkingText="Acta parlamentaria y votaciones nominales registradas"
          image="/robots/robot_ciudadano_hi.jpg"
          justificacion="Transparencia y publicidad legislativa: Registro fidedigno de intervenciones de legisladores, votaciones en grande y detalle, y acuerdos tomados en plenario."
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

                {/* Tabla de Votaciones */}
                <div style={{ background: 'rgba(15,23,42,0.85)', padding: '18px', borderRadius: '12px', border: '1px solid rgba(0,180,216,0.25)', marginBottom: '20px' }}>
                  <h4 style={{ color: '#00B4D8', fontSize: '0.95rem', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    🗳️ Resultados de Votación Nominal
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
                    {votaciones.map((v, idx) => (
                      <div key={idx} style={{
                        background: 'rgba(30,41,59,0.7)',
                        padding: '14px',
                        borderRadius: '10px',
                        border: '1px solid rgba(148,163,184,0.2)'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                          <span style={{ color: '#ffffff', fontWeight: 700, fontSize: '0.9rem' }}>{v.articulo}</span>
                          <span className="badge badge-green">{v.votacion}</span>
                        </div>
                        <div style={{ display: 'flex', gap: '12px', fontSize: '0.82rem', color: '#cbd5e1' }}>
                          <span>A favor: <strong style={{ color: '#8AC926' }}>{v.favor}</strong></span>
                          <span>En contra: <strong style={{ color: '#f87171' }}>{v.contra}</strong></span>
                          <span>Abstención: <strong style={{ color: '#F4A261' }}>{v.abstenciones}</strong></span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

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

                {/* Acción Siguiente */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '14px' }}>
                  <button
                    onClick={handleBicameral}
                    disabled={isProcessing}
                    className="btn-primary"
                    style={{ fontSize: '1.05rem', padding: '14px 30px' }}
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
      )}

      {/* ── STEP 13: RESULTADO COMUNICACIÓN BICAMERAL ── */}
      {effectiveViewStep === 13 && bicameralData && (
        <AgentResultCard
          agentName="Agente Comunicación Bicameral"
          role="Coordinación y Reconciliación entre Cámaras Legislativas"
          theme="sky"
          status="completed"
          phaseLabel="Fase 5: Bicameral"
          model="Nemotron-70B (CrewAI)"
          thinkingText="Cotejo de versiones entre Cámaras completado"
          image="/robots/robot_distribuidor_hi.jpg"
          justificacion="Art. 163 CPE: Reconciliación del trámite bicameral entre la Cámara de Origen y la Cámara Revisora para sanción legislativa."
        >
          {(() => {
            const ciclo = bicameralData.ciclo_bicameral || {};
            return (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <div style={{ background: 'rgba(14,165,233,0.2)', borderRadius: '50%', padding: '12px' }}>
                      <GitBranch size={32} color="#38bdf8" />
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                        Etapa 6 · Trámite Bicameral
                      </div>
                      <h3 style={{ fontSize: '1.4rem', color: '#ffffff', fontWeight: 800, margin: 0 }}>
                        Reconciliación de Cámaras Legislativas
                      </h3>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <span className="badge" style={{ background: 'rgba(14,165,233,0.2)', color: '#38bdf8', border: '1px solid #0ea5e9' }}>
                      Cambios: {ciclo.clasificacion_cambios || 'MENORES'}
                    </span>
                    <span className="badge badge-green">
                      Ruta: {ciclo.ruta_siguiente || 'SANCION_DIRECTA'}
                    </span>
                  </div>
                </div>

                <div style={{ background: 'rgba(12,74,110,0.25)', border: '1px solid rgba(14,165,233,0.3)', padding: '18px', borderRadius: '12px', marginBottom: '20px' }}>
                  <h4 style={{ color: '#38bdf8', fontSize: '0.9rem', marginBottom: '6px' }}>🔍 Justificación Técnica del Trámite</h4>
                  <p style={{ color: '#e0f2fe', fontSize: '0.88rem', lineHeight: 1.6, margin: 0 }}>
                    {ciclo.justificacion || 'Trámite bicameral completado. Las versiones de ambas cámaras convergen favorablemente.'}
                  </p>
                </div>

                {/* Acción Siguiente */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '14px' }}>
                  <button
                    onClick={handleVetoPromulgacion}
                    disabled={isProcessing}
                    className="btn-primary"
                    style={{ fontSize: '1.05rem', padding: '14px 30px' }}
                  >
                    {isProcessing ? (
                      <><Cpu size={20} className="pulse-active" /><span>Evaluando veto...</span></>
                    ) : (
                      <><Gavel size={20} /><span>Continuar: Evaluación Veto / Promulgación</span><ArrowRight size={18} /></>
                    )}
                  </button>
                </div>
              </div>
            );
          })()}
        </AgentResultCard>
      )}

      {/* ── STEP 14: RESULTADO VETO / PROMULGACIÓN ── */}
      {effectiveViewStep === 14 && vetoPromulgacionData && (
        <AgentResultCard
          agentName="Agente Veto y Promulgación"
          role="Evaluación Estratégica Multicriterio del Órgano Ejecutivo"
          theme="blue"
          status="completed"
          phaseLabel="Fase 5: Decisión Ejecutiva"
          model="Nemotron-70B (CrewAI)"
          thinkingText="Evaluación estratégica multicriterio emitida"
          image="/robots/robot_consistencia_hi.jpg"
          justificacion="Art. 163-167 CPE: Control político y constitucional previo a la promulgación presidencial. Dictamen sobre viabilidad política, legalidad, factibilidad y sostenibilidad."
        >
          {(() => {
            const ev = vetoPromulgacionData.evaluacion_veto || {};
            const crit = ev.criterios || {};
            const esPromulgar = ev.decision === 'PROMULGAR';
            return (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <div style={{ background: esPromulgar ? 'rgba(138,201,38,0.2)' : 'rgba(231,111,81,0.2)', borderRadius: '50%', padding: '12px' }}>
                      <Gavel size={32} color={esPromulgar ? '#8AC926' : '#E76F51'} />
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                        Etapa 7 · Decisión Estratégica Ejecutiva
                      </div>
                      <h3 style={{ fontSize: '1.5rem', color: '#ffffff', fontWeight: 800, margin: 0 }}>
                        {esPromulgar ? '✅ Sanción Aprobada: Proceder a Promulgación' : `⚠️ Dictamen de Veto: ${ev.decision}`}
                      </h3>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <span className="badge badge-gold">
                      Score Multicriterio: {ev.score_final || '7.5'}/10
                    </span>
                    <span className={`badge ${esPromulgar ? 'badge-green' : 'badge-red'}`}>
                      {ev.decision || 'PROMULGAR'}
                    </span>
                  </div>
                </div>

                {/* 4 Criterios Estratégicos */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '14px', marginBottom: '20px' }}>
                  <div style={{ background: 'rgba(15,23,42,0.85)', padding: '14px', borderRadius: '12px', border: '1px solid rgba(0,180,216,0.25)' }}>
                    <div style={{ fontSize: '0.75rem', color: '#00B4D8', fontWeight: 700, textTransform: 'uppercase' }}>Viabilidad Política</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ffffff', margin: '4px 0' }}>{crit.viabilidad_politica?.score || 8}/10</div>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{crit.viabilidad_politica?.razon || 'Consenso alcanzado'}</div>
                  </div>

                  <div style={{ background: 'rgba(15,23,42,0.85)', padding: '14px', borderRadius: '12px', border: '1px solid rgba(138,201,38,0.3)' }}>
                    <div style={{ fontSize: '0.75rem', color: '#8AC926', fontWeight: 700, textTransform: 'uppercase' }}>Legalidad Constitucional</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ffffff', margin: '4px 0' }}>{crit.legalidad_constitucional?.score || 9}/10</div>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{crit.legalidad_constitucional?.razon || 'Conforme a CPE Art. 410'}</div>
                  </div>

                  <div style={{ background: 'rgba(15,23,42,0.85)', padding: '14px', borderRadius: '12px', border: '1px solid rgba(56,189,248,0.25)' }}>
                    <div style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 700, textTransform: 'uppercase' }}>Factibilidad Técnica</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ffffff', margin: '4px 0' }}>{crit.factibilidad_tecnica?.score || 7}/10</div>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{crit.factibilidad_tecnica?.razon || 'Estructura técnica viable'}</div>
                  </div>

                  <div style={{ background: 'rgba(15,23,42,0.85)', padding: '14px', borderRadius: '12px', border: '1px solid rgba(244,162,97,0.3)' }}>
                    <div style={{ fontSize: '0.75rem', color: '#F4A261', fontWeight: 700, textTransform: 'uppercase' }}>Sostenibilidad Fiscal</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ffffff', margin: '4px 0' }}>{crit.sostenibilidad_fiscal?.score || 7}/10</div>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{crit.sostenibilidad_fiscal?.razon || 'Impacto presupuestario sostenible'}</div>
                  </div>
                </div>

                {/* Justificación */}
                {ev.justificacion && (
                  <div style={{ background: 'rgba(11,37,69,0.5)', border: '1px solid rgba(0,180,216,0.3)', padding: '16px', borderRadius: '12px', marginBottom: '24px' }}>
                    <p style={{ color: '#e2e8f0', fontSize: '0.88rem', lineHeight: 1.6, margin: 0 }}>
                      {ev.justificacion}
                    </p>
                  </div>
                )}

                {/* Acción Siguiente */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '14px' }}>
                  <button
                    onClick={handlePublicacion}
                    disabled={isProcessing}
                    className="btn-primary"
                    style={{ fontSize: '1.05rem', padding: '14px 30px' }}
                  >
                    {isProcessing ? (
                      <><Cpu size={20} className="pulse-active" /><span>Publicando en boletín...</span></>
                    ) : (
                      <><Newspaper size={20} /><span>Continuar: Publicación Oficial en Gaceta</span><ArrowRight size={18} /></>
                    )}
                  </button>
                </div>
              </div>
            );
          })()}
        </AgentResultCard>
      )}

      {/* ── STEP 15: RESULTADO PUBLICACIÓN OFICIAL (FIN DEL PIPELINE) ── */}
      {effectiveViewStep === 15 && publicacionData && (
        <AgentResultCard
          agentName="Agente de Publicación Oficial"
          role="Registro Oficial y Promulgación en Gaceta / Boletín"
          theme="blue"
          status="completed"
          phaseLabel="Fase 5: Promulgación & Vigencia"
          model="Nemotron-70B (CrewAI)"
          thinkingText="Ley formalmente promulgada y registrada en el Boletín Oficial"
          image="/robots/robot_concentrador_hi.jpg"
          justificacion="Art. 164 CPE: Las leyes serán de cumplimiento obligatorio desde el día de su publicación en la Gaceta Oficial del Estado Plurinacional."
        >
          {(() => {
            const pub = publicacionData.publicacion_oficial || {};
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
                    {pub.numero_ley || 'Ley Sancionada y Promulgada'}
                  </h2>
                  <p style={{ color: '#e0e7ff', fontSize: '1.05rem', maxWidth: '750px', margin: '0 auto' }}>
                    {pub.titulo || 'Proyecto de Ley'}
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

                {/* Acciones Finales */}
                <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', flexWrap: 'wrap' }}>
                  {pdfResult?.filename && (
                    <a
                      href={`http://127.0.0.1:8085/uploaded_files/informes/${pdfResult.filename}`}
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
    </div>
  );
}
