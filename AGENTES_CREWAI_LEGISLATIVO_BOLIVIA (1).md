# 📜 Sistema Multiagente CrewAI para Proceso Legislativo Boliviano con Módulo de Voz

## Tabla de Contenidos
1. [Introducción](#introducción)
2. [Marco Legal Boliviano](#marco-legal-boliviano)
3. [Arquitectura CrewAI](#arquitectura-crewai)
4. [Definición de Agentes](#definición-de-agentes)
5. [Estructura de Base de Datos](#estructura-de-base-de-datos)
6. [Flujo de Voz STT/TTS](#flujo-de-voz-stttts)
7. [Implementación en Python](#implementación-en-python)

---

## Introducción

> [!NOTE]
> **Evolución del Sistema hacia la Arquitectura v2.0 Unificada (NVIDIA NIM & Prometheus PDT):**  
> Este documento representa la especificación conceptual y prototípica del sistema multi-agente. En la **implementación operativa vigente de producción**, el sistema ha evolucionado con:
> 1. **Inferencia con NVIDIA NIM API:** Estandarización sobre el catálogo NIM (`openai/gpt-oss-20b` para auditoría ágil, `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` y `nvidia/nemotron-3-super-120b-a12b` para pensamiento analítico ampliado CoT).
> 2. **Agente Concentrador y Emisor:** Incorporación del Nivel 3 para consolidación forense de dictámenes, deduplicación de fuentes y compilación del informe oficial en PDF.
> 3. **Ingeniería Formal Prometheus PDT v2:** Modelado detallado (Agent Overview, Capability Overview y Process Diagram de 16 pasos) disponible en [`informe/figurasPrometheus_v2/`](informe/figurasPrometheus_v2/).
> 4. **Persistencia Unificada:** Centralización en el esquema `sistema.*` de PostgreSQL Neon con pgvector (2048d) y MongoDB Atlas.

Este documento describe un sistema multiagente basado en **CrewAI** que automatiza el proceso legislativo boliviano, desde la presentación de un proyecto de ley hasta su promulgación, integrando:

- **Módulo de Voz**: Captura (STT) y generación (TTS) de audio
- **Base de Datos Relacional**: PostgreSQL para datos estructurados
- **Base de Datos NoSQL**: MongoDB para expedientes y documentos flexibles
- **14 Agentes Especializados**: Cada uno con rol específico en el proceso legislativo

---

## Marco Legal Boliviano

### Contexto Constitucional
- **Constitución Política del Estado**: Artículos 156-161 definen el proceso legislativo
- **Órgano Legislativo**: Asamblea Legislativa Plurinacional (bicameral)
  - Cámara de Diputados (130 miembros)
  - Cámara de Senadores (36 miembros)

### Proceso de Aprobación de Leyes en Bolivia

```
┌─────────────────────────────────────────────────────────────┐
│                    PROCESO LEGISLATIVO BOLIVIANO            │
└─────────────────────────────────────────────────────────────┘

FASE 1: PRESENTACIÓN (Mesa de Entradas)
├─ Actor: Ciudadano, Institución, Legislador
├─ Entidad: Agente Distribuidor
├─ Acción: Registro de proyecto de ley
├─ Tiempo: Inmediato
└─ Salida: Número de proyecto + Acuse de recibo

FASE 2: ADMISIBILIDAD (Comisión de Turno)
├─ Actor: Comisión especializada según materia
├─ Entidades: Verificador Constitucionalidad, Consistencia Normativa
├─ Acciones:
│  ├─ Verificar forma y requisitos legales
│  ├─ Chequeo de constitucionalidad
│  ├─ Análisis de consistencia con leyes vigentes
│  └─ Emisión de dictamen
├─ Tiempo: 5-10 días hábiles
└─ Salida: Proyecto aceptado o rechazado

FASE 3: TRATAMIENTO EN COMISIÓN (1ª Lectura)
├─ Actor: Miembros de comisión especializada
├─ Entidades: Presidencia de Comisión, Especialistas Técnicos
├─ Acciones:
│  ├─ Análisis técnico y jurídico detallado
│  ├─ Consulta con expertos (economistas, abogados, etc.)
│  ├─ Debate interno
│  ├─ Proposición de enmiendas
│  └─ Aprobación en comisión
├─ Tiempo: 15-30 días hábiles
└─ Salida: Proyecto con observaciones técnicas

FASE 4: 1ª LECTURA EN CÁMARA ORIGEN
├─ Actor: Diputados/Senadores de cámara origen
├─ Entidades: Concentrador, Secretario de Cámara
├─ Acciones:
│  ├─ Presentación general de proyecto
│  ├─ Debate artículo por artículo
│  ├─ Votación de enmiendas
│  ├─ Votación final de proyecto
│  └─ Registro de acta de sesión
├─ Tiempo: 2-5 días
└─ Salida: Proyecto aprobado o rechazado

FASE 5: 2ª LECTURA EN CÁMARA REVISORA
├─ Actor: Diputados/Senadores de cámara revisora
├─ Entidades: Comunicación Bicameral, Agentes de análisis
├─ Acciones:
│  ├─ Revisión integral del proyecto
│  ├─ Posibles enmiendas
│  ├─ Debate en plenaria
│  ├─ Votación
│  └─ Envío de resultado a cámara origen
├─ Tiempo: 2-5 días
└─ Salida: Proyecto aprobado, modificado o rechazado

FASE 6: CONFERENCIA BICAMERAL (si hay diferencias)
├─ Actor: Miembros de ambas cámaras (comisión mixta)
├─ Entidades: Agente Bicameral, Gestor de Consenso
├─ Acciones:
│  ├─ Análisis de diferencias
│  ├─ Negociación de términos
│  ├─ Redacción de texto consensuado
│  └─ Votación de acuerdo
├─ Tiempo: 3-7 días
└─ Salida: Texto armonizado

FASE 7: PRESENTACIÓN AL EJECUTIVO
├─ Actor: Presidencia de Asamblea Legislativa
├─ Entidades: Agente de Publicación, Veto y Promulgación
├─ Acciones:
│  ├─ Envío formal a Presidencia de Estado
│  ├─ Análisis ejecutivo
│  └─ Decisión (Promulgar, Vetar, Vetar parcialmente)
├─ Tiempo: 5-10 días
└─ Salida: Ley promulgada o veto

FASE 8: PROMULGACIÓN Y PUBLICACIÓN
├─ Actor: Presidencia de Estado
├─ Entidades: Agente de Publicación Oficial
├─ Acciones:
│  ├─ Emisión de Decreto de Promulgación
│  ├─ Publicación en Gaceta Oficial de Bolivia
│  ├─ Entrada en vigencia (15 días después o fecha especificada)
│  └─ Registro en base de datos normativa
├─ Tiempo: 1 día
└─ Salida: Ley vigente

FASE 9: EJECUCIÓN Y FISCALIZACIÓN
├─ Actor: Organismos ejecutores + órganos de fiscalización
├─ Entidades: Agente de Fiscalización, Control Posterior
├─ Acciones:
│  ├─ Monitoreo de implementación
│  ├─ Detección de anomalías
│  ├─ Seguimiento de indicadores
│  └─ Informes de auditoría
├─ Tiempo: Continuo (durante vigencia de ley)
└─ Salida: Reportes de cumplimiento

TIEMPO TOTAL ESTIMADO: 60-90 días hábiles (3-4 meses)
```

### Leyes Relacionadas con el Proceso
- **Ley Nº 1630** (Reglamento de la Asamblea Legislativa Plurinacional)
- **Ley Nº 1369** (Ley de Gobierno Electrónico)
- **CPE - Artículos 156-161** (Proceso legislativo)

---

## Arquitectura CrewAI

### Concepto de CrewAI
CrewAI es un framework que permite:
- Definir **Agents** (agentes inteligentes)
- Crear **Tasks** (tareas específicas)
- Orquestar con **Crews** (equipos coordinados)
- Usar **Tools** (herramientas/funciones)

### Estructura General

```python
from crewai import Agent, Task, Crew, Process

# 1. DEFINIR AGENTES (Roles + Objetivos)
agent_distribuidor = Agent(
    role="Agente Distribuidor",
    goal="Clasificar y enrutar proyectos legislativos",
    backstory="Puerta de entrada del sistema...",
    tools=[...]
)

# 2. DEFINIR TAREAS (Qué hace cada agente)
tarea_distribucion = Task(
    description="Recibir proyecto y clasificar...",
    agent=agent_distribuidor,
    expected_output="Clasificación y enrutamiento"
)

# 3. CREAR CREW (Equipo coordinado)
crew = Crew(
    agents=[agent_distribuidor, ...],
    tasks=[tarea_distribucion, ...],
    process=Process.hierarchical  # o Process.sequential
)

# 4. EJECUTAR
resultado = crew.kickoff(inputs={"proyecto": "..."})
```

---

## Definición de Agentes

### Estructura General de cada Agente

```markdown
## AGENTE: [Nombre]

**Rol**: [Función principal en el proceso]
**Objetivo Principal**: [Goal del agente]
**Tipo de Razonamiento**: [Lógica que usa]
**Entrada (Percepción)**: [Qué recibe]
**Salida (Acción)**: [Qué entrega]
**Creencias/Datos**: [Bases de datos que consulta]
**Mensajes**: [Comunicación con otros agentes]
**Proceso en Bolivia**: [Fase legislativa que cubre]
**Almacenamiento**: [Qué datos guardar en BD]
```

---

### AGENTE 1: DISTRIBUIDOR (Mesa de Entradas)

**Rol**: Primer punto de contacto del sistema  
**Objetivo Principal**: Clasificar proyectos de ley según materia y derivar a comisión correcta  
**Tipo de Razonamiento**: Clasificación por reglas y precedentes  
**Actor Legislativo**: Mesa de Entradas (Artículo 156 CPE)

#### Percepción (Entrada)
- `ingreso_consulta`: Ciudadano presenta proyecto por voz o texto
- `envio_documento`: Documento PDF/Word del proyecto
- `datos_remitente`: Nombre, cédula, institución

#### Acciones (Salida)
- `emitir_acuse_recibo`: Envío de comprobante con número de proyecto
- `clasificar_por_materia`: Categorización (Tributaria, Laboral, Ambiental, etc.)
- `generar_numero_proyecto`: ID único del proyecto

#### Creencias (Base de Datos)
```
PostgreSQL:
├─ tabla: proyectos
│  ├─ id_proyecto (PK)
│  ├─ numero_proyecto (Ej: PL-2024-001)
│  ├─ titulo
│  ├─ materia
│  ├─ estado (presentado, admitido, rechazado)
│  ├─ fecha_presentacion
│  ├─ id_remitente (FK → remitentes)
│  └─ comision_asignada (FK → comisiones)
│
├─ tabla: remitentes
│  ├─ id_remitente (PK)
│  ├─ nombre
│  ├─ tipo (ciudadano, institución, legislador)
│  ├─ cedula
│  ├─ email
│  ├─ telefono
│  └─ institucion

├─ tabla: comisiones
│  ├─ id_comision (PK)
│  ├─ nombre
│  ├─ materia (Tributaria, Laboral, etc.)
│  ├─ presidente
│  └─ miembros

├─ tabla: auditoria_distribucion
│  ├─ id_log (PK)
│  ├─ id_proyecto (FK)
│  ├─ timestamp
│  ├─ usuario
│  ├─ accion (clasificado, enrutado)
│  └─ detalles

MongoDB:
└─ collection: expedientes_raw
   ├─ _id: ObjectId
   ├─ id_proyecto: "PL-2024-001"
   ├─ documento_original: (PDF binario base64)
   ├─ transcripcion_voz: "El proyecto trata sobre..."
   ├─ metadata:
   │  ├─ date_ingreso
   │  ├─ canal_ingreso (voz, web, email)
   │  └─ confianza_transcripcion: 0.95
   └─ versiones: [...]
```

#### Mensaje a Otros Agentes
```
{
  "tipo": "NUEVO_PROYECTO",
  "id_proyecto": "PL-2024-001",
  "titulo": "Ley de Protección de Datos Personales",
  "materia": "Derechos Digitales",
  "comision_destino": "Comisión de Tecnología",
  "ruta": ["Verificador_Const", "Consistencia", "Especialista_Técnico"],
  "prioridad": "alta"
}
```

#### Implementación CrewAI
```python
from crewai import Agent, Tool
from tools.voz import capturar_audio, transcribir_audio
from tools.bd import guardar_proyecto, asignar_comision

agent_distribuidor = Agent(
    role="Agente Distribuidor - Mesa de Entradas",
    goal="Clasificar proyectos de ley según materia constitucional y derivar a comisión correcta conforme Art. 157 CPE",
    backstory="""Eres el agente encargado de la Mesa de Entradas de la Asamblea Legislativa 
    Plurinacional de Bolivia. Tu responsabilidad es:
    1. Recibir proyectos de ley de ciudadanos, instituciones y legisladores
    2. Validar que cumplan requisitos de forma (Ley 1630)
    3. Clasificar por materia constitucional
    4. Asignar a comisión especializada
    5. Emitir acuse de recibo con número de proyecto
    
    Debes seguir el Artículo 156 de la CPE y la Ley de Reglamento de la Asamblea.""",
    tools=[capturar_audio, transcribir_audio, guardar_proyecto, asignar_comision],
    llm="gpt-4",  # o claude-sonnet para mejor contexto legal
    verbose=True
)

tarea_distribucion = Task(
    description="""Recibe un nuevo proyecto de ley (vía voz o archivo).
    1. Si es voz: Transcribir usando STT
    2. Validar que incluya título, justificación, articulado
    3. Clasificar por materia (usa tabla de materias constitucionales)
    4. Asignar comisión competente
    5. Guardar en DB (PostgreSQL para datos estructurados, MongoDB para documento original)
    6. Generar número de proyecto único (PL-YYYY-NNN)
    7. Emitir acuse de recibo por email/SMS/voz
    
    Responde con:
    - Número de proyecto asignado
    - Comisión destino
    - Próximas acciones""",
    agent=agent_distribuidor,
    expected_output="""JSON con:
    {
        "numero_proyecto": "PL-2024-001",
        "titulo": "...",
        "materia": "...",
        "comision_asignada": "...",
        "acuse_recibo_generado": true,
        "estado": "admitido",
        "mensaje_usuario": "Tu proyecto fue admitido y enviado a Comisión de..."
    }"""
)
```

---

### AGENTE 2: VERIFICADOR DE CONSTITUCIONALIDAD

**Rol**: Filtro inicial de legalidad  
**Objetivo Principal**: Detectar contradicciones directas entre proyecto y Constitución  
**Tipo de Razonamiento**: Deducción lógica determinista  
**Actor Legislativo**: Comisión de Constitución (análisis formal, Art. 156 CPE)

#### Percepción
- `solicitud_verificacion`: Mensaje del Distribuidor con proyecto
- `constitución_vigente`: Texto de CPE 2009 (base de datos)
- `jurisprudencia`: Sentencias del Tribunal Constitucional

#### Acciones
- `emitir_reporte_contradicciones`: Documento de incumplimientos
- `etiquetar_valido`: Marca proyecto como constitucionalmente válido
- `solicitar_aclaraciones`: Pide enmiendas al proponente

#### Creencias
```
PostgreSQL:
├─ tabla: constitucion
│  ├─ id_articulo (PK)
│  ├─ titulo (Ej: "Derechos y Deberes")
│  ├─ numero (Ej: 21)
│  ├─ texto
│  ├─ inciso
│  ├─ palabra_clave (para búsqueda)
│  └─ materia (FK → materias)

├─ tabla: jurisprudencia_tc
│  ├─ id_sentencia (PK)
│  ├─ numero_sentencia
│  ├─ fecha
│  ├─ tema
│  ├─ fallo
│  ├─ artículos_relacionados
│  └─ texto_completo

├─ tabla: verificaciones_constitucionales
│  ├─ id_verificacion (PK)
│  ├─ id_proyecto (FK)
│  ├─ fecha_verificacion
│  ├─ resultado (válido, inválido, parcialmente válido)
│  ├─ articulos_problema
│  ├─ recomendaciones
│  └─ verificador_ia

MongoDB:
└─ collection: reportes_constitucionalidad
   ├─ _id: ObjectId
   ├─ id_proyecto: "PL-2024-001"
   ├─ analisis_detallado:
   │  ├─ articulos_revisados: [21, 45, 112, ...]
   │  ├─ contradicciones_encontradas: [
   │  │  {
   │  │    articulo_proyecto: "Art. 3",
   │  │    texto_proyecto: "...",
   │  │    articulo_cpe: "Art. 21",
   │  │    conflicto: "Vulnera derecho a la vida",
   │  │    severidad: "crítica"
   │  │  }
   │  │]
   │  ├─ precedentes_aplicables: ["STC 0001/2020", ...]
   │  └─ recomendaciones: ["Modificar Art. 3", ...]
   ├─ cadena_razonamiento: "Artifact",  # CoT (Chain of Thought)
   └─ timestamp: ISODate
```

#### Implementación CrewAI
```python
agent_verificador = Agent(
    role="Agente Verificador de Constitucionalidad",
    goal="""Detectar contradicciones directas y evidentes entre el articulado de un proyecto 
    de ley y la Constitución Política del Estado Plurinacional de Bolivia (2009)""",
    backstory="""Eres especialista en Derecho Constitucional Boliviano. Tu función es:
    1. Leer el proyecto artículo por artículo
    2. Comparar contra Constitución vigente (Arts. 1-146)
    3. Aplicar jurisprudencia del Tribunal Constitucional
    4. Emitir reporte de contradicciones (si las hay)
    5. Sugerir correcciones
    
    Tu análisis es LÓGICO y DETERMINISTA (no interpretativo).""",
    tools=[
        buscar_articulo_constitucion,
        buscar_jurisprudencia,
        extraer_articulos_proyecto,
        generar_reporte_contradicciones
    ],
    verbose=True
)

tarea_verificacion = Task(
    description="""Analiza el proyecto PL-2024-001 para detectar contradicciones 
    con la Constitución:
    1. Extrae todos los artículos del proyecto
    2. Para cada artículo, busca artículos de CPE relacionados
    3. Compara lógicamente el texto
    4. Si hay prohibición explícita en CPE: reporta como contradicción crítica
    5. Si hay conflicto con jurisprudencia TC: reporta como contradicción
    6. Genera reporte estructurado
    
    IMPORTANTE: Solo reporta contradicciones DIRECTAS y EVIDENTES, no interpretaciones.""",
    agent=agent_verificador,
    expected_output="""JSON con:
    {
        "id_proyecto": "PL-2024-001",
        "resultado": "válido" | "inválido" | "parcialmente_válido",
        "contradicciones": [
            {
                "articulo_proyecto": "Art. 5",
                "articulo_cpe": "Art. 23",
                "descripción": "...",
                "severidad": "crítica" | "moderada" | "leve"
            }
        ],
        "recomendaciones": ["Modificar Art. 5 para alinearse con Art. 23 CPE"],
        "fecha_verificacion": "2024-01-15",
        "puede_continuar": true | false
    }"""
)
```

---

### AGENTE 3: CONSISTENCIA NORMATIVA

**Rol**: Validador de coherencia legal  
**Objetivo Principal**: Detectar conflictos con leyes vigentes  
**Tipo de Razonamiento**: Análisis semántico y estructural  
**Actor Legislativo**: Comisión especializada (análisis técnico-jurídico)

#### Percepción
- `proyecto_a_revisar`: Del Verificador de Constitucionalidad
- `ordenamiento_vigente`: Base de todas las leyes vigentes
- `registros_derogaciones`: Historial de leyes derogadas

#### Acciones
- `emitir_reporte_inconsistencias`: Documento de conflictos legales
- `etiquetar_consistente`: Marca como coherente con ordenamiento

#### Creencias
```
PostgreSQL:
├─ tabla: leyes_vigentes
│  ├─ id_ley (PK)
│  ├─ numero_ley
│  ├─ titulo
│  ├─ fecha_promulgacion
│  ├─ materia
│  ├─ estado (vigente, derogada, parcialmente_vigente)
│  ├─ descripcion_contenido
│  └─ articulos_texto

├─ tabla: relaciones_normativas
│  ├─ id_relacion (PK)
│  ├─ ley_padre (FK)
│  ├─ ley_hija (FK)
│  ├─ tipo_relacion (deroga, modifica, complementa, entra_en_conflicto)
│  └─ detalles

├─ tabla: analisis_consistencia
│  ├─ id_analisis (PK)
│  ├─ id_proyecto (FK)
│  ├─ leyes_relacionadas: [...]
│  ├─ conflictos_detectados
│  ├─ redundancias
│  └─ vacios_legales

MongoDB:
└─ collection: mapeo_normativo
   ├─ _id: ObjectId
   ├─ id_proyecto: "PL-2024-001"
   ├─ analisis_semántico:
   │  ├─ conceptos_clave: ["protección de datos", "privacidad", ...]
   │  ├─ leyes_con_concepto_similar: [
   │  │  {
   │  │    ley: "Ley 1686 - Código de Procedimiento Civil",
   │  │    similitud: 0.78,
   │  │    conflicto_potencial: "Ambas regulan confidencialidad"
   │  │  }
   │  │]
   │  ├─ derogaciones_implicitas: ["Art. 45 Ley 123"],
   │  └─ vacios_regulatorios: ["No hay sanción para incumplimiento"]
   └─ recomendaciones
```

#### Implementación CrewAI
```python
agent_consistencia = Agent(
    role="Agente de Consistencia Normativa",
    goal="Detectar colisiones, redundancias y vacíos legales entre proyecto y ordenamiento vigente",
    backstory="""Eres especialista en análisis semántico y comparativo de leyes.
    Tu función es mapear el nuevo proyecto contra todas las leyes vigentes en Bolivia:
    1. Buscar conceptos clave del proyecto
    2. Encontrar leyes que regulen conceptos similares
    3. Detectar potenciales conflictos
    4. Identificar derogaciones implícitas
    5. Señalar vacíos regulatorios
    6. Emitir reporte de consistencia
    
    Usas similitud semántica (NLP) para búsquedas no literales.""",
    tools=[
        buscar_leyes_relacionadas,
        analisis_semantico,
        detectar_derogaciones,
        generar_reporte_consistencia
    ],
    verbose=True
)
```

---

### AGENTE 4: ESPECIALISTA TÉCNICO (Por Materia)

**Rol**: Evaluador de viabilidad técnica  
**Objetivo Principal**: Validar factibilidad técnica, seguridad e impacto  
**Tipo de Razonamiento**: Análisis basado en conocimiento de dominio  
**Especialidades**: Tributaria, Ambiental, Laboral, Tecnológica, etc.

#### Percepción
- `proyecto_verificado`: Proyecto aprobado en verificación constitucional
- `datos_contexto`: Información técnica, económica del país
- `estándares_internacionales`: ISO, OIT, Banco Mundial, etc.

#### Acciones
- `emitir_dictamen_tecnico`: Evaluación de viabilidad
- `etiquetar_riesgo`: Marca nivel de riesgo (bajo/medio/alto)

#### Creencias
```
PostgreSQL:
├─ tabla: especialistas_tecnicos
│  ├─ id_especialista (PK)
│  ├─ nombre
│  ├─ especialidad (Tributaria, Ambiental, etc.)
│  ├─ años_experiencia
│  └─ contacto

├─ tabla: estándares_tecnicos
│  ├─ id_estandar (PK)
│  ├─ organismo (ISO, OIT, OMS, etc.)
│  ├─ código
│  ├─ descripcion
│  └─ sector_aplicable

├─ tabla: dictamenes_tecnicos
│  ├─ id_dictamen (PK)
│  ├─ id_proyecto (FK)
│  ├─ especialidad
│  ├─ fecha_dictamen
│  ├─ viabilidad (viable, no_viable, viable_con_condiciones)
│  ├─ riesgos_identificados
│  ├─ recomendaciones
│  └─ especialista_responsable

MongoDB:
└─ collection: analisis_tecnico_detallado
   ├─ _id: ObjectId
   ├─ id_proyecto: "PL-2024-001"
   ├─ especialidad: "Tecnología/Protección de Datos"
   ├─ evaluacion:
   │  ├─ viabilidad_tecnica:
   │  │  ├─ score: 8.5/10
   │  │  ├─ infraestructura_requerida: ["Centro de datos", "API federal"]
   │  │  └─ costo_estimado: 5000000 USD
   │  ├─ impacto_economico:
   │  │  ├─ costo_directo: 5000000
   │  │  ├─ costo_operativo_anual: 1200000
   │  │  └─ beneficio_estimado: 15000000
   │  ├─ riesgos:
   │  │  ├─ {riesgo: "Resistencia del sector privado", probabilidad: 0.6, impacto: "alto"}
   │  │  └─ {riesgo: "Capacitación insuficiente", probabilidad: 0.4, impacto: "medio"}
   │  └─ estándares_internacionales_aplicables: ["ISO 27001", "GDPR"]
   └─ cadena_razonamiento_detallada
```

---

### AGENTE 5: PRESIDENCIA DE COMISIÓN

**Rol**: Orquestador del debate en comisión  
**Objetivo Principal**: Gestionar tiempos, convocar especialistas, dirimir conflictos  
**Tipo de Razonamiento**: Planificación secuencial y gestión de turnos  
**Actor Legislativo**: Presidente/a de Comisión especializada

#### Percepción
- `proyecto_para_debatir`: Del Concentrador
- `calendario_sesiones`: Disponibilidad de comisión
- `solicitudes_especialistas`: Necesidades de análisis adicional

#### Acciones
- `emitir_orden_debate`: Cronograma de sesión
- `convocar_sesion`: Invitación formal a miembros

#### Creencias
```
PostgreSQL:
├─ tabla: sesiones_comision
│  ├─ id_sesion (PK)
│  ├─ id_comision (FK)
│  ├─ fecha_sesion
│  ├─ proyectos_a_tratar: []
│  ├─ asistentes: []
│  ├─ acta_sesion
│  └─ resultado

├─ tabla: calendario_legislativo
│  ├─ id_evento (PK)
│  ├─ tipo_evento (sesión, receso, feriado)
│  ├─ fecha_inicio
│  ├─ fecha_fin
│  └─ descripcion

├─ tabla: orden_de_dia
│  ├─ id_orden (PK)
│  ├─ id_sesion (FK)
│  ├─ numero_orden
│  ├─ proyecto_id (FK)
│  ├─ tiempo_asignado
│  ├─ especialistas_convocados
│  └─ resultado_votacion

MongoDB:
└─ collection: planes_debate
   ├─ _id: ObjectId
   ├─ id_proyecto: "PL-2024-001"
   ├─ plan_sesion:
   │  ├─ fecha_propuesta: "2024-02-01"
   │  ├─ duracion_estimada: "3 horas"
   │  ├─ orden_de_dia: [
   │  │  {
   │  │    numero: 1,
   │  │    punto: "Exposición de proyecto (30 min)",
   │  │    responsable: "Proponente"
   │  │  },
   │  │  {
   │  │    numero: 2,
   │  │    punto: "Dictamen técnico (20 min)",
   │  │    responsable: "Especialista técnico"
   │  │  }
   │  │]
   │  ├─ especialistas_a_convocar: ["Abogado constitucionalista", "Economista", ...]
   │  └─ documentos_preparatorios: ["Dictamen", "Informe financiero", ...]
   └─ notas_presidencia
```

---

### AGENTE 6: COMISIÓN DE CONSTITUCIÓN (Análisis de Fondo)

**Rol**: Intérprete constitucional  
**Objetivo Principal**: Análisis jurídico profundo y aplicación de principios constitucionales  
**Tipo de Razonamiento**: Razonamiento jurídico analógico y principialista  
**Actor Legislativo**: Comisión de Constitución, Legislación e Industria

#### Percepción
- `proyecto_para_analisis`: Del Presidencia de Comisión
- `jurisprudencia_constitucional`: Fallos del TC y doctrina
- `precedentes_legislativos`: Leyes similares anteriores

#### Acciones
- `emitir_dictamen_fondo`: Análisis jurídico fundamentado
- `recomendar_enmiendas`: Propuestas de mejora legal

#### Creencias
```
PostgreSQL:
├─ tabla: principios_constitucionales
│  ├─ id_principio (PK)
│  ├─ nombre (Ej: "Dignidad de la persona")
│  ├─ articulo_cpe
│  ├─ descripcion
│  └─ precedentes_tc: []

├─ tabla: doctrina_constitucional
│  ├─ id_doctrina (PK)
│  ├─ autor
│  ├─ tema
│  ├─ texto
│  ├─ año_publicacion
│  └─ referencias

├─ tabla: dictamenes_fondo
│  ├─ id_dictamen (PK)
│  ├─ id_proyecto (FK)
│  ├─ fecha_dictamen
│  ├─ principios_aplicados
│  ├─ analisis_detallado
│  ├─ conclusion
│  ├─ voto_favorable_miembros
│  └─ voto_adverso_miembros

MongoDB:
└─ collection: argumentacion_constitucional
   ├─ _id: ObjectId
   ├─ id_proyecto: "PL-2024-001"
   ├─ tesis:
   │  ├─ titulo: "Protección del Derecho a la Intimidad"
   │  ├─ proposicion: "El proyecto es constitucional porque..."
   │  ├─ argumentos_principales: [
   │  │  {
   │  │    numero: 1,
   │  │    argumento: "Respeta derecho a la intimidad (Art. 21)",
   │  │    sustento: "STC 0812/2012",
   │  │    doctrina: "Ferrajoli, Luigi. Derechos y garantías..."
   │  │  }
   │  │]
   │  ├─ contra_argumentos_considerados: ["...", "..."],
   │  └─ conclusion: "Por tanto, es constitucionalmente válido"
   └─ votacion:
      ├─ total_miembros: 5
      ├─ votos_favor: 4
      ├─ votos_contra: 1
      └─ abstenciones: 0
```

---

### AGENTE 7: SECRETARIO DE CÁMARA (Registro de Actas)

**Rol**: Registrador oficial de procedimientos  
**Objetivo Principal**: Documentar fielmente el debate legislativo  
**Tipo de Razonamiento**: Registro estructurado paso a paso (Chain of Thought)  
**Actor Legislativo**: Secretaría de la Cámara (asiste a todas las sesiones)

#### Percepción
- `eventos_sesion`: Audio/transcripción de sesiones
- `votaciones`: Resultados de votaciones
- `intervenciones`: Discursos de legisladores

#### Acciones
- `generar_acta_sesion`: Documento oficial de lo acontecido
- `registrar_votacion`: Resultado de votación por legislador
- `guardar_intervenciones`: Discursos transcriptos

#### Creencias
```
PostgreSQL:
├─ tabla: actas_sesion
│  ├─ id_acta (PK)
│  ├─ id_sesion (FK)
│  ├─ fecha_sesion
│  ├─ inicio_sesion
│  ├─ cierre_sesion
│  ├─ proyectos_tratados
│  ├─ asistentes
│  ├─ texto_acta
│  └─ firma_secretario

├─ tabla: votaciones
│  ├─ id_votacion (PK)
│  ├─ id_proyecto (FK)
│  ├─ fecha_votacion
│  ├─ descripcion_votacion
│  ├─ total_votos
│  ├─ votos_afirmativos
│  ├─ votos_negativos
│  ├─ abstenciones
│  └─ resultado (aprobado, rechazado)

├─ tabla: intervenciones
│  ├─ id_intervencion (PK)
│  ├─ id_sesion (FK)
│  ├─ legislador_id (FK)
│  ├─ orden_intervención
│  ├─ tiempo_minutos
│  ├─ tema
│  ├─ transcripcion
│  └─ archivo_audio

MongoDB:
└─ collection: actas_detalladas
   ├─ _id: ObjectId
   ├─ id_sesion: "SES-2024-001"
   ├─ cronologia: [
   │  {
   │    timestamp: "2024-02-01T09:00:00Z",
   │    evento: "Apertura de sesión",
   │    detalles: "Presidenta declara abierta la sesión"
   │  },
   │  {
   │    timestamp: "2024-02-01T09:05:00Z",
   │    evento: "Intervención",
   │    legislador: "Dip. María García",
   │    texto: "Agradezco la presencia de especialistas...",
   │    audio_url: "s3://audio/ses-2024-001/001.mp3"
   │  },
   │  {
   │    timestamp: "2024-02-01T10:30:00Z",
   │    evento: "Votación",
   │    resultado: "Aprobado 87 votos, 40 contra, 3 abstenciones"
   │  }
   │]
   ├─ resumen_ejecutivo: "Se aprobó el proyecto con enmiendas al Art. 5..."
   └─ documentos_adjuntos: ["Audio sesión", "Intervenciones originales", ...]
```

#### Implementación CrewAI
```python
agent_secretario = Agent(
    role="Secretario/a de Cámara - Registro de Actas",
    goal="Documentar fielmente cada evento de la sesión legislativa en orden cronológico",
    backstory="""Eres el registrador oficial de las sesiones de la Asamblea Legislativa.
    Tu función es:
    1. Capturar audio de la sesión (STT para transcripción)
    2. Registrar cronológicamente cada evento
    3. Documentar intervenciones de legisladores
    4. Registrar votaciones con detalle de votos por persona
    5. Generar acta oficial firmada
    
    Usas Chain of Thought para no omitir detalles.""",
    tools=[
        capturar_audio_sesion,
        transcribir_intervenciones,
        registrar_votacion,
        generar_acta_oficial
    ],
    verbose=True
)

tarea_acta = Task(
    description="""Durante la sesión del proyecto PL-2024-001:
    1. Transcribe audio de sesión usando STT
    2. Registra cronológicamente: apertura, intervenciones, votaciones, cierre
    3. Para cada intervención: legislador, tema, duración, texto completo
    4. Para votación: total votos, favor, contra, abstenciones, por legislador
    5. Genera acta oficial con timestamp de cada evento
    6. Guarda en PostgreSQL (datos estructurados) y MongoDB (documento completo)""",
    agent=agent_secretario,
    expected_output="""Acta oficial con:
    {
        "id_acta": "ACTA-2024-001",
        "fecha": "2024-02-01",
        "proyecto": "PL-2024-001",
        "inicio": "09:00",
        "cierre": "11:30",
        "cronologia": [...],
        "resultado_final": "Aprobado con enmiendas"
    }"""
)
```

---

### AGENTE 8: COMUNICACIÓN BICAMERAL

**Rol**: Gestor de ida y vuelta entre cámaras  
**Objetivo Principal**: Detectar diferencias, resolver conflictos, armonizar texto  
**Tipo de Razonamiento**: Seguimiento de estado y gestión de consenso  
**Actor Legislativo**: Secretaría legislativa (coordina entre cámaras)

#### Percepción
- `proyecto_aprobado_c1`: De Cámara 1 (Diputados)
- `proyecto_modificado_c2`: De Cámara 2 (Senadores) con cambios
- `reglas_bicamerales`: Protocolos de resolución

#### Acciones
- `detectar_diferencias`: Identifica artículos modificados
- `iniciar_conferencia`: Convoca comisión mixta si hay desacuerdo
- `armonizar_texto`: Propone versión consensuada

#### Creencias
```
PostgreSQL:
├─ tabla: ciclos_bicamerales
│  ├─ id_ciclo (PK)
│  ├─ id_proyecto (FK)
│  ├─ estado_c_diputados
│  ├─ estado_c_senadores
│  ├─ version_actual
│  ├─ diferencias_detectadas
│  └─ fecha_ultima_actualizacion

├─ tabla: conferencia_bicameral
│  ├─ id_conferencia (PK)
│  ├─ id_ciclo (FK)
│  ├─ fecha_convocatoria
│  ├─ integrantes_c1: []
│  ├─ integrantes_c2: []
│  ├─ resultado_consenso
│  └─ texto_final

MongoDB:
└─ collection: historial_versiones
   ├─ _id: ObjectId
   ├─ id_proyecto: "PL-2024-001"
   ├─ versiones: [
   │  {
   │    numero_version: 1,
   │    origen: "Cámara de Diputados",
   │    fecha: "2024-02-01",
   │    estado: "aprobado",
   │    texto_articulos: {...}
   │  },
   │  {
   │    numero_version: 2,
   │    origen: "Cámara de Senadores",
   │    fecha: "2024-02-10",
   │    estado: "modificado",
   │    cambios: [
   │      {
   │        articulo: 5,
   │        texto_anterior: "...",
   │        texto_nuevo: "...",
   │        motivo: "Protección de trabajadores"
   │      }
   │    ]
   │  }
   │]
   ├─ diferencias_por_articulo: {...}
   └─ consenso_alcanzado: true
```

---

### AGENTE 9: VETO Y PROMULGACIÓN

**Rol**: Tomador de decisión final  
**Objetivo Principal**: Evaluar proyecto y decidir promulgar, vetar total o parcialmente  
**Tipo de Razonamiento**: Evaluación estratégica multicriterio  
**Actor Legislativo**: Presidencia del Estado (ejecutivo)

#### Percepción
- `proyecto_aprobado`: Del Concentrador bicameral
- `alertas_presupuestarias`: Del agente de Planificación
- `contexto_politico`: Coaliciones, prioridades ejecutivas

#### Acciones
- `promulgar_ley`: Aprueba proyecto
- `vetar_totalmente`: Rechaza todo el proyecto
- `vetar_parcialmente`: Observaciones a artículos específicos

#### Creencias
```
PostgreSQL:
├─ tabla: decisiones_ejecutivas
│  ├─ id_decision (PK)
│  ├─ id_proyecto (FK)
│  ├─ fecha_recepcion
│  ├─ fecha_decision
│  ├─ tipo_decision (promulgación, veto total, veto parcial)
│  ├─ argumentos
│  └─ decreto_numero

├─ tabla: evaluacion_multicriterio
│  ├─ id_evaluacion (PK)
│  ├─ id_proyecto (FK)
│  ├─ criterio
│  ├─ puntuacion (0-10)
│  ├─ peso_criterio
│  └─ observacion

MongoDB:
└─ collection: evaluacion_ejecutiva
   ├─ _id: ObjectId
   ├─ id_proyecto: "PL-2024-001"
   ├─ evaluacion_multicriterio:
   │  ├─ legalidad: {score: 9, peso: 0.25}
   │  ├─ viabilidad_tecnica: {score: 7, peso: 0.2}
   │  ├─ impacto_fiscal: {score: 5, peso: 0.25}
   │  ├─ alineamiento_politico: {score: 8, peso: 0.15}
   │  └─ urgencia: {score: 6, peso: 0.15}
   ├─ score_total: 7.1/10
   ├─ recomendacion: "PROMULGAR CON OBSERVACIONES"
   ├─ observaciones_propuestas: ["Modificar Art. 12", ...]
   └─ decision_final: "PROMULGADA CON VETO PARCIAL"
```

---

### AGENTE 10: PUBLICACIÓN OFICIAL

**Rol**: Publicador de leyes vigentes  
**Objetivo Principal**: Asignar número de ley, publicar en Gaceta Oficial, registrar vigencia  
**Tipo de Razonamiento**: Procedimiento determinista automatizado  
**Actor Legislativo**: Gaceta Oficial de Bolivia

#### Acciones
- `asignar_numero_ley`: Número secuencial (Ley Nº XXXX)
- `generar_decreto_promulgación`: Documento oficial firmado
- `publicar_gaceta_oficial`: Publicación en medio oficial
- `registrar_vigencia`: Fecha de entrada en vigencia (generalmente 15 días)

#### Creencias
```
PostgreSQL:
├─ tabla: leyes_promulgadas
│  ├─ id_ley (PK)
│  ├─ numero_ley
│  ├─ titulo
│  ├─ fecha_promulgacion
│  ├─ fecha_vigencia
│  ├─ texto_oficial
│  ├─ decreto_numero
│  ├─ url_gaceta_oficial
│  └─ estado (vigente, derogada, modificada)

├─ tabla: secuencia_leyes
│  ├─ id_secuencia (PK)
│  ├─ numero_siguiente (para asignación automática)
│  └─ ultima_actualizacion

MongoDB:
└─ collection: publicacion_oficial
   ├─ _id: ObjectId
   ├─ id_proyecto: "PL-2024-001"
   ├─ numero_ley_asignado: 1234
   ├─ decreto_promulgacion:
   │  ├─ texto_completo: "CONSIDERANDO QUE..."
   │  ├─ firmado_por: "Presidente del Estado"
   │  ├─ fecha_firma: "2024-02-15"
   │  └─ archivo_pdf: "s3://decretos/Dec-2024-001.pdf"
   ├─ gaceta_oficial:
   │  ├─ numero_edicion: "GO-2024-050"
   │  ├─ fecha_publicacion: "2024-02-16"
   │  ├─ paginas: "1-15"
   │  └─ url: "http://www.gacetaoficial.gob.bo/..."
   ├─ vigencia:
   │  ├─ fecha_entrada: "2024-03-02"  # 15 días después
   │  └─ disposicion_especial: null
   └─ registro_normativo_nacional: true
```

---

### AGENTE 11: FISCALIZACIÓN (Control Posterior)

**Rol**: Monitor de implementación  
**Objetivo Principal**: Detectar anomalías en ejecución post-legislativa  
**Tipo de Razonamiento**: Inferencia causal abductiva  
**Actor Legislativo**: Órganos de control (Contraloría, Procuraduría)

#### Percepción
- `ley_en_vigencia`: De Publicación Oficial
- `datos_ejecución`: Reportes de organismos ejecutores
- `indicadores_desvío`: Alarmas de sobreprecios, retrasos

#### Acciones
- `generar_hipótesis_irregularidad`: Documento de análisis causal
- `emitir_alerta_auditoria`: Aviso a órgano fiscalizador

#### Creencias
```
PostgreSQL:
├─ tabla: leyes_en_ejecucion
│  ├─ id_ley (FK)
│  ├─ presupuesto_asignado
│  ├─ presupuesto_ejecutado_actual
│  ├─ indicadores_clave: {}
│  ├─ estado_implementacion (en_plazo, retraso, crítico)
│  └─ organismos_responsables: []

├─ tabla: alertas_fiscalizacion
│  ├─ id_alerta (PK)
│  ├─ id_ley (FK)
│  ├─ fecha_alerta
│  ├─ tipo_anomalia
│  ├─ nivel_riesgo (bajo, medio, alto, crítico)
│  ├─ descripcion
│  └─ organismo_notificado

MongoDB:
└─ collection: analisis_ejecucion
   ├─ _id: ObjectId
   ├─ id_ley: 1234
   ├─ monitoreo_indicadores:
   │  ├─ indicador_1:
   │  │  ├─ nombre: "Presupuesto ejecutado"
   │  │  ├─ valor_esperado: 100000000
   │  │  ├─ valor_actual: 130000000
   │  │  ├─ desvío_porcentaje: 30
   │  │  └─ estado: "ALERTA"
   │  └─ indicador_2: {...}
   ├─ hipotesis_irregularidad: [
   │  {
   │    anomalia: "Sobreprecio 30%",
   │    causas_posibles: [
   │      {causa: "Falta de licitación competitiva", probabilidad: 0.7},
   │      {causa: "Cambios en especificaciones técnicas", probabilidad: 0.5}
   │    ],
   │    causa_mas_probable: "Falta de licitación",
   │    confianza: 0.75
   │  }
   │]
   └─ recomendaciones_auditoria
```

---

### AGENTE 12: PLANIFICACIÓN Y PRESUPUESTO

**Rol**: Analista fiscal  
**Objetivo Principal**: Evaluar impacto presupuestario y sostenibilidad fiscal  
**Tipo de Razonamiento**: Proyección económica y análisis de escenarios  
**Actor Legislativo**: Comisión de Planificación y Presupuesto

#### Percepción
- `proyecto_para_presupuestar`: Del Presidencia de Comisión
- `presupuesto_nacional`: Estado de ingresos y gastos
- `proyecciones_economicas`: PIB, inflación, desempleo

#### Acciones
- `generar_analisis_presupuestario`: Evaluación fiscal
- `emitir_alerta_presupuesto`: Si proyecto compromete estabilidad

#### Creencias
```
PostgreSQL:
├─ tabla: presupuesto_nacional
│  ├─ año (PK)
│  ├─ ingresos_totales
│  ├─ gastos_totales
│  ├─ deficit_superavit
│  ├─ deuda_publica
│  └─ tasas_interes

├─ tabla: evaluacion_presupuestaria
│  ├─ id_eval (PK)
│  ├─ id_proyecto (FK)
│  ├─ costo_directo
│  ├─ costo_operativo_anual
│  ├─ beneficio_estimado
│  ├─ tir (Tasa Interna de Retorno)
│  └─ viabilidad_fiscal

MongoDB:
└─ collection: analisis_fiscal_detallado
   ├─ _id: ObjectId
   ├─ id_proyecto: "PL-2024-001"
   ├─ proyecciones: [
   │  {
   │    escenario: "Optimista",
   │    crecimiento_pib: 0.04,
   │    inflacion: 0.025,
   │    costo_total: 4500000,
   │    beneficio: 18000000,
   │    van: 10000000
   │  },
   │  {
   │    escenario: "Conservador",
   │    crecimiento_pib: 0.025,
   │    inflacion: 0.035,
   │    costo_total: 5500000,
   │    beneficio: 12000000,
   │    van: 5000000
   │  },
   │  {
   │    escenario: "Pesimista",
   │    crecimiento_pib: 0.01,
   │    inflacion: 0.05,
   │    costo_total: 6500000,
   │    beneficio: 8000000,
   │    van: 500000
   │  }
   │]
   ├─ recomendacion: "VIABLE en todos los escenarios"
   └─ condiciones_implementacion: ["Fuente de financiamiento asegurada", ...]
```

---

### AGENTE 13: DIFUSIÓN CIUDADANA

**Rol**: Traductor de lenguaje legal  
**Objetivo Principal**: Comunicar ley a ciudadanía en lenguaje simple  
**Tipo de Razonamiento**: Simplificación lingüística  
**Actor Legislativo**: Secretaría de Comunicación

#### Acciones
- `generar_resumen_ciudadano`: Versión simplificada de la ley
- `extraer_obligaciones`: Lo que el ciudadano debe hacer
- `identificar_derechos`: Lo que el ciudadano puede hacer
- `especificar_plazos`: Cuándo rige, plazos de implementación

#### Creencias
```
MongoDB:
└─ collection: comunicacion_ciudadana
   ├─ _id: ObjectId
   ├─ id_ley: 1234
   ├─ resumen_ejecutivo_simple:
   │  ├─ titulo: "Lo que debes saber sobre la nueva Ley 1234"
   │  ├─ proposito: "Esta ley protege tus datos personales..."
   │  ├─ articulos_clave: [
   │  │  {
   │  │    numero_articulo: 5,
   │  │    titulo_simple: "Tu derecho a conocer qué datos recopilan",
   │  │    explicacion: "Las empresas deben decirte qué información..."
   │  │  }
   │  │]
   │  ├─ mis_obligaciones: [
   │  │  "Autorizar expresamente recopilación de datos",
   │  │  "Exigir rectificación si hay errores"
   │  │]
   │  ├─ mis_derechos: [
   │  │  "Acceso a mis datos",
   │  │  "Rectificación de datos inexactos",
   │  │  "Derecho al olvido"
   │  │]
   │  └─ fecha_vigencia: "2024-03-02"
   └─ infografias_preguntas_frecuentes: [...]
```

---

### AGENTE 14: INTERACCIÓN CON CIUDADANÍA

**Rol**: Interfaz conversacional  
**Objetivo Principal**: Atender consultas ciudadanas, capturar intención, enrutar  
**Tipo de Razonamiento**: PLN + reconocimiento de intención  
**Actor Legislativo**: Ventanilla digital / Centro de atención ciudadana

#### Percepción
- `consulta_ciudadano`: Vía voz (STT), chat, email
- `historial_ciudadano`: Consultas previas del usuario
- `base_conocimiento_civico`: FAQs, leyes, trámites

#### Acciones
- `responder_consulta`: Información o derivación
- `registrar_consulta`: Guarda en expediente ciudadano
- `derivar_caso`: Envía a agente especializado si necesario

#### Creencias
```
PostgreSQL:
├─ tabla: consultas_ciudadanas
│  ├─ id_consulta (PK)
│  ├─ id_ciudadano (FK)
│  ├─ fecha_consulta
│  ├─ canal (voz, chat, email, presencial)
│  ├─ tema
│  ├─ transcripcion_consulta
│  ├─ respuesta_generada
│  └─ satisfaccion_ciudadano (1-5)

├─ tabla: faq_legislativo
│  ├─ id_faq (PK)
│  ├─ pregunta
│  ├─ respuesta
│  ├─ ley_relacionada (FK)
│  ├─ frecuencia_consulta
│  └─ ultima_actualizacion

MongoDB:
└─ collection: expedientes_ciudadanos
   ├─ _id: ObjectId
   ├─ id_ciudadano: "CEDULA-123456"
   ├─ nombre: "Juan Pérez"
   ├─ contacto:
   │  ├─ email: "juan@email.com"
   │  ├─ telefono: "+591-2-1234567"
   │  └─ telefono_movil: "+591-76-1234567"
   ├─ historico_consultas: [
   │  {
   │    fecha: "2024-01-10",
   │    canal: "voz",
   │    tema: "¿Qué es protección de datos?",
   │    respuesta_breve: "Es el derecho a proteger tu información personal...",
   │    ley_relacionada: "1234",
   │    satisfaccion: 5
   │  }
   │]
   ├─ expedientes_asociados: ["TRÁ-2024-001", "PL-2024-001"],
   └─ preferencias:
      ├─ idioma: "es"
      ├─ canal_preferido: "voz"
      └─ recibir_noticias: true
```

---

## Estructura de Base de Datos

### 📊 PostgreSQL (Datos Estructurados)

```sql
-- ============================================
-- TABLA CENTRAL: PROYECTOS
-- ============================================
CREATE TABLE proyectos (
    id_proyecto SERIAL PRIMARY KEY,
    numero_proyecto VARCHAR(20) UNIQUE NOT NULL,  -- PL-2024-001
    titulo VARCHAR(500) NOT NULL,
    descripcion TEXT,
    materia VARCHAR(100),  -- Tributaria, Laboral, etc.
    estado VARCHAR(50),    -- presentado, admitido, en_comisión, aprobado, etc.
    fecha_presentacion TIMESTAMP DEFAULT NOW(),
    fecha_ultimo_cambio TIMESTAMP DEFAULT NOW(),
    id_remitente INT REFERENCES remitentes(id_remitente),
    comision_asignada INT REFERENCES comisiones(id_comision),
    numero_ley_final INT UNIQUE,  -- Una vez promulgado
    CONSTRAINT estado_valido CHECK (estado IN (
        'presentado', 'admitido', 'rechazado_admisibilidad',
        'en_comisión', 'en_debate_c1', 'en_debate_c2',
        'en_conferencia_bicameral', 'en_ejecutivo',
        'vetado', 'promulgado', 'vigente', 'derogado'
    ))
);

-- ============================================
-- TABLA: REMITENTES (Ciudadanos, Instituciones)
-- ============================================
CREATE TABLE remitentes (
    id_remitente SERIAL PRIMARY KEY,
    tipo VARCHAR(50),  -- ciudadano, institución, legislador
    nombre VARCHAR(255) NOT NULL,
    cedula VARCHAR(15),
    institucion VARCHAR(255),
    email VARCHAR(255),
    telefono VARCHAR(20),
    direccion TEXT,
    fecha_registro TIMESTAMP DEFAULT NOW(),
    UNIQUE(cedula, tipo)
);

-- ============================================
-- TABLA: COMISIONES
-- ============================================
CREATE TABLE comisiones (
    id_comision SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL UNIQUE,
    materia VARCHAR(100),
    presidente INT REFERENCES legisladores(id_legislador),
    cantidad_miembros INT,
    fecha_creacion DATE
);

-- ============================================
-- TABLA: LEGISLADORES
-- ============================================
CREATE TABLE legisladores (
    id_legislador SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    cedula VARCHAR(15) UNIQUE,
    camara VARCHAR(50),  -- Diputados, Senadores
    partido VARCHAR(255),
    departamento VARCHAR(100),
    email VARCHAR(255),
    fecha_inicio DATE,
    activo BOOLEAN DEFAULT TRUE
);

-- ============================================
-- TABLA: SESIONES
-- ============================================
CREATE TABLE sesiones (
    id_sesion SERIAL PRIMARY KEY,
    id_comision INT REFERENCES comisiones(id_comision),
    fecha_sesion DATE NOT NULL,
    hora_inicio TIME,
    hora_cierre TIME,
    asistentes INT,
    orden_del_dia TEXT,
    acta_id INT,  -- Referencia a acta una vez generada
    UNIQUE(id_comision, fecha_sesion)
);

-- ============================================
-- TABLA: VOTACIONES
-- ============================================
CREATE TABLE votaciones (
    id_votacion SERIAL PRIMARY KEY,
    id_proyecto INT REFERENCES proyectos(id_proyecto),
    fecha_votacion TIMESTAMP,
    camara VARCHAR(50),  -- Diputados, Senadores
    descripcion VARCHAR(500),
    total_votos INT,
    votos_afirmativos INT,
    votos_negativos INT,
    abstenciones INT,
    resultado VARCHAR(50),  -- aprobado, rechazado
    CONSTRAINT votos_validos CHECK (votos_afirmativos + votos_negativos + abstenciones = total_votos)
);

-- ============================================
-- TABLA: VOTO_INDIVIDUAL (Para auditoría)
-- ============================================
CREATE TABLE voto_individual (
    id_voto SERIAL PRIMARY KEY,
    id_votacion INT REFERENCES votaciones(id_votacion),
    id_legislador INT REFERENCES legisladores(id_legislador),
    voto VARCHAR(20),  -- favor, contra, abstención
    UNIQUE(id_votacion, id_legislador)
);

-- ============================================
-- TABLA: DICTAMENES
-- ============================================
CREATE TABLE dictamenes (
    id_dictamen SERIAL PRIMARY KEY,
    id_proyecto INT REFERENCES proyectos(id_proyecto),
    tipo_dictamen VARCHAR(50),  -- constitucionalidad, técnico, presupuestario, etc.
    fecha_dictamen TIMESTAMP,
    resultado VARCHAR(50),  -- válido, inválido, parcialmente_válido, viable, no_viable
    redactor VARCHAR(255),
    observaciones TEXT,
    recomendaciones TEXT,
    UNIQUE(id_proyecto, tipo_dictamen)
);

-- ============================================
-- TABLA: AUDITORIA (Todos los cambios)
-- ============================================
CREATE TABLE auditoria (
    id_log SERIAL PRIMARY KEY,
    id_proyecto INT REFERENCES proyectos(id_proyecto),
    timestamp TIMESTAMP DEFAULT NOW(),
    usuario VARCHAR(255),
    accion VARCHAR(100),  -- creado, modificado, clasificado, votado, etc.
    tabla_afectada VARCHAR(100),
    valor_anterior TEXT,
    valor_nuevo TEXT,
    ip_origen INET,
    detalles TEXT
);

-- ============================================
-- TABLA: VOZ/AUDIO METADATA
-- ============================================
CREATE TABLE audio_metadata (
    id_audio SERIAL PRIMARY KEY,
    id_proyecto INT REFERENCES proyectos(id_proyecto),
    tipo_audio VARCHAR(50),  -- ingreso, sesión, intervención
    fecha_captura TIMESTAMP,
    canal_ingreso VARCHAR(50),  -- teléfono, web, presencial
    duracion_segundos INT,
    confianza_transcripcion FLOAT,  -- 0-1
    transcripcion TEXT,
    url_s3 VARCHAR(500),  -- Ubicación en S3 del audio original
    procesado BOOLEAN DEFAULT FALSE
);

-- ============================================
-- TABLA: LEYES PROMULGADAS
-- ============================================
CREATE TABLE leyes (
    id_ley SERIAL PRIMARY KEY,
    numero_ley INT UNIQUE NOT NULL,
    titulo VARCHAR(500),
    id_proyecto_origen INT REFERENCES proyectos(id_proyecto),
    fecha_promulgacion DATE,
    fecha_vigencia DATE,
    decreto_numero VARCHAR(50),
    estado VARCHAR(50),  -- vigente, derogada, modificada
    url_gaceta_oficial VARCHAR(500),
    texto_oficial TEXT
);

-- ============================================
-- TABLA: MODIFICACIONES DE LEYES
-- ============================================
CREATE TABLE modificaciones_ley (
    id_modif SERIAL PRIMARY KEY,
    id_ley_original INT REFERENCES leyes(id_ley),
    id_proyecto_modificador INT REFERENCES proyectos(id_proyecto),
    tipo_modif VARCHAR(50),  -- deroga, modifica, complementa
    fecha_modif TIMESTAMP,
    descripcion TEXT
);
```

### 🗄️ MongoDB (Documentos Flexibles)

```javascript
// ===========================================
// COLECCIÓN: expedientes_digitales
// ===========================================
db.createCollection("expedientes_digitales", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["id_proyecto", "titulo"],
      properties: {
        _id: { bsonType: "objectId" },
        id_proyecto: { bsonType: "string", description: "PL-2024-001" },
        titulo: { bsonType: "string" },
        documento_original: { bsonType: "string", description: "PDF en base64" },
        transcripcion_voz: {
          bsonType: "object",
          properties: {
            texto: { bsonType: "string" },
            confianza: { bsonType: "double" },
            idioma: { bsonType: "string" },
            date: { bsonType: "date" }
          }
        },
        versiones: {
          bsonType: "array",
          items: {
            bsonType: "object",
            properties: {
              numero: { bsonType: "int" },
              fecha: { bsonType: "date" },
              origen: { bsonType: "string" },  // Diputados, Senadores, etc.
              cambios: { bsonType: "array" },
              url_documento: { bsonType: "string" }
            }
          }
        },
        dictamenes_completos: {
          bsonType: "object",
          properties: {
            constitucionalidad: { bsonType: "object" },
            consistencia_normativa: { bsonType: "object" },
            tecnico: { bsonType: "object" },
            presupuestario: { bsonType: "object" }
          }
        },
        acta_sesion: {
          bsonType: "object",
          properties: {
            cronologia: { bsonType: "array" },
            intervenciones: { bsonType: "array" },
            votacion: { bsonType: "object" },
            resumen: { bsonType: "string" }
          }
        },
        historial_completo: {
          bsonType: "array",
          items: {
            bsonType: "object",
            properties: {
              timestamp: { bsonType: "date" },
              evento: { bsonType: "string" },
              detalles: { bsonType: "string" },
              agente_responsable: { bsonType: "string" }
            }
          }
        }
      }
    }
  }
});

// ===========================================
// COLECCIÓN: registros_audio
// ===========================================
db.createCollection("registros_audio", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      properties: {
        _id: { bsonType: "objectId" },
        id_proyecto: { bsonType: "string" },
        tipo_audio: {
          enum: ["ingreso", "sesión", "intervención", "testimonio"]
        },
        fecha_captura: { bsonType: "date" },
        canal_ingreso: {
          enum: ["telefónico", "web", "presencial", "app_móvil"]
        },
        duracion_segundos: { bsonType: "int" },
        audio_base64: { bsonType: "string" },
        transcripcion: {
          bsonType: "object",
          properties: {
            texto_completo: { bsonType: "string" },
            confianza: { bsonType: "double" },
            puntos_clave: { bsonType: "array" },
            intención_detectada: { bsonType: "string" }
          }
        },
        metadata:
 {
          bsonType: "object",
          properties: {
            locutor_nombre: { bsonType: "string" },
            locutor_cedula: { bsonType: "string" },
            ip_origen: { bsonType: "string" },
            dispositivo: { bsonType: "string" },
            calidad_audio: { bsonType: "string" }  // excelente, buena, regular
          }
        },
        procesamiento_ia: {
          bsonType: "object",
          properties: {
            stt_engine: { enum: ["google_cloud", "azure", "openai"] },
            modelo_intención: { bsonType: "string" },
            entidades_identificadas: { bsonType: "array" },
            sentimiento: { enum: ["positivo", "neutral", "negativo"] }
          }
        }
      }
    }
  }
});

// ===========================================
// COLECCIÓN: respuestas_ciudadanas
// ===========================================
db.createCollection("respuestas_ciudadanas", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      properties: {
        _id: { bsonType: "objectId" },
        id_consulta: { bsonType: "string" },
        id_ciudadano: { bsonType: "string" },
        consulta_original: { bsonType: "string" },
        respuesta_generada: { bsonType: "string" },
        respuesta_audio: {
          bsonType: "object",
          properties: {
            base64: { bsonType: "string" },
            duracion: { bsonType: "int" },
            voz_seleccionada: { enum: ["femenina", "masculina"] },
            velocidad: { enum: ["lenta", "normal", "rápida"] },
            url_s3: { bsonType: "string" }
          }
        },
        satisfaccion_ciudadano: { bsonType: "int" },  // 1-5
        mejoras_sugeridas: { bsonType: "string" },
        timestamp: { bsonType: "date" }
      }
    }
  }
});
```

---

## Flujo de Voz STT/TTS

### 🎤 Captura de Audio (STT)

```python
import speech_recognition as sr
from google.cloud import speech_v1
import asyncio

class ModuloSTT:
    def __init__(self):
        self.client = speech_v1.SpeechClient()
        self.recognizer = sr.Recognizer()
    
    async def capturar_audio_web(self, audio_stream):
        """
        Captura audio desde navegador (Web Audio API)
        """
        config = speech_v1.RecognitionConfig(
            encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="es-BO",
            enable_automatic_punctuation=True,
            model="latest_long",
            use_enhanced=True
        )
        
        audio = speech_v1.RecognitionAudio(content=audio_stream)
        response = self.client.recognize(config=config, audio=audio)
        
        resultados = []
        for result in response.results:
            if result.alternatives:
                alternativa = result.alternatives[0]
                resultados.append({
                    "transcripcion": alternativa.transcript,
                    "confianza": alternativa.confidence,
                    "es_final": result.is_final
                })
        
        return resultados
    
    async def capturar_audio_telefono(self, numero_telefono):
        """
        Captura audio desde llamada telefónica
        """
        # Integración con Twilio o similar
        pass

class ProcesadorIntenciones:
    """
    Detecta intención del usuario
    """
    def __init__(self, client_openai):
        self.client = client_openai
    
    async def detectar_intención(self, transcripción):
        """
        Clasifica si es consulta, trámite, reclamo, etc.
        """
        prompt = f"""
        Analiza la siguiente consulta y clasifica su intención.
        Categorías: consulta_general, trámite_formal, reclamo, información_ley, otra
        
        Consulta: "{transcripción}"
        
        Responde en JSON:
        {{
            "intención": "consulta_general",
            "confianza": 0.95,
            "tema": "protección de datos",
            "requiere_derivación": true,
            "agente_destino": "Agente de Interacción"
        }}
        """
        
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return json.loads(response.choices[0].message.content)
```

### 🔊 Generación de Audio (TTS)

```python
from google.cloud import texttospeech
from elevenlabs import generate, stream

class ModuloTTS:
    def __init__(self, use_elevenlabs=True):
        self.use_elevenlabs = use_elevenlabs
        if not use_elevenlabs:
            self.tts_client = texttospeech.TextToSpeechClient()
    
    async def generar_respuesta_voz(self, texto_respuesta, configuracion):
        """
        Convierte texto de respuesta a audio natural
        
        configuracion = {
            "voz": "femenina" | "masculina",
            "velocidad": 1.0,  # 0.5 - 2.0
            "idioma": "es-BO"
        }
        """
        
        if self.use_elevenlabs:
            return await self._generar_elevenlabs(texto_respuesta, configuracion)
        else:
            return await self._generar_google_cloud(texto_respuesta, configuracion)
    
    async def _generar_google_cloud(self, texto, config):
        """Usa Google Cloud Text-to-Speech"""
        synthesis_input = texttospeech.SynthesisInput(text=texto)
        
        voice_params = {
            "femenina": ("es-BO-Neural2-A", "FEMALE"),
            "masculina": ("es-BO-Neural2-B", "MALE")
        }
        
        voice_name, ssml_gender = voice_params.get(
            config.get("voz", "femenina")
        )
        
        voice = texttospeech.VoiceSelectionParams(
            language_code="es-BO",
            name=voice_name,
            ssml_gender=ssml_gender
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=config.get("velocidad", 1.0),
            pitch=0.0
        )
        
        response = self.tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return response.audio_content
    
    async def _generar_elevenlabs(self, texto, config):
        """Usa ElevenLabs (más natural)"""
        voces = {
            "femenina": "EXAVITQu4vr4xnSDxMaL",  # ID de voz femenina en ElevenLabs
            "masculina": "21m00Tcm4TlvDq8ikWAM"   # ID de voz masculina
        }
        
        voice_id = voces.get(config.get("voz", "femenina"))
        
        audio = generate(
            text=texto,
            voice=voice_id,
            model="eleven_monolingual_v1",
            stream=False
        )
        
        return audio
```

### 🔄 Flujo Completo STT → Procesamiento → TTS

```python
from crewai import Agent, Task, Crew

class FlujoComunicacionVoz:
    def __init__(self, db_postgres, db_mongo):
        self.db_pg = db_postgres
        self.db_mongo = db_mongo
        self.stt = ModuloSTT()
        self.tts = ModuloTTS(use_elevenlabs=True)
        self.detector_intenciones = ProcesadorIntenciones()
    
    async def procesar_consulta_voz_completa(self, audio_stream, id_ciudadano):
        """
        Flujo end-to-end: Audio → Transcripción → Procesamiento → Respuesta → Audio
        """
        
        # PASO 1: STT - Convertir audio a texto
        print("▶ PASO 1: Transcribiendo audio...")
        resultados_stt = await self.stt.capturar_audio_web(audio_stream)
        
        if not resultados_stt or resultados_stt[0]["confianza"] < 0.7:
            respuesta = "No entendí bien tu consulta. ¿Puedes repetir, por favor?"
            audio_respuesta = await self.tts.generar_respuesta_voz(
                respuesta,
                {"voz": "femenina", "velocidad": 0.9}
            )
            return {"exito": False, "audio": audio_respuesta, "motivo": "baja_confianza_transcripción"}
        
        transcripcion = resultados_stt[0]["transcripcion"]
        confianza_stt = resultados_stt[0]["confianza"]
        
        # Guardar en MongoDB
        await self.db_mongo["registros_audio"].insert_one({
            "id_ciudadano": id_ciudadano,
            "tipo_audio": "ingreso",
            "fecha_captura": datetime.now(),
            "canal_ingreso": "web",
            "transcripcion": {
                "texto_completo": transcripcion,
                "confianza": confianza_stt
            }
        })
        
        # PASO 2: Detectar intención
        print("▶ PASO 2: Detectando intención...")
        intención = await self.detector_intenciones.detectar_intención(transcripcion)
        
        # PASO 3: Enrutar a agente especializado
        print(f"▶ PASO 3: Enrutando a {intención['agente_destino']}...")
        
        # Ejecutar crew de CrewAI basado en intención
        if intención["requiere_derivación"]:
            respuesta_texto = await self._ejecutar_crew_especializado(
                intención["agente_destino"],
                transcripcion,
                id_ciudadano
            )
        else:
            respuesta_texto = "Tu consulta ha sido registrada. Te contactaremos pronto."
        
        # PASO 4: TTS - Convertir respuesta a audio
        print("▶ PASO 4: Generando respuesta en voz...")
        config_voz = {
            "voz": "femenina",
            "velocidad": 1.0,
            "idioma": "es-BO"
        }
        audio_respuesta = await self.tts.generar_respuesta_voz(
            respuesta_texto,
            config_voz
        )
        
        # Guardar respuesta en MongoDB
        await self.db_mongo["respuestas_ciudadanas"].insert_one({
            "id_ciudadano": id_ciudadano,
            "consulta_original": transcripcion,
            "respuesta_generada": respuesta_texto,
            "respuesta_audio": {
                "duracion": len(audio_respuesta) // (16000 * 2),  # Aproximado
                "voz_seleccionada": "femenina",
                "velocidad": 1.0
            },
            "timestamp": datetime.now()
        })
        
        # PASO 5: Retornar respuesta al usuario
        print("▶ PASO 5: Reproduciendo respuesta...")
        return {
            "exito": True,
            "transcripcion": transcripcion,
            "respuesta": respuesta_texto,
            "audio": audio_respuesta,
            "intención": intención
        }
    
    async def _ejecutar_crew_especializado(self, agente_destino, consulta, id_ciudadano):
        """
        Ejecuta el crew de CrewAI correspondiente a la intención
        """
        
        if agente_destino == "Agente de Interacción":
            crew = self._crear_crew_interaccion()
        elif agente_destino == "Agente Distribuidor":
            crew = self._crear_crew_distribuidor()
        else:
            crew = self._crear_crew_generico()
        
        resultado = crew.kickoff(inputs={
            "consulta": consulta,
            "id_ciudadano": id_ciudadano
        })
        
        return resultado
```

---

## Implementación en Python (Partial)

### 📌 Estructura del Proyecto

```
crewai-legislativo-bolivia/
├── config/
│   ├── database.py           # Conexión PostgreSQL + MongoDB
│   ├── api_keys.env          # Claves API (Google, OpenAI, ElevenLabs)
│   └── constantes.py         # Constantes del proceso legislativo boliviano
├── agentes/
│   ├── agente_distribuidor.py
│   ├── agente_verificador_const.py
│   ├── agente_consistencia.py
│   ├── agente_especialista.py
│   ├── agente_presidencia.py
│   ├── agente_comisión_const.py
│   ├── agente_secretario.py
│   ├── agente_bicameral.py
│   ├── agente_veto.py
│   ├── agente_publicación.py
│   ├── agente_fiscalización.py
│   ├── agente_presupuesto.py
│   ├── agente_difusión.py
│   └── agente_interacción.py
├── tareas/
│   ├── tarea_distribución.py
│   ├── tarea_verificación.py
│   └── ...
├── tools/
│   ├── voz/
│   │   ├── stt.py             # Speech-to-Text
│   │   └── tts.py             # Text-to-Speech
│   ├── bases_datos/
│   │   ├── postgres.py
│   │   └── mongodb.py
│   ├── integraciones/
│   │   ├── twilio.py          # Para llamadas telefónicas
│   │   ├── gaceta_oficial.py
│   │   └── tribunal_const.py
│   └── utilidades/
│       ├── clasificador_materias.py
│       ├── detector_intenciones.py
│       └── generador_reportes.py
├── crews/
│   ├── crew_admisibilidad.py
│   ├── crew_debate.py
│   ├── crew_ciudadania.py
│   └── crew_master.py         # Orquestador principal
├── modelos/
│   ├── esquemas.py            # Pydantic models para validación
│   └── estados.py             # Estados del proceso legislativo
├── api/
│   ├── main.py               # FastAPI o similar
│   ├── rutas/
│   │   ├── proyectos.py
│   │   ├── ciudadania.py
│   │   ├── voz.py
│   │   └── reportes.py
│   └── middleware/
│       ├── autenticación.py
│       └── auditoria.py
├── tests/
│   ├── test_agentes.py
│   ├── test_voz.py
│   └── test_bd.py
├── logs/
│   └── sistema.log
├── requirements.txt
├── .env
├── docker-compose.yml
└── README.md
```

### 🔨 Instalación y Setup

```bash
# Clonar repositorio
git clone https://github.com/bolacomunista/crewai-legislativo-bolivia.git
cd crewai-legislativo-bolivia

# Crear ambiente virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus claves API

# Inicializar bases de datos
python scripts/init_db.py

# Ejecutar servidor
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### requirements.txt

```
# Frameworks & IA
crewai==0.12.0
crewai-tools==0.1.6
langchain==0.1.0
anthropic==0.25.0
openai==1.3.0

# Bases de datos
psycopg2-binary==2.9.9  # PostgreSQL
pymongo==4.6.0          # MongoDB
sqlalchemy==2.0.23

# Voz & Audio
google-cloud-speech==2.25.0
google-cloud-texttospeech==2.14.0
elevenlabs==0.2.0
PyAudio==0.2.13
librosa==0.10.0

# Web & API
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
python-multipart==0.0.6

# Utilidades
python-dotenv==1.0.0
requests==2.31.0
aiohttp==3.9.1
pandas==2.1.3
openpyxl==3.10.10  # Para exportar reportes Excel

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# Logging & Monitoring
python-json-logger==2.0.7
sentry-sdk==1.38.0
```

---

## Conclusiones

Este documento proporciona una arquitectura completa de un **Sistema Multiagente CrewAI** para el proceso legislativo boliviano, integrando:

✅ **14 Agentes especializados** con roles claramente definidos  
✅ **Módulo de Voz bidireccional** (STT/TTS)  
✅ **Base de Datos híbrida**: PostgreSQL + MongoDB  
✅ **Cumplimiento normativo boliviano**: CPE, Ley 1630, etc.  
✅ **Auditoría completa** de cada etapa del proceso  
✅ **Experiencia ciudadana mejorada** con comunicación natural  

---

## Referencias

- **Constitución Política del Estado Plurinacional de Bolivia (2009)**
- **Ley Nº 1630 - Reglamento de la Asamblea Legislativa Plurinacional**
- **Ley Nº 1369 - Ley de Gobierno Electrónico**
- CrewAI Documentation: https://docs.crewai.com/
- PostgreSQL Documentation: https://www.postgresql.org/docs/
- MongoDB Documentation: https://docs.mongodb.com/
- Google Cloud Speech API: https://cloud.google.com/speech-to-text

---

**Autor**: Sistema IA | **Fecha**: Enero 2024 | **Versión**: 1.0
