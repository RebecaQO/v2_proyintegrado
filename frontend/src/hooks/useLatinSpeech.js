/**
 * Hook personalizado para interacción por voz en Español Latino / Neutro (STT & TTS)
 * ====================================================================================
 * Proporciona:
 *  1. Reconocimiento de voz (Speech-to-Text) en español latinoamericano ('es-419' / 'es-MX').
 *  2. Síntesis de voz (Text-to-Speech) con filtrado estricto anti-acento peninsular (excluye 'es-ES').
 *  3. Priorización y selección de variantes latinoamericanas (es-419, es-MX, es-CO, es-AR, etc.).
 *  4. Gestión de estados (isListening, isSpeaking, isPaused, transcript, voices, selectedVoice).
 */

import { useState, useEffect, useRef, useCallback } from 'react';

// Variantes latinoamericanas reconocidas con sus etiquetas de visualización
const LATIN_REGIONS = {
  'es-419': { name: 'Español Latinoamericano (Neutral)', flag: '🌎', priority: 1 },
  'es-mx': { name: 'Español (México - Neutro)', flag: '🇲🇽', priority: 2 },
  'es-us': { name: 'Español (Latinoamérica / EE.UU.)', flag: '🇺🇸', priority: 3 },
  'es-co': { name: 'Español (Colombia)', flag: '🇨🇴', priority: 4 },
  'es-ar': { name: 'Español (Argentina)', flag: '🇦🇷', priority: 5 },
  'es-cl': { name: 'Español (Chile)', flag: '🇨🇱', priority: 6 },
  'es-pe': { name: 'Español (Perú)', flag: '🇵🇪', priority: 7 },
  'es-bo': { name: 'Español (Bolivia)', flag: '🇧🇴', priority: 8 },
  'es-ec': { name: 'Español (Ecuador)', flag: '🇪🇨', priority: 9 },
  'es-ve': { name: 'Español (Venezuela)', flag: '🇻🇪', priority: 10 },
  'es-uy': { name: 'Español (Uruguay)', flag: '🇺🇾', priority: 11 },
  'es-cr': { name: 'Español (Costa Rica)', flag: '🇨🇷', priority: 12 },
  'es-gt': { name: 'Español (Guatemala)', flag: '🇬🇹', priority: 13 },
};

export function useLatinSpeech() {
  // Estados de Síntesis de Voz (TTS)
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [rate, setRate] = useState(1.0); // Velocidad (0.8x a 1.4x)
  const [pitch, setPitch] = useState(1.0); // Tono (0.8 a 1.2)

  // Estados de Reconocimiento de Voz (STT)
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [recognitionStatus, setRecognitionStatus] = useState('idle'); // 'idle' | 'listening' | 'processing' | 'ready'
  const [error, setError] = useState(null);

  // Soporte de navegador
  const [isSTTSupported, setIsSTTSupported] = useState(false);
  const [isTTSSupported, setIsTTSSupported] = useState(false);

  // Referencias a instancias nativas
  const recognitionRef = useRef(null);
  const utteranceRef = useRef(null);
  const finalTranscriptAccumulator = useRef('');

  // ──────────────────────────────────────────────────────────────────────────
  // 1. CARGA Y FILTRADO ESTRICTO DE VOCES EN ESPAÑOL LATINO / NEUTRO
  // ──────────────────────────────────────────────────────────────────────────
  const filterAndSortLatinVoices = useCallback((availableVoices) => {
    if (!availableVoices || availableVoices.length === 0) return [];

    // Filtro estricto anti-acento peninsular
    // Descartamos expresamente es-ES y variantes con denominaciones de España / Castilian
    const isPeninsular = (voice) => {
      const langLower = (voice.lang || '').toLowerCase();
      const nameLower = (voice.name || '').toLowerCase();

      return (
        langLower === 'es-es' ||
        langLower.startsWith('es-es') ||
        langLower.startsWith('es_es') ||
        nameLower.includes('spain') ||
        nameLower.includes('españa') ||
        nameLower.includes('castilian') ||
        nameLower.includes('peninsular')
      );
    };

    // Filtrar sólo voces en español que NO sean peninsulares
    let latinVoices = availableVoices.filter((voice) => {
      const langLower = (voice.lang || '').toLowerCase();
      const isSpanish = langLower.startsWith('es') || langLower.startsWith('es_');
      return isSpanish && !isPeninsular(voice);
    });

    // Asignar metadatos y ordenar por prioridad geográfica (Neutro / México / Colombia, etc.)
    const scoredVoices = latinVoices.map((voice) => {
      const langLower = (voice.lang || '').toLowerCase().replace('_', '-');
      const region = LATIN_REGIONS[langLower] || {
        name: `Español (${voice.lang || 'Latinoamérica'})`,
        flag: '🌎',
        priority: 99,
      };

      // Si el nombre contiene 'Mexico', 'Sabina', 'Paulina', 'Jorge', darle alta relevancia
      let extraBoost = 0;
      const nameLower = voice.name.toLowerCase();
      if (nameLower.includes('mexic') || langLower === 'es-mx') extraBoost -= 2;
      if (langLower === 'es-419' || nameLower.includes('latin') || nameLower.includes('neural')) extraBoost -= 3;

      return {
        voice,
        id: `${voice.name}-${voice.lang}`,
        name: voice.name,
        lang: voice.lang,
        label: `${region.flag} ${voice.name} (${region.name.replace('Español ', '')})`,
        regionInfo: region,
        score: region.priority + extraBoost,
      };
    });

    // Ordenar de menor score (más prioritario) a mayor
    scoredVoices.sort((a, b) => a.score - b.score);

    // Fallback de resiliencia: si el cliente no tiene voces latinas identificadas,
    // utilizar cualquier voz en español disponible para no romper la interfaz
    if (scoredVoices.length === 0) {
      const allSpanish = availableVoices.filter((v) => (v.lang || '').toLowerCase().startsWith('es'));
      if (allSpanish.length > 0) {
        return allSpanish.map((v) => ({
          voice: v,
          id: `${v.name}-${v.lang}`,
          name: v.name,
          lang: v.lang,
          label: `🌐 ${v.name} (${v.lang}) [Genérico]`,
          regionInfo: { name: 'Español Genérico', flag: '🌐', priority: 100 },
          score: 100,
        }));
      }
    }

    return scoredVoices;
  }, []);

  // Cargar voces del sistema
  useEffect(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setIsTTSSupported(false);
      return;
    }

    setIsTTSSupported(true);

    const updateVoices = () => {
      try {
        const rawVoices = window.speechSynthesis.getVoices();
        const filtered = filterAndSortLatinVoices(rawVoices);
        setVoices(filtered);

        // Si no hay voz seleccionada o la actual ya no está, asignar la más prioritaria (es-MX o es-419)
        if (filtered.length > 0) {
          setSelectedVoice((prev) => {
            if (!prev) return filtered[0];
            const stillExists = filtered.find((v) => v.id === prev.id);
            return stillExists || filtered[0];
          });
        }
      } catch (err) {
        console.warn('[useLatinSpeech] Error al cargar voces:', err);
      }
    };

    updateVoices();

    // Algunos navegadores cargan las voces asíncronamente
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }

    return () => {
      if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = null;
      }
    };
  }, [filterAndSortLatinVoices]);

  // ──────────────────────────────────────────────────────────────────────────
  // 2. CONFIGURACIÓN DEL RECONOCIMIENTO DE VOZ (STT NATIVO)
  // ──────────────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSTTSupported(false);
      return;
    }

    setIsSTTSupported(true);

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      // Estricto español latino / neutro
      recognition.lang = 'es-419'; // Si el motor no lo soporta, fallback a 'es-MX'
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        setIsListening(true);
        setRecognitionStatus('listening');
        setError(null);
      };

      recognition.onresult = (event) => {
        let interim = '';
        let currentFinal = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const result = event.results[i];
          if (result.isFinal) {
            currentFinal += result[0].transcript + ' ';
          } else {
            interim += result[0].transcript;
          }
        }

        if (currentFinal) {
          finalTranscriptAccumulator.current += currentFinal;
          setTranscript(finalTranscriptAccumulator.current.trim());
          setRecognitionStatus('processing');
        }

        setInterimTranscript(interim);
      };

      recognition.onerror = (event) => {
        console.warn('[useLatinSpeech] Error STT:', event.error);
        if (event.error === 'no-speech') {
          // No es un error crítico, sólo silencio
          return;
        }

        let msg = 'Error en el reconocimiento de voz.';
        if (event.error === 'not-allowed') {
          msg = 'Permiso de micrófono denegado. Permite el acceso al micrófono en el navegador.';
        } else if (event.error === 'network') {
          msg = 'Error de red en el servicio de reconocimiento de voz.';
        } else if (event.error === 'audio-capture') {
          msg = 'No se detectó ningún micrófono conectado o en funcionamiento.';
        }

        setError(msg);
        setIsListening(false);
        setRecognitionStatus('idle');
      };

      recognition.onend = () => {
        setIsListening(false);
        setInterimTranscript('');
        setRecognitionStatus('ready');
      };

      recognitionRef.current = recognition;
    } catch (err) {
      console.error('[useLatinSpeech] Error inicializando SpeechRecognition:', err);
      setIsSTTSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {}
      }
    };
  }, []);

  // ──────────────────────────────────────────────────────────────────────────
  // 3. MÉTODOS DE CONTROL STT (MICRÓFONO)
  // ──────────────────────────────────────────────────────────────────────────
  const startListening = useCallback(() => {
    if (!recognitionRef.current) {
      setError('El reconocimiento de voz no está soportado en este navegador (se recomienda Chrome o Edge).');
      return;
    }

    setError(null);
    try {
      // Detener cualquier síntesis activa para que no interfiera con el micrófono
      if (window.speechSynthesis && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
        setIsSpeaking(false);
        setIsPaused(false);
      }

      recognitionRef.current.start();
    } catch (err) {
      // Si ya estaba iniciado, reiniciar
      console.warn('[useLatinSpeech] startListening warn:', err);
      try {
        recognitionRef.current.stop();
        setTimeout(() => {
          recognitionRef.current?.start();
        }, 150);
      } catch (e) {}
    }
  }, []);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      try {
        recognitionRef.current.stop();
      } catch (err) {
        console.warn('[useLatinSpeech] stopListening error:', err);
      }
    }
    setIsListening(false);
    setRecognitionStatus('ready');
  }, [isListening]);

  const clearTranscript = useCallback(() => {
    finalTranscriptAccumulator.current = '';
    setTranscript('');
    setInterimTranscript('');
    setError(null);
    setRecognitionStatus('idle');
  }, []);

  // ──────────────────────────────────────────────────────────────────────────
  // 4. MÉTODOS DE CONTROL TTS (SÍNTESIS DE VOZ)
  // ──────────────────────────────────────────────────────────────────────────
  const speak = useCallback(
    (textToSpeak, customOptions = {}) => {
      if (typeof window === 'undefined' || !window.speechSynthesis) {
        setError('La síntesis de voz no está disponible en este navegador.');
        return;
      }

      const text = (textToSpeak || transcript || '').trim();
      if (!text) {
        setError('No hay texto para reproducir. Dicta o escribe un mensaje primero.');
        return;
      }

      // Detener cualquier locución previa
      window.speechSynthesis.cancel();

      // Si el micrófono está activo, detenerlo para evitar feedback de audio
      if (isListening) {
        stopListening();
      }

      try {
        const utterance = new SpeechSynthesisUtterance(text);
        utteranceRef.current = utterance;

        // Asignar voz seleccionada o la primera latina disponible
        const activeVoice = customOptions.voice || selectedVoice?.voice;
        if (activeVoice) {
          utterance.voice = activeVoice;
          utterance.lang = activeVoice.lang || 'es-419';
        } else {
          utterance.lang = 'es-419';
        }

        // Parámetros de velocidad y tono
        utterance.rate = Math.max(0.8, Math.min(1.4, customOptions.rate ?? rate));
        utterance.pitch = Math.max(0.8, Math.min(1.2, customOptions.pitch ?? pitch));

        utterance.onstart = () => {
          setIsSpeaking(true);
          setIsPaused(false);
          setError(null);
        };

        utterance.onend = () => {
          setIsSpeaking(false);
          setIsPaused(false);
        };

        utterance.onerror = (e) => {
          console.warn('[useLatinSpeech] Error en síntesis de voz:', e);
          setIsSpeaking(false);
          setIsPaused(false);
        };

        utterance.onpause = () => setIsPaused(true);
        utterance.onresume = () => setIsPaused(false);

        window.speechSynthesis.speak(utterance);
      } catch (err) {
        console.error('[useLatinSpeech] Error al ejecutar speak:', err);
        setError('Ocurrió un error al reproducir la voz.');
        setIsSpeaking(false);
      }
    },
    [transcript, selectedVoice, rate, pitch, isListening, stopListening]
  );

  const pauseSpeaking = useCallback(() => {
    if (window.speechSynthesis && isSpeaking && !isPaused) {
      window.speechSynthesis.pause();
      setIsPaused(true);
    }
  }, [isSpeaking, isPaused]);

  const resumeSpeaking = useCallback(() => {
    if (window.speechSynthesis && isPaused) {
      window.speechSynthesis.resume();
      setIsPaused(false);
    }
  }, [isPaused]);

  const stopSpeaking = useCallback(() => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      setIsPaused(false);
    }
  }, []);

  return {
    // Estados STT
    isListening,
    transcript,
    setTranscript,
    interimTranscript,
    recognitionStatus,
    startListening,
    stopListening,
    clearTranscript,

    // Estados TTS
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

    // Soporte y diagnósticos
    isSTTSupported,
    isTTSSupported,
    error,
    setError,
  };
}

export default useLatinSpeech;
