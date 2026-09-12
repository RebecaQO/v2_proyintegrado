# ✅ Criterios de Aceptación — Frontend (SMA Congreso)

> **Pregunta clave que responde este documento:** *¿Qué debe cumplirse en el Frontend para dar el proyecto o una funcionalidad por terminada con calidad de producción?*

---

## 📐 1. Criterios Globales de Calidad e Interfaz

Para considerar que la aplicación Frontend cumple con los estándares institucionales requeridos, debe satisfacer las siguientes listas de verificación:

### 🎨 Diseño y Estética Institucional
- [x] **Cero Estilos Genéricos**: La interfaz debe emplear una paleta de colores coherente (Slate Dark `#0f172a`, `#1e293b`, Acentos Tricolor `#C0392B`, `#F1C40F`, `#0D5C3A`).
- [x] **Tipografía Profesional**: Uso verificado de las fuentes de Google Fonts (*Outfit* para títulos/badges e *Inter* para lectura).
- [x] **Feedback Visual Reactivo**: Todos los botones de acción principal (Ejecutar Agente, Subir Documento, Confirmar Categoría) muestran estados de carga (*spinners*, deshabilitado temporal o cambio de texto) durante peticiones HTTP.
- [x] **Adaptabilidad de Pantalla**: La UI no presenta desbordamientos horizontales ni textos superpuestos en resoluciones estándar de escritorio (1366px, 1440px y 1920px).

---

## 🎯 2. Criterios de Aceptación por Módulo

### 📥 Módulo 1: Mesa de Partes Virtual (`MesaPartes.jsx`)

#### Criterio 1.1: Carga y Procesamiento del Documento
- **Dado que** el operador ingresa al módulo de Mesa de Partes,
- **Cuando** arrastra o selecciona un archivo (PDF, DOCX, TXT) o ingresa texto directo y presiona "Extraer y Cargar Documento",
- **Entonces**:
  1. Se invoca exitosamente `api.uploadDocument(file)`.
  2. Se muestra una tarjeta con el resultado de la extracción: conteo de palabras, caracteres, páginas y vista previa del texto.
  3. No se bloquea la interfaz en caso de archivos pesados.

#### Criterio 1.2: Clasificación de Fase 1 (Agente Distribuidor)
- **Dado que** el documento ha sido cargado con éxito,
- **Cuando** el usuario hace clic en "Ejecutar Fase 1: Clasificación Nivel 1",
- **Entonces**:
  1. Se invoca `api.runPhase1()`.
  2. La tarjeta de [`RobotCard.jsx`](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/src/components/RobotCard.jsx) del Agente Distribuidor pasa a estado *"En Ejecución..."* con animación y luego a *"✓ Ejecutado"*.
  3. Se muestra la justificación devuelta por el LLM y la categoría asignada.

#### Criterio 1.3: Punto de Control Humano (Human-in-the-Loop)
- **Dado que** la Fase 1 finaliza,
- **Cuando** se despliega el cuadro de pausa para confirmación humana,
- **Entonces**:
  1. El sistema permite al operador mantener la categoría sugerida o elegir una diferente en un selector desplegable.
  2. El botón de confirmación ("Confirmar y Continuar a Fase 2") habilita la ejecución de los agentes de auditoría de Fase 2.

#### Criterio 1.4: Auditoría de Fase 2 y Notificación
- **Dado que** se ha confirmado la categoría como *AGENTE_REGISTRO_LEGISLATIVO*,
- **Cuando** el usuario ejecuta los agentes de Fase 2,
- **Entonces**:
  1. Se visualiza la respuesta y estado de los agentes: *Comisión Legislativa*, *Verificador Constitucional* y *Consistencia Normativa*.
  2. El dictamen constitucional despliega badges de validez (*CONFORME* o *OBSERVADO*) y tabla de artículos a favor / en contra.
  3. Al presionar "Generar Dictamen PDF", se descarga o visualiza el enlace al archivo emitido.
  4. Al presionar "Notificar a la Comisión", se envía la notificación por correo y se muestra la confirmación de envío.

---

### 📋 Módulo 2: Registro de Expedientes (`Expedientes.jsx`)

#### Criterio 2.1: Listado y Buscador
- **Dado que** el usuario navega a la pestaña *Expedientes*,
- **Cuando** la página carga o el usuario escribe en la barra de búsqueda,
- **Entonces**:
  1. Se obtienen los datos mediante `api.getExpedientes()`.
  2. La tabla muestra número de expediente, título, comisión asignada, fecha e indicador de dictamen constitucional.
  3. El filtro por texto actualiza la lista en tiempo real sin recargar la página.

#### Criterio 2.2: Modal de Detalle de Expediente
- **Dado que** el usuario hace clic en el botón "Ver Detalle" de un expediente,
- **Cuando** se abre el modal emergente,
- **Entonces**:
  1. Se consulta `api.getExpedienteDetalle(id)`.
  2. Se puede navegar entre las pestañas del modal: *Información General*, *Bitácora de Auditoría*, *Observaciones Constitucionales* y *Consistencia Normativa*.
  3. Al presionar la tecla `ESC` o el botón de cerrar (`X`), el modal se cierra limpiando el estado.

---

### 📚 Módulo 3: Consistencia Normativa (`ConsistenciaNormativa.jsx`)

#### Criterio 3.1: Buscador Semántico pgvector
- **Dado que** el usuario está en el módulo de Consistencia Normativa,
- **Cuando** escribe una consulta en lenguaje natural (ej. *"¿Qué leyes regulan la expropiación de tierras?"*) y presiona "Buscar Artículos Semánticos",
- **Entonces**:
  1. Se realiza la llamada a `api.searchNormativa(query)`.
  2. Se despliega una lista de resultados ordenados por porcentaje de similitud vectorial (ej. `89.4% Similitud`).
  3. Se resalta el documento fuente (CPE, Código Penal, Ley Sectorial) y el texto exacto del artículo.

---

### 📊 Módulo 4: Monitoreo y Bus de Mensajes (`Monitoreo.jsx`)

#### Criterio 4.1: Consola de Eventos en Tiempo Real
- **Dado que** los agentes están procesando documentos en segundo plano,
- **Cuando** el usuario ingresa a *Monitoreo*,
- **Entonces**:
  1. Se obtienen los últimos mensajes del bus de MongoDB Atlas vía `api.getMessages()`.
  2. Cada tarjeta de mensaje refleja la hora, el agente origen, el agente destino, el tipo de tarea y el contenido JSON del payload.
  3. La lista puede actualizarse manualmente con un botón "Refrescar Eventos".

---

## 🛡️ 3. Criterios de Manejo de Errores e Infraestructura

- [x] **Graceful Degradation**: Si el servidor backend no responde (`http://127.0.0.1:8085`), el indicador de salud en la [`Navbar.jsx`](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/src/components/Navbar.jsx) cambia a *"Offline"* y la UI muestra alertas rojas comprensibles sin romper la renderización de la página.
- [x] **Resiliencia en Subida de Archivos**: Si se intenta subir un archivo vacío o corrupto, la UI muestra una notificación de advertencia indicando el problema.
