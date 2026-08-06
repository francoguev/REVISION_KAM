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
