# HUMAN-GATES.md — Política de Control Humano Proporcional al Riesgo
> **Proyecto:** SMA Congreso (Sistema Multi-Agente Legislativo Boliviano — Prometheus PDT v2.0)  
> **Principio Rector:** *"Ningún proceso automatizado sustituye la fe pública parlamentaria ni la soberanía del operador sobre el código y los datos de producción."*

---

## 1. Justificación y Matriz de Riesgo del Proyecto

Este sistema automatiza etapas del proceso de formación de leyes del Estado Plurinacional de Bolivia, interactuando con bases de datos relacionales críticas (PostgreSQL Neon), bases de datos documentales (MongoDB Atlas), búsqueda semántica vectorial (`pgvector` de 2048 dimensiones) e inferencia de modelos de lenguaje grande (NVIDIA NIM).

Un error no controlado en este repositorio puede ocasionar:
1. **Corrupción del ordenamiento legal:** Dictámenes falsos de inconstitucionalidad o antinomia por alucinación de citas.
2. **Violación de la CPE:** Auto-promulgación de leyes sin la sanción bicameral ni la firma del Presidente del Estado (violación de los Arts. 163 y 164 CPE).
3. **Pérdida de integridad de datos:** Alteración del esquema relacional `sistema.*` en Neon o borrado de bitácoras inmutables.
4. **Fuga de secretos de Estado o credenciales:** Exposición de API keys de NVIDIA NIM, tokens de Google Drive o credenciales de conexión.

Por tanto, se establecen **tres niveles de control humano vinculantes**:

---

## Nivel 1: Automático sin Gate (Bajo Riesgo / Reversible)

Cambios rutinarios, acotados y totalmente reversibles que pueden ser aplicados directamente por el desarrollador o el agente de IA, siempre que se verifiquen con herramientas automatizadas antes del commit.

### ¿Qué califica en este nivel?
* Mejoras de redacción en documentación markdown (`README.md`, `docs/`, `AGENTS.md`).
* Adición o corrección de pruebas unitarias (`test_*.py`, `frontend/scripts/*.mjs`).
* Refactorizaciones cosméticas internas que no alteren la firma pública ni el JSON de salida.
* Ajustes de estilos CSS o micro-componentes visuales en `frontend/src/`.

### Verificación Obligatoria para aprobar el cambio:
1. `npm run lint` en `frontend/` $\rightarrow$ Cero errores.
2. `python test_14_agentes.py` $\rightarrow$ Código de salida 0.
3. `npm run build` $\rightarrow$ Compilación exitosa en `dist/`.

---

## Nivel 2: Gate de Revisión de Pull Request (Riesgo Medio)

Toda nueva funcionalidad, cambio en la lógica de inferencia o ajuste en la comunicación inter-agente debe presentarse mediante Pull Request (PR) y requiere revisión humana de código antes de incorporarse a la rama `main`.

### ¿Qué califica en este nivel?
* Refactorización o adición de prompts en `sma_unified/config/agents.yaml` o `tasks.yaml`.
* Modificación de la lógica interna de los agentes en `sma_unified/agents/`.
* Creación de nuevos endpoints en `server.py` o nuevos componentes en `frontend/src/pages/`.
* Modificación de reglas heurísticas o de búsqueda en `verificador_constitucional.py` o `consistencia_normativa.py`.

### Lista de Comprobación Obligatoria para el Revisor Humano:
- [ ] **Diff exhaustivo leído:** El PR no excede los 300 renglones de cambio neto.
- [ ] **Contratos JSON verificados:** No se renombraron ni eliminaron claves raíz obligatorias (`dictamen_fondo`, `acta_debate`, `ciclo_bicameral`, `evaluacion_veto`, etc.).
- [ ] **Candado anti-alucinación activo:** Se mantiene el principio de *"Sin cita textual verificable, el hallazgo no existe"*.
- [ ] **Criterio de fin demostrado:** Se adjunta la captura o log del comando de verificación especificado en el `SPEC.md` correspondiente.

---

## Nivel 3: Gate de Aprobación Explícita (Alto Riesgo / Acciones Críticas)

Operaciones que tienen impacto directo en infraestructura, persistencia de datos, seguridad, cumplimiento legal constitucional o despliegue. **Nadie —ni humano ni agente de IA— puede ejecutarlas sin la autorización expresa, escrita y registrada del propietario del proyecto.**

### LISTA TAXATIVA DE ACCIONES QUE REQUIEREN GATE EXPLÍCITO:

1. **Migraciones y DDLs de Base de Datos:**
   * Ejecución de scripts de migración (e.g., `aplicar_migracion_*.py`, `cargar_normativa.py`, `cargar_reglamentos_profesionales.py`).
   * Creación, modificación o eliminación de tablas, columnas, vistas o índices en el esquema `sistema.*` de PostgreSQL Neon.
   * Modificación de dimensiones vectoriales (cambio de 2048d) o funciones de similitud en `pgvector`.
2. **Gestión de Secretos y Configuración de Red:**
   * Modificación o creación de variables en el archivo `.env`.
   * Rotación o cambio de credenciales (`NEON_DATABASE_URL`, `MONGO_URI`, `NVIDIA_API_KEY`, SendGrid o Google Drive).
   * Modificación de reglas de proxy en [frontend/vite.config.js](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/vite.config.js) o puertos del servidor en [server.py](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/server.py).
3. **Dependencias del Ecosistema:**
   * Adición o actualización de paquetes en `requirements.txt` o `package.json`.
   * Especial atención al conflicto de librerías PDF (`fpdf` vs `fpdf2`).
4. **Circuito Constitucional y Freno Humano del Workflow:**
   * Modificación de las reglas de aprobación humana en [workflows.yaml](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/sma_unified/config/workflows.yaml) (`control_aprobacion.requiere_aprobacion_humana`).
   * Desactivación de validaciones matemáticas de quórum o votación en `control_legislativo.py`.
   * Cualquier lógica que intente auto-promulgar una ley sin la intervención del rol `Presidente` o `Senador`.
5. **Despliegues y Operaciones en Producción:**
   * Despliegue de nuevas versiones del servidor FastAPI o del cliente web.
   * Ejecución de scripts que borren colecciones en MongoDB Atlas o ejecuten `DROP TABLE / TRUNCATE`.

---

## Protocolo de Registro de Aprobación para Nivel 3

Antes de ejecutar cualquiera de las acciones de Nivel 3, el agente de IA o colaborador debe:
1. Exponer claramente:
   * **Qué acción se va a ejecutar.**
   * **Por qué es necesaria.**
   * **El impacto exacto y reversibilidad (plan de rollback).**
2. Esperar la instrucción confirmatoria del usuario (e.g., *"Aprobado, procede con la migración 004"*).
3. Registrar la acción en la bitácora transaccional (`sistema.bitacora_proceso`) indicando el usuario responsable.
