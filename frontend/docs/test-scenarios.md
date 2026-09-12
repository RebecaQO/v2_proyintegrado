# 🧪 Escenarios de Prueba — Frontend (SMA Congreso)

> **Pregunta clave que responde este documento:** *¿Cómo se validará el Frontend ante diferentes situaciones de uso, tipos de archivo, respuestas de agentes y condiciones de red?*

---

## 🎯 1. Estrategia Global de Pruebas

La estrategia de validación del Frontend abarca:
1. **Pruebas de Componentes UI**: Verificación visual de renderizado de tarjetas, avatares, modales y tablas.
2. **Pruebas de Integración con API**: Simulación e interacción real con el backend FastAPI (`http://127.0.0.1:8085`).
3. **Pruebas de Resiliencia y Red**: Comportamiento de la UI cuando el backend se desconecta o cuando un agente de IA tarda en responder.
4. **Pruebas de Usabilidad de Flujo Completo**: Recorrido de punta a punta desde la carga de un proyecto de ley hasta la emisión del PDF y notificación.

---

## 📝 2. Matriz de Escenarios de Prueba

### Escenario 01: Carga de Archivos de Diferentes Formatos
- **Objetivo**: Validar la extracción de texto en distintos tipos de documentos parlamentarios.
- **Pasos**:
  1. Ingresar al módulo *Mesa de Partes*.
  2. Cargar sucesivamente un archivo `.pdf`, `.docx`, `.rtf`, `.odt` y `.txt`.
- **Resultado Esperado**:
  - En cada caso, el servidor responde con status HTTP 200.
  - La UI muestra correctamente el número de caracteres, palabras y la vista previa del texto limpio extraído.
  - En caso de un archivo vacío o corrupto, se muestra un mensaje de advertencia rojo sin bloquear la interfaz.

---

### Escenario 02: Flujo Completo de Auditoría Legislativa (Fase 1 + Human-in-the-loop + Fase 2)
- **Objetivo**: Validar la secuencia de ejecución de los agentes y la pausa de confirmación humana.
- **Pasos**:
  1. Cargar un Proyecto de Ley de prueba (ej. *Ley de Incentivos a la Energía Solar*).
  2. Hacer clic en "Ejecutar Fase 1: Clasificación Nivel 1".
  3. Verificar que la tarjeta del **Agente Distribuidor** se anime e indique *"En Ejecución..."* y posteriormente muestre la categoría `AGENTE_REGISTRO_LEGISLATIVO`.
  4. Verificar la aparición de la caja de alerta de **Punto de Control Humano**.
  5. Confirmar la categoría y presionar "Continuar a Fase 2".
  6. Ejecutar el **Agente Comisión Legislativa**, **Verificador Constitucional** y **Consistencia Normativa**.
  7. Hacer clic en "Generar Dictamen PDF" y "Notificar a la Comisión".
- **Resultado Esperado**:
  - Todas las tarjetas de agente muestran su estado final *"✓ Ejecutado"*.
  - Se genera el enlace para descargar el PDF tricolor institucional.
  - Se muestra la notificación exitosa del envío de correo.

---

### Escenario 03: Cambio Manual de Categoría en el Punto de Control Humano
- **Objetivo**: Comprobar que el usuario puede corregir la decisión del Agente Distribuidor.
- **Pasos**:
  1. Cargar un documento ambiguo (ej. una carta de reclamo con formato de nota formal).
  2. Ejecutar Fase 1 (el Agente Distribuidor sugiere `AGENTE_REGISTRO_LEGISLATIVO`).
  3. En la caja de confirmación humana, cambiar el selector a `AGENTE_ATENCION_CIUDADANA`.
  4. Presionar "Confirmar y Procesar Solicitud".
- **Resultado Esperado**:
  - El sistema redirige la ejecución al pipeline de Atención Ciudadana en lugar del pipeline legislativo pesado.
  - Se actualiza el registro en la base de datos con la categoría ajustada por el operador.

---

### Escenario 04: Búsqueda Semántica en Consistencia Normativa
- **Objetivo**: Validar el funcionamiento de la consola de búsqueda vectorial `pgvector`.
- **Pasos**:
  1. Ir a la pestaña *Consistencia Normativa*.
  2. Escribir la consulta: *"Sanciones por delitos ambientales e incendios forestales"*.
  3. Presionar "Buscar Artículos Semánticos".
- **Resultado Esperado**:
  - Aparece un spinner de carga mientras se generan los embeddings de NVIDIA.
  - Se retornan los artículos de leyes y decretos aplicables ordenados por la puntuación de similitud semántica.

---

### Escenario 05: Modal de Detalle e Historial de Expedientes
- **Objetivo**: Validar la consulta e inspección profunda de proyectos de ley.
- **Pasos**:
  1. Navegar a la pestaña *Expedientes*.
  2. Usar la barra de búsqueda para filtrar por una palabra clave.
  3. Hacer clic en el botón "Ver Detalle" de cualquier expediente.
- **Resultado Esperado**:
  - Se abre un modal superpuesto con efecto *glassmorphism*.
  - Se puede conmutar libremente entre las 5 pestañas del modal (Resumen, Bitácora, Dictamen, Consistencia, Enrutamiento).
  - La bitácora muestra la línea de tiempo cronológica con los tiempos de respuesta en segundos de cada agente.

---

### Escenario 06: Comportamiento ante Caída del Backend (Offline / Error 500)
- **Objetivo**: Verificar la resiliencia y notificaciones de error en la UI.
- **Pasos**:
  1. Detener el proceso del servidor FastAPI (`server.py`).
  2. Observar la barra superior [`Navbar.jsx`](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/src/components/Navbar.jsx) tras transcurrir 15 segundos.
  3. Intentar realizar una acción en la UI (ej. subir documento).
- **Resultado Esperado**:
  - El badge de salud de la Navbar cambia automáticamente a estado `Offline` (Gris/Rojo).
  - La acción fallida despliega un banner de alerta con el detalle: `"Error: No se pudo conectar con el servidor backend en http://127.0.0.1:8085"`.
  - La SPA permanece reactiva sin colapsar.

---

## 🛠️ 3. Herramientas de Validación Recomendadas

| Nivel de Prueba | Herramienta | Comando / Procedimiento |
|---|---|---|
| **Análisis Estático (Linting)** | [oxlint](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/package.json#L21) | `npx oxlint` dentro de `/frontend` |
| **Construcción de Producción** | Vite Build | `npm run build` |
| **Pruebas de Componentes UI** | Browser DevTools | Inspección de consola, red (Network tab) y rendimiento. |
| **Pruebas E2E / Manuales** | Chrome / Edge | Ejecución de los 6 escenarios descritos arriba. |
