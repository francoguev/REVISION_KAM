# Especificación Técnica de Diseño: Tabla Presentación

Todas las tablas construidas en el informe ejecutivo deben guiarse por el estándar visual **Tabla Presentación**:

## 📐 1. Estructura del Contenedor y Dimensiones
- **Contenedor Tarjeta (`.table-slide-card`, `.table-container-card`)**:
  - Fondo: Blanco puro (`#ffffff`).
  - Borde Exterior: `1px solid #e2e8f0` (Gris Pizarra claro).
  - Forma de Bordes: Esquinas redondeadas suaves (`border-radius: 12px`).
  - Contención: `overflow: hidden` (corta esquinas del encabezado).
- **Área de Desplazamiento (`.table-scroll-area`, `.table-scroll-wrapper`)**:
  - Scroll dinámico vertical y horizontal (`overflow-y: auto`, `overflow-x: auto`).
  - Encabezado fijo al scroll vertical (`position: sticky; top: 0; z-index: 20`).

## 🎨 2. Colores, Bordes y Alturas por Tipo de Fila
### 🏢 A. Encabezado (`thead th`)
- Fondo: Azul Marino Profundo Sólido (`background-color: #0f172a`).
- Color de Texto: Blanco Grisáceo (`color: #f1f5f9`).
- Borde Inferior: `2px solid #1e293b` (Azul Noche).
- Altura de Celda (Padding): `padding: 10px 8px` (Altura total aprox.: 34px).
- Hover en Columnas Ordenables: Texto cambia a Celeste Neón (`color: #38bdf8`).

### 🧮 B. Fila de Total General (`.row-grand-total`)
- Fondo: Gradiente Ejecutivo Oscuro (`linear-gradient(135deg, #0f172a, #1e293b)`).
- Color de Texto: Blanco Sólido (`color: #ffffff`).
- Borde Inferior: Acento Azul Rey brillante (`2px solid #3b82f6`).
- Altura de Celda (Padding): `padding: 10px 10px` (Altura total aprox.: 36px).
- **Sin Iconos**: La fila Total General NO lleva icono de calculadora ni prefijo gráfico en la primera columna; muestra únicamente el texto en blanco extra negrita (`TOTAL FORTALECERNOS`).

### 👤 C. Filas de Supervisor (`.row-spv`)
- Fondo: Gris/Azul de baja saturación (`background: #f8fafc`).
- Fondo Hover: `#f1f5f9`.
- Color de Texto: Azul Noche (`color: #0f172a`).
- Borde Inferior: Línea ultra fina (`1px solid #f1f5f9`).
- Altura de Celda (Padding): `padding: 8px 10px` (Altura total aprox.: 32px).

### 🏬 D. Filas de Punto de Venta / PDV (`.row-pdv`, `.row-pdv-shaded`)
- Fondo: Blanco Puro (`background: #ffffff`).
- Fondo Hover: `#f8fafc`.
- Color de Texto: Gris Pizarra Oscuro (`color: #334155`).
- Borde Inferior: Línea ultra fina (`1px solid #f1f5f9`).
- Altura de Celda (Padding): `padding: 8px 10px` (Altura total aprox.: 32px).

### 👨‍💼 E. Filas de Asesor (`.row-asesor`)
- Fondo: Blanco Puro (`background: #ffffff`).
- Fondo Hover: Azul translúcido muy suave (`rgba(59, 130, 246, 0.04)`).
- Color de Texto (Código/User): Gris Pizarra (`color: #64748b`).
- Color de Texto (Nombre Real): Gris Claro (`color: #64748b` en 9.5px).
- Borde Inferior: Línea ultra fina (`1px solid #f1f5f9`).
- Altura de Celda (Padding): `padding: 8px 10px` (Altura total aprox.: 32px).

## 🔤 3. Tipografía, Pesos y Alineación
- Fuente General: Sistema San-Serif Limpio (`Inter`, `system-ui`, `Segoe UI`, `Roboto`).
- **Primera Columna Estandarizada**: El título obligatorios para la primera columna de la estructura en todas las tablas es siempre **`PUNTO DE VENTA / ASESOR`**.
- Tamaños de Fuente:
  - Encabezados: `10.5px`, Negrita (`font-weight: 700`), Mayúsculas (`text-transform: uppercase`), Espaciado de letras (`letter-spacing: 0.5px`).
  - Total General: `12.5px`, Extra Negrita (`font-weight: 800`).
  - Supervisor: `11.5px`, Extra Negrita (`font-weight: 800`).
  - PDV / Tienda: `11.5px`, Negrita media (`font-weight: 600`).
  - Asesor: `11px`, Regular (`font-weight: 400`).
- Alineación:
  - Primera Columna (`ESTRUCTURA` / `PDV`): Izquierda (`text-align: left`).
  - Celdas de Valores: Centro (`text-align: center`).
- Anti-desbordamiento: `white-space: nowrap`.

## 📐 4. Sangrías Jerárquicas
- Total General / Supervisor: `padding-left: 0px` (Indent 0).
- PDV / Tienda: `padding-left: 18px` (Indent 1).
- Asesor: `padding-left: 36px` (Indent 2).
- Botón Desplegable Chevron (`.toggle-icon`): `18px x 18px`, `border-radius: 4px`, `#e2e8f0` fondo, `#0f172a` icono.

## 🏷️ 5. Indicadores Específicos por Página
- Se respetan únicamente insignias exclusivas (ej. Claro en Rojo en Página 7, Calidad NPS en Página 4, Mix de Planes en Página 5).

## ⭐ 6. Ordenamiento Específico por Vista
- **Página 4 (Reporte de Calidad y NPS)**:
  - Los PDVs se ordenan **de mayor a menor TOTAL NPS** (descendente).
  - A nivel interno dentro de cada PDV, los Asesores se ordenan **de mayor a menor TOTAL NPS** (descendente).
  - Las tablas de NPS deben estar **comprimidas/contraídas por defecto hasta nivel PDV** (se expanden para mostrar asesores únicamente a demanda del usuario).
  - Esta regla aplica dinámicamente tanto para la pestaña **NPS VENTA** como para **NPS POSTVENTA** y se mantiene vigente para futuras cargas de datos.

## 🏷️ 7. Regla Estricta de Unidades de Medida
- La **ÚNICA unidad de medida explícita** que se permite mostrar en celdas, tarjetas e insignias de todas las tablas es el símbolo de Porcentaje (**`%`**).
- Se prohíbe el uso de la letra `Q` como sufijo de encuestas (ej. `(1Q)` → `(1)`, `(4Q)` → `(4)`). Se conserva la cifra entre paréntesis indicando la cantidad de respuestas, pero retirando únicamente la letra `Q`.

## 📅 8. Regla Estricta de Proyección y Días Hábiles (Página 1)
- Cada vez que el usuario pida actualizar los datos del informe porque actualizó el Excel, **el asistente DEBE pedir SIEMPRE confirmación de los Días Totales y Días Transcurridos** antes de calcular las proyecciones de la Página 1.
- La fórmula de proyección en la Página 1 se calcula estrictamente como: `Proyección (UND) = Math.round((Ventas / Días Transcurridos) * Días Totales)`.
- Los mismos valores confirmados alimentan las columnas calculadas de todos los productos de la Página 1: `IDEAL = Math.round((Cuota / Días Totales) * Días Transcurridos)` y `GAP = Avance - IDEAL`.
- `IDEAL` se muestra como entero. `GAP` conserva únicamente el diseño de flecha/color de `VAR VS MES ANTERIOR`: flecha arriba para positivo, flecha abajo para negativo y sin porcentaje.
- No se cuentan domingos en el cómputo de días hábiles transcurridos.

## ⚙️ 9. Regla Estricta de Actualización Automatizada de Datos (Master Pipeline Rule)
- Cada vez que el usuario solicite actualizar los datos del informe porque actualizó el archivo `INFORME DE AVANCE.xlsx`:
  1. **Confirmación Obligatoria**: Solicitar siempre la confirmación de los Días Hábiles Transcurridos y Días Hábiles Totales para la Página 1 (por ejemplo, 8/26).
  2. **Ejecución del Pipeline en 1 Segundo**: Ejecutar el script automatizado `python update_dashboard_data.py <dias_transcurridos> <dias_totales>` desde la raíz del proyecto local.
  3. **Alcance Automatizado**: El script procesa automáticamente todas las hojas del Excel (`POST + PRE`, `RENO SS`, `CUOTAS`, `ARRIBOS`, `ZONAS`, `MIX PLANES`, `PERMANENCIA`) para actualizar las Páginas 0, 1, 2, 3, 4, 5.
  4. **Normalización Estricta de Planes (Página 4)**: Normaliza automáticamente las variaciones de nombres de planes con/sin sufijo `" N"` (`Power 39.90`, `Power Ilim 79.90 SD`, etc.) garantizando una coincidencia exacta al 100% con el Postpago Total de la Página 1 (513 Unidades == 513 Unidades).
  5. **Verificación Estricta en Local**: Ejecutar la prueba de renderizado en Node.js para garantizar 0 errores en las 8 páginas antes de concluir la tarea.

## 🗓️ 10. Regla Estricta de Filtro de Camadas en Permanencia (Página 5)
- La Página 5 (Permanencia) no debe mostrar todas las camadas a la vez.
- Utiliza la columna `CAMADAS` de la hoja `PERMANENCIA` (`AGOSTO`, `JULIO`, `JUNIO`, `ENERO`) como selector de mes dinámico.
- Por defecto, el filtro selecciona **Agosto 2026**.
- Al cambiar el selector, se recalculan y actualizan dinámicamente las tarjetas de KPI y la tabla jerárquica de PDVs y Asesores.

## 🧱 11. Regla Estricta de Independencia entre Páginas
- Cada página mantiene sus estilos exclusivamente en `styles/page-N.css`, donde `N` corresponde a su número de página.
- Todo selector de una hoja `page-N.css` debe estar limitado por `#slidePageN`; queda prohibido aplicar desde ella reglas a otra página.
- `styles/shell.css` se reserva únicamente para la estructura exterior: lienzo, contenedor, navegación, pie y panel lateral. No puede contener estilos internos de tablas, cabeceras o tarjetas de las páginas.
- Aunque dos páginas compartan inicialmente colores, tipografías o dimensiones, cada una debe declarar sus propios valores dentro de su archivo. Una modificación visual puntual no puede propagarse a otra página.
- El estado interactivo se guarda en `pageState[N]`. Filtros, búsquedas, ordenamiento, expansiones y selectores de una página no pueden reutilizar el estado de otra.
- Todos los elementos interactivos deben tener identificadores únicos. Se prohíbe reutilizar un mismo `id` en páginas diferentes.
- Antes de concluir cualquier cambio se ejecuta `node verify_dashboard.js`, que debe validar aislamiento, identificadores, unidades permitidas y funcionamiento de las ocho páginas.

## 📆 12. Regla Estricta de Filtros Mensuales
- Todo filtro de mes muestra únicamente meses individuales disponibles en sus datos.
- El mes actual debe aparecer preseleccionado; para el informe vigente es **Agosto**.
- Las opciones se rotulan exclusivamente con el nombre del mes: `Agosto`, `Julio`, `Junio`, etc.
- Quedan prohibidos años, emojis, indicadores relativos y cualquier sufijo en las opciones, incluidos `M-1`, `M-2`, `Mes vigente` y `Cierre`.
- Quedan prohibidas las opciones que agrupen períodos, como `Todos los meses`, `Últimos 3 meses`, acumulados o rangos equivalentes.
- Cuando una tabla compare contra otro mes, debe mostrar el nombre real del mes (`Julio`, por ejemplo) y nunca una etiqueta relativa como `M-1`.
- `verify_dashboard.js` debe impedir que vuelvan a introducirse opciones mensuales agrupadas, etiquetas relativas o sufijos de unidades como `u.`.

## 👥 13. Regla de Antigüedad de Asesores (Página 1)
- La hoja `USUARIOS` es la fuente oficial para la fecha de ingreso y el estado de cada asesor.
- En la estructura `PUNTO DE VENTA / ASESOR` de la Página 1, cada asesor muestra junto a su nombre una de estas categorías: `0 a 30 días`, `1 a 3 meses`, `3 a 6 meses`, `6 meses a un año` o `Mayor a un año`.
- La categoría activa incluye entre paréntesis la fecha exacta de `FECHA INGRESO` con formato `dd/mm/aaaa`.
- Si `FECHA INGRESO` contiene `CESE`, `CESADO` o `CESADA`, se muestra únicamente `Cesado`, sin categoría ni fecha.
- Si un asesor de ventas no existe en `USUARIOS` o no tiene una fecha válida, se muestra `Sin registro`; nunca se inventa una fecha o categoría.
- Esta información se genera nuevamente desde el Excel en cada ejecución de `update_dashboard_data.py` y se aplica exclusivamente a la Página 1.
- Las expresiones de tiempo de esta regla son una excepción explícita a la restricción general de unidades, porque describen antigüedad laboral y no una métrica comercial.
