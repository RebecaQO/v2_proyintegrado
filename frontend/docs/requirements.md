# 📋 Requerimientos del Sistema — Frontend (SMA Congreso)

> **Pregunta clave que responde este documento:** *¿Qué debe hacer el proyecto en su capa de interfaz de usuario?*

---

## 🎯 1. Objetivo General del Frontend

El frontend debe proporcionar una interfaz web fluida, interactiva e intuitiva para los operadores de la **Mesa de Partes Virtual** de la Asamblea Legislativa Plurinacional de Bolivia. Debe permitir la gestión integral de documentos parlamentarios desde su ingreso digital hasta su notificación a las comisiones legislativas, ofreciendo visibilidad completa de las decisiones tomadas por el Sistema Multi-Agente (SMA).

---

## ⚙️ 2. Requerimientos Funcionales (RF)

### RF-01: Gestión de Navegación y Estado Global (Navbar & Health Status)
- **RF-01.1**: Proporcionar una barra de navegación fija ([`Navbar.jsx`](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/src/components/Navbar.jsx)) que permita alternar entre 5 módulos principales: *Mesa de Partes*, *Expedientes*, *Consistencia Normativa*, *Atención Ciudadana* y *Monitoreo*.
- **RF-01.2**: Ejecutar un polling automático cada 15 segundos hacia el endpoint `/api/health` para reflejar en tiempo real el estado operacional de las bases de datos (PostgreSQL Neon, MongoDB Atlas) y del servicio de IA (NVIDIA NIM).
- **RF-01.3**: Mostrar un indicador visual de salud con código de colores (Verde = Saludable, Amarillo = Degradado, Rojo/Gris = Offline).

---

### RF-02: Módulo Mesa de Partes Virtual (`MesaPartes.jsx`)
- **RF-02.1: Carga Multi-Formato de Documentos**:
  - Permitir el arrastre (*drag and drop*) o selección de archivos en formatos PDF, DOCX, ODT, RTF y TXT.
  - Permitir la alternancia a modo "Texto Directo" para escribir o pegar un proyecto de ley en un campo textarea.
  - Al subir un archivo, llamar al endpoint `/api/upload` y mostrar metadatos inmediatos: nombre, tamaño en bytes, conteo de palabras, cantidad de caracteres y vista previa del texto extraído.
- **RF-02.2: Ejecución de Fase 1 (Agente Distribuidor Nivel 1)**:
  - Disparar la clasificación inicial llamando a `/api/pipeline/phase1`.
  - Desplegar una tarjeta interactiva ([`RobotCard.jsx`](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/src/components/RobotCard.jsx)) para el **Agente Distribuidor**, indicando el modelo en uso (`nvidia/llama-3.1-nemotron-70b-instruct`) y la justificación de la clasificación realizada.
- **RF-02.3: Punto de Control Humano (Human-in-the-Loop)**:
  - Pausar automáticamente el flujo tras la Fase 1 y desplegar una caja de alerta de confirmación humana.
  - Permitir al usuario operador confirmar la categoría sugerida por la IA o modificarla mediante un selector (*Registro Legislativo*, *Atención Ciudadana*, *Correspondencia Oficial*).
  - Incluir un botón de alto (*Pausar/Ajustar*) antes de ejecutar las auditorías pesadas de Fase 2.
- **RF-02.4: Ejecución Secuencial/Modular de Fase 2**:
  - Proporcionar controles para ejecutar secuencialmente o en lote los agentes de auditoría:
    1. **Agente Comisión Legislativa**: Asigna automáticamente la comisión competente e identifica la directiva parlamentaria.
    2. **Agente Verificador Constitucional**: Audita el texto contra la CPE 2009 y clasifica los hallazgos en *A Favor*, *En Contra* o *Neutral*.
    3. **Agente Consistencia Normativa**: Ejecuta la búsqueda semántica pgvector en paralelo para detectar conflictos normativos o derogaciones tácitas.
- **RF-02.5: Generación de PDF y Notificación Oficial**:
  - Proporcionar un botón para llamar a `/api/pipeline/emit_pdf` y generar el dictamen técnico-jurídico institucional en PDF.
  - Ofrecer un panel final para enviar el informe vía correo electrónico a la comisión asignada y destinatarios adicionales (`/api/pipeline/agent_notificador`).

---

### RF-03: Módulo de Expedientes Legislativos (`Expedientes.jsx`)
- **RF-03.1**: Renderizar una tabla/cuadrícula con el catálogo histórico de proyectos de ley registrados en PostgreSQL Neon.
- **RF-03.2**: Permitir filtrado por texto dinámico (búsqueda por título, resumen, número de expediente o comisión).
- **RF-03.3**: Mostrar badges de estado de auditoría (Semáforo de Constitucionalidad: Conforme, Observado, Crítico).
- **RF-03.4: Modal de Detalle Integral**:
  - Al hacer clic en un expediente, abrir un panel emergente modal que consulte `/api/expedientes/{id_proyecto}`.
  - Mostrar pestañas de detalle: *Resumen de Proyecto*, *Bitácora de Auditoría*, *Dictamen Constitucional*, *Consistencia Normativa* y *Enrutamiento*.

---

### RF-04: Módulo de Consistencia Normativa (`ConsistenciaNormativa.jsx`)
- **RF-04.1**: Proporcionar una consola de prueba de búsqueda semántica en tiempo real (`/api/normativa/search`).
- **RF-04.2**: Permitir al usuario ingresar preguntas o fragmentos de leyes para recuperar los artículos legalmente más cercanos utilizando similitud coseno sobre vectores de 2048 dimensiones.
- **RF-04.3**: Desplegar estadísticas del corpus cargado (total de leyes, decretos, artículos indexados y análisis realizados).

---

### RF-05: Módulo de Atención Ciudadana (`AtencionCiudadana.jsx`)
- **RF-05.1**: Listar las peticiones ciudadanas, cartas y solicitudes registradas.
- **RF-05.2**: Mostrar el resumen generado por IA, el agente de destino asignado y el índice de confianza del modelo.

---

### RF-06: Módulo de Monitoreo de Eventos (`Monitoreo.jsx`)
- **RF-06.1**: Visualizar la secuencia cronológica de mensajes intercambiados en el bus asíncrono MongoDB Atlas (`agent_messages`).
- **RF-06.2**: Filtrar mensajes por `sesion_id` o por agente de origen/destino.
- **RF-06.3**: Mostrar KPIs consolidados (total de mensajes intercambiados, tiempo promedio de respuesta y estado de los agentes).

---

### RF-07: Módulo Asistente de Voz Parlamentario (`VoiceAssistantPage.jsx`)
- **RF-07.1: Reconocimiento de Voz Nativo (STT)**:
  - Utilizar Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`) configurado estrictamente en español latino (`es-419` / `es-MX`).
  - Mostrar transcripción continua y resultados intermedios (*interim transcript*) con feedback visual dinámico (onda/halo pulsante).
  - Permitir la edición manual y corrección del texto transcrito en un área `<textarea>` limpia.
- **RF-07.2: Síntesis de Voz (TTS) con Filtro Anti-Peninsular**:
  - Utilizar `window.speechSynthesis` excluyendo expresamente voces con código `es-ES` o modismos peninsulares.
  - Listar y priorizar variantes de español latinoamericano (`es-419`, `es-MX`, `es-US`, `es-CO`, `es-AR`, etc.).
  - Permitir ajuste de velocidad (`rate` de 0.8x a 1.4x) y tono (`pitch` de 0.8 a 1.2).
- **RF-07.3: Operadores Robóticos y Consultas Parlamentarias**:
  - Intercambiar operadores robóticos activos con sus correspondientes temas y saludos audibles.
  - Cargar consultas parlamentarias de ejemplo con un solo clic y derivar textos a la Mesa de Partes.

---

## 🔒 3. Requerimientos No Funcionales (RNF)

- **RNF-01: Rendimiento y Responsividad**:
  - Tiempo de renderizado inicial de la SPA menor a 1.2 segundos en red local.
  - Feedback de estado inmediato (spinners, animaciones de robot pensando) durante llamadas asíncronas a los endpoints de IA que pueden tomar entre 2 y 15 segundos.
- **RNF-02: Usabilidad e Identidad Visual**:
  - Diseño responsivo compatible con resoluciones de escritorio (1920x1080, 1440x900) y laptops institucionales.
  - Paleta de colores consistente con la temática tricolor de Bolivia y modo oscuro institucional (*Dark Slate*).
- **RNF-03: Tolerancia a Fallos y Degradación Elegante**:
  - Si una llamada de API falla o el servidor backend está fuera de línea, el frontend debe capturar el error y mostrar mensajes claros en la UI sin bloquear la aplicación ni arrojar pantallas en blanco (*Uncaught Errors*).
- **RNF-04: Mantenibilidad del Código**:
  - Estructura limpia basada en componentes reutilizables ([`RobotCard.jsx`](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/src/components/RobotCard.jsx), [`Navbar.jsx`](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/src/components/Navbar.jsx)).
  - Gestión centralizada de llamadas HTTP mediante el módulo de servicios [`frontend/src/services/api.js`](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/src/services/api.js).
