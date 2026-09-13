/**
 * VoiceAssistantPage.jsx — Módulo de Interacción por Voz Multimodal (TTS & STT)
 * ==============================================================================
 * Sistema Multi-Agente (SMA) Congreso de Bolivia.
 *
 * Características principales:
 *  - Reconocimiento de voz nativo (Speech-to-Text) en Español Latino / Neutro ('es-419').
 *  - Síntesis de voz (Text-to-Speech) con filtrado estricto anti-acento peninsular (excluye 'es-ES').
 *  - Selector de variantes latinoamericanas priorizadas (México, Colombia, Argentina, etc.).
 *  - Control de velocidad (0.8x a 1.4x) y tono (pitch).
 *  - Operadores robóticos intercambiables (Distribuidor, Constitucionalista, Consistencia, etc.).
 *  - Transcripción editable en tiempo real con soporte de interim results.
 *  - Consultas parlamentarias predefinidas de un solo clic.
 *  - Barra de acciones flotante con animaciones reactivas y pulsaciones dinámicas.
 */

import React, { useState, useEffect } from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Square,
  Play,
  Pause,
  RotateCcw,
  Sparkles,
  Bot,
  Copy,
  Check,
  Cpu,
  Settings,
  AlertCircle,
  CheckCircle2,
  Send,
  MessageSquare,
  Radio,
  Sliders,
  FileText,
  Scale,
  ShieldCheck,
  Zap,
  Info
} from 'lucide-react';
import { useLatinSpeech } from '../hooks/useLatinSpeech';

// Catálogo de operadores robóticos parlamentarios seleccionables
const VOICE_OPERATORS = [
  {
    id: 'distribuidor',
    name: 'Operador Distribuidor',
    role: 'Mesa de Partes & Admisión',
    image: '/robots/robot_distribuidor_hi.jpg',
    theme: 'cyan',
    primaryColor: '#00f0ff',
    badge: 'Nivel 1 • Admisión',
    greeting: 'Saludos parlamentarios. Soy el Operador de Admisión de la Mesa de Partes. Dicta o escribe el resumen o título del documento que deseas canalizar al sistema legislativo.',
  },
  {
    id: 'constitucional',
    name: 'Operador Constitucionalista',
    role: 'Auditor de la CPE 2009',
    image: '/robots/robot_constitucional_hi.jpg',
    theme: 'green',
    primaryColor: '#10b981',
    badge: 'Nivel 2 • CPE 2009',
    greeting: 'Atención legislativa. Me encargo del control de constitucionalidad. ¿Deseas consultar la conformidad de algún artículo o principio fundamental de la CPE?',
  },
  {
    id: 'consistencia',
    name: 'Operador de Consistencia',
    role: 'Vectores pgvector & Leyes Vigentes',
    image: '/robots/robot_consistencia_hi.jpg',
    theme: 'gold',
    primaryColor: '#f59e0b',
    badge: 'Nivel 2 • pgvector',
    greeting: 'Base normativa conectada con embeddings de 2048 dimensiones. Pregúntame sobre posibles colisiones normativas con el Código Penal o Leyes Sectoriales.',
  },
  {
    id: 'ciudadano',
    name: 'Operador de Interacción Ciudadana',
    role: 'Ventanilla Social & Peticiones',
    image: '/robots/robot_ciudadano_hi.jpg',
    theme: 'violet',
    primaryColor: '#a855f7',
    badge: 'Nivel 1 • Ciudadanía',
    greeting: 'Bienvenido. Estoy listo para escuchar y transcribir solicitudes, peticiones o reclamos de la ciudadanía para derivarlos a la unidad competente.',
  },
];

// Prompts sugeridos parlamentarios para prueba rápida
const SAMPLE_QUERIES = [
  {
    label: 'Energía Renovable',
    icon: Zap,
    text: 'Proyecto de ley que establece incentivos arancelarios y fiscales para la generación comunitaria de energía solar en el altiplano y valles de Bolivia.',
  },
  {
    label: 'Consulta CPE',
    icon: ShieldCheck,
    text: '¿El artículo 15 del proyecto sobre seguridad ciudadana colisiona con las garantías constitucionales del debido proceso y la libertad de locomoción?',
  },
  {
    label: 'Consistencia Penal',
    icon: Scale,
    text: 'Evaluar consistencia normativa del artículo de sanciones ambientales frente al Código Penal vigente y la Ley Marco de la Madre Tierra.',
  },
  {
    label: 'Petición Ciudadana',
    icon: MessageSquare,
    text: 'Solicitud formal de la Federación de Productores Agrícolas para solicitar una audiencia pública ante la Comisión de Economía Plural.',
  },
];

export default function VoiceAssistantPage({ onNavigateTab }) {
  // Hook de voz en español latinoamericano
  const {
    isListening,
    transcript,
    setTranscript,
    interimTranscript,
    recognitionStatus,
    startListening,
    stopListening,
    clearTranscript,
    voices,
    selectedVoice,
    setSelectedVoice,
    isSpeaking,
    isPaused,
    rate,
    setRate,
    pitch,
    setPitch,
    speak,
    pauseSpeaking,
    resumeSpeaking,
    stopSpeaking,
    isSTTSupported,
    isTTSSupported,
    error,
    setError,
  } = useLatinSpeech();

  // Operador robótico activo
  const [activeOperator, setActiveOperator] = useState(VOICE_OPERATORS[0]);
  const [showSettings, setShowSettings] = useState(false);
  const [copied, setCopied] = useState(false);
  const [assistantResponse, setAssistantResponse] = useState(VOICE_OPERATORS[0].greeting);

  // Al cambiar de operador, actualizar el saludo inicial
  const handleSelectOperator = (op) => {
    setActiveOperator(op);
    setAssistantResponse(op.greeting);
    if (isSpeaking) {
      stopSpeaking();
    }
  };

  // Copiar transcripción al portapapeles
  const handleCopy = async () => {
    const textToCopy = transcript.trim() || assistantResponse;
    if (!textToCopy) return;

    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.warn('Error al copiar:', e);
    }
  };

  // Cargar una consulta parlamentaria de prueba
  const handleLoadSample = (sampleText) => {
    setTranscript(sampleText);
    setError(null);
  };

  // Reproducir el saludo del operador o la transcripción
  const handleSpeakText = (textToRead) => {
    const targetText = textToRead || transcript || assistantResponse;
    if (!targetText) return;
    speak(targetText);
  };

  return (
    <div
      style={{
        maxWidth: '1440px',
        margin: '0 auto',
        padding: '28px 24px 80px 24px',
        color: '#f8fafc',
        fontFamily: "'Inter', sans-serif",
      }}
    >
      {/* ── 1. HEADER / HERO DE LA CONSOLA MULTIMODAL ── */}
      <div
        style={{
          background: 'linear-gradient(145deg, #091322 0%, #0d1b2e 100%)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          borderRadius: '24px',
          padding: '24px 28px',
          marginBottom: '24px',
          boxShadow: '0 12px 35px rgba(0, 0, 0, 0.35)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Glow de fondo decorativo */}
        <div
          style={{
            position: 'absolute',
            top: '-50px',
            right: '-50px',
            width: '240px',
            height: '240px',
            background: 'radial-gradient(circle, rgba(16, 185, 129, 0.15) 0%, transparent 70%)',
            pointerEvents: 'none',
          }}
        />

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px',
          }}
        >
          {/* Título & Badge de Módulo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div
              style={{
                width: '54px',
                height: '54px',
                borderRadius: '16px',
                background: 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 20px rgba(14, 165, 233, 0.45)',
                border: '1.5px solid rgba(255, 255, 255, 0.25)',
                flexShrink: 0,
              }}
            >
              <Radio size={28} color="#ffffff" className={isListening ? 'animate-pulse' : ''} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <h1
                  style={{
                    fontFamily: "'Outfit', sans-serif",
                    fontWeight: 800,
                    fontSize: '1.65rem',
                    color: '#ffffff',
                    margin: 0,
                    letterSpacing: '-0.02em',
                  }}
                >
                  Asistente de Voz Parlamentario
                </h1>
                <span
                  className="badge badge-blue"
                  style={{ fontSize: '0.72rem', padding: '3px 10px', fontWeight: 700 }}
                >
                  STT + TTS Latino Neutro
                </span>
                <span
                  className="badge badge-gold"
                  style={{ fontSize: '0.72rem', padding: '3px 10px', fontWeight: 700 }}
                >
                  Web Speech API
                </span>
              </div>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.86rem', color: '#94a3b8' }}>
                Dictado y síntesis vocal en español latinoamericano (excluye modismos peninsulares). Conectado con la directiva robótica del SMA.
              </p>
            </div>
          </div>

          {/* Badges de Soporte y Diagnóstico del Navegador */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            {/* Soporte Micrófono (STT) */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '9999px',
                background: isSTTSupported ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                border: `1px solid ${isSTTSupported ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.35)'}`,
                fontSize: '0.78rem',
                fontWeight: 600,
                color: isSTTSupported ? '#34d399' : '#f87171',
              }}
            >
              {isSTTSupported ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
              <span>STT: {isSTTSupported ? 'Micrófono Activo (es-419)' : 'No Soportado'}</span>
            </div>

            {/* Soporte Síntesis (TTS) */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '9999px',
                background: isTTSSupported ? 'rgba(56, 189, 248, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                border: `1px solid ${isTTSSupported ? 'rgba(56, 189, 248, 0.35)' : 'rgba(239, 68, 68, 0.35)'}`,
                fontSize: '0.78rem',
                fontWeight: 600,
                color: isTTSSupported ? '#38bdf8' : '#f87171',
              }}
            >
              {isTTSSupported ? <Volume2 size={14} /> : <VolumeX size={14} />}
              <span>TTS: {voices.length} Voces Latinas</span>
            </div>

            {/* Botón Configuración de Audio */}
            <button
              onClick={() => setShowSettings(!showSettings)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '7px 14px',
                borderRadius: '12px',
                background: showSettings ? 'rgba(14, 165, 233, 0.3)' : 'rgba(255, 255, 255, 0.06)',
                border: `1px solid ${showSettings ? '#0ea5e9' : 'rgba(255, 255, 255, 0.15)'}`,
                color: '#f8fafc',
                cursor: 'pointer',
                fontFamily: "'Outfit', sans-serif",
                fontWeight: 600,
                fontSize: '0.82rem',
                transition: 'all 0.2s ease',
              }}
            >
              <Settings size={15} color={showSettings ? '#38bdf8' : '#cbd5e1'} />
              <span>Ajustes de Voz</span>
            </button>
          </div>
        </div>

        {/* ── PANEL DESPLEGABLE: AJUSTES DE VOZ LATINA Y PARÁMETROS ── */}
        {showSettings && (
          <div
            style={{
              marginTop: '20px',
              padding: '18px 20px',
              borderRadius: '16px',
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '18px',
              alignItems: 'center',
            }}
          >
            {/* Selector de Voz Latina */}
            <div>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  color: '#38bdf8',
                  marginBottom: '8px',
                }}
              >
                <Sliders size={14} /> Voz en Español Latinoamericano:
              </label>
              <select
                value={selectedVoice?.id || ''}
                onChange={(e) => {
                  const found = voices.find((v) => v.id === e.target.value);
                  if (found) setSelectedVoice(found);
                }}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: '10px',
                  background: '#0a101d',
                  border: '1px solid rgba(56, 189, 248, 0.4)',
                  color: '#ffffff',
                  fontSize: '0.84rem',
                  fontWeight: 500,
                  outline: 'none',
                  cursor: 'pointer',
                }}
              >
                {voices.length === 0 ? (
                  <option value="">Cargando voces del navegador...</option>
                ) : (
                  voices.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.label}
                    </option>
                  ))
                )}
              </select>
              <span style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px', display: 'block' }}>
                ✓ Filtro activo: Se excluyen expresamente voces peninsulares ('es-ES').
              </span>
            </div>

            {/* Slider de Velocidad (Rate: 0.8x a 1.4x) */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#e2e8f0' }}>
                  Velocidad de Lectura:
                </span>
                <span style={{ fontSize: '0.8rem', color: '#10b981', fontWeight: 700 }}>
                  {rate.toFixed(2)}x
                </span>
              </div>
              <input
                type="range"
                min="0.8"
                max="1.4"
                step="0.05"
                value={rate}
                onChange={(e) => setRate(parseFloat(e.target.value))}
                style={{
                  width: '100%',
                  accentColor: '#10b981',
                  cursor: 'pointer',
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: '#64748b' }}>
                <span>0.8x (Pausado)</span>
                <span>1.0x (Normal)</span>
                <span>1.4x (Rápido)</span>
              </div>
            </div>

            {/* Slider de Tono (Pitch: 0.8 a 1.2) */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#e2e8f0' }}>
                  Tono / Frecuencia (Pitch):
                </span>
                <span style={{ fontSize: '0.8rem', color: '#f59e0b', fontWeight: 700 }}>
                  {pitch.toFixed(2)}
                </span>
              </div>
              <input
                type="range"
                min="0.8"
                max="1.2"
                step="0.05"
                value={pitch}
                onChange={(e) => setPitch(parseFloat(e.target.value))}
                style={{
                  width: '100%',
                  accentColor: '#f59e0b',
                  cursor: 'pointer',
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: '#64748b' }}>
                <span>0.8 (Grave)</span>
                <span>1.0 (Neutro)</span>
                <span>1.2 (Agudo)</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── BANNER DE ALERTA DE ERROR SI EXISTE ── */}
      {error && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid #ef4444',
            borderRadius: '14px',
            padding: '12px 18px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertCircle size={20} color="#f87171" />
            <span style={{ fontSize: '0.86rem', color: '#fca5a5' }}>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#f87171',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '0.8rem',
            }}
          >
            Entendido
          </button>
        </div>
      )}

      {/* ── 2. SECCIÓN PRINCIPAL: OPERADOR ROBÓTICO + PANEL MULTIMODAL ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '340px 1fr',
          gap: '24px',
          alignItems: 'start',
        }}
      >
        {/* COLUMNA IZQUIERDA: TARJETA DEL OPERADOR ROBÓTICO ACTIVO */}
        <div
          style={{
            background: 'linear-gradient(160deg, #0a1727 0%, #060e1a 100%)',
            border: `2px solid ${isListening ? '#00f0ff' : isSpeaking ? '#10b981' : 'rgba(56, 189, 248, 0.4)'}`,
            borderRadius: '24px',
            padding: '22px',
            boxShadow: isListening
              ? '0 0 35px rgba(0, 240, 255, 0.35)'
              : isSpeaking
              ? '0 0 35px rgba(16, 185, 129, 0.35)'
              : '0 10px 30px rgba(0, 0, 0, 0.4)',
            transition: 'all 0.3s ease',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {/* Selector de Operador */}
          <div style={{ marginBottom: '14px' }}>
            <span style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
              Operador de Voz Parlamentario:
            </span>
            <div style={{ display: 'flex', gap: '6px', marginTop: '6px', flexWrap: 'wrap' }}>
              {VOICE_OPERATORS.map((op) => {
                const isCurrent = op.id === activeOperator.id;
                return (
                  <button
                    key={op.id}
                    onClick={() => handleSelectOperator(op)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '8px',
                      border: `1px solid ${isCurrent ? op.primaryColor : 'rgba(255, 255, 255, 0.1)'}`,
                      background: isCurrent ? `${op.primaryColor}22` : 'rgba(255, 255, 255, 0.04)',
                      color: isCurrent ? '#ffffff' : '#94a3b8',
                      fontSize: '0.72rem',
                      fontWeight: isCurrent ? 700 : 500,
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    {op.name.replace('Operador ', '')}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Imagen del Robot con Efecto Holográfico y Escáner */}
          <div
            style={{
              width: '100%',
              height: '240px',
              borderRadius: '18px',
              overflow: 'hidden',
              position: 'relative',
              background: 'radial-gradient(circle at center, #1e293b 0%, #070c16 100%)',
              border: `1.5px solid ${isListening ? '#00f0ff' : 'rgba(255, 255, 255, 0.12)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '16px',
            }}
          >
            <img
              src={activeOperator.image}
              alt={activeOperator.name}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'contain',
                padding: '6px',
                filter: isListening
                  ? 'brightness(1.2) drop-shadow(0 0 12px rgba(0, 240, 255, 0.5))'
                  : isSpeaking
                  ? 'brightness(1.15) drop-shadow(0 0 12px rgba(16, 185, 129, 0.5))'
                  : 'none',
                transition: 'all 0.3s ease',
              }}
            />

            {/* Efecto de escaneo láser en vivo cuando está escuchando */}
            {isListening && (
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: '3px',
                  background: 'linear-gradient(90deg, transparent, #00f0ff, transparent)',
                  boxShadow: '0 0 15px #00f0ff',
                  animation: 'scan-laser 2s linear infinite',
                }}
              />
            )}

            {/* Badge de Estado en el avatar */}
            <div
              style={{
                position: 'absolute',
                bottom: '10px',
                left: '10px',
                right: '10px',
                background: 'rgba(15, 23, 42, 0.88)',
                backdropFilter: 'blur(8px)',
                borderRadius: '10px',
                padding: '6px 10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                border: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              <span style={{ fontSize: '0.74rem', color: '#cbd5e1', fontWeight: 600 }}>
                {isListening ? '🎙️ Capturando audio...' : isSpeaking ? '🔊 Reproduciendo voz...' : 'En Espera'}
              </span>
              <span
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: isListening ? '#00f0ff' : isSpeaking ? '#10b981' : '#64748b',
                  boxShadow: isListening ? '0 0 8px #00f0ff' : isSpeaking ? '0 0 8px #10b981' : 'none',
                }}
              />
            </div>
          </div>

          {/* Información del Operador Activo */}
          <div style={{ textAlign: 'left' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
              <h3 style={{ fontFamily: "'Outfit', sans-serif", fontSize: '1.15rem', color: '#ffffff', margin: 0 }}>
                {activeOperator.name}
              </h3>
              <span className="badge badge-green" style={{ fontSize: '0.68rem' }}>
                {activeOperator.badge}
              </span>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#38bdf8', fontWeight: 600, margin: '0 0 10px 0' }}>
              {activeOperator.role}
            </p>
            <div
              style={{
                background: 'rgba(0, 0, 0, 0.4)',
                borderRadius: '12px',
                padding: '10px 12px',
                fontSize: '0.78rem',
                color: '#e2e8f0',
                lineHeight: 1.45,
                borderLeft: `3px solid ${activeOperator.primaryColor}`,
              }}
            >
              {assistantResponse}
            </div>

            {/* Botón para escuchar el saludo del robot */}
            <button
              onClick={() => handleSpeakText(assistantResponse)}
              disabled={isSpeaking}
              style={{
                width: '100%',
                marginTop: '12px',
                padding: '8px 12px',
                borderRadius: '10px',
                background: isSpeaking ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.06)',
                border: `1px solid ${isSpeaking ? '#10b981' : 'rgba(255, 255, 255, 0.15)'}`,
                color: '#ffffff',
                fontSize: '0.78rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <Volume2 size={15} color="#34d399" />
              <span>{isSpeaking ? 'Hablando...' : 'Escuchar Saludo del Operador'}</span>
            </button>
          </div>
        </div>

        {/* COLUMNA DERECHA: CONSOLA DE DIÁLOGO Y TRANSCRIPCIÓN */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Panel Principal de Transcripción / Entrada de Texto */}
          <div
            style={{
              background: 'linear-gradient(145deg, #0f1c2e 0%, #0a1320 100%)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: '24px',
              padding: '24px',
              boxShadow: '0 8px 30px rgba(0, 0, 0, 0.3)',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
            }}
          >
            {/* Barra superior de la consola de transcripción */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <MessageSquare size={18} color="#38bdf8" />
                <span style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 700, fontSize: '1rem', color: '#ffffff' }}>
                  Transcripción y Dictado en Tiempo Real
                </span>
                {isListening && (
                  <span
                    className="badge badge-gold animate-pulse"
                    style={{ fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    <Mic size={12} /> Escuchando...
                  </span>
                )}
              </div>

              {/* Acciones rápidas: Copiar y Limpiar */}
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={handleCopy}
                  title="Copiar texto al portapapeles"
                  style={{
                    padding: '6px 12px',
                    borderRadius: '8px',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#e2e8f0',
                    fontSize: '0.76rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    cursor: 'pointer',
                  }}
                >
                  {copied ? <Check size={14} color="#34d399" /> : <Copy size={14} />}
                  <span>{copied ? '¡Copiado!' : 'Copiar'}</span>
                </button>

                <button
                  onClick={clearTranscript}
                  title="Limpiar transcripción"
                  style={{
                    padding: '6px 12px',
                    borderRadius: '8px',
                    background: 'rgba(239, 68, 68, 0.08)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    color: '#f87171',
                    fontSize: '0.76rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    cursor: 'pointer',
                  }}
                >
                  <RotateCcw size={14} />
                  <span>Limpiar</span>
                </button>
              </div>
            </div>

            {/* Textarea de transcripción editable con texto intermedio */}
            <div style={{ position: 'relative' }}>
              <textarea
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                placeholder="Presiona el micrófono para comenzar a dictar o escribe directamente aquí en lenguaje parlamentario..."
                rows={6}
                style={{
                  width: '100%',
                  padding: '16px',
                  borderRadius: '16px',
                  background: '#070d17',
                  border: isListening ? '2px solid #00f0ff' : '1px solid rgba(56, 189, 248, 0.25)',
                  boxShadow: isListening ? '0 0 20px rgba(0, 240, 255, 0.25) inset' : 'none',
                  color: '#ffffff',
                  fontSize: '0.95rem',
                  lineHeight: 1.6,
                  fontFamily: "'Inter', sans-serif",
                  resize: 'vertical',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />

              {/* Indicador de texto en proceso (interim transcript) */}
              {interimTranscript && (
                <div
                  style={{
                    position: 'absolute',
                    bottom: '12px',
                    left: '16px',
                    right: '16px',
                    background: 'rgba(14, 165, 233, 0.15)',
                    border: '1px dashed #0ea5e9',
                    borderRadius: '8px',
                    padding: '6px 12px',
                    fontSize: '0.82rem',
                    color: '#67e8f9',
                    fontStyle: 'italic',
                  }}
                >
                  Capturando: {interimTranscript}
                </div>
              )}
            </div>

            {/* Consultas Parlamentarias Rápidas de Prueba */}
            <div>
              <span style={{ fontSize: '0.74rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>
                💡 Consultas Parlamentarias de Ejemplo (Clic para Cargar):
              </span>
              <div style={{ display: 'flex', gap: '8px', marginTop: '8px', flexWrap: 'wrap' }}>
                {SAMPLE_QUERIES.map((sq, idx) => {
                  const Icon = sq.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => handleLoadSample(sq.text)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: '10px',
                        background: 'rgba(255, 255, 255, 0.04)',
                        border: '1px solid rgba(255, 255, 255, 0.12)',
                        color: '#cbd5e1',
                        fontSize: '0.76rem',
                        fontWeight: 500,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(56, 189, 248, 0.15)';
                        e.currentTarget.style.borderColor = '#38bdf8';
                        e.currentTarget.style.color = '#ffffff';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.12)';
                        e.currentTarget.style.color = '#cbd5e1';
                      }}
                    >
                      <Icon size={14} color="#38bdf8" />
                      <span>{sq.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* ── 3. BARRA DE ACCIONES FLOTANTE / INFERIOR ── */}
          <div
            style={{
              background: 'linear-gradient(145deg, #091322 0%, #0d1b2e 100%)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: '20px',
              padding: '16px 24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '16px',
              boxShadow: '0 10px 30px rgba(0, 0, 0, 0.4)',
            }}
          >
            {/* Control Principal del Micrófono con Halo Pulsante */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <div style={{ position: 'relative' }}>
                {isListening && (
                  <div
                    style={{
                      position: 'absolute',
                      inset: '-6px',
                      borderRadius: '50%',
                      background: 'radial-gradient(circle, rgba(0, 240, 255, 0.6) 0%, transparent 70%)',
                      animation: 'ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite',
                    }}
                  />
                )}
                <button
                  onClick={isListening ? stopListening : startListening}
                  style={{
                    position: 'relative',
                    width: '56px',
                    height: '56px',
                    borderRadius: '50%',
                    background: isListening
                      ? 'linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)'
                      : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    border: '2px solid rgba(255, 255, 255, 0.3)',
                    color: '#ffffff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    boxShadow: isListening
                      ? '0 0 25px rgba(239, 68, 68, 0.65)'
                      : '0 0 25px rgba(16, 185, 129, 0.45)',
                    transition: 'all 0.25s ease',
                  }}
                >
                  {isListening ? <MicOff size={26} /> : <Mic size={26} />}
                </button>
              </div>

              <div>
                <div style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 700, fontSize: '1rem', color: '#ffffff' }}>
                  {isListening ? 'Grabando Audio...' : 'Dictar por Micrófono'}
                </div>
                <div style={{ fontSize: '0.78rem', color: isListening ? '#34d399' : '#94a3b8' }}>
                  {isListening ? 'Habla claramente en español latinoamericano' : 'Presiona el botón para iniciar STT nativo'}
                </div>
              </div>
            </div>

            {/* Controles de Síntesis de Voz (Reproducir / Pausa / Detener) */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {/* Botón Principal Speak */}
              <button
                onClick={() => (isSpeaking ? stopSpeaking() : handleSpeakText(transcript))}
                disabled={!transcript && !assistantResponse}
                style={{
                  padding: '11px 20px',
                  borderRadius: '12px',
                  background: isSpeaking
                    ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
                    : 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  color: '#ffffff',
                  fontFamily: "'Outfit', sans-serif",
                  fontWeight: 700,
                  fontSize: '0.88rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  cursor: !transcript && !assistantResponse ? 'not-allowed' : 'pointer',
                  opacity: !transcript && !assistantResponse ? 0.5 : 1,
                  boxShadow: '0 4px 15px rgba(14, 165, 233, 0.35)',
                  transition: 'all 0.2s ease',
                }}
              >
                {isSpeaking ? <Square size={17} /> : <Volume2 size={17} />}
                <span>{isSpeaking ? 'Detener Voz' : 'Leer Texto (TTS)'}</span>
              </button>

              {/* Botón Pausar / Reanudar si está hablando */}
              {isSpeaking && (
                <button
                  onClick={isPaused ? resumeSpeaking : pauseSpeaking}
                  style={{
                    padding: '11px 14px',
                    borderRadius: '12px',
                    background: 'rgba(255, 255, 255, 0.08)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    color: '#ffffff',
                    cursor: 'pointer',
                  }}
                >
                  {isPaused ? <Play size={16} /> : <Pause size={16} />}
                </button>
              )}

              {/* Enlace o Derivación a Mesa de Partes si hay navegación disponible */}
              {onNavigateTab && transcript && (
                <button
                  onClick={() => onNavigateTab('mesa')}
                  style={{
                    padding: '11px 18px',
                    borderRadius: '12px',
                    background: 'rgba(16, 185, 129, 0.15)',
                    border: '1px solid #10b981',
                    color: '#34d399',
                    fontFamily: "'Outfit', sans-serif",
                    fontWeight: 700,
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <Send size={15} />
                  <span>Mesa de Partes</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── CSS KEYFRAMES LOCALES PARA ANIMACIONES DE ESCÁNER Y PING ── */}
      <style>{`
        @keyframes scan-laser {
          0% { top: 0%; opacity: 0.8; }
          50% { top: 96%; opacity: 1; }
          100% { top: 0%; opacity: 0.8; }
        }
        @keyframes ping {
          75%, 100% {
            transform: scale(1.6);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
}
