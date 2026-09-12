import React, { useRef, useState, useEffect } from 'react';
import {
  CheckCircle2,
  Sparkles,
  ChevronRight,
  ChevronLeft,
  ShieldCheck,
  Scale,
  Building2,
  FileCheck,
  Mail,
  Zap,
  ArrowRight,
  Maximize2,
  Minimize2,
  FolderInput,
  FileSearch,
  SendHorizontal,
  BookOpen,
  Merge,
  MessagesSquare,
  GitBranch,
  Gavel,
  Newspaper,
  Info,
  Eye
} from 'lucide-react';

// ── Logos de agentes disponibles (desde /robots/logos/) ──
const AGENT_LOGOS = {
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

// ── Paleta institucional por agente (Opción 6 — Tono Ejecutivo Moderno) ──
const INST_COLORS = {
  distribuidor:       { primary: '#00B4D8', glow: 'rgba(0,180,216,0.55)',   ring: '#00B4D8', done: '#8AC926' },
  comision:           { primary: '#38BDF8', glow: 'rgba(56,189,248,0.5)',   ring: '#38BDF8', done: '#8AC926' },
  constitucional:     { primary: '#8AC926', glow: 'rgba(138,201,38,0.55)',  ring: '#8AC926', done: '#8AC926' },
  consistencia:       { primary: '#F4A261', glow: 'rgba(244,162,97,0.55)',  ring: '#F4A261', done: '#8AC926' },
  emisor:             { primary: '#A78BFA', glow: 'rgba(167,139,250,0.5)', ring: '#A78BFA', done: '#8AC926' },
  notificador:        { primary: '#38BDF8', glow: 'rgba(56,189,248,0.5)',   ring: '#38BDF8', done: '#8AC926' },
  constitucion_fondo: { primary: '#8AC926', glow: 'rgba(138,201,38,0.55)',  ring: '#8AC926', done: '#8AC926' },
  concentrador_crew:  { primary: '#00B4D8', glow: 'rgba(0,180,216,0.5)',   ring: '#00B4D8', done: '#8AC926' },
  secretario:         { primary: '#F4A261', glow: 'rgba(244,162,97,0.5)',   ring: '#F4A261', done: '#8AC926' },
  bicameral:          { primary: '#38BDF8', glow: 'rgba(56,189,248,0.5)',   ring: '#38BDF8', done: '#8AC926' },
  veto_promulgacion:  { primary: '#E76F51', glow: 'rgba(231,111,81,0.5)',   ring: '#E76F51', done: '#8AC926' },
  publicacion:        { primary: '#8AC926', glow: 'rgba(138,201,38,0.55)',  ring: '#8AC926', done: '#8AC926' },
};

export const AGENTS_DEFINITION = [
  // ── ETAPA 1: DISTRIBUIDOR ──
  {
    id: 'distribuidor', key: 'distribuidor', stepNumber: '01',
    name: 'Agente Distribuidor', shortName: 'Distribuidor',
    role: 'Clasificación Institucional',
    phaseKey: 'fase1', phaseName: 'Fase 1: Admisión',
    theme: 'cyan', activeStep: 1, doneAtStep: 2,
    desc: 'Determina si el documento es legislativo, ciudadano o correspondencia.',
    justificacion: 'Debido proceso parlamentario: canaliza cada documento por su vía institucional correcta.',
    garantiaEtica: 'Distribución justa, imparcial y debida custodia documental',
    model: 'Nemotron-3 30B',
    workflowIcon: FolderInput, iconLabel: 'Admisión', isParallel: false
  },
  // ── ETAPA 2: COMISIÓN ──
  {
    id: 'comision', key: 'comision', stepNumber: '02',
    name: 'Comisión Legislativa', shortName: 'Comisión',
    role: 'Asignación Parlamentaria',
    phaseKey: 'fase2', phaseName: 'Fase 2: Asignación',
    theme: 'blue', activeStep: 3, doneAtStep: 4,
    desc: 'Asigna la comisión parlamentaria competente según la materia de ley.',
    justificacion: 'Art. 158 CPE: distribución por especialidad temática a comisiones camarales.',
    garantiaEtica: 'Asignación objetiva por competencia material y especialidad',
    model: 'Nemotron-3 30B',
    workflowIcon: Building2, iconLabel: 'Comisiones', isParallel: false
  },
  // ── ETAPA 3a: VERIFICADOR CONSTITUCIONAL (PARALELO) ──
  {
    id: 'constitucional', key: 'constitucional', stepNumber: '03',
    name: 'Verificador Constitucional', shortName: 'Constitucional',
    role: 'Auditoría CPE 2009',
    phaseKey: 'fase2', phaseName: 'Fase 2: CPE 2009',
    theme: 'green', activeStep: 4, doneAtStep: 5,
    desc: 'Coteja artículos contra la Constitución Política del Estado.',
    justificacion: 'Art. 410 CPE: Supremacía Constitucional frente a cualquier proyecto de ley.',
    garantiaEtica: 'Supremacía constitucional y salvaguarda del debido proceso',
    model: 'Nemotron-3 30B',
    workflowIcon: Scale, iconLabel: 'CPE 2009', isParallel: true, parallelGroup: 'auditoria'
  },
  // ── ETAPA 3b: CONSISTENCIA NORMATIVA (PARALELO) ──
  {
    id: 'consistencia', key: 'consistencia', stepNumber: '04',
    name: 'Consistencia Normativa', shortName: 'Consistencia',
    role: 'pgvector & Antinomias',
    phaseKey: 'fase2', phaseName: 'Fase 2: Leyes Vigentes',
    theme: 'gold', activeStep: 5, doneAtStep: 6,
    desc: 'Detecta contradicciones o repeticiones contra leyes vigentes.',
    justificacion: 'Seguridad jurídica: previene antinomias con códigos y leyes vigentes.',
    garantiaEtica: 'Seguridad jurídica: prevención rigurosa de antinomias normativas',
    model: 'pgvector 2048d',
    workflowIcon: FileSearch, iconLabel: 'Leyes 2048d', isParallel: true, parallelGroup: 'auditoria'
  },
  // ── ETAPA 4: EMISOR PDF ──
  {
    id: 'emisor', key: 'emisor', stepNumber: '05',
    name: 'Concentrador y Emisor', shortName: 'Emisor PDF',
    role: 'Síntesis Oficial & PDF',
    phaseKey: 'fase3', phaseName: 'Fase 3: Dictamen PDF',
    theme: 'pink', activeStep: 6, doneAtStep: 7,
    desc: 'Consolida los dictámenes y emite el reporte profesional en PDF.',
    justificacion: 'Publicidad y rigor técnico: consolida todos los hallazgos en un informe oficial.',
    garantiaEtica: 'Fidelidad documental y trazabilidad integral del expediente oficial',
    model: 'ReportLab + IA',
    workflowIcon: FileCheck, iconLabel: 'Informe PDF', isParallel: false
  },
  // ── ETAPA 5: NOTIFICADOR ──
  {
    id: 'notificador', key: 'notificador', stepNumber: '06',
    name: 'Notificador de Comisión', shortName: 'Notificador',
    role: 'Correo Institucional HTML',
    phaseKey: 'fase3', phaseName: 'Fase 3: Notificación',
    theme: 'violet', activeStep: 7, doneAtStep: 8,
    desc: 'Redacta y despacha la notificación formal HTML a los legisladores.',
    justificacion: 'Notificación oportuna: comunica formalmente el dictamen a los parlamentarios.',
    garantiaEtica: 'Notificación fehaciente y estricta confidencialidad institucional',
    model: 'SMTP / HTML SMA',
    db: ['MongoDB'],
    workflowIcon: SendHorizontal, iconLabel: 'Despacho HTML', isParallel: false
  },
  // ── ETAPA 6: CONSTITUCIÓN FONDO ──
  {
    id: 'constitucion_fondo', key: 'constitucion_fondo', stepNumber: '07',
    name: 'Comisión Constitución Fondo', shortName: 'CPE Fondo',
    role: 'Hermenéutica Constitucional',
    phaseKey: 'fase4', phaseName: 'Fase 4: Fondo',
    theme: 'purple', activeStep: 9, doneAtStep: 10,
    desc: 'Análisis hermenéutico sustantivo: precedentes TC, ponderación de derechos.',
    justificacion: 'Art. 196 CPE: interpretación conforme al fondo de la norma constitucional.',
    garantiaEtica: 'Interpretación pro homine y protección de derechos fundamentales',
    model: 'Nemotron-70B (CrewAI)',
    db: ['Neon PostgreSQL', 'MongoDB'],
    workflowIcon: BookOpen, iconLabel: 'CPE Fondo', isParallel: false
  },
  // ── ETAPA 7: CONCENTRADOR CREWAI ──
  {
    id: 'concentrador_crew', key: 'concentrador_crew', stepNumber: '08',
    name: 'Concentrador y Emisor', shortName: 'Concentrador',
    role: 'Síntesis Multi-Agente',
    phaseKey: 'fase4', phaseName: 'Fase 4: Síntesis',
    theme: 'emerald', activeStep: 10, doneAtStep: 11,
    desc: 'Integra observaciones de todos los agentes en un expediente consolidado.',
    justificacion: 'Trazabilidad total: consolida dictámenes con origen de cada observación.',
    garantiaEtica: 'Cadena de custodia intacta y síntesis probatoria transparente',
    model: 'Nemotron-70B (CrewAI)',
    db: ['Neon PostgreSQL', 'MongoDB'],
    workflowIcon: Merge, iconLabel: 'Síntesis', isParallel: false
  },
  // ── ETAPA 8: SECRETARIO ──
  {
    id: 'secretario', key: 'secretario', stepNumber: '09',
    name: 'Secretario de Cámara', shortName: 'Secretario',
    role: 'Acta de Debate & Votaciones',
    phaseKey: 'fase4', phaseName: 'Fase 4: Debate',
    theme: 'amber', activeStep: 11, doneAtStep: 12,
    desc: 'Registra intervenciones, votaciones nominales y acuerdos en sesión plenaria.',
    justificacion: 'Transparencia parlamentaria: acta fidedigna del debate legislativo.',
    garantiaEtica: 'Fe pública parlamentaria y registro nominal inalterable de votos',
    model: 'Nemotron-70B (CrewAI)',
    db: ['Neon PostgreSQL', 'MongoDB'],
    workflowIcon: MessagesSquare, iconLabel: 'Acta Debate', isParallel: false
  },
  // ── ETAPA 9: BICAMERAL ──
  {
    id: 'bicameral', key: 'bicameral', stepNumber: '10',
    name: 'Comunicación Bicameral', shortName: 'Bicameral',
    role: 'Trámite entre Cámaras',
    phaseKey: 'fase5', phaseName: 'Fase 5: Bicameral',
    theme: 'sky', activeStep: 12, doneAtStep: 13,
    desc: 'Compara versiones de ambas cámaras y decide ruta: Sanción o Conferencia.',
    justificacion: 'Art. 163 CPE: coordinación obligatoria entre Cámara de Origen y Revisora.',
    garantiaEtica: 'Equilibrio democrático y respeto al trámite bicameral',
    model: 'Nemotron-70B (CrewAI)',
    db: ['Neon PostgreSQL', 'MongoDB'],
    workflowIcon: GitBranch, iconLabel: 'Bicameral', isParallel: false
  },
  // ── ETAPA 10: VETO/PROMULGACIÓN ──
  {
    id: 'veto_promulgacion', key: 'veto_promulgacion', stepNumber: '11',
    name: 'Veto y Promulgación', shortName: 'Veto/Promulg.',
    role: 'Decisión Ejecutiva Final',
    phaseKey: 'fase5', phaseName: 'Fase 5: Veto',
    theme: 'rose', activeStep: 13, doneAtStep: 14,
    desc: 'Evalúa 4 criterios estratégicos y decide: PROMULGAR, VETAR_TOTAL o VETAR_PARCIAL.',
    justificacion: 'Art. 163-167 CPE: potestad promulgatoria y veto ejecutivo del proyecto.',
    garantiaEtica: 'Motivación jurídica transparente y razonabilidad ejecutiva',
    model: 'Nemotron-70B (CrewAI)',
    db: ['Neon PostgreSQL', 'MongoDB'],
    workflowIcon: Gavel, iconLabel: 'Promulgar', isParallel: false
  },
  // ── ETAPA 11: PUBLICACIÓN ──
  {
    id: 'publicacion', key: 'publicacion', stepNumber: '12',
    name: 'Publicación Oficial', shortName: 'Gaceta',
    role: 'Boletín & Gaceta Oficial',
    phaseKey: 'fase5', phaseName: 'Fase 5: Publicación',
    theme: 'indigo', activeStep: 14, doneAtStep: 15,
    desc: 'Genera número de ley, publica en Gaceta Oficial y emite boletín legislativo.',
    justificacion: 'Art. 164 CPE: publicidad registral oficial para presunción de conocimiento.',
    garantiaEtica: 'Publicidad registral oficial y presunción de conocimiento universal de la ley',
    model: 'Nemotron-70B (CrewAI)',
    db: ['Neon PostgreSQL', 'MongoDB'],
    workflowIcon: Newspaper, iconLabel: 'Gaceta Oficial', isParallel: false
  }
];

// ── Nodo circular individual ──
function CircularAgentNode({ agent, pipelineStep, isInspected, onSelect, compact = false }) {
  const [hovered, setHovered] = useState(false);
  const isActive = pipelineStep === agent.activeStep;
  const isDone   = pipelineStep >= agent.doneAtStep;
  const tc = INST_COLORS[agent.id] || INST_COLORS.distribuidor;
  const logoUrl = AGENT_LOGOS[agent.id];
  const size = compact ? 52 : 70;

  const borderColor = isInspected
    ? '#FFFFFF'
    : isDone
    ? tc.done
    : isActive
    ? tc.primary
    : 'rgba(100,116,139,0.5)';

  const boxShadow = isActive
    ? `0 0 0 3px ${tc.glow}, 0 0 20px ${tc.glow}`
    : isInspected
    ? `0 0 0 3px rgba(255,255,255,0.5)`
    : isDone
    ? `0 0 10px rgba(138,201,38,0.35)`
    : 'none';

  return (
    <div
      className={`agent-circle-node ${isActive ? 'node-active' : ''} ${isDone ? 'node-done' : ''}`}
      onClick={() => onSelect(agent)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}
    >
      {/* Tooltip */}
      {hovered && (
        <div style={{
          position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
          background: 'rgba(15,23,42,0.97)', border: '1px solid rgba(0,180,216,0.35)',
          borderRadius: '10px', padding: '8px 12px', zIndex: 100,
          whiteSpace: 'nowrap', marginBottom: '10px', pointerEvents: 'none',
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)'
        }}>
          <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#F1F5F9',
            fontFamily: 'Outfit, sans-serif', marginBottom: '2px' }}>
            {agent.name}
          </div>
          <div style={{ fontSize: '0.68rem', color: '#94A3B8', marginBottom: '5px' }}>{agent.role}</div>
          <div style={{ display: 'flex', gap: '4px' }}>
            <span style={{ fontSize: '0.62rem', padding: '2px 7px', borderRadius: '4px',
              background: isDone ? 'rgba(138,201,38,0.15)' : isActive ? 'rgba(0,180,216,0.15)' : 'rgba(100,116,139,0.15)',
              color: isDone ? '#8AC926' : isActive ? '#00B4D8' : '#64748B',
              fontWeight: 700 }}>
              {isDone ? 'Completado' : isActive ? 'En Proceso' : 'En Espera'}
            </span>
            <span style={{ fontSize: '0.62rem', color: '#475569', padding: '2px 4px' }}>Clic para detalles</span>
          </div>
        </div>
      )}

      {/* Círculo principal */}
      <div style={{
        width: `${size}px`, height: `${size}px`, borderRadius: '50%',
        border: `2.5px solid ${borderColor}`,
        boxShadow,
        overflow: 'hidden',
        background: 'linear-gradient(145deg, #0F172A, #1E293B)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        position: 'relative', flexShrink: 0,
        transition: 'all 0.25s ease',
        transform: hovered ? 'scale(1.1)' : 'scale(1)',
        cursor: 'pointer'
      }}>
        {logoUrl ? (
          <img
            src={logoUrl}
            alt={agent.name}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              filter: isDone ? 'brightness(0.95)' : isActive ? 'brightness(1.18)' : 'brightness(0.72)'
            }}
          />
        ) : (
          <div style={{
            width: '100%',
            height: '100%',
            background: `linear-gradient(135deg, #0B2545, #134074)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: tc.primary
          }}>
            {React.createElement(agent.workflowIcon || ShieldCheck, { size: compact ? 22 : 28 })}
          </div>
        )}

        {/* Anillo giratorio si activo */}
        {isActive && (
          <div style={{ position: 'absolute', inset: '-4px', borderRadius: '50%',
            border: `2px dashed ${tc.primary}`, opacity: 0.85,
            animation: 'spin 3s linear infinite', pointerEvents: 'none' }} />
        )}

        {/* Checkmark si completado */}
        {isDone && (
          <div style={{ position: 'absolute', bottom: '1px', right: '1px',
            background: '#8AC926', borderRadius: '50%',
            width: compact ? '16px' : '20px', height: compact ? '16px' : '20px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: '2px solid #0B2545' }}>
            <CheckCircle2 size={compact ? 9 : 12} color="#0B2545" />
          </div>
        )}

        {/* Indicador de inspección */}
        {isInspected && (
          <div style={{ position: 'absolute', inset: 0, borderRadius: '50%',
            background: 'rgba(255,255,255,0.12)', display: 'flex',
            alignItems: 'center', justifyContent: 'center' }}>
            <Eye size={16} color="#FFFFFF" />
          </div>
        )}
      </div>

      {/* Etiqueta + paso */}
      <div style={{ marginTop: '6px', textAlign: 'center', maxWidth: `${size + 20}px` }}>
        <div style={{ fontSize: compact ? '0.6rem' : '0.68rem', fontWeight: 700,
          color: isInspected ? '#FFFFFF' : isDone ? '#8AC926' : isActive ? tc.primary : '#64748B',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          fontFamily: 'Outfit, sans-serif', transition: 'color 0.2s' }}>
          {agent.shortName}
        </div>
        <div style={{ fontSize: '0.56rem', color: '#475569', fontFamily: 'monospace', marginTop: '1px' }}>
          P{agent.stepNumber}
        </div>
      </div>
    </div>
  );
}

// ── Conector Curvo Horizontal Interactivo (Entre nodos estándar) ──
function CurvedFlowConnector({ isDone, isActive, compact = false }) {
  const color = isDone ? '#8AC926' : isActive ? '#00B4D8' : 'rgba(100,116,139,0.32)';
  const glowId = useRef(`glow_${Math.random().toString(36).substr(2, 6)}`).current;
  const pathD = "M 4 20 C 16 10, 30 30, 42 20";

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
      width: compact ? '36px' : '48px',
      height: '40px',
      position: 'relative',
      userSelect: 'none'
    }}>
      <svg
        width={compact ? "36" : "48"}
        height="40"
        viewBox="0 0 48 40"
        fill="none"
        style={{ overflow: 'visible' }}
      >
        <defs>
          <filter id={glowId} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Resplandor amplio si activo */}
        {isActive && (
          <path
            d={pathD}
            stroke="#00B4D8"
            strokeWidth="5"
            strokeOpacity="0.25"
            strokeLinecap="round"
            fill="none"
          />
        )}

        {/* Trazo curvo con animación de flujo */}
        <path
          d={pathD}
          stroke={color}
          strokeWidth={isActive || isDone ? "2.6" : "1.8"}
          strokeDasharray={isActive ? "6 3" : "none"}
          strokeLinecap="round"
          fill="none"
          filter={isActive || isDone ? `url(#${glowId})` : undefined}
          style={{
            transition: 'stroke 0.4s ease, stroke-width 0.4s ease',
            animation: isActive ? 'flowDash 1.2s linear infinite' : 'none'
          }}
        />

        {/* Punta de flecha orientada al siguiente nodo */}
        <polygon
          points="39,15 47,20 39,25"
          fill={color}
          filter={isActive || isDone ? `url(#${glowId})` : undefined}
          style={{ transition: 'fill 0.4s ease' }}
        />

        {/* Partícula de pulso interactivo viajando a lo largo del flujo */}
        {isActive && (
          <circle r="3.2" fill="#00B4D8" filter={`url(#${glowId})`}>
            <animateMotion
              dur="1.2s"
              repeatCount="indefinite"
              path={pathD}
            />
          </circle>
        )}
      </svg>
    </div>
  );
}

// ── Conector de Bifurcación (Single -> Paralelo) ──
function SplitFlowConnector({ isDone, isActive, compact = false }) {
  const color = isDone ? '#8AC926' : isActive ? '#00B4D8' : 'rgba(100,116,139,0.32)';
  const glowId = useRef(`split_glow_${Math.random().toString(36).substr(2, 6)}`).current;
  const pathTop = "M 4 80 C 22 80, 26 34, 44 34";
  const pathBottom = "M 4 80 C 22 80, 26 126, 44 126";

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
      width: compact ? '40px' : '52px',
      height: '160px',
      position: 'relative'
    }}>
      <svg
        width={compact ? "40" : "52"}
        height="160"
        viewBox="0 0 52 160"
        fill="none"
        style={{ overflow: 'visible' }}
      >
        <defs>
          <filter id={glowId} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Ramal hacia auditoría constitucional (superior) */}
        <path
          d={pathTop}
          stroke={color}
          strokeWidth={isActive || isDone ? "2.5" : "1.8"}
          strokeDasharray={isActive ? "6 3" : "none"}
          strokeLinecap="round"
          fill="none"
          filter={isActive || isDone ? `url(#${glowId})` : undefined}
          style={{
            transition: 'stroke 0.4s ease',
            animation: isActive ? 'flowDash 1.2s linear infinite' : 'none'
          }}
        />
        <polygon points="41,29 48,34 41,39" fill={color} />

        {/* Ramal hacia consistencia normativa (inferior) */}
        <path
          d={pathBottom}
          stroke={color}
          strokeWidth={isActive || isDone ? "2.5" : "1.8"}
          strokeDasharray={isActive ? "6 3" : "none"}
          strokeLinecap="round"
          fill="none"
          filter={isActive || isDone ? `url(#${glowId})` : undefined}
          style={{
            transition: 'stroke 0.4s ease',
            animation: isActive ? 'flowDash 1.2s linear infinite' : 'none'
          }}
        />
        <polygon points="41,121 48,126 41,131" fill={color} />

        {/* Partículas interactivas en ambas vías paralelas */}
        {isActive && (
          <>
            <circle r="3" fill="#00B4D8" filter={`url(#${glowId})`}>
              <animateMotion dur="1.3s" repeatCount="indefinite" path={pathTop} />
            </circle>
            <circle r="3" fill="#00B4D8" filter={`url(#${glowId})`}>
              <animateMotion dur="1.3s" repeatCount="indefinite" path={pathBottom} />
            </circle>
          </>
        )}
      </svg>
    </div>
  );
}

// ── Conector de Convergencia (Paralelo -> Single) ──
function MergeFlowConnector({ isDone, isActive, compact = false }) {
  const color = isDone ? '#8AC926' : isActive ? '#00B4D8' : 'rgba(100,116,139,0.32)';
  const glowId = useRef(`merge_glow_${Math.random().toString(36).substr(2, 6)}`).current;
  const pathTop = "M 4 34 C 24 34, 28 80, 44 80";
  const pathBottom = "M 4 126 C 24 126, 28 80, 44 80";

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
      width: compact ? '40px' : '52px',
      height: '160px',
      position: 'relative'
    }}>
      <svg
        width={compact ? "40" : "52"}
        height="160"
        viewBox="0 0 52 160"
        fill="none"
        style={{ overflow: 'visible' }}
      >
        <defs>
          <filter id={glowId} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Convergencia superior */}
        <path
          d={pathTop}
          stroke={color}
          strokeWidth={isActive || isDone ? "2.5" : "1.8"}
          strokeDasharray={isActive ? "6 3" : "none"}
          strokeLinecap="round"
          fill="none"
          filter={isActive || isDone ? `url(#${glowId})` : undefined}
          style={{
            transition: 'stroke 0.4s ease',
            animation: isActive ? 'flowDash 1.2s linear infinite' : 'none'
          }}
        />

        {/* Convergencia inferior */}
        <path
          d={pathBottom}
          stroke={color}
          strokeWidth={isActive || isDone ? "2.5" : "1.8"}
          strokeDasharray={isActive ? "6 3" : "none"}
          strokeLinecap="round"
          fill="none"
          filter={isActive || isDone ? `url(#${glowId})` : undefined}
          style={{
            transition: 'stroke 0.4s ease',
            animation: isActive ? 'flowDash 1.2s linear infinite' : 'none'
          }}
        />

        {/* Flecha consolidada hacia el agente emisor */}
        <polygon points="41,75 49,80 41,85" fill={color} />

        {/* Partículas interactivas convergiendo */}
        {isActive && (
          <>
            <circle r="3" fill="#00B4D8" filter={`url(#${glowId})`}>
              <animateMotion dur="1.3s" repeatCount="indefinite" path={pathTop} />
            </circle>
            <circle r="3" fill="#00B4D8" filter={`url(#${glowId})`}>
              <animateMotion dur="1.3s" repeatCount="indefinite" path={pathBottom} />
            </circle>
          </>
        )}
      </svg>
    </div>
  );
}

// Bloque paralelo (constitucional + consistencia)
function ParallelBlock({ agents, pipelineStep, inspectedAgentId, onSelectAgent, compact }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center',
      gap: '6px', flexShrink: 0 }}>
      {/* Badge PARALELO */}
      <div style={{ fontSize: '0.54rem', fontWeight: 800, color: '#00B4D8',
        background: 'rgba(0,180,216,0.12)', border: '1px solid rgba(0,180,216,0.25)',
        borderRadius: '4px', padding: '1px 8px', letterSpacing: '0.06em', textTransform: 'uppercase',
        marginBottom: '2px' }}>
        Auditoria Paralela
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px',
        padding: '10px 12px', borderRadius: '14px',
        border: '1px dashed rgba(0,180,216,0.25)',
        background: 'rgba(0,180,216,0.04)', position: 'relative' }}>
        {agents.map((agent) => (
          <div key={agent.id} style={{ position: 'relative' }}>
            <CircularAgentNode
              agent={agent}
              pipelineStep={pipelineStep}
              isInspected={inspectedAgentId === agent.id}
              onSelect={onSelectAgent}
              compact={compact}
            />
          </div>
        ))}
        {/* Línea vertical de conexión */}
        <div style={{ position: 'absolute', left: '50%', top: '50%',
          transform: 'translate(-50%, -50%)',
          width: '1px', height: '30px',
          background: 'linear-gradient(to bottom, rgba(0,180,216,0.4), rgba(244,162,97,0.4))',
          zIndex: 0 }} />
      </div>
    </div>
  );
}

export default function HorizontalAgentFlow({
  pipelineStep = 0,
  inspectedAgentId = null,
  onSelectAgent = () => {}
}) {
  const scrollContainerRef = useRef(null);
  const [activeFilter, setActiveFilter] = useState('all');
  const [compact, setCompact] = useState(false);

  // Auto-scroll al agente activo
  useEffect(() => {
    if (!scrollContainerRef.current) return;
    const el = scrollContainerRef.current.querySelector('.node-active');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
  }, [pipelineStep]);

  const completedCount = AGENTS_DEFINITION.filter(a => pipelineStep >= a.doneAtStep).length;
  const progressPercent = Math.round((completedCount / AGENTS_DEFINITION.length) * 100);

  // Filtros de fase
  const allPhaseFilters = [
    { key: 'all',   label: `Todos (${AGENTS_DEFINITION.length})` },
    { key: 'fase1', label: 'Admision' },
    { key: 'fase2', label: 'Auditoria' },
    { key: 'fase3', label: 'Despacho' },
    { key: 'fase4', label: 'Debate' },
    { key: 'fase5', label: 'Promulgacion' },
  ];

  const filteredAgents = activeFilter === 'all'
    ? AGENTS_DEFINITION
    : AGENTS_DEFINITION.filter(a => a.phaseKey === activeFilter);

  // Agrupar para renderizado: agentes paralelos van juntos
  const renderGroups = [];
  let i = 0;
  while (i < filteredAgents.length) {
    const agent = filteredAgents[i];
    if (agent.isParallel) {
      // Recoger todos los del mismo grupo paralelo
      const group = filteredAgents.filter(a => a.parallelGroup === agent.parallelGroup);
      renderGroups.push({ type: 'parallel', agents: group });
      i += group.length;
    } else {
      renderGroups.push({ type: 'single', agent });
      i++;
    }
  }

  const handleScrollLeft  = () => scrollContainerRef.current?.scrollBy({ left: -250, behavior: 'smooth' });
  const handleScrollRight = () => scrollContainerRef.current?.scrollBy({ left: 250, behavior: 'smooth' });

  return (
    <div style={{ width: '100%', marginBottom: '26px' }}>

      {/* ── BARRA DE CONTROLES ── */}
      <div style={{
        background: 'rgba(15,23,42,0.85)',
        border: '1px solid rgba(0,180,216,0.2)',
        borderRadius: '14px',
        padding: '10px 16px',
        marginBottom: '14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '10px',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 4px 18px rgba(0,0,0,0.4)'
      }}>
        {/* Izquierda: título + filtros */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#0B2545',
            background: 'linear-gradient(135deg, #00B4D8, #0284C7)',
            padding: '4px 12px', borderRadius: '8px',
            display: 'flex', alignItems: 'center', gap: '6px', letterSpacing: '0.03em' }}>
            <Zap size={12} />
            <span>FLUX PIPELINE MULTI-AGENTE</span>
          </div>

          {/* Filtros de fase */}
          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
            {allPhaseFilters.map(f => (
              <button key={f.key} onClick={() => setActiveFilter(f.key)}
                style={{ border: 'none',
                  background: activeFilter === f.key ? 'rgba(0,180,216,0.2)' : 'rgba(255,255,255,0.05)',
                  color: activeFilter === f.key ? '#00B4D8' : '#64748B',
                  padding: '4px 10px', borderRadius: '7px',
                  fontSize: '0.7rem', fontWeight: activeFilter === f.key ? 700 : 500,
                  cursor: 'pointer', transition: 'all 0.15s ease',
                  whiteSpace: 'nowrap',
                  borderBottom: activeFilter === f.key ? '2px solid #00B4D8' : '2px solid transparent'
                }}>
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Derecha: toggle + progreso + scroll */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Toggle tamaño */}
          <button onClick={() => setCompact(c => !c)}
            style={{ border: '1px solid rgba(0,180,216,0.25)',
              background: 'rgba(30,41,59,0.7)', color: '#CBD5E1',
              padding: '4px 10px', borderRadius: '8px',
              fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '5px',
              cursor: 'pointer' }}>
            {compact ? <Maximize2 size={12} color="#00B4D8" /> : <Minimize2 size={12} color="#00B4D8" />}
            <span>{compact ? 'Ampliar' : 'Compacto'}</span>
          </button>

          {/* Progreso */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
            <div style={{ width: '100px', height: '6px',
              background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
              <div style={{ width: `${progressPercent}%`, height: '100%',
                background: 'linear-gradient(90deg, #0284C7, #00B4D8, #8AC926)',
                transition: 'width 0.4s ease', borderRadius: '3px' }} />
            </div>
            <span style={{ fontSize: '0.72rem', color: '#94A3B8', fontWeight: 700 }}>
              {completedCount}/{AGENTS_DEFINITION.length} ({progressPercent}%)
            </span>
          </div>

          {/* Scroll arrows */}
          <div style={{ display: 'flex', gap: '3px' }}>
            <button onClick={handleScrollLeft} title="Anterior"
              style={{ border: '1px solid rgba(100,116,139,0.3)',
                background: 'rgba(30,41,59,0.8)', color: '#E2E8F0',
                borderRadius: '6px', width: '26px', height: '26px',
                display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
              <ChevronLeft size={13} />
            </button>
            <button onClick={handleScrollRight} title="Siguiente"
              style={{ border: '1px solid rgba(100,116,139,0.3)',
                background: 'rgba(30,41,59,0.8)', color: '#E2E8F0',
                borderRadius: '6px', width: '26px', height: '26px',
                display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
              <ChevronRight size={13} />
            </button>
          </div>
        </div>
      </div>

      {/* ── TRACK DEL FLUJO HORIZONTAL ── */}
      <div style={{
        background: 'rgba(11,37,69,0.5)',
        border: '1px solid rgba(0,180,216,0.15)',
        borderRadius: '16px',
        padding: compact ? '14px 16px' : '18px 16px',
        backdropFilter: 'blur(8px)'
      }}>
        <div ref={scrollContainerRef}
          style={{ display: 'flex', alignItems: 'center', gap: '6px',
            overflowX: 'auto', paddingBottom: '4px',
            scrollBehavior: 'smooth', userSelect: 'none' }}>

          {renderGroups.map((group, gi) => {
            const isLastGroup = gi === renderGroups.length - 1;
            const representativeAgent = group.type === 'single' ? group.agent : group.agents[0];
            const isDone   = pipelineStep >= representativeAgent.doneAtStep;
            const isActive = pipelineStep === representativeAgent.activeStep ||
              (group.type === 'parallel' && group.agents.some(a => pipelineStep === a.activeStep));

            return (
              <React.Fragment key={gi}>
                {group.type === 'single' ? (
                  <div style={{ position: 'relative', flexShrink: 0 }}>
                    <CircularAgentNode
                      agent={group.agent}
                      pipelineStep={pipelineStep}
                      isInspected={inspectedAgentId === group.agent.id}
                      onSelect={onSelectAgent}
                      compact={compact}
                    />
                  </div>
                ) : (
                  <ParallelBlock
                    agents={group.agents}
                    pipelineStep={pipelineStep}
                    inspectedAgentId={inspectedAgentId}
                    onSelectAgent={onSelectAgent}
                    compact={compact}
                  />
                )}

                {/* Conector interactivo inteligente entre grupos */}
                {!isLastGroup && (() => {
                  const nextGroup = renderGroups[gi + 1];
                  if (group.type === 'single' && nextGroup?.type === 'parallel') {
                    return (
                      <SplitFlowConnector
                        key={`split-${gi}`}
                        isDone={isDone}
                        isActive={isActive}
                        compact={compact}
                      />
                    );
                  }
                  if (group.type === 'parallel' && nextGroup?.type === 'single') {
                    return (
                      <MergeFlowConnector
                        key={`merge-${gi}`}
                        isDone={isDone}
                        isActive={isActive}
                        compact={compact}
                      />
                    );
                  }
                  return (
                    <CurvedFlowConnector
                      key={`conn-${gi}`}
                      isDone={isDone}
                      isActive={isActive}
                      compact={compact}
                    />
                  );
                })()}
              </React.Fragment>
            );
          })}
        </div>

        {/* ── LEYENDA RÁPIDA ── */}
        <div style={{ display: 'flex', gap: '16px', marginTop: '12px',
          paddingTop: '10px', borderTop: '1px solid rgba(0,180,216,0.1)',
          flexWrap: 'wrap' }}>
          {
            [
              { color: '#8AC926', label: 'Completado' },
              { color: '#00B4D8', label: 'En Proceso' },
              { color: 'rgba(100,116,139,0.5)', label: 'En Espera' },
              { color: '#00B4D8', label: 'Auditoria Paralela', dashed: true },
            ].map((l, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '50%',
                  background: l.dashed ? 'transparent' : l.color,
                  border: l.dashed ? `1.5px dashed ${l.color}` : `1.5px solid ${l.color}55` }} />
                <span style={{ fontSize: '0.66rem', color: '#64748B', fontWeight: 600 }}>
                  {l.label}
                </span>
              </div>
            ))
          }
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Info size={11} color="#475569" />
            <span style={{ fontSize: '0.66rem', color: '#475569' }}>
              Seleccione un agente para ver su actividad
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
