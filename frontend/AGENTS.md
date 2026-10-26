# AGENTS.md — Subdirectorio Frontend (React 19 + Vite)
> **Ámbito:** `frontend/` (Prevalece sobre el AGENTS.md raíz para tareas de frontend)

---

## 1. Comandos Verificados del Frontend

| Acción | Comando | Descripción |
| :--- | :--- | :--- |
| **Instalar Dependencias** | `npm install` | Instala librerías React 19, Vite, Lucide y plugins. |
| **Servidor de Desarrollo**| `npm run dev` | Inicia en `http://localhost:5173` con HMR activo. |
| **Linting Rápido** | `npm run lint` | Ejecuta `oxlint` sobre todos los componentes JSX. |
| **Compilar Producción** | `npm run build` | Compila en `dist/` usando Vite y Rollup. |
| **Previsualizar Build** | `npm run preview` | Sirve la carpeta `dist/` localmente. |

---

## 2. Convenciones Específicas de Frontend

1. **Proxy y Conectividad:**
   * El archivo [vite.config.js](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/vite.config.js) rutea automáticamente las peticiones `/api/*` y `/uploaded_files/*` a `http://127.0.0.1:8085`.
   * En desarrollo, no hardcodear URLs absolutas `http://localhost:8085` en las llamadas `fetch` o `axios`; usar rutas relativas `/api/...`.
2. **Ciclo de Vida de Agentes en la UI:**
   * El flujo visual principal reside en [src/components/HorizontalAgentFlow.jsx](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/src/components/HorizontalAgentFlow.jsx) y [src/pages/MesaPartes.jsx](file:///c:/Users/julio/Downloads/Proyectos_2026/v2_proy/v2_proyintegrado/frontend/src/pages/MesaPartes.jsx).
   * Al agregar o modificar estados de un agente, se deben sincronizar los identificadores (`distribuidor`, `comision`, `constitucional`, `consistencia`, `concentrador`, `secretario`, `bicameral`, `veto_promulgacion`, `publicacion`).
3. **Manejo de Errores en Peticiones:**
   * Todo llamado a la API debe contar con bloque `try/catch` y presentar alertas amigables al usuario mediante toast o banners de error (`errorMessage`), evitando que la UI quede congelada en estado de carga.
