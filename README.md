# 🏛️ SMA Congreso — Sistema Multi-Agente de Auditado y Registro Legislativo

Sistema Multi-Agente inteligente diseñado para la **recepción, clasificación, auditoría constitucional y verificación de consistencia normativa** de proyectos de ley y documentos oficiales del Congreso de Bolivia.

La **ciudadanía es la puerta de entrada del sistema**: cualquier persona puede conversar con el *Agente de Interacción Ciudadana* (por texto o voz), consultar leyes y trámites, o **presentar un proyecto de ley o una propuesta** que entra al mismo circuito de auditoría que los demás expedientes.

El sistema combina modelos de lenguaje de última generación (**NVIDIA NIM API**), búsqueda vectorial semántica (**pgvector en PostgreSQL Neon**), un bus de mensajería asíncrono (**MongoDB Atlas**), y una interfaz moderna en **React + Vite**.

---

## 📐 Arquitectura del Sistema

El flujo **comienza en la ciudadanía**. El primer agente que interviene es el **Agente de Interacción Ciudadana** (Ventanilla multimodal): detecta la intención de la persona y, cuando esta presenta un **proyecto de ley o propuesta**, lo entrega al pipeline legislativo. Desde ahí cada expediente se procesa en dos fases secuenciales con un **punto de control humano de confirmación (Pausable/Confirmable)**:

```mermaid
flowchart TD
    CIU[👤 Ciudadanía\nTexto · Voz STT · PDF/DOCX] --> IC[💬 Agente Interacción Ciudadana\nVentanilla multimodal · Primer agente]
    IC --> INT{Intención detectada}

    INT -->|CONSULTA_INFORMACION| R1[Respuesta en lenguaje claro\nFacetas profesionales + Especialista Técnico]
    INT -->|ESTADO_TRAMITE| R2[Consulta del estado del expediente]
    INT -->|RECLAMO_QUEJA| F[Agente Atención Ciudadana\nPrioridad y área responsable]
    INT -->|PRESENTACION_INICIATIVA| P[📜 Proyecto de Ley o Propuesta Ciudadana\nPOST /api/ciudadana/presentaciones]

    A[📄 Entrada interna: PDF / Documento de Ley\nOperador] --> B
    P --> B[Fase 1: Agente Distribuidor]
    B --> C{🛑 Punto de Control Humano\nConfirmar o Ajustar Categoría}
    C -->|Aprobado| D[Fase 2: Ejecución de Agentes de Nivel 2]

    D -->|Proyectos de Ley| E[Agente Registro Legislativo]
    D -->|Peticiones / Reclamos| F
    D -->|Oficios / Cartas| G[Agente Gestión Correspondencia]

    E --> H[Agente Comisión Legislativa\nAsignación automática de comisión]
    E --> I[Agente Verificador Constitucional\nCotejo contra CPE 2009 con LLM]
    E --> J[Agente Consistencia Normativa\nEmbedding + pgvector + Parallel LLM]

    H --> K[(PostgreSQL Neon\nRegistro Relacional + pgvector)]
    I --> K
    J --> K

    H --> L[(MongoDB Atlas\nBus de Eventos SMA + Snapshots)]
    I --> L
    J --> L

    H --> M[Agente Concentrador\nExpediente consolidado + Dictamen PDF]
    I --> M
    J --> M

    M --> SEC[Agente Secretario de Cámara\nQuórum y Registro de Votaciones]
    SEC --> BIC[Agente Coordinación Bicameral\nCotejo de Minutas Art. 163 CPE]
    BIC --> CH2{🛑 Punto de Control Humano 2\nSanción Bicameral ALP en RevisionLegislativa}
    
    CH2 -->|Sancionado| VETO[Agente Veto y Promulgación\nEvaluación Presidencial / Despacho Ejecutivo]
    CH2 -->|Observado / Discrepancia| DEV[Devuelto a Comisión / Conferencia]
    DEV -.-> H

    VETO -->|Promulgar| GAC[Agente Publicación Oficial\nGaceta Oficial de Bolivia]
    VETO -->|Veto Total/Parcial| ALP[Devuelto a ALP con Pliego Fundado]
    ALP -.-> SEC

    GAC --> DIF[Agente Difusión Ciudadana\nLenguaje Claro y Guías Cívicas]
    GAC --> FISC[Agente Fiscalización\nControl Posterior y Decretos]

    DIF -.->|Comprensión y transparencia| CIU
    FISC -.->|Alertas ciudadanas| CIU
```

### 🧑‍🤝‍🧑 Ruta de la iniciativa ciudadana (proyecto de ley o propuesta)

1. **Ingreso:** la persona escribe o dicta (STT) su mensaje, o adjunta el texto/archivo, en la página **Interacción Ciudadana**.
2. **Detección de intención:** el `Agente_Interaccion_Ciudadana` distingue entre `CONSULTA_INFORMACION`, `ESTADO_TRAMITE`, `PRESENTACION_INICIATIVA` y `RECLAMO_QUEJA`. Si la confianza es baja (< 0.7) pide aclaración en lugar de asumir.
3. **Presentación:** ante una `PRESENTACION_INICIATIVA`, el ciudadano envía título, texto, tipo (`iniciativa`) y **cámara de destino** (`Diputados`, `Senadores` o `Ambas`). El servidor responde `202` y procesa en segundo plano.
4. **Fase 1:** el `Agente_Distribuidor` clasifica el documento y registra el expediente (`sistema.proyecto_ley`).
5. **Fase 2 automática:** se ejecutan Comisión Legislativa, Verificador Constitucional y Consistencia Normativa, y el **Concentrador** consolida todo en un expediente con dictamen.
6. **Seguimiento legislativo:** el caso queda en estado `PENDIENTE_SEGUIMIENTO_LEGISLADOR` (o `..._CON_OBSERVACIONES` si alguna auditoría quedó pendiente). A partir del Concentrador solo un **Diputado o Senador** puede continuar el trámite; el ciudadano consulta resultados y puede **reanudar** auditorías pendientes de su propio caso, pero no editar el trámite.

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/ciudadana/presentaciones` | Presentar proyecto de ley o propuesta (devuelve `202`) |
| POST | `/api/ciudadana/presentaciones/{id}/reanudar` | Reanudar auditorías pendientes sin repetir el Distribuidor (`403` si es otro ciudadano, `409` si ya está procesando) |
| GET | `/api/casos` | Listar casos compartidos, con resultados de dictamen y consistencia |

```json
{
  "titulo": "Iniciativa de prueba",
  "texto": "Artículo 1. Objeto de esta iniciativa ciudadana.",
  "tipo": "iniciativa",
  "camara_destino": "Senadores"
}
```

Los casos se guardan con control de versiones en la colección `casos_compartidos` de MongoDB Atlas (`sma_unified/db/casos_compartidos.py`).

### 🔁 Proceso legislativo extendido (5 fases)

Tras la auditoría, el orquestador CrewAI (`config/workflows.yaml`, `crew_orchestrator.py`) cubre el ciclo completo y **vuelve a la ciudadanía** en la última fase:

```mermaid
flowchart LR
    F1[Fase 1\nIngreso y Atención Ciudadana] --> F2[Fase 2\nComisión y Dictámenes]
    F2 --> F3[Fase 3\nPlenaria y Trámite Bicameral]
    F3 --> F4[Fase 4\nVeto / Promulgación y Publicación]
    F4 --> F5[Fase 5\nDifusión Ciudadana y Fiscalización]
    F5 -.->|Lenguaje claro| CIU[👤 Ciudadanía]
```

---

## 🤖 Catálogo de Agentes Inteligentes

### Ciudadanía — primer punto de contacto

| Agente | Nivel | Función Principal | Tecnología / Modelo |
|---|---|---|---|
| **`Agente_Interaccion_Ciudadana`** (`Interaccion_Ciudadana`) | Entrada · Fase 1 | **Primer agente del sistema.** Atiende por voz (STT) o texto, detecta la intención (`CONSULTA_INFORMACION`, `ESTADO_TRAMITE`, `PRESENTACION_INICIATIVA`, `RECLAMO_QUEJA`), responde en lenguaje accesible y **recibe el proyecto de ley o propuesta ciudadana para derivarlo al Distribuidor**. No da asesoría legal vinculante. | LLM NIM (`gpt-oss-20b`, temp 0.2) + `voz_agent` (STT/TTS) |
| **`Agente_Multifaceta_Ciudadano`** | Entrada · Chat | Asistente con facetas (Arquitectura y Urbanismo, Salud, Educación, Trámites Legislativos, etc.). El router elige la faceta de cada mensaje; sin estado. Con un caso adjunto puede activar el **Especialista Técnico**. | LLM NIM con fallback resiliente + pgvector (corpus profesional) |

### Auditoría y registro (Fases 1 y 2)

| Agente | Nivel | Función Principal | Tecnología / Modelo |
|---|---|---|---|
| **`Agente_Distribuidor`** | Nivel 1 | Recibe lo enviado por la ciudadanía o el operador y lo clasifica en: Registro Legislativo, Atención Ciudadana o Correspondencia. | LLM NVIDIA NIM |
| **`Agente_Comision_Legislativa`** | Nivel 2 | Determina la comisión parlamentaria competente (Justicia Plural, Economía, Derechos Humanos, etc.). | LLM NVIDIA NIM + Neon PostgreSQL |
| **`Agente_Verificador_Constitucional`** | Nivel 2 | Audita el proyecto contra la Constitución Política del Estado (CPE 2009), clasificando hallazgos en `A_FAVOR`, `EN_CONTRA` o `NEUTRAL`. | Embedding NVIDIA + Postgres Vector + LLM (Temp 0.0) |
| **`Agente_Consistencia_Normativa`** | Nivel 2 | Coteja el proyecto contra el corpus de leyes vigentes (Códigos, Leyes Sectoriales, Decretos) para detectar derogaciones tácitas y conflictos de especialidad. | Búsqueda Semántica pgvector + LLM Multihilo Paralelo |
| **`Agente_Atencion_Ciudadana`** | Nivel 2 | Clasifica solicitudes, peticiones y reclamos de la población asignando prioridad y área responsable. | LLM NIM |
| **`Agente_Gestion_Correspondencia`** | Nivel 2 | Procesa notas oficiales, cartas e informes identificando remitente, urgencia y unidad de destino. | LLM NIM |
| **`Agente_Especialista_Tecnico`** | Fase 2 | Evalúa factibilidad técnica y estándares de la materia; también responde al ciudadano sobre su caso adjunto. | LLM NIM |
| **`Agente_Presidencia_Comision`** | Fase 2 | Conduce el trabajo y planifica el debate en comisión. | LLM NIM |
| **`Agente_Constitucion_Fondo`** | Fase 2 | Análisis hermenéutico de fondo y precedentes del TCP. | LLM NIM + pgvector |
| **`Agente_Presupuesto`** | Fase 2 | Evalúa sostenibilidad presupuestaria y techos del TGN. | LLM NIM |
| **`Agente_Concentrador`** | Fase 2 | Integra los dictámenes, emite el expediente consolidado y el **Dictamen Oficial en PDF**. | LLM NIM + generación PDF |

### Plenaria, Ejecutivo y retorno a la ciudadanía (Fases 3 a 5)

| Agente | Nivel | Función Principal | Tecnología / Modelo |
|---|---|---|---|
| **`Agente_Secretario_Camara`** | Fase 3 | Registra el debate en la Cámara de Origen (quórum, oradores, votación en grande y en detalle). Control humano de aprobación. | LLM NIM + reglas deterministas |
| **`Agente_Bicameral`** | Fase 3 | Gestiona el trámite entre Cámara de Origen y Revisora, enmiendas y retorno a comisiones. | LLM NIM + reglas deterministas |
| **`Agente_Veto_Promulgacion`** | Fase 4 | Asesoría al Ejecutivo (Arts. 163-165 CPE) con decisión humana de promulgar u observar. | LLM NIM |
| **`Agente_Publicacion_Oficial`** | Fase 4 | Asigna número y vigencia, y publica en Gaceta Oficial (lógica determinista). | Reglas + PDF |
| **`Agente_Difusion_Ciudadana`** | Fase 5 | Explica la ley en **lenguaje claro** para devolverla a la ciudadanía. | LLM NIM |
| **`Agente_Fiscalizacion`** | Fase 5 | Monitorea decretos reglamentarios y ejecución presupuestaria. | LLM NIM + Neon |
| **`Agente_Notificador_Comision`** | Fase 5 | Envía notificaciones formales HTML/email a la comisión con el dictamen. | SMTP + HTML |

---

## 📐 Especificación Arquitectónica Formal (Metodología Prometheus PDT v2)

Para los agentes clave de la columna vertebral legislativa, el sistema cuenta con especificaciones de ingeniería formal bajo la metodología **Prometheus (AOSE / PDT v2)** ubicadas en [`informe/figurasPrometheus_v2/`](informe/figurasPrometheus_v2/). Cada agente dispone de su tríada de diagramas de alta resolución y su especificación técnica completa:

| Agente Parlamentario | Diagrama de Visión General (*Agent Overview*) | Descomposición de Capacidades (*Capability Overview*) | Diagrama de Proceso Secuencial (*Process Diagram*) | Especificación y Código Generador |
|---|---|---|---|---|
| **Agente Concentrador y Emisor** | [Ver Visión General](informe/figurasPrometheus_v2/concentrador/01_Agent_Overview_Concentrador.png) | [Síntesis Legislativa](informe/figurasPrometheus_v2/concentrador/02_Capability_Overview_Sintesis_Legislativa.png) | [Flujo 16 Pasos (CoT 120B / PDF)](informe/figurasPrometheus_v2/concentrador/03_Process_Diagram_Concentrador.png) | [Doc A.1-A.5](informe/figurasPrometheus_v2/concentrador/especificacion_agente_concentrador.txt) · [Script Python](informe/figurasPrometheus_v2/concentrador/generar_diagramas_concentrador_v2.py) |
| **Agente Secretario de Cámara** | [Ver Visión General](informe/figurasPrometheus_v2/secretario/01_Agent_Overview_Secretario.png) | [Control Votaciones](informe/figurasPrometheus_v2/secretario/02_Capability_Overview_Control_Votaciones.png) | [Flujo 16 Pasos (Quórum / Escrutinio)](informe/figurasPrometheus_v2/secretario/03_Process_Diagram_Secretario.png) | [Doc A.1-A.5](informe/figurasPrometheus_v2/secretario/especificacion_agente_secretario.txt) · [Script Python](informe/figurasPrometheus_v2/secretario/generar_diagramas_secretario_v2.py) |
| **Agente Trámite Bicameral** | [Ver Visión General](informe/figurasPrometheus_v2/bicameral/01_Agent_Overview_Bicameral.png) | [Conciliación Art. 163](informe/figurasPrometheus_v2/bicameral/02_Capability_Overview_Conciliacion_Bicameral.png) | [Flujo 16 Pasos (Diff / Freno Humano)](informe/figurasPrometheus_v2/bicameral/03_Process_Diagram_Bicameral.png) | [Doc A.1-A.5](informe/figurasPrometheus_v2/bicameral/especificacion_agente_bicameral.txt) · [Script Python](informe/figurasPrometheus_v2/bicameral/generar_diagramas_bicameral_v2.py) |
| **Agente Veto y Promulgación** | [Ver Visión General](informe/figurasPrometheus_v2/veto&promulgacion/01_Agent_Overview_Veto_Promulgacion.png) | [Evaluación Estratégica](informe/figurasPrometheus_v2/veto&promulgacion/02_Capability_Overview_Evaluacion_Estrategica.png) | [Flujo 16 Pasos (10 días / Mandatario)](informe/figurasPrometheus_v2/veto&promulgacion/03_Process_Diagram_Veto_Promulgacion.png) | [Doc A.1-A.5](informe/figurasPrometheus_v2/veto&promulgacion/especificacion_agente_veto_promulgacion.txt) · [Script Python](informe/figurasPrometheus_v2/veto&promulgacion/generar_diagramas_veto_promulgacion_v2.py) |


## ⚡ Rendimiento y Optimizaciones Clave

- **Auditoría Paralela Multihilo (`ThreadPoolExecutor`)**: La verificación normativa y constitucional clasifica los candidatos candidateados en paralelo (5 hilos concurrentes), reduciendo el tiempo de análisis de **4 minutos a 15 segundos (aceleración 10x)**.
- **Deduplicación Estricta de Normas**: Filtra artículos constitucionales o normativos por identificador único para prevenir duplicaciones en el reporte final.
- **Auto-Reparación de JSON Truncados (`_reparar_json_truncado`)**: Algoritmo heurístico que auto-cierra cadenas y llaves recortadas por la ventana de tokens, evitando caídas en fallbacks.
- **Análisis Objetivo Fáctico (Temperatura 0.0)**: Evaluaciones constitucionales estrictamente fundamentadas en el texto expreso normativo sin alucinaciones.

---

## 💾 Persistencia y Estructura de Base de Datos

### 1. Esquema de Tablas (PostgreSQL Neon)

Para mantener una arquitectura limpia y ordenada, la persistencia se divide organizativamente:

*   **Esquema `sistema` (Preferido para la lógica del sistema):**
    Aquí residen todas las tablas transaccionales y de estado del flujo de trabajo:
    *   `sistema.proyecto_ley`: Registro maestro de expedientes, proyectos y su estado.
    *   `sistema.observaciones_constitucionales`: Dictámenes y auditorías realizadas por los agentes.
    *   `sistema.bitacora_proceso`: Historial y auditoría de cada evento/paso del pipeline.
    *   `sistema.comision`: Catálogo referencial de comisiones.
    *   `sistema.enrutamiento_documento`: Tracking del flujo de mensajes inter-agente.

*   **Esquema `public` (Exclusivo para Corpus RAG):**
    Este esquema se reserva *exclusivamente* para el corpus de lectura vectorial estático.
    *   `public.articulos_constitucion`: Corpus constitucional vectorizado.
    *   `public.normativas`: Corpus de leyes y decretos vigentes con embeddings.

**🧹 Optimización y Reducción de Redundancia:**
Para evitar un diseño repetitivo, se recomienda **eliminar** tablas transitorias como `Clasificacion_Agente` y `Clasificacion_Comision`. La lógica de clasificación (qué agente lo procesa o qué comisión se le asigna) se registra directamente en los campos `id_comision_actual` de `sistema.proyecto_ley` y se audita mediante inserciones en `sistema.bitacora_proceso`. Centralizar la información en el proyecto/expediente reduce la duplicidad de datos.

### 2. Tablas Principales de la Lógica Backend
Toda la lógica de ruteo en el backend (`server.py`) y la toma de decisiones de los agentes trabaja de manera centralizada con:
1.  **`sistema.proyecto_ley`**: Centraliza el ciclo de vida del trámite.
2.  **`sistema.observaciones_constitucionales`**: Guarda las salidas estructuradas del LLM.
3.  **Vectores en `public`**: Para los procesos de Retrieval-Augmented Generation (RAG).

### 3. Bus de Eventos Auxiliar (MongoDB Atlas)
*   Bus de mensajes asíncronos y estados transitorios del SMA (`agent_messages`).
*   Trazabilidad de eventos rápidos de los agentes.

---

## 🤖 Orquestación Multi-Agente (CrewAI + YAML)

El sistema utiliza **CrewAI** como framework principal para la orquestación y delegación de tareas entre los distintos agentes de IA. Para lograr un código limpio, modular y fácilmente mantenible, el comportamiento de los agentes no está "hardcodeado", sino que se gestiona mediante archivos **YAML**:

*   **`config/agents.yaml`**: Define de manera declarativa el rol, el objetivo (goal) y el contexto base (backstory) de cada agente (ej. Distribuidor, Verificador, etc.).
*   **`config/tasks.yaml`**: Define las tareas específicas, la descripción de lo que debe hacer el LLM, los resultados esperados (expected_output) y qué agente las ejecutará.

Esta separación YAML/Python permite ajustar los "prompts" de los agentes y la estructura del flujo de trabajo directamente desde los archivos de configuración sin necesidad de modificar el código fuente del orquestador.

---

## 📁 Estructura del Proyecto

```
.
├── server.py                   # API Backend REST principal (FastAPI + Uvicorn)
├── cargar_normativa.py         # CLI para ingesta e indización de PDFs de leyes en pgvector
├── cargar_reglamentos_profesionales.py  # Ingesta del corpus de reglamentos profesionales (facetas)
├── aplicar_migracion_004.py    # Aplica la migración 004 (circuito bicameral / ejecutivo)
├── upload_server.py            # Servidor independiente de carga y procesamiento de documentos
├── test_*.py                   # Pruebas (conexiones, bicameral, cotejo CPE, facetas, presentación ciudadana, etc.)
├── requirements.txt            # Dependencias de Python
├── .env.example                # Plantilla de variables de entorno
├── migrations/                 # Esquemas SQL (001–004, incl. agentes ciudadanos)
├── frontend/                   # Aplicación Frontend React 19 + Vite
│   ├── src/
│   │   ├── components/         # UI (AsistenteMultifacetaPanel, GestionFacetasPanel, ...)
│   │   ├── main.jsx            # Punto de entrada React
│   │   └── index.css           # Estilos globales y tokens
│   └── package.json
└── sma_unified/                # Paquete principal del SMA
    ├── config.py               # Configuración central (.env, settings)
    ├── config/
    │   ├── agents.yaml         # Rol, objetivo y backstory de cada agente
    │   ├── tasks.yaml          # Tareas y salidas esperadas
    │   └── workflows.yaml      # Pipelines de 5 fases y filtro rápido
    ├── agents/
    │   ├── ── Ciudadanía (entrada) ──
    │   ├── ciudadana.py                 # Atención ciudadana (peticiones y reclamos)
    │   ├── multiagente_ciudadano.py     # Chat multifaceta con routing automático
    │   ├── facetas_semanticas.py        # Selección y análisis de facetas profesionales
    │   ├── especialista_chat.py         # Especialista Técnico sobre el caso adjunto
    │   ├── voz_agent.py                 # STT/TTS y comandos de voz por agente
    │   ├── ── Pipeline y auditoría ──
    │   ├── pipeline.py                  # Orquestador del pipeline en 2 fases
    │   ├── crew_orchestrator.py         # Orquestador CrewAI de las 5 fases
    │   ├── distribuidor.py              # Agente clasificador Nivel 1
    │   ├── comision.py                  # Asignación de comisiones
    │   ├── verificador_constitucional.py# Auditoría CPE 2009
    │   ├── cotejo_constitucional.py     # Cotejo conjunto de candidatos CPE
    │   ├── consistencia_normativa.py    # Consistencia con el ordenamiento vigente
    │   ├── tools_constitucional.py      # Herramientas LangChain de búsqueda y cotejo
    │   ├── concentrador.py              # Expediente consolidado + dictamen
    │   ├── emisor_resultados.py         # Dictamen PDF tricolor
    │   ├── ── Plenaria, Ejecutivo y difusión ──
    │   ├── secretario.py · bicameral.py · control_legislativo.py
    │   ├── veto_promulgacion.py · publicacion.py · gaceta_pdf_generator.py
    │   ├── difusion_ciudadana.py · fiscalizacion.py · notificador_comision.py
    │   └── llm_client.py                # Cliente resiliente de NVIDIA NIM + Parser JSON
    ├── db/
    │   ├── neon_postgres.py · neon_client.py  # Relacional y pgvector en Neon
    │   ├── mongo_atlas.py                     # Bus de eventos SMA y Snapshots
    │   └── casos_compartidos.py               # Casos ciudadanos versionados entre equipos
    └── utils/                   # Extracción de documentos, parser de normativa, Drive
```

---

## 🛠️ Requisitos Previos

- **Python 3.11+**
- **Node.js 18+** & npm
- Cuenta y API Key de **NVIDIA NIM**
- Base de datos **PostgreSQL Neon** (con extensión `vector` habilitada)
- Clúster en **MongoDB Atlas**

---

## 🚀 Instalación y Configuración

### 1. Clonar el repositorio y configurar el entorno Python

```bash
# Clonar el proyecto
git clone <URL_DEL_REPOSITORIO>
cd proy_integrado

# Crear y activar entorno virtual
python -m venv venv

# En Windows:
.\venv\Scripts\activate

# En Linux/macOS:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copia el archivo `.env.example` a `.env` y completa tus credenciales:

```bash
cp .env.example .env
```

Variables principales en `.env`:

```ini
# LLM & Embeddings (NVIDIA NIM)
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxx
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_MODEL_CREW=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
LLM_MODEL_NVIDIA=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
LLM_MODEL_CONSISTENCIA=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
NVIDIA_EMBED_MODEL=nvidia/nemotron-3-embed-1b
NVIDIA_EMBED_DIM=2048
# Modelos complementarios en ejecución:
# - openai/gpt-oss-20b (inferencia rápida ~2.0s y extracción JSON)
# - nvidia/nemotron-3-super-120b-a12b (razonamiento analítico profundo CoT en Concentrador)

# MongoDB Atlas
MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/sma_congreso
MONGO_DB=sma_congreso

# PostgreSQL Neon (con pgvector)
NEON_DATABASE_URL=postgresql://usuario:password@ep-host.neon.tech/neondb?sslmode=require
```

### 3. Instalar dependencias del Frontend

```bash
cd frontend
npm install
cd ..
```

---

## 📥 Ingesta del Corpus Normativo (Requisito para Consistencia Normativa)

Para poblar la base de datos de leyes vigentes contra las cuales se auditarán los proyectos:

```bash
# Cargar la Constitución Política del Estado
python cargar_normativa.py --pdf datos/cpe.pdf --nombre "Constitución Política del Estado" --tipo Constitucion --jerarquia 1

# Cargar un Código o Ley Sectorial
python cargar_normativa.py --pdf datos/codigo_penal.pdf --nombre "Código Penal Boliviano" --tipo Codigo --jerarquia 2
```

---

## 🖥️ Ejecución de la Aplicación

### 1. Verificar conexiones de servicios

```bash
python test_sma.py
```

### 2. Iniciar el Backend (FastAPI)

```bash
# Con el entorno virtual activado:
python -m uvicorn server:app --host 127.0.0.1 --port 8085 --reload

# O directamente sin activar:
.\venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8085 --reload
```
* API activa en: `http://127.0.0.1:8085`
* Documentación Swagger: `http://127.0.0.1:8085/docs`

### 3. Iniciar el Frontend (React + Vite)

En otra terminal:

```bash
cd frontend
npm run dev
```
* Aplicación web lista en: `http://localhost:5173`

---

## 🔄 Flujo de Auditoría Legislativa

0. **Interacción Ciudadana (primer paso):** la persona conversa con el `Agente_Interaccion_Ciudadana` y, si desea participar legislativamente, **presenta su proyecto de ley o propuesta**.
1. **Carga del Expediente:** el documento ingresa como texto o archivo (PDF/DOCX/Texto), ya sea desde la ciudadanía o desde la plataforma interna.
2. **Fase 1 (Clasificación):** El `Agente_Distribuidor` clasifica el documento y propone la ruta.
3. **Punto de Control Humano (🛑 Pause/Confirm):** El operador aprueba o corrige la clasificación sugerida.
4. **Fase 2 (Auditoría Paralela Nivel 2):**
   - Asignación de Comisión Parlamentaria.
   - Auditoría Constitucional contra la CPE 2009.
   - Análisis de Consistencia contra el corpus legal vigente.
5. **Emisión de Dictamen:** Generación automatizada de reportes con contradicciones, artículos respaldados, derogas tácitas y nivel de riesgo normativo.
6. **Seguimiento por la cámara de destino:** el caso pasa a un Diputado o Senador, y la ciudadanía recibe el resultado y, al final del ciclo, la explicación en lenguaje claro.

---


## Agente Multi-Faceta de Atención Ciudadana (routing automático de prompts)

> Forma parte de la capa de **Ciudadanía**, el primer eslabón del sistema (ver *Arquitectura*). Para presentar un proyecto de ley o propuesta, ver *Ruta de la iniciativa ciudadana*.

Módulo: `sma_unified/agents/multiagente_ciudadano.py` · Tabla: `sistema.agentes_ciudadanos`

Asistente ciudadano compuesto por varias **facetas** (sub-agentes), cada una con
su nombre, logo, `system_prompt` y un `trigger_description`. El ciudadano **no
elige** la faceta: cada mensaje se analiza con el LLM y se enruta solo a la que
mejor encaja. Es **sin estado**: no se guarda historial de chat.

Facetas sembradas al primer arranque (idempotente): Arquitectura y Urbanismo,
Salud, Educación y Trámites Legislativos.

### Integración con el resto del SMA

- **Base de datos**: reutiliza la conexión Neon del sistema (`NEON_DATABASE_URL`),
  no una `DATABASE_URL` aparte.
- **LLM**: usa `chat_completion_resiliente` (cascada de modelos NVIDIA NIM con
  fallback automático), no un modelo fijo que queda *end of life*.
- **Trazabilidad**: cada consulta se publica en MongoDB Atlas como mensaje
  inter-agente, igual que los demás agentes, y el agente se autoregistra en
  `sistema.agentes_registrados` (visible en `GET /api/agentes`).
- **No requiere variables de entorno ni dependencias nuevas.**

### Endpoints

| Método | Ruta                             | Descripción                                   |
|--------|----------------------------------|-----------------------------------------------|
| POST   | `/api/ciudadana/chat`            | Enviar consulta; la faceta se elige sola       |
| GET    | `/api/ciudadana/agentes`         | Listar facetas (`?solo_activos=true`)          |
| POST   | `/api/ciudadana/agentes`         | Crear faceta                                   |
| GET    | `/api/ciudadana/agentes/{id}`    | Ver una faceta                                 |
| PATCH  | `/api/ciudadana/agentes/{id}`    | Editar faceta                                  |
| DELETE | `/api/ciudadana/agentes/{id}`    | Eliminar faceta                                |

```bash
curl -X POST http://localhost:8085/api/ciudadana/chat \
  -H "Content-Type: application/json" \
  -d '{"mensaje": "¿Qué necesito para aprobar los planos de una ampliación?"}'
```

```json
{
  "success": true,
  "reply": "...",
  "agente_nombre": "Arquitectura y Urbanismo",
  "agente_logo": "🏗️",
  "routing_automatico": true,
  "modelo_usado": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
}
```

### Frontend

`frontend/src/components/AsistenteMultifacetaPanel.jsx`, montado en la página
**Atención Ciudadana**. Muestra las facetas disponibles como chips y, en cada
respuesta, qué faceta atendió, el modelo usado y la latencia.

Si el router no logra decidir o el modelo no responde, cae a la primera faceta
activa — el chat nunca falla por el routing.

### Especialista Técnico sobre un caso subido

En el panel del chat ciudadano se puede **adjuntar un caso** (PDF/DOCX/TXT). Al
hacerlo aparece el botón **«Usar Especialista Técnico»**: al activarlo se emite
una vez el dictamen pericial del documento (`POST /api/ciudadana/especialista/dictamen`,
módulo `sma_unified/agents/especialista_chat.py`, sobre el `AgenteEspecialistaTecnico`
ya existente) y, a partir de ahí, **cada mensaje del chatbot lo responde el
Especialista** sobre ese dictamen y el texto del caso, sin volver a peritar.

- Sin el toggle, el caso adjunto viaja igual como contexto y responde la faceta
  que elija el router (arquitectura, salud, educación, trámites).
- El dictamen viaja de ida y vuelta en el campo `dictamen`, así el chat sigue
  siendo sin estado en el servidor.
- Campos nuevos de `POST /api/ciudadana/chat`: `caso_texto`, `caso_nombre`,
  `usar_especialista`, `dictamen`.

### Crear facetas desde el frontend

`frontend/src/components/GestionFacetasPanel.jsx`, montado en **Atención
Ciudadana** solo para roles internos (`esRolInterno(currentUser.rol)` —
cualquier rol distinto de `Ciudadano`). Permite crear, editar, activar/desactivar
y eliminar facetas sin tocar código ni la base de datos a mano; usa los mismos
endpoints `GET/POST/PATCH/DELETE /api/ciudadana/agentes[/id]`.

Un ciudadano sin sesión interna solo ve el chat (`AsistenteMultifacetaPanel`),
nunca el panel de administración.

---

## 📄 Licencia

Desarrollado para el análisis y auditoría legislativa del Congreso. Reservados todos los derechos.