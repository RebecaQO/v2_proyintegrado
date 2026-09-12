# 📊 Estado de Avance y Roadmap — Frontend (SMA Congreso)

> **Pregunta clave que responde este documento:** *¿Dónde estamos actualmente en el desarrollo del Frontend y qué sigue en el plan de trabajo?*

---

## 🚦 1. Estado Actual del Desarrollo (Snapshot)

- **Estado General**: **Fase 3 Completada / En Fase de Pulido y Optimización**
- **Versión de la SPA**: `2.0.0`
- **Servidor Dev**: Funcionando en `http://localhost:5173` (Vite)
- **Integración Backend**: Operativa contra FastAPI en `http://127.0.0.1:8085/api`

---

## 📈 2. Matriz de Cobertura de Funcionalidades del Frontend

| Módulo / Componente | Sub-funcionalidad | Estado | Notas |
|---|---|---|---|
| **`Navbar.jsx`** | Navegación por Pestañas | 🟢 100% | Cambio dinámico de pestañas activo. |
| | Polling de Salud (`/api/health`) | 🟢 100% | Polling automático a 15s con estado de BDs e IA. |
| **`MesaPartes.jsx`** | Extracción de Texto Multiformato | 🟢 100% | Soporta PDF, DOCX, ODT, RTF y TXT. |
| | Fase 1: Agente Distribuidor | 🟢 100% | Invocación e integración con `RobotCard.jsx`. |
| | Punto de Control Humano | 🟢 100% | Pausa activa, confirmación y edición de categoría. |
| | Fase 2: Agentes de Auditoría | 🟢 100% | Asignación de comisión, CPE 2009 y consistencia pgvector. |
| | Emisión de Dictamen PDF | 🟢 100% | Descarga e informe institucional tricolor. |
| | Agente Notificador Correo | 🟢 100% | Despacho de correos HTML a la comisión legislativa. |
| **`Expedientes.jsx`** | Tabla / Cuadrícula de Proyectos | 🟢 100% | Búsqueda rápida, badges de estado y ordenamiento. |
| | Modal de Auditoría Integral | 🟢 100% | Pestañas con la historia del proyecto y bitácora. |
| **`ConsistenciaNormativa.jsx`** | Buscador Semántico Vectorial | 🟢 100% | Consulta por embeddings y filtrado por jerarquía. |
| | Catálogo de Leyes | 🟢 100% | Muestra estadísticas y normas cargadas. |
| **`AtencionCiudadana.jsx`** | Solicitudes y Correspondencia | 🟢 100% | Bandeja de entrada con resumen de IA y confianza. |
| **`Monitoreo.jsx`** | Consola Bus de Mensajes | 🟢 100% | Lectura de eventos MongoDB Atlas (`agent_messages`). |

---

## 🎯 3. Logros Recientes

1. **Diseño Visual de Alto Impacto (Dark Slate + Tricolor)**:
   Se implementó una experiencia de usuario moderna sin necesidad de librerías externas pesadas como Tailwind, logrando una carga ultrarrápida y animaciones fluidas para los robots avatares en CSS nativo.
2. **Resiliencia en Polling de Salud**:
   Se incorporó el control periódico del estado del backend en [`App.jsx`](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/src/App.jsx), permitiendo al operador conocer en todo momento si las bases de datos (Neon / MongoDB) o el servicio de IA (NVIDIA NIM) experimentan interrupciones.
3. **Modal de Expediente con Trazabilidad Completa**:
   La vista de [`Expedientes.jsx`](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/src/pages/Expedientes.jsx) permite inspeccionar la bitácora de auditoría paso por paso, con duraciones en segundos y niveles de confianza devueltos por el backend.

---

## 🔮 4. Próximos Pasos y Backlog (Roadmap)

### 🚀 Corto Plazo (Sprint Actual)
- [ ] **Soporte PWA / Modo Offline Ligero**: Permitir la consulta en caché de la lista de expedientes previamente cargados cuando la red caiga.
- [ ] **Exportación Directa de Tablas a Excel / CSV**: Añadir un botón en *Expedientes* y *Consistencia Normativa* para descargar los listados filtrados.
- [ ] **Mejora del Visualizador de PDF**: Integrar un visor emergente de PDF dentro del mismo modal de expedientes para leer el dictamen sin salir de la app.

### 🔭 Mediano Plazo
- [ ] **Gráficas Analíticas e Indicadores KPI**: Agregar gráficos interactivos (vía Recharts o Chart.js) en el dashboard para mostrar el volumen de leyes aprobadas vs observadas por mes.
- [ ] **Notificaciones Web (Push / In-App)**: Alertas sonoras o visuales tipo *Toast* cuando un agente termine una tarea larga en segundo plano.
