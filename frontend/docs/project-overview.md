# 📐 Visión General del Proyecto — Frontend (SMA Congreso)

> **Pregunta clave que responde este documento:** *¿Cómo está organizado el proyecto de frontend actual y cuáles son sus componentes principales?*

---

## 🏛️ 1. Resumen Ejecutivo del Frontend

El frontend de **SMA Congreso** es una aplicación SPA (Single Page Application) desarrollada con **React 19** y **Vite**. Sirve como la interfaz de usuario moderna para la **Mesa de Partes Virtual**, la **Auditoría Constitucional y Normativa**, la **Bandeja de Expedientes**, la **Gestión Ciudadana** y el **Monitoreo de Eventos en Tiempo Real** del Sistema Multi-Agente de la Asamblea Legislativa Plurinacional de Bolivia.

La interfaz implementa un diseño institucional de alto impacto visual ("Tricolor" y "Dark Slate Mode"), con feedback reactivo, polling periódico de salud de los microservicios y animación interactiva del estado de los agentes de IA mediante avatares renderizados dinámicamente en CSS y tarjetas de estado.

---

## 📁 2. Estructura de Directorios del Frontend

```
frontend/
├── docs/                             # 📚 Documentación técnica del Frontend
│   ├── project-overview.md           # Visión general y arquitectura
│   ├── requirements.md               # Requerimientos funcionales y no funcionales
│   ├── acceptance-criteria.md        # Criterios de aceptación
│   ├── implementation-plan.md        # Plan de implementación y componentes
│   ├── test-scenarios.md             # Escenarios de prueba e integración
│   └── progress.md                   # Estado actual del desarrollo y backlog
├── public/                           # Assets estáticos de la aplicación
├── src/
│   ├── assets/                       # Recursos gráficos e imágenes
│   ├── components/                   # Componentes UI reutilizables
│   │   ├── Navbar.jsx                # Navegación global, branding e indicador de salud backend
│   │   ├── RobotCard.jsx             # Tarjeta interactiva del estado y justificación del agente
│   │   └── CssRobotAvatar.jsx        # Avatar robot animado renderizado por CSS
│   ├── pages/                        # Vistas principales (Tabs)
│   │   ├── MesaPartes.jsx            # Pipeline principal: Carga, Fase 1, Human-in-the-loop, Fase 2, PDF y Email
│   │   ├── Expedientes.jsx           # Listado de proyectos de ley, filtrado y modal de detalle integral
│   │   ├── ConsistenciaNormativa.jsx # Buscador semántico pgvector y catálogo del ordenamiento jurídico
│   │   ├── AtencionCiudadana.jsx     # Solicitudes de la ciudadanía y correspondencia oficial
│   │   └── Monitoreo.jsx             # Bus de eventos de agentes (MongoDB Atlas) e indicadores KPI
│   ├── services/
│   │   └── api.js                    # Cliente HTTP (fetch wrapper) para consumir FastAPI Backend
│   ├── App.jsx                       # Enrutador principal de tabs y estado global de salud
│   ├── App.css                       # Estilos complementarios
│   ├── index.css                     # Sistema de diseño global (Tokens CSS, variables, badges y animaciones)
│   └── main.jsx                      # Punto de entrada de React 19
├── index.html                        # Plantilla HTML con fuentes de Google Fonts (Outfit, Inter, JetBrains Mono)
├── package.json                      # Dependencias del proyecto (React 19, Lucide Icons, Vite)
└── vite.config.js                    # Configuración del empaquetador Vite
```

---

## 🛠️ 3. Stack Tecnológico del Frontend

| Categoria | Tecnología / Librería | Versión | Propósito |
|---|---|---|---|
| **Framework Base** | [React](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/package.json#L14) | 19.2.8 | Librería UI orientada a componentes declarativos y hooks de estado (`useState`, `useEffect`). |
| **Bundler & Dev Server** | [Vite](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/package.json#L22) | 8.2.2 | Compilación ultra-rápida en desarrollo mediante ES Modules nativos. |
| **Iconografía** | [lucide-react](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/package.json#L13) | 1.37.0 | Set de íconos vectoriales para dashboards y controles. |
| **Linter & Formatter** | [oxlint](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/package.json#L21) | 1.79.0 | Herramienta de análisis estático de código JavaScript ultra-rápida. |
| **Estilos CSS** | Vanilla CSS3 + Variables CSS | Nativo | Variables CSS globales (`--primary`, `--accent`, `--bg-dark`), animaciones `@keyframes`, glassmorphism y diseño responsivo sin Tailwind. |

---

## 🔌 4. Integración con el Backend REST

El cliente HTTP principal reside en [`frontend/src/services/api.js`](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/src/services/api.js) y consume el servidor FastAPI (`http://127.0.0.1:8085/api`).

### Mapeo de Vistas a Endpoints Backend

```mermaid
graph LR
    subgraph Frontend React
        Navbar[Navbar.jsx]
        Mesa[MesaPartes.jsx]
        Exp[Expedientes.jsx]
        Norm[ConsistenciaNormativa.jsx]
        Ciudad[AtencionCiudadana.jsx]
        Monit[Monitoreo.jsx]
    end

    subgraph Backend FastAPI
        E1[/api/health]
        E2[/api/pipeline/phase1]
        E3[/api/pipeline/agent_*]
        E4[/api/expedientes]
        E5[/api/normativa/search]
        E6[/api/ciudadana]
        E7[/api/messages]
    end

    Navbar --> E1
    Mesa --> E2
    Mesa --> E3
    Exp --> E4
    Norm --> E5
    Ciudad --> E6
    Monit --> E7
```

---

## 🎨 5. Sistema de Diseño e Identidad Visual

1. **Paleta Institucional Bolivia (Tricolor Accent)**:
   - Rojo Patrio: `#C0392B`
   - Amarillo Oro: `#F1C40F`
   - Verde Esmeralda: `#0D5C3A`
2. **Superficies en Modo Oscuro Slate**:
   - Fondo Principal: `#0f172a` (Slate 900)
   - Contenedores / Tarjetas: `#1e293b` (Slate 800)
   - Bordes Sutiles: `#334155` (Slate 700)
3. **Tipografía Modernizada**:
   - Titulares y Badges: `Outfit` (Google Fonts)
   - Cuerpo de Texto: `Inter`
   - Código / Tokens / IDs: `JetBrains Mono`

---

## 📍 6. Módulos y Navegación de Vistas

- **`MesaPartes`**: Orquestación interactiva del flujo en 2 fases con punto de control humano. Carga de archivos (PDF/Word/TXT), vista previa, clasificación inicial, confirmación de categoría, ejecución de agentes especializados, emisión de PDF institucional y notificación vía correo HTML a diputados/senadores.
- **`Expedientes`**: Repositorio centralizado de proyectos de ley. Permite buscar por número o palabras clave, filtrar por estado y abrir un modal modal detallado con la historia clínica del proyecto, bitácora de auditoría, dictamen constitucional y hallazgos de consistencia.
- **`ConsistenciaNormativa`**: Herramienta de consulta semántica del ordenamiento legal vigente. Permite probar consultas en lenguaje natural usando embeddings de NVIDIA y recuperar artículos mediante vector similarity en PostgreSQL Neon.
- **`AtencionCiudadana`**: Bandeja de solicitudes de la población y notas oficiales con resumen por IA y grado de confianza.
- **`Monitoreo`**: Consola de supervisión del bus de eventos de MongoDB Atlas (`agent_messages`), mostrando la actividad en tiempo real de los agentes del SMA.
