# AGENTS.md — Guía Operativa de Trabajo para Agentes y Desarrolladores
> **Proyecto:** SMA Congreso — Sistema Multi-Agente para el Proceso Legislativo Plurinacional de Bolivia  
> **Arquitectura:** Prometheus PDT v2.0 (FastAPI + CrewAI + React 19/Vite + Neon pgvector + MongoDB Atlas)

---

## 1. Comandos Verificados del Proyecto

Todos los comandos listados a continuación han sido ejecutados y validados en el entorno de desarrollo local (Windows PowerShell / Python 3.12 / Node.js 24).

### 1.1 Backend (Python 3.12 + FastAPI + CrewAI)

| Acción | Comando | Descripción |
| :--- | :--- | :--- |
| **Activar venv** | `.\venv\Scripts\Activate.ps1` | Activa el entorno virtual de dependencias. |
| **Instalar deps** | `pip install -r requirements.txt` | Instala librerías core (FastAPI, CrewAI, Neon, Mongo, NVIDIA). |
| **Iniciar Dev** | `python server.py` | Inicia el backend FastAPI en `http://localhost:8085` con recarga activa. |
| **Test Arquitectura** | `python test_14_agentes.py` | Valida YAMLs y la instanciación de los 14 agentes + integradores. |
| **Test Constitucional**| `python test_cotejo_constitucional.py` | Valida las 10 pruebas unitarias del motor de cotejo literal CPE. |
| **Test Bicameral** | `python test_decision_bicameral.py` | Valida el motor de decisión bicameral y rutas constitucionales. |
| **Test RAG Facetas** | `python test_facetas_semanticas.py` | Valida la indexación y recuperación vectorial de 2048d. |
| **Test Escrutinio** | `python test_control_legislativo.py` | Valida quórum, conteo de votos nominales y firmas SHA-256. |
| **Carga Normativa** | `python cargar_normativa.py` | Ingesta corpus de leyes bolivianas hacia `sistema.articulos_normativos`. |
| **Carga Reglamentos**| `python cargar_reglamentos_profesionales.py` | Ingesta reglamentos profesionales hacia Neon. |

### 1.2 Frontend (React 19 + Vite + SWC)

| Acción | Comando | Descripción |
| :--- | :--- | :--- |
| **Instalar deps** | `cd frontend; npm install` | Instala dependencias de React 19 y plugins de Vite. |
| **Iniciar Dev** | `cd frontend; npm run dev` | Inicia Vite en `http://localhost:5173` (proxy automático a `:8085`). |
| **Linting** | `cd frontend; npm run lint` | Ejecuta `oxlint` sobre los componentes y páginas JSX. |
| **Compilar Build** | `cd frontend; npm run build` | Genera bundle de producción optimizado en `frontend/dist/`. |

---

## 2. Mapa de Arquitectura del Repositorio

Rutas reales verificadas en el árbol de directorios:

```text
v2_proyintegrado/
├── server.py                        # Servidor principal FastAPI: API REST, endpoints de pipeline y WebSockets
├── requirements.txt                 # Dependencias Python (FastAPI, CrewAI, pgvector, PyMongo, FPDF2)
├── sma_unified/                     # Paquete modular central del Sistema Multi-Agente
│   ├── agents/                      # Módulos ejecutables de los 14 agentes legislativos
│   │   ├── crew_orchestrator.py     # Orquestador del pipeline completo de 5 fases
│   │   ├── pipeline.py              # Pipeline transaccional con punto de control humano
│   │   ├── base_agent.py            # Clase base de conexión con CrewAI y agents.yaml
│   │   ├── distribuidor.py          # Agente 1: Mesa de Entradas y triaje
│   │   ├── verificador_constitucional.py # Agente 2: Control literal CPE (Filtro R1-R7)
│   │   ├── consistencia_normativa.py # Agente 3: RAG pgvector contra leyes vigentes
│   │   ├── especialista_tecnico.py  # Agente 4: Peritaje fáctico y matriz de riesgos
│   │   ├── presidencia_comision.py  # Agente 5: Orden del día y cronograma de comisión
│   │   ├── constitucion_fondo.py    # Agente 6: Hermenéutica y precedentes del TCP
│   │   ├── presupuesto.py           # Agente 7: Auditoría SAFCO 1178 y techos TGN
│   │   ├── concentrador.py          # Agente 8: Integración forense y PDF oficial
│   │   ├── secretario.py            # Agente 9: Quórum y actas de votación en grande/detalle
│   │   ├── bicameral.py             # Agente 10: Diff articulado y trámite Art. 163 CPE
│   │   ├── veto_promulgacion.py     # Agente 11: Asesoría ejecutiva y veto presidencial
│   │   ├── publicacion.py           # Agente 12: Publicación determinista en Gaceta Oficial
│   │   ├── difusion_ciudadana.py    # Agente 13: Traducción a Lenguaje Claro
│   │   ├── fiscalizacion.py         # Agente 14: Control posterior y alertas a Contraloría
│   │   ├── control_legislativo.py   # Motor lógico-matemático de quórum y hashing SHA-256
│   │   └── multiagente_ciudadano.py # Router semántico para ventanilla cívica
│   ├── config/                      # Especificación declarativa en YAML
│   │   ├── agents.yaml              # Roles, metas, restricciones anti-alucinación y salidas JSON
│   │   ├── tasks.yaml               # Definición formal de las tareas de cada agente
│   │   └── workflows.yaml           # Grafo de ejecución (DAG), paralelismo y Human Gates
│   └── db/                          # Capa de persistencia híbrida
│       ├── neon_postgres.py         # Conexión relacional y pgvector (esquema sistema.*)
│       ├── neon_client.py           # Pool de conexiones y queries estructuradas
│       ├── mongo_atlas.py           # Trazabilidad inter-agente y expedientes en Mongo
│       └── cosmos_client.py         # Cliente compatible Cosmos DB / MongoDB Atlas
├── frontend/                        # Aplicación SPA cliente (React 19 + Vite)
│   ├── src/pages/                   # Vistas principales (MesaPartes, RevisionLegislativa, etc.)
│   ├── src/components/              # Componentes de UI (HorizontalAgentFlow, etc.)
│   └── vite.config.js               # Proxy inverso a http://127.0.0.1:8085
├── docs/                            # Documentación y especificaciones operativas
└── informe/figurasPrometheus_v2/    # Especificaciones formales Prometheus PDT v2
```

---

## 3. Convenciones Detectadas del Proyecto

1. **Esquema de Base de Datos:**
   * Todas las tablas del sistema residen en el esquema `sistema` de PostgreSQL Neon (`sistema.proyecto_ley`, `sistema.observaciones_unificadas`, `sistema.bitacora_proceso`, `sistema.articulos_constitucion`, `sistema.articulos_normativos`). Jamás crear tablas en `public` sin justificación explícita.
   * La columna de estado en `sistema.proyecto_ley` se llama `estado_actual` y `estado_tramite` (NO `estado_proyecto`).
2. **Contratos de Salida JSON:**
   * Cada agente Python debe devolver un diccionario estructurado que contenga su clave raíz canónica (`dictamen_fondo`, `dictamen_tecnico`, `evaluacion_fiscal`, `expediente_consolidado`, `acta_debate`, `ciclo_bicameral`, `evaluacion_veto`, `publicacion_oficial`, `difusion_ciudadana`, `reporte_fiscalizacion`). Alterar estas claves rompe la compatibilidad con el frontend y los tests.
3. **Manejo de Errores y Fallbacks:**
   * El sistema utiliza `chat_completion_resiliente` con fallback en cascada a través del catálogo de NVIDIA NIM. Si un modelo no responde, cae al siguiente sin interrumpir el pipeline.
   * Si faltan datos en etapas legislativas (e.g., quórum o actas), se marca `PENDIENTE_DATOS` o `PENDIENTE_APROBACION_HUMANA`, nunca se inventan datos ni se aprueba en falso.
4. **Citas Literales Obligatorias:**
   * En auditoría constitucional, rige el principio: *"Sin cita literal verificable del proyecto y de la CPE, el hallazgo no existe"*. Se clasifica como `NEUTRAL` con `verificado: false`.

---

## 4. Seguridad y Gestión de Secretos

1. **Ubicación de Secretos:**
   * Todas las credenciales viven en el archivo local `.env` en la raíz (ignorado por Git en [.gitignore](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/.gitignore)).
   * Variables críticas: `NEON_DATABASE_URL`, `MONGO_URI`, `NVIDIA_API_KEY`, `SENDGRID_API_KEY`, `DRIVE_CLIENT_SECRET_FILE`.
2. **Prohibiciones Absolutas:**
   * **PROHIBIDO** commitear `.env`, archivos `credentials.json`, `token.pickle`, `*.pem` o `*.key`.
   * **PROHIBIDO** imprimir en logs de consola o bitácoras de MongoDB las contraseñas de base de datos o API keys.
   * Los documentos subidos en `uploaded_files/` no deben commitearse si contienen datos personales o sensibles.

---

## 5. Pautas de Pull Requests (PR)

1. **Tamaño Máximo:** Un PR no debe superar los **300 renglones de cambio neto** (diff), salvo migraciones masivas de datos o documentación de corpus.
2. **Requisitos Obligatorios para cada PR:**
   * Ejecución exitosa de `python test_14_agentes.py` (cero errores en validación de agentes).
   * Ejecución exitosa de `npm run lint` en frontend (cero errores de linting).
   * Referencia explícita en la descripción a la tarea o especificación en `docs/specs/`.
3. **Nomenclatura de Ramas y Commits:**
   * Ramas: `feature/<nombre-tarea>`, `fix/<bug-reportado>`, `docs/<seccion>`.
   * Commits convencionales: `feat(agentes): ...`, `fix(secretario): ...`, `docs(specs): ...`, `refactor(prompts): ...`.
