# 🏛️ SMA Congreso — Frontend (React 19 + Vite)

Interfaz de usuario moderna e institucional para el **Sistema Multi-Agente de Auditoría y Trámite Legislativo** de la Asamblea Legislativa Plurinacional de Bolivia.

La aplicación opera como una SPA (Single Page Application) reactiva construida con **React 19** y **Vite**, implementando un sistema de diseño institucional de alto impacto visual (*Tricolor* y *Dark Slate Mode*) con tokens CSS nativos, micro-animaciones interactivas, iconografía con [Lucide React](https://lucide.dev/) y compatibilidad con comandos de voz multimodal (STT/TTS latino neutro).

---

## 📐 Catálogo de Vistas y Páginas Principales

La aplicación se organiza en **8 vistas operativas** accesibles según el rol del usuario:

| Vista | Módulo (`src/pages/`) | Rol Principal | Descripción Funcional |
|---|---|---|---|
| **Mesa de Partes Virtual** | [`MesaPartes.jsx`](src/pages/MesaPartes.jsx) | Operador / Legislador | Entrada principal de documentos legislativos. Soporta carga de archivos (PDF/DOCX/TXT), ejecución de la **Fase 1** (clasificación con Agente Distribuidor), **Punto de Control Humano 1** (confirmación de materia), ejecución paralela de la **Fase 2** (Comisión, Verificador CPE y Consistencia pgvector), línea de tiempo interactiva y descarga del Dictamen Oficial en PDF. |
| **Bandeja de Expedientes** | [`Expedientes.jsx`](src/pages/Expedientes.jsx) | Asambleístas / Personal | Registro histórico y seguimiento del ciclo de vida de los proyectos de ley. Permite filtrado por estado, cámara, fecha y comisión asignada, con modal forense detallado (`AllAgentsResultsModal`). |
| **Consistencia Normativa** | [`ConsistenciaNormativa.jsx`](src/pages/ConsistenciaNormativa.jsx) | Abogados / Auditores | Explorador del ordenamiento jurídico vigente. Permite búsquedas semánticas vectoriales con pgvector (Neon) contra la Constitución Política del Estado, Códigos y Leyes Sectoriales para detectar antinomias y derogaciones. |
| **Atención Ciudadana** | [`AtencionCiudadana.jsx`](src/pages/AtencionCiudadana.jsx) | Ciudadanía / Asesores | Ventanilla de interacción ciudadana que aloja el chatbot multifacético ([`AsistenteMultifacetaPanel`](src/components/AsistenteMultifacetaPanel.jsx)). Cuenta con selección semántica de facetas profesionales (Arquitectura, Salud, Educación, Trámites), botón para adjuntar casos y activar el peritaje del **Especialista Técnico**, y panel administrativo ([`GestionFacetasPanel`](src/components/GestionFacetasPanel.jsx)). |
| **Despacho Ejecutivo** | [`DespachoEjecutivo.jsx`](src/pages/DespachoEjecutivo.jsx) | Presidencia del Estado | Portal de seguimiento para el Órgano Ejecutivo (Fase 4). Evalúa minutas sancionadas por la ALP, monitorea el plazo perentorio de 10 días hábiles (Art. 164 CPE), genera el borrador del Decreto Supremo de Promulgación o estructura el pliego fundado de Veto. |
| **Asistente de Voz** | [`VoiceAssistantPage.jsx`](src/pages/VoiceAssistantPage.jsx) | Todos los roles | Interfaz multimodal por voz con reconocimiento de voz continuo (Speech-to-Text) y síntesis auditiva (Text-to-Speech) adaptada a español latinoamericano neutro (`es-419`) para consultar el estado del expediente o dictar instrucciones. |
| **Monitoreo de Agentes** | [`Monitoreo.jsx`](src/pages/Monitoreo.jsx) | Administrador / DevOps | Dashboard de telemetría en tiempo real conectado al bus de eventos de MongoDB Atlas (`agent_messages`). Presenta indicadores de latencia P50/P95, actividad por agente y registro de auditoría. |
| **Acceso y Roles** | [`Login.jsx`](src/pages/Login.jsx) | Control de Sesión | Selector de perfil y autenticación basada en roles institucionales (`Senador`, `Diputado`, `Operador_Mesa_Partes`, `Presidente_Estado`, `Ciudadano`). |

---

## 🤖 Componentes Multi-Agente Clave (`src/components/`)

* **[`HorizontalAgentFlow.jsx`](src/components/HorizontalAgentFlow.jsx):**  
  Línea de tiempo horizontal interactiva que mapea visualmente el avance del expediente a través de las etapas del pipeline, visualizando el estado de cada agente (inactivo, procesando, aprobado o con observaciones).
* **[`RevisionLegislativa.jsx`](src/components/RevisionLegislativa.jsx):**  
  Módulo de deliberación parlamentaria y control humano en la fase bicameral. Presenta el cotejo de enmiendas (diff textual), la verificación de quórum y mayorías nominales, y los controles para la Sanción de la Ley o devolución a comisiones.
* **[`LegalAgentCard.jsx`](src/components/LegalAgentCard.jsx) y [`RobotCard.jsx`](src/components/RobotCard.jsx):**  
  Tarjetas interactivas con avatares robot renderizados en CSS puro ([`CssRobotAvatar.jsx`](src/components/CssRobotAvatar.jsx)), mostrando la justificación legal, el modelo de IA utilizado (`openai/gpt-oss-20b`, `nemotron-3-nano-30b`, `nemotron-3-super-120b`), la latencia y el estado de la tarea.
* **[`AllAgentsResultsModal.jsx`](src/components/AllAgentsResultsModal.jsx):**  
  Modal integral que consolida los dictámenes de los agentes evaluadores (Constitucional, Consistencia Normativa, Especialista Técnico y Presupuesto) con descarga de informes PDF oficiales.
* **[`AgentVoiceModule.jsx`](src/components/AgentVoiceModule.jsx):**  
  Módulo flotante para captura y dictado de voz, con filtrado inteligente de comandos de voz para asambleístas y ciudadanos.

---

## 🔌 Integración con la API Backend

El cliente HTTP reside en [`src/services/api.js`](src/services/api.js) y se comunica con el servidor FastAPI:

* **URL Base en Desarrollo:** `http://127.0.0.1:8085/api`
* **Módulos de API integrados:**
  * `/pipeline`: Carga de expedientes, clasificación Fase 1, ejecución Fase 2, revisión bicameral y dictamen del Concentrador.
  * `/ciudadana`: Chat multifaceta, presentación de iniciativas ciudadanas y gestión de facetas profesionales.
  * `/normativas`: Búsqueda vectorial semántica y listado de leyes vigentes en pgvector.
  * `/monitoreo`: Telemetría de MongoDB Atlas y verificación de salud de microservicios (`GET /api/health`).

---

## 🚀 Instalación y Puesta en Marcha

### Requisitos Previos
* **Node.js 18+** y **npm**
* Servidor Backend FastAPI activo en el puerto `8085`

### 1. Instalar dependencias
```bash
cd frontend
npm install
```

### 2. Iniciar el servidor de desarrollo (Vite)
```bash
npm run dev
```
La aplicación web se iniciará automáticamente en: `http://localhost:5173`

### 3. Compilar para Producción
```bash
npm run build
```
Los archivos estáticos optimizados se generarán en la carpeta `dist/`.

---

## 🎨 Sistema de Diseño

La interfaz no utiliza librerías de estilos masivas como TailwindCSS o Bootstrap; está construida con **Vanilla CSS3 modular** centralizado en [`src/index.css`](src/index.css) mediante tokens de diseño:
* **Paleta Tricolor Institucional:** `--primary` (Rojo boliviano `#dc2626`), `--accent-yellow` (`#f59e0b`), `--accent-green` (`#10b981`).
* **Modo Oscuro Slate:** `--bg-dark` (`#0f172a`), `--surface-dark` (`#1e293b`), `--border-dark` (`#334155`).
* **Tipografías:** Google Fonts (`Outfit` para títulos y números, `Inter` para lectura legal, `JetBrains Mono` para identificadores y hashes SHA-256).
