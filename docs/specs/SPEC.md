# SPEC: Especificación Formal de Requerimientos Técnicos
> **Proyecto:** SMA Congreso — Sistema Multi-Agente para el Proceso Legislativo Plurinacional de Bolivia  
> **Arquitectura:** Prometheus PDT v2.0 (FastAPI + CrewAI + React 19/Vite + Neon pgvector + MongoDB Atlas)

---

## 01. Objetivo
Centralizar todos los prompts de los **14 agentes legislativos canónicos y los 4 agentes auxiliares del sistema** en los archivos declarativos [sma_unified/config/agents.yaml](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/config/agents.yaml) y [tasks.yaml](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/config/tasks.yaml), estructurándolos rigurosamente bajo los frameworks de ingeniería de prompts acordados (CO-STAR, CRAFT, RACE, RTF, BAB, CARE) y dotándolos de carga dinámica desde [sma_unified/agents/base_agent.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/base_agent.py).

Esto elimina la duplicidad y las cadenas hardcodeadas en los módulos Python de [sma_unified/agents/](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/), garantizando el cumplimiento estricto de las reglas anti-alucinación constitucionales bolivianas y preservando intactos los contratos JSON de API requeridos por el backend y el frontend.

---

## 02. Alcance Detallado: Cobertura del 100% de los Agentes

### Dentro del Alcance (IN-SCOPE): Cobertura Integral de 18 Componentes

#### Fase 1: Ingreso, Admisión y Atención Cívica
1. **Agente Distribuidor** ([distribuidor.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/distribuidor.py)):
   * *Framework:* **RTF (Role - Task - Format)** con XML Tags y Negative Prompting.
   * *Función:* Calificación de forma (Ley 1630 / Art. 156 CPE) y triaje unívoco (`AGENTE_REGISTRO_LEGISLATIVO`, `AGENTE_ATENCION_CIUDADANA`, `AGENTE_GESTION_CORRESPONDENCIA`).
2. **Agente Interacción Ciudadana / Multifaceta** ([ciudadana.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/ciudadana.py), [multiagente_ciudadano.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/multiagente_ciudadano.py), [voz_agent.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/voz_agent.py)):
   * *Framework:* **CO-STAR + ReAct** (Reasoning + Acting) con RAG dinámico sobre normas profesionales.
   * *Función:* Detección de intenciones ciudadanas por voz o texto y enrutamiento a sub-agentes temáticos.
3. **Agente Gestión de Correspondencia** ([correspondencia.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/correspondencia.py)):
   * *Framework:* **RTF**.
   * *Función:* Enrutamiento de oficios, notas y memoriales interinstitucionales.

#### Fase 2: Auditoría Normativa, Dictámenes Técnicos y Concentración
4. **Agente Verificador de Constitucionalidad Formal** ([verificador_constitucional.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/verificador_constitucional.py)):
   * *Framework:* **CRAFT + Chain of Thought (CoT)** con Contrastive Prompting y reglas R1-R7.
   * *Candado Anti-Alucinación:* *"Sin cita literal exacta de la CPE y del proyecto, el hallazgo es NEUTRAL con verificado=false"*.
5. **Agente de Consistencia Normativa y Antinomias** ([consistencia_normativa.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/consistencia_normativa.py)):
   * *Framework:* **CO-STAR** con búsqueda vectorial `pgvector` de 2048 dimensiones.
   * *Función:* Detección de antinomias temporales (*Lex posterior derogat priori*) y derogaciones tácitas.
6. **Agente Especialista Técnico Parlamentario** ([especialista_tecnico.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/especialista_tecnico.py), [especialista_chat.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/especialista_chat.py)):
   * *Framework:* **RACE (Role - Action - Context - Expectation)**.
   * *Función:* Factibilidad fáctica de infraestructura, estándares internacionales (ISO, OIT) y matriz cuantificada de riesgos.
7. **Agente Presidencia de Comisión** ([presidencia_comision.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/presidencia_comision.py)):
   * *Framework:* **CARE (Context - Action - Result - Example)**.
   * *Función:* Elaboración del Orden del Día, citación pericial y cronograma perentorio (15 a 30 días, Art. 156 CPE).
8. **Agente Comisión de Constitución - Fondo** ([constitucion_fondo.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/constitucion_fondo.py)):
   * *Framework:* **CO-STAR con CoT Cuatrifásico** (Fin Legítimo, Idoneidad, Necesidad, Proporcionalidad estricta).
   * *Función:* Hermenéutica sustantiva, doctrina del Vivir Bien y jurisprudencia vinculante del TCP (Sentencias SCP).
9. **Agente de Planificación Fiscal y Presupuesto** ([presupuesto.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/presupuesto.py)):
   * *Framework:* **CRAFT** con simulación en 3 escenarios (Optimista, Conservador, Estresado/Pesimista).
   * *Función:* Auditoría Ley 1178 (SAFCO), techos presupuestarios del TGN y alerta roja si no hay fuente de financiamiento.
10. **Agente Concentrador y Emisor (Nivel 3)** ([concentrador.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/concentrador.py), [emisor_resultados.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/emisor_resultados.py)):
    * *Framework:* **CO-STAR con Extended Deep Reasoning (CoT de 120B)**.
    * *Función:* Deduplicación forense de observaciones sin pérdida de fuentes y generación de Dictamen Parlamentario PDF en letra negra.
11. **Agente Asignación de Comisión** ([comision.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/comision.py)):
    * *Framework:* **RTF**.
    * *Función:* Mapeo temático de comisiones conforme al Reglamento Camaral.

#### Fase 3: Debate Plenario y Circuito Bicameral
12. **Agente Secretario de Cámara** ([secretario.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/secretario.py), [control_legislativo.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/control_legislativo.py)):
    * *Framework:* **RTF con CoT y Validación Matemática**.
    * *Función:* Verificación estricta de quórum y doble votación nominal ("En Grande" y "En Detalle").
13. **Agente Coordinación y Trámite Bicameral** ([bicameral.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/bicameral.py), [bicameral_pdf.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/bicameral_pdf.py)):
    * *Framework:* **CRAFT con Contrastive Prompting (Diff Textual)**.
    * *Función:* Conciliación de textos (Origen vs Revisora) conforme al Art. 163 CPE y freno humano (`PENDIENTE_APROBACION_HUMANA`).

#### Fase 4: Poder Ejecutivo y Publicación Oficial
14. **Agente Veto y Promulgación Presidencial** ([veto_promulgacion.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/veto_promulgacion.py)):
    * *Framework:* **RACE con Evaluación Multicriterio Ponderada** (Legalidad 25%, Fiscal 25%, Técnica 20%, Política 15%, Social 15%).
    * *Función:* Asesoría al Presidente del Estado en la ventana de 10 días para Promulgar, Vetar Parcial o Vetar Total.
15. **Agente de Publicación Oficial** ([publicacion.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/publicacion.py), [gaceta_pdf_generator.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/gaceta_pdf_generator.py)):
    * *Framework:* **RTF con Procedimiento Determinista Puro**.
    * *Función:* Asignación correlativa de Ley, cómputo de 15 días de vacatio legis y publicación en Gaceta Oficial.

#### Fase 5: Comunicación Cívica, Control Posterior y Notificaciones
16. **Agente de Difusión Ciudadana** ([difusion_ciudadana.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/difusion_ciudadana.py)):
    * *Framework:* **BAB (Before - After - Bridge) + CO-STAR** (Lenguaje Claro / Plain Language).
    * *Función:* Desglose pedagógico de derechos, obligaciones, beneficiarios y preguntas frecuentes.
17. **Agente de Fiscalización y Control Posterior** ([fiscalizacion.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/fiscalizacion.py)):
    * *Framework:* **RACE con Inferencia Causal Abductiva**.
    * *Función:* Control post-legislativo (Art. 158 CPE) sobre decretos reglamentarios y gasto ejecutado vs programado.
18. **Agentes Notificadores Oficiales** ([notificador_comision.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/notificador_comision.py), [notificador_camara_opuesta.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/agents/notificador_camara_opuesta.py)):
    * *Framework:* **RTF**.
    * *Función:* Redacción epistolar y despacho de notificaciones HTML formales.

### Fuera del Alcance (OUT-OF-SCOPE):
* Modificación de firmas de los métodos `ejecutar(...)` de las clases Python.
* Alteración de las claves canónicas de primer nivel en los JSON devueltos por cada agente.
* Modificaciones de rutas en `server.py` o de componentes React en `frontend/src/`.

---

## 03. Restricciones Técnicas y Legales
1. **Zero Breaking Changes:** El backend y los tests unitarios (`test_14_agentes.py`, `test_flujo_cadena_agentes.py`, etc.) deben continuar pasando con código de salida 0.
2. **Arquitectura con Fallback Seguro:** Si una plantilla YAML no puede cargarse en tiempo de ejecución, el agente Python debe degradar de forma transparente al prompt de contingencia sin arrojar excepción.
3. **Rigor Constitucional:** Respetar la supremacía de la CPE 2009, la Ley 1630 (ALP), la Ley 1178 (SAFCO) y la reserva de ley.

---

## 04. Criterios de Fin (Definition of Done)
1. **Carga en `base_agent.py`:** `BaseAgenteLegislativo` expone `get_prompt_templates(nombre_agente)` y resuelve las plantillas de los 18 componentes.
2. **Verificación de Inferencia:** Los 18 agentes consumen la configuración YAML al invocar `chat_completion_resiliente`.
3. **Validación Automatizada:**
   * `python test_14_agentes.py` $\rightarrow$ Exit code 0 (16 agentes, 16 tareas, 5 fases).
   * `python test_decision_bicameral.py` $\rightarrow$ Exit code 0 (3/3 tests OK).
   * `python test_cotejo_constitucional.py` $\rightarrow$ Exit code 0 (10/10 tests OK).
   * `cd frontend; npm run lint` $\rightarrow$ Exit code 0 (0 errores).

---

## 05. Contexto Necesario
* Configuración declarativa: `sma_unified/config/agents.yaml`, `tasks.yaml`, `workflows.yaml`.
* Código base de agentes: `sma_unified/agents/`.
* Persistencia: Esquema `sistema.*` en PostgreSQL Neon y base de datos `sma_congreso` en MongoDB Atlas.
