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
  requestAnimationFrame(callback) { callback(); },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(`${dataCode}\n${scriptMatch[1]}`, sandbox, { filename: 'dashboard.bundle.js' });

const failures = [];
const check = (condition, message) => {
  if (!condition) failures.push(message);
};
check(html.includes('<span>AGOSTO S1-S2</span>'), 'La portada no muestra AGOSTO S1-S2.');
check(!html.includes('<span>AGOSTO S1</span>'), 'La portada conserva el rótulo anterior AGOSTO S1.');
const run = (label, fn) => {
  try {
    fn();
    console.log(`[OK] ${label}`);
  } catch (error) {
    failures.push(`${label}: ${error.message}`);
  }
};

for (let page = 0; page <= 7; page += 1) {
  run(`Página ${page}`, () => {
    sandbox.switchSlidePage(page);
    check(documentMock.getElementById('rowCountLabel').textContent === 'Equipo de Operaciones • 2026', `La Página ${page} no muestra el texto inferior uniforme.`);
    if (page === 0) check(documentMock.getElementById('pageFooterNum').textContent === '', 'La portada conserva texto adicional en el pie.');
  });
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
run('Productividades HC', () => {
  sandbox.openProductivityModal();
  const productivity = sandbox.PRODUCTIVIDADES_DATA;
  check(productivity.default_month === 'Agosto', 'Productividades HC no inicia en Agosto.');
  check(productivity.columns.length === 20, 'Productividades HC no conserva todas las columnas del Excel.');
  check(productivity.months.Agosto.length === 27 && productivity.months.Julio.length === 31, 'Productividades HC no conserva todos los registros mensuales.');
  check(productivity.months.Agosto.every((row) => typeof row.Antiguedad === 'number'), 'Antiguedad no se conserva como cantidad de meses.');
  const theadHTML = documentMock.getElementById('productivityThead').innerHTML;
  const tbodyHTML = documentMock.getElementById('productivityTbody').innerHTML;
  check(!theadHTML.includes('>MES<') && (theadHTML.match(/<th>/g) || []).length === 19, 'MES no se ocultó de la tabla de Productividades HC.');
  check(/<tr>\s*<td[^>]*>TE AYACUCHO<\/td>/.test(tbodyHTML), 'Productividades HC no está ordenada alfabéticamente por PDV.');
  check((tbodyHTML.match(/<tr>/g) || []).length === 27, 'El modal no renderiza los 27 registros de Agosto.');
  check(tbodyHTML.includes('is-active') && tbodyHTML.includes('is-inactive'), 'El modal no diferencia visualmente activos y no activos.');
  check(tbodyHTML.includes('meses'), 'El modal no muestra Antiguedad en meses.');
  sandbox.closeProductivityModal();
});

const postpagoAugust = sandbox.SALES_DATA.summary.global_units.POSTPAGO_TOTAL.m202608;
const elapsedDaysMatch = html.match(/var ELAPSED_WD = (\d+);/);
const totalDaysMatch = html.match(/var TOTAL_WD = (\d+);/);
const verifiedElapsedDays = Number(elapsedDaysMatch?.[1] || 0);
const verifiedTotalDays = Number(totalDaysMatch?.[1] || 0);
check(verifiedElapsedDays > 0 && verifiedTotalDays >= verifiedElapsedDays, 'El corte de días hábiles no es válido.');
check(/AVANCE<\/th>\s*<th[^>]*>IDEAL<\/th>\s*<th[^>]*>GAP<\/th>/.test(html), 'IDEAL y GAP no están ubicados a la derecha de AVANCE.');
check(/Math\.round\(\(numericQuota \/ TOTAL_WD\) \* ELAPSED_WD\)/.test(html), 'IDEAL no usa Cuota / días totales * días transcurridos.');
check((html.match(/getIdealValue\((?:grand|spv|pdv|ase)Quota\)/g) || []).length === 8, 'IDEAL no se calcula en todos los niveles y meses de la Página 1.');
check((html.match(/getGapBadgeHTML\((?:grand|spv|pdv|ase)Gap\)/g) || []).length === 8, 'GAP no se muestra en todos los niveles y meses de la Página 1.');
check(sandbox.getIdealValue(1486) === Math.round((1486 / verifiedTotalDays) * verifiedElapsedDays), 'IDEAL no aplica el corte vigente de días hábiles.');
check(sandbox.getGapBadgeHTML(58).includes('fa-arrow-up') && sandbox.getGapBadgeHTML(-58).includes('fa-arrow-down'), 'GAP no utiliza las flechas de variación positiva y negativa.');
const visibleCutLabel = `Avance ${verifiedElapsedDays}/${verifiedTotalDays} Días Hábiles`;
check((html.match(new RegExp(visibleCutLabel, 'g')) || []).length === 2, 'El texto visible de avance no muestra el corte vigente de días hábiles en todos sus estados.');
const mixAugust = sandbox.MIX_PLANES_DATA.months.Agosto.summary.total;
check(postpagoAugust === mixAugust, `Mix de planes (${mixAugust}) no coincide con Postpago (${postpagoAugust}).`);

for (const channel of ['venta', 'postventa']) {
  const channelData = sandbox.NPS_DATA[channel];
  const pdvs = channelData.pdvs;
  check(pdvs.every((item, index) => index === 0 || pdvs[index - 1].total_nps >= item.total_nps), `Los PDV de NPS ${channel} no están ordenados de mayor a menor.`);
  check(pdvs.every((pdv) => (pdv.children || []).every((item, index) => index === 0 || pdv.children[index - 1].total_nps >= item.total_nps)), `Los asesores de NPS ${channel} no están ordenados de mayor a menor.`);
  const pdvTotalQ = pdvs.reduce((sum, pdv) => sum + Number(pdv.total_q || 0), 0);
  const pdvWeightedNps = pdvs.reduce((sum, pdv) => sum + Number(pdv.total_nps || 0) * Number(pdv.total_q || 0), 0);
  const expectedNps = pdvTotalQ > 0 ? Math.round((pdvWeightedNps / pdvTotalQ) * 10) / 10 : 0;
  check(channelData.summary.total_q === pdvTotalQ, `El total de encuestas NPS ${channel} no reconcilia con sus PDV.`);
  check(Math.abs(channelData.summary.total_nps - expectedNps) < 0.11, `El NPS total de ${channel} no reconcilia con sus PDV.`);
  check(Array.isArray(channelData.weeks) && channelData.weeks.length > 0, `NPS ${channel} no declara semanas disponibles.`);
}
check(sandbox.NPS_DATA.venta.summary.total_nps === 50 && sandbox.NPS_DATA.venta.summary.total_q === 16, 'NPS Venta no coincide con 50% y 16 encuestas.');
check(sandbox.NPS_DATA.postventa.summary.total_nps === 25 && sandbox.NPS_DATA.postventa.summary.total_q === 4, 'NPS Postventa no coincide con 25% y 4 encuestas.');
check(/const weeklyResults = availableWeeks\.map/.test(html) && !html.includes("SEM3 (89% NPS)"), 'La baldosa Pico Semanal no se calcula dinámicamente.');
check(/function getAvailableNpsWeeks\(channelData\)/.test(html), 'La Página 7 no limita las columnas a las semanas disponibles.');
check(!html.includes('toggleNpsWeeks') && !html.includes('Mostrar Semana') && !html.includes('Ocultar Semana'), 'La Página 7 conserva el control semanal.');
check(/weekGroupHeaders[\s\S]*colspan="2"/.test(html) && /weekMetricHeaders[\s\S]*>NPS<[\s\S]*>Q</.test(html), 'Las semanas no muestran siempre NPS y Q.');
check(!html.includes('% TOTAL') && !html.includes('ESTADO CUMPLIMIENTO'), 'La tabla NPS conserva columnas ajenas a NPS y Q.');
check(!/\$\{totNps\.toFixed\(0\)\}% \$\{getNpsBadgeHTML/.test(html), 'La baldosa NPS Logrado repite el porcentaje.');
check(/id="tabNpsVenta"[\s\S]*?NPS VENTA\s*<\/button>/.test(html), 'El selector de NPS Venta contiene texto adicional.');
check(/id="tabNpsPostventa"[\s\S]*?NPS POSTVENTA\s*<\/button>/.test(html), 'El selector de NPS Postventa contiene texto adicional.');
check(!/NPS (?:VENTA|POSTVENTA) \([^)]*\)/.test(html), 'Los selectores NPS todavía contienen texto entre paréntesis.');
check(/const npsUserNameMap = window\.PERMANENCIA_DATA && window\.PERMANENCIA_DATA\.user_name_map/.test(html), 'La Página 7 no cruza los usuarios NPS con la hoja USUARIOS.');
check(/npsUserNameMap\[normalizedUserCode\] \|\| ''/.test(html), 'La Página 7 no deja vacío el nombre cuando el usuario no existe.');
check(/margin-left: 8px; font-weight: 500; color: #94a3b8; font-size: 10px;/.test(html), 'Los nombres NPS no conservan el estilo sutil de Permanencia.');
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
check(!html.includes('${pctTasaUso.toFixed(1)}% ${getDiscountUsageBadgeHTML(pctTasaUso, targetMeta)}'), 'La baldosa Tasa Uso Lograda de la Página 2 repite el indicador.');
check(!html.includes('Portada • Informe Ejecutivo 360°'), 'La portada todavía muestra el texto inferior que debía retirarse.');
check((html.match(/labelEl\.textContent = 'Equipo de Operaciones • 2026'/g) || []).length === 4, 'No todas las páginas conservan el texto inferior de Equipo de Operaciones.');
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
