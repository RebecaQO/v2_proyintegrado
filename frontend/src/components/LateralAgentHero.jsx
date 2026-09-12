/**
 * LateralAgentHero — Banner lateral nítido
 * Muestra la imagen completa del banner de manera nítida,
 * sin recuadros ni texto superpuesto, solamente la imagen institucional.
 */
import React, { useState } from 'react';

// Mapeo de banners (imagen nítida de alta resolución desde /robots/banner/)
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

// Colores de acento institucional para el marco según el agente activo
const AGENT_ACCENT = {
  distribuidor:       '#00B4D8',
  comision:           '#38BDF8',
  constitucional:     '#8AC926',
  consistencia:       '#F4A261',
  emisor:             '#A78BFA',
  notificador:        '#38BDF8',
  constitucion_fondo: '#8AC926',
  concentrador_crew:  '#00B4D8',
  secretario:         '#F4A261',
  bicameral:          '#38BDF8',
  veto_promulgacion:  '#E76F51',
  publicacion:        '#8AC926',
};

export default function LateralAgentHero({
  agent,
  isProcessing = false,
  isCompleted = false,
}) {
  if (!agent) return null;

  const [imgError, setImgError] = useState(false);
  const bannerUrl = AGENT_BANNER_MAP[agent.id] || '/robots/banner/disribuidor.png';
  const accent = AGENT_ACCENT[agent.id] || '#00B4D8';

  return (
    <div style={{
      position: 'relative',
      width: '100%',
      height: '100%',
      minHeight: '540px',
      borderRadius: '20px',
      overflow: 'hidden',
      border: isProcessing ? `2px solid ${accent}` : `1.5px solid ${accent}44`,
      boxShadow: isProcessing
        ? `0 0 28px ${accent}66, 0 12px 36px rgba(0,0,0,0.6)`
        : '0 10px 32px rgba(0,0,0,0.5)',
      background: '#0B2545',
      transition: 'all 0.4s ease',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      {!imgError ? (
        <img
          src={bannerUrl}
          alt={`Banner ${agent.name}`}
          onError={() => setImgError(true)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            objectPosition: 'center top',
            display: 'block',
            filter: 'none', // Completamente nítida, sin filtros oscurecedores ni viñetas
          }}
        />
      ) : (
        <div style={{
          width: '100%',
          height: '100%',
          minHeight: '540px',
          background: `linear-gradient(160deg, #0B2545 0%, #134074 50%, ${accent}33 100%)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: accent,
          fontWeight: 700,
          fontSize: '1rem'
        }}>
          {agent.name}
        </div>
      )}
    </div>
  );
}
