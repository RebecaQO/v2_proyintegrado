# TASKS: Desglose Atómico de Tareas de Implementación
> **Plan Asociado:** [docs/specs/PLAN.md](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/docs/specs/PLAN.md) (PLAN-001)  
> **Especificación:** [docs/specs/SPEC.md](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/docs/specs/SPEC.md) (SPEC-001)  
> **Cobertura:** 100% de los 14 Agentes Legislativos Canónicos + 4 Agentes Auxiliares (18 Componentes)

---

## Matriz de Tareas Atómicas y Criterios de Aceptación

| ID | Tarea / Alcance | Estado | Dependencia | Archivos Involucrados | Criterio de Aceptación Verificable |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **T-01** | **Auditar y asegurar línea base del sistema** | [x] | Ninguna | `test_14_agentes.py`, `agents.yaml` | `python test_14_agentes.py` sale con código 0; 16 agentes y 5 fases verificadas. |
| **T-02** | **Centralizar plantillas de prompts en `agents.yaml`** | [x] | T-01 | `sma_unified/config/agents.yaml` | Los 18 agentes cuentan con `prompt_framework`, `system_prompt_template` y `user_prompt_template` sin errores YAML. |
| **T-03** | **Implementar cargador dinámico en `base_agent.py`** | [x] | T-02 | `sma_unified/agents/base_agent.py` | `get_prompt_templates(nombre_agente)` retorna tupla de strings no vacíos para cada uno de los 18 agentes. |
| **T-04** | **Refactorizar Fase 1: Admisión y Ciudadanía** | [x] | T-03 | `distribuidor.py`, `multiagente_ciudadano.py`, `ciudadana.py`, `correspondencia.py` | Clasificación devuelve categorías exactas; router ciudadano opera sin error. |
| **T-05** | **Refactorizar Fase 2A: Auditoría Normativa y RAG** | [x] | T-04 | `verificador_constitucional.py`, `consistencia_normativa.py` | `python test_cotejo_constitucional.py` pasa 10/10 tests; candado literal CPE activo. |
| **T-06** | **Refactorizar Fase 2B: Dictámenes Especializados** | [x] | T-05 | `especialista_tecnico.py`, `presidencia_comision.py`, `constitucion_fondo.py`, `presupuesto.py` | Retornos preservan `dictamen_tecnico`, `plan_comision`, `dictamen_fondo` y `evaluacion_fiscal`. |
| **T-07** | **Refactorizar Fase 2C: Concentrador Forense Nivel 3** | [x] | T-06 | `concentrador.py`, `emisor_resultados.py` | Generación de `expediente_consolidado` y compilación de PDF formal en letra negra con `fpdf2`. |
| **T-08** | **Refactorizar Fase 3: Plenario Camaral y Bicameral** | [x] | T-07 | `secretario.py`, `bicameral.py`, `control_legislativo.py` | `python test_decision_bicameral.py` pasa 3/3; freno humano `PENDIENTE_APROBACION_HUMANA` activo. |
| **T-09** | **Refactorizar Fase 4: Ejecutivo y Publicación Oficial** | [x] | T-08 | `veto_promulgacion.py`, `publicacion.py` | Evaluación multicriterio ponderada calcula score; asignación correlativa de Ley y 15 días de vigencia. |
| **T-10** | **Refactorizar Fase 5: Comunicación, Control y Notificaciones** | [x] | T-09 | `difusion_ciudadana.py`, `fiscalizacion.py`, `notificador_comision.py`, `notificador_camara_opuesta.py` | Guía en Lenguaje Claro generada con FAQ; alertas a Contraloría estructuradas; despacho HTML verificado. |
| **T-11** | **Verificación Integral y Pruebas de Regresión** | [x] | T-10 | Todos los archivos modificados | `python test_14_agentes.py`, `python test_decision_bicameral.py` y `npm run lint` en frontend salen con código 0. |

---

## Protocolo de Ejecución para el Desarrollador / Agente

1. **Secuencialidad Obligatoria:** No iniciar una tarea sin que sus dependencias inmediatas estén marcadas con `[x]`.
2. **Validación en Consola:** Antes de marcar `[x]`, ejecutar el comando exacto listado en la columna *Criterio de Aceptación Verificable*.
3. **Resguardo de Contratos JSON:** Bajo ninguna circunstancia alterar las claves canónicas esperadas por el frontend y por [server.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/server.py).
4. **Human Gate:** Al culminar `T-03` y `T-08`, detener la ejecución para requerir validación explícita del operador humano.
