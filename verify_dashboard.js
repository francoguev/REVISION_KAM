const fs = require('fs');
const path = require('path');
const vm = require('vm');

const projectDir = __dirname;
const html = fs.readFileSync(path.join(projectDir, 'index.html'), 'utf8');
const dataCode = fs.readFileSync(path.join(projectDir, 'data.js'), 'utf8');
const scriptMatch = html.match(/<script src="data\.js[^>]*><\/script>\s*<script>([\s\S]*?)<\/script>\s*<\/body>/i);

if (!scriptMatch) {
  throw new Error('No se encontró el script principal del dashboard.');
}

const elements = new Map();
const defaultValue = (id) => {
  if (id === 'monthFilter') return 'm202608';
  if (id === 'dotacionPeriodFilter') return '9-15';
  if (/month/i.test(id)) return 'Agosto';
  if (/zone|spv/i.test(id)) return 'ALL';
  return '';
};

const createElement = (id = '') => ({
  id,
  value: defaultValue(id),
  className: '',
  innerHTML: '',
  textContent: '',
  style: {},
  children: [],
  classList: {
    add() {},
    remove() {},
    toggle() {},
    contains() { return false; },
  },
  appendChild(child) { this.children.push(child); return child; },
  setAttribute() {},
  addEventListener() {},
  focus() {},
});

const documentMock = {
  body: createElement('body'),
  addEventListener() {},
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, createElement(id));
    return elements.get(id);
  },
  createElement() { return createElement(); },
  querySelectorAll() { return []; },
};

const sandbox = {
  console,
  document: documentMock,
  setTimeout,
  clearTimeout,
  setInterval,
  clearInterval,
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(`${dataCode}\n${scriptMatch[1]}`, sandbox, { filename: 'dashboard.bundle.js' });

const failures = [];
const check = (condition, message) => {
  if (!condition) failures.push(message);
};
const run = (label, fn) => {
  try {
    fn();
    console.log(`[OK] ${label}`);
  } catch (error) {
    failures.push(`${label}: ${error.message}`);
  }
};

for (let page = 0; page <= 7; page += 1) {
  run(`Página ${page}`, () => sandbox.switchSlidePage(page));
}

run('Tabla de ventas', () => sandbox.renderTreeTable());
run('Tabla de descuentos', () => sandbox.renderDiscountTable());
run('Tabla de operador cedente', () => sandbox.renderCedenteTable());
run('Tabla de mix de planes', () => sandbox.renderMixPlanesTable());
run('Tabla de permanencia', () => sandbox.renderPermanenciaTable());
run('Tabla de dotación', () => sandbox.renderDotacionTable());
for (const period of ['5-11', '9-15']) {
  run(`Tabla de dotación ${period}`, () => {
    documentMock.getElementById('dotacionPeriodFilter').value = period;
    sandbox.renderDotacionTable();
    const periodData = sandbox.DOTACION_DATA.periods[period];
    check(documentMock.getElementById('toggleDaysText').textContent.includes(`${periodData.daily_headers[0]} - ${periodData.daily_headers[periodData.daily_headers.length - 1]}`), `El encabezado diario no corresponde al periodo ${period}.`);
    check(documentMock.getElementById('dotacionKpiCards').innerHTML.includes(`${periodData.summary.hc_obj} Asesores`), `Los indicadores superiores no corresponden al periodo ${period}.`);
  });
}
run('NPS Venta', () => sandbox.selectNpsChannel('venta'));
run('NPS Postventa', () => sandbox.selectNpsChannel('postventa'));
run('Semanas NPS', () => sandbox.toggleNpsWeeks());

const postpagoAugust = sandbox.SALES_DATA.summary.global_units.POSTPAGO_TOTAL.m202608;
const mixAugust = sandbox.MIX_PLANES_DATA.months.Agosto.summary.total;
check(postpagoAugust === mixAugust, `Mix de planes (${mixAugust}) no coincide con Postpago (${postpagoAugust}).`);

for (const channel of ['venta', 'postventa']) {
  const pdvs = sandbox.NPS_DATA[channel].pdvs;
  check(pdvs.every((item, index) => index === 0 || pdvs[index - 1].total_nps >= item.total_nps), `Los PDV de NPS ${channel} no están ordenados de mayor a menor.`);
  check(pdvs.every((pdv) => (pdv.children || []).every((item, index) => index === 0 || pdv.children[index - 1].total_nps >= item.total_nps)), `Los asesores de NPS ${channel} no están ordenados de mayor a menor.`);
}
check(sandbox.NPS_DATA.venta.summary.total_nps === 50, 'El NPS total de Venta debe ser 50%.');
check(sandbox.NPS_DATA.venta.summary.total_q === 8, 'El total de encuestas de Venta debe ser 8.');
check(sandbox.NPS_DATA.venta.summary.sem1_nps === 50 && sandbox.NPS_DATA.venta.summary.sem1_q === 8, 'SEM1 de Venta no coincide con el Excel.');
check(sandbox.NPS_DATA.venta.summary.sem5_nps === undefined && sandbox.NPS_DATA.venta.summary.sem5_q === undefined, 'Venta conserva una SEM5 que ya no existe en el Excel.');
check(sandbox.NPS_DATA.postventa.summary.total_nps === -50 && sandbox.NPS_DATA.postventa.summary.total_q === 2, 'El resumen de Postventa no coincide con el Excel.');
check(/const weeklyResults = availableWeeks\.map/.test(html) && !html.includes("SEM3 (89% NPS)"), 'La baldosa Pico Semanal no se calcula dinámicamente.');
check(/function getAvailableNpsWeeks\(channelData\)/.test(html), 'La Página 7 no limita las columnas a las semanas disponibles.');
check(!html.includes('Mostrar Semanas (SEM1 - SEM5)'), 'El control semanal anuncia semanas inexistentes.');
check(!/\$\{totNps\.toFixed\(0\)\}% \$\{getNpsBadgeHTML/.test(html), 'La baldosa NPS Logrado repite el porcentaje.');
check(/id="tabNpsVenta"[\s\S]*?NPS VENTA\s*<\/button>/.test(html), 'El selector de NPS Venta contiene texto adicional.');
check(/id="tabNpsPostventa"[\s\S]*?NPS POSTVENTA\s*<\/button>/.test(html), 'El selector de NPS Postventa contiene texto adicional.');
check(!/NPS (?:VENTA|POSTVENTA) \([^)]*\)/.test(html), 'Los selectores NPS todavía contienen texto entre paréntesis.');
const ventaExpected = {
  'TE PISCO': [-100, 1, 12.5],
  'TE ICA 3': [33.3, 3, 37.5],
  'TE ICA II': [100, 1, 12.5],
  'TE NAZCA': [100, 1, 12.5],
  'TE SATELITE BARRIO CHINO': [100, 2, 25],
};
for (const pdv of sandbox.NPS_DATA.venta.pdvs) {
  const expected = ventaExpected[pdv.name];
  check(Boolean(expected) && pdv.total_nps === expected[0] && pdv.total_q === expected[1] && pdv.total_pct_q === expected[2], `${pdv.name} no coincide con NPS VENTA.`);
}
const postventaExpected = {
  'TE ICA II': [0, 1, 50],
  'TE SATELITE BARRIO CHINO': [-100, 1, 50],
};
for (const pdv of sandbox.NPS_DATA.postventa.pdvs) {
  const expected = postventaExpected[pdv.name];
  check(Boolean(expected) && pdv.total_nps === expected[0] && pdv.total_q === expected[1] && pdv.total_pct_q === expected[2], `${pdv.name} no coincide con NPS POSTVENTA.`);
}

check(['Agosto', 'Julio', 'Junio', 'Enero'].every((month) => sandbox.PERMANENCIA_DATA.months[month]), 'Faltan camadas requeridas en Permanencia.');
check(!html.includes('fa-calculator'), 'La fila Total General todavía contiene un icono de calculadora.');
check(!/>ESTRUCTURA<|PUNTO DE VENTA \(PDV\) \/ ASESOR/.test(html), 'Hay encabezados de primera columna fuera del estándar.');
check(!/ENCUESTAS \(Q\)|TOTAL Q|\$\{q\}Q|\bu\.|\bUND\.?\b|\bUnidades?\b|\bRespuestas?\b/i.test(html), 'Se encontraron unidades explícitas no permitidas.');
check(/const isPdvExpanded = pageState\[7\]\.expanded\[pdv\.name\] === true;/.test(html), 'NPS no inicia contraído al nivel PDV.');
check(/const isPdvExpanded = pageState\[2\]\.expanded\[pdv\.id\] === true;/.test(html), 'Descuentos no inicia contraído al nivel PDV.');
check(/isPdvExpanded && pdv\.asesores && Array\.isArray\(pdv\.asesores\)/.test(html), 'Operador cedente no usa la colección de asesores al desplegar un PDV.');
const cedenteAdvisors = sandbox.OPERADOR_CEDENTE_DATA.tree.flatMap((supervisor) =>
  (supervisor.children || []).flatMap((pdv) => pdv.asesores || []),
);
check(cedenteAdvisors.length > 0, 'Operador cedente no contiene asesores.');
check(cedenteAdvisors.every((advisor) => advisor.name && advisor.user_code && advisor.name !== 'undefined' && advisor.user_code !== 'undefined'), 'Operador cedente contiene asesores sin nombre válido.');
check(html.includes("ase.user_code || ase.name || 'Sin asesor'"), 'La Página 3 no tiene respaldo seguro para el nombre del asesor.');
const cedenteScript = html.match(/\/\/ ================= PAGE 3: OPERADOR CEDENTE =================([\s\S]*?)\/\/ ================= PAGE 4:/)?.[1] || '';
check((cedenteScript.match(/color: #dc2626/g) || []).length === 3 && (cedenteScript.match(/color: #b91c1c/g) || []).length === 3, 'Claro no conserva su paleta roja exclusiva en todos los niveles de la página 3.');
check(!/#2563eb|#1d4ed8|#3b82f6|#60a5fa/.test(cedenteScript), 'Persisten colores azules dentro de la tabla de operador cedente.');
check(html.includes('class="grand-total-pct"'), 'Los porcentajes de la fila total de la página 4 no tienen un estilo aislado.');
const page4Css = fs.readFileSync(path.join(projectDir, 'styles', 'page-4.css'), 'utf8');
check(/#slidePage4 \.row-grand-total \.grand-total-pct\s*\{[^}]*color:\s*#ffffff;/s.test(page4Css), 'Los porcentajes de la fila total de la página 4 no son blancos.');

check(!html.includes('<style>'), 'index.html todavía contiene CSS compartido en línea.');
check(html.includes('styles/shell.css'), 'Falta la hoja de estilos exclusiva de la estructura externa.');
for (let page = 0; page <= 7; page += 1) {
  const cssPath = path.join(projectDir, 'styles', `page-${page}.css`);
  check(fs.existsSync(cssPath), `Falta styles/page-${page}.css.`);
  if (!fs.existsSync(cssPath)) continue;
  const pageCss = fs.readFileSync(cssPath, 'utf8');
  check(pageCss.includes(`#slidePage${page}`), `page-${page}.css no está limitado a su página.`);
  for (let otherPage = 0; otherPage <= 7; otherPage += 1) {
    if (otherPage !== page) check(!pageCss.includes(`#slidePage${otherPage}`), `page-${page}.css contiene reglas de la página ${otherPage}.`);
  }
}

const shellCssPath = path.join(projectDir, 'styles', 'shell.css');
check(fs.existsSync(shellCssPath), 'Falta styles/shell.css.');
if (fs.existsSync(shellCssPath)) {
  const shellCss = fs.readFileSync(shellCssPath, 'utf8');
  check(!/\.slide-header|\.table-slide-card|\.tree-table|\.row-grand-total|\.kpi-card/.test(shellCss), 'shell.css contiene estilos internos compartidos entre páginas.');
}

check(!/\bvar\s+(currentSort|currentProductCode|currentMonthFilter|expandedState|discountExpandedState|dotacionExpandedState|npsExpandedState|mixExpandedState|permExpandedState|cedenteExpandedState)\b/.test(html), 'Persisten variables de estado global que pueden cruzar páginas.');
check(html.includes('id="zoneSelectPage3"') && html.includes('id="zoneSelectPage7"'), 'Los filtros de zona de Cedente y NPS no tienen identificadores independientes.');

const monthFilters = {
  monthSelectHeader: { selected: 'm202608', labels: ['Agosto', 'Julio', 'Junio'] },
  monthDiscountFilter: { selected: 'Agosto', labels: ['Agosto', 'Julio', 'Junio'] },
  monthCedenteFilter: { selected: 'Agosto', labels: ['Agosto', 'Julio', 'Junio'] },
  monthMixPlanesFilter: { selected: 'Agosto', labels: ['Agosto', 'Julio', 'Junio'] },
  monthPermanenciaFilter: { selected: 'Agosto', labels: ['Agosto', 'Julio', 'Junio', 'Enero'] },
};
for (const [id, expected] of Object.entries(monthFilters)) {
  const selectMatch = html.match(new RegExp(`<select[^>]*id="${id}"[\\s\\S]*?<\\/select>`));
  check(Boolean(selectMatch), `No se encontró el filtro mensual ${id}.`);
  if (!selectMatch) continue;
  const options = [...selectMatch[0].matchAll(/<option\s+value="([^"]+)"([^>]*)>([^<]+)<\/option>/g)];
  const labels = options.map((option) => option[3].trim());
  const selected = options.find((option) => /\bselected\b/.test(option[2]));
  check(JSON.stringify(labels) === JSON.stringify(expected.labels), `${id} contiene meses agrupados, sufijos o rótulos incorrectos.`);
  check(selected && selected[1] === expected.selected, `${id} no preselecciona Agosto.`);
  check(options.every((option) => option[1] !== 'ALL'), `${id} contiene una opción mensual agrupada.`);
}
check(!/>[^<]*(?:M-[0-9]|Últimos\s+[0-9]|Todos los meses)[^<]*</i.test(html), 'Hay etiquetas mensuales relativas o agrupadas visibles.');
check(!html.includes('zoneSelectPage5'), 'La Página 5 todavía contiene el filtro de zonas.');
check(!html.includes('zoneSelectPage6'), 'La Página 6 todavía contiene el filtro de zonas.');
check(html.includes('permData.user_name_map && permData.user_name_map[userCode.toUpperCase()]'), 'La Página 5 no cruza los usuarios con su mapa exclusivo de nombres.');
check(html.includes('${realName ? `<span style="margin-left: 8px; font-weight: 500; color: #94a3b8; font-size: 10px;">${realName}</span>` : \'\'}'), 'La Página 5 no deja en blanco los usuarios sin coincidencia o no aplica la jerarquía secundaria.');
check(html.includes('id="dotacionPeriodFilter"'), 'La Página 6 no contiene el selector de periodo de dotación.');
check(html.includes('<option value="5-11">5-11</option>') && html.includes('<option value="9-15" selected>9-15</option>'), 'El selector de dotación no contiene ambos periodos o no preselecciona 9-15.');
check(html.includes('function getActiveDotacionData()'), 'La Página 6 no selecciona una fuente de dotación independiente por periodo.');
check(sandbox.DOTACION_DATA && sandbox.DOTACION_DATA.periods && sandbox.DOTACION_DATA.periods['5-11'] && sandbox.DOTACION_DATA.periods['9-15'], 'DOTACION_DATA no contiene ambas hojas 5-11 y 9-15.');

check(html.includes("const monthNames = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];"), 'La Pagina 5 no contiene el calendario para generar encabezados por mes.');
check(html.includes('monthAbbreviations[(selectedMonthIndex + monthOffset) % monthAbbreviations.length]'), 'Los encabezados M0 a M6 de la Pagina 5 no avanzan desde el mes filtrado.');
check(html.includes('`SS TOTAL (${selectedMonthLabel})`') && html.includes('`M${monthOffset} (${monthLabel})`'), 'Los encabezados dinamicos de permanencia no respetan el formato solicitado.');

check(html.includes('return advisorMonth && Number(advisorMonth.total_u || 0) > 0;'), 'La Pagina 3 muestra asesores sin ventas de Portabilidad OSS en el mes filtrado.');

const salesAdvisors = sandbox.SALES_DATA.tree.flatMap((supervisor) =>
  (supervisor.children || []).flatMap((pdv) => pdv.children || []),
);
const advisorsWithTenure = salesAdvisors.filter((advisor) => advisor.tenure);
check(advisorsWithTenure.length === salesAdvisors.length, 'Hay asesores sin estado de antigüedad en la Página 1.');
const allowedTenureCategories = new Set([
  '0 a 30 días',
  '1 a 3 meses',
  '3 a 6 meses',
  '6 meses a un año',
  'Mayor a un año',
]);
for (const advisor of advisorsWithTenure) {
  const tenure = advisor.tenure;
  if (tenure.status === 'ceased') {
    check(tenure.label === 'Cesado' && !tenure.date && !tenure.category, `${advisor.name} no respeta el formato exclusivo Cesado.`);
  } else if (tenure.status === 'missing') {
    check(tenure.label === 'Sin registro' && !tenure.date && !tenure.category, `${advisor.name} no respeta el formato Sin registro.`);
  } else {
    check(tenure.status === 'active', `${advisor.name} tiene un estado de antigüedad inválido.`);
    check(allowedTenureCategories.has(tenure.category), `${advisor.name} tiene una categoría de antigüedad inválida.`);
    check(/^\d{2}\/\d{2}\/\d{4}$/.test(tenure.date || ''), `${advisor.name} no tiene fecha dd/mm/aaaa.`);
  }
}
check(html.includes('getAdvisorTenureHTML(ase)'), 'La Página 1 no renderiza la antigüedad junto al asesor.');
check(html.includes('getPostpagoTotalSalesInMonth(ase, pageState[1].monthFilter) > 0'), 'La plantilla de asesores de la Página 1 no se basa en POSTPAGO TOTAL del mes filtrado.');
const quotaMonths = ['m202606', 'm202607', 'm202608'];
const productCodes = sandbox.SALES_DATA.summary.prod_definitions.map((product) => product.id);
for (const supervisor of sandbox.SALES_DATA.tree) {
  for (const pdv of supervisor.children || []) {
    for (const month of quotaMonths) {
      const template = (pdv.children || []).filter((advisor) => (advisor.products.POSTPAGO_TOTAL.units[month] || 0) > 0);
      if (template.length === 0) continue;
      for (const productCode of productCodes) {
        const expectedQuota = pdv.products[productCode].quotas[month] / template.length;
        for (const advisor of template) {
          const actualQuota = advisor.products[productCode].quotas[month];
          check(Math.abs(actualQuota - expectedQuota) < 1e-9, `${advisor.name} no tiene la cuota proporcional de ${productCode} en ${month}.`);
        }
        const assignedQuota = template.reduce((sum, advisor) => sum + advisor.products[productCode].quotas[month], 0);
        check(Math.abs(assignedQuota - pdv.products[productCode].quotas[month]) < 1e-9, `Las cuotas de asesores no reconcilian con ${pdv.name}, ${productCode}, ${month}.`);
      }
    }
  }
}
const pageOneCss = fs.readFileSync(path.join(projectDir, 'styles', 'page-1.css'), 'utf8');
check(pageOneCss.includes('#slidePage1 .advisor-tenure'), 'Faltan estilos aislados para la antigüedad en Página 1.');
for (let page = 0; page <= 7; page += 1) {
  if (page === 1) continue;
  const otherCss = fs.readFileSync(path.join(projectDir, 'styles', `page-${page}.css`), 'utf8');
  check(!otherCss.includes('.advisor-tenure'), `La antigüedad se filtró a los estilos de la Página ${page}.`);
}

if (failures.length) {
  console.error('\nVerificación fallida:');
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log('\n[OK] Las ocho páginas y los lineamientos automatizables fueron verificados.');
