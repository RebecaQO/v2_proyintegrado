/**
 * Cliente de API REST para SMA Congreso (FastAPI Backend)
 */

const API_BASE_URL = 'http://127.0.0.1:8085/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      let errorDetail = `Error ${response.status}: ${response.statusText}`;
      try {
        const errorJson = await response.json();
        errorDetail = errorJson.detail || errorDetail;
      } catch (e) {}
      throw new Error(errorDetail);
    }

    return await response.json();
  } catch (err) {
    console.error(`[API Error] ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  getHealth: () => request('/health'),
  getDashboardStats: () => request('/dashboard/stats'),

  login: (correo_electronico, contrasena) =>
    request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ correo_electronico, contrasena }),
    }),

  register: (data) =>
    request('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  confirmarAprobacionBicameral: (data) =>
    request('/pipeline/confirmar_aprobacion_bicameral', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  uploadDocument: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/upload', { method: 'POST', body: formData });
  },

  runPhase1: (data) =>
    request('/pipeline/phase1', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  runAgentComision: (data) =>
    request('/pipeline/agent_comision', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  runAgentConstitucional: (data) =>
    request('/pipeline/agent_constitucional', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  runAgentConsistencia: (data) =>
    request('/pipeline/agent_consistencia', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  emitPdf: (data) =>
    request('/pipeline/emit_pdf', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  runAgentNotificador: (data) =>
    request('/pipeline/agent_notificador', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  // AGENTES CREWAI YAML — FLUJO LEGISLATIVO EXTENDIDO
  runAgentConstitucionFondo: (data) =>
    request('/pipeline/agent_constitucion_fondo', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  runAgentConcentrador: (data) =>
    request('/pipeline/agent_concentrador', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  runAgentSecretario: (data) =>
    request('/pipeline/agent_secretario', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  runAgentBicameral: (data) =>
    request('/pipeline/agent_bicameral', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  runAgentVetoPromulgacion: (data) =>
    request('/pipeline/agent_veto_promulgacion', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  runAgentPublicacion: (data) =>
    request('/pipeline/agent_publicacion', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  runPipelineCompleto: (data) =>
    request('/pipeline/pipeline_completo', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  getExpedientes: (limit = 50) => request(`/expedientes?limit=${limit}`),
  getExpedienteDetalle: (id) => request(`/expedientes/${id}`),
  getComisiones: () => request('/comisiones'),
  getMiembrosComision: (id_comision) => request(`/comisiones/${id_comision}/miembros`),
  addMiembroComision: (id_comision, data) =>
    request(`/comisiones/${id_comision}/miembros`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  removeMiembroComision: (id_miembro) =>
    request(`/comisiones/miembros/${id_miembro}`, { method: 'DELETE' }),
  getNormativa: (limit = 30) => request(`/normativa?limit=${limit}`),
  searchNormativa: (query, documento = null, umbral = 0.5, top_k = 8) =>
    request('/normativa/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query, documento, umbral, top_k }) }),
  getCiudadana: (limit = 50) => request(`/ciudadana?limit=${limit}`),
  getMessages: (limit = 50, sesion_id = null) => {
    const q = sesion_id ? `?limit=${limit}&sesion_id=${sesion_id}` : `?limit=${limit}`;
    return request(`/messages${q}`);
  },
};