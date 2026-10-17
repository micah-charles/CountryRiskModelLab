import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const root = path.dirname(fileURLToPath(import.meta.url));
const outputDir = path.join(root, 'outputs');
const sourcePath = path.join(root, 'data', 'processed', 'daily_yields.csv');
const metadataPath = path.join(root, 'data', 'processed', 'source_metadata.json');
await fs.mkdir(outputDir, { recursive: true });

const csvText = await fs.readFile(sourcePath, 'utf8');
const csvRows = csvText.trimEnd().split(/\r?\n/).map((line) => line.split(','));
const [csvHeaders, ...csvBody] = csvRows;
const countryKeys = ['US', 'UK', 'France', 'Italy', 'Germany', 'Japan'];
const labels = {
  US: 'United States', UK: 'United Kingdom', France: 'France',
  Italy: 'Italy', Germany: 'Germany', Japan: 'Japan',
};
const metadata = JSON.parse(await fs.readFile(metadataPath, 'utf8'));
const dates = csvBody.map((row) => row[0]);
const latest = metadata.period_end_latest_available;
const chartRows = [['Date', ...countryKeys.map((k) => labels[k]), 'Chart date label (ISO)']];
for (const row of csvBody) {
  const d = row[0];
  const values = row.slice(1, 7).map((v) => v === '' ? null : Number(v));
  chartRows.push([new Date(`${d}T00:00:00.000Z`), ...values, d]);
}
const lastRow = chartRows.length;
const dataEndRow = lastRow + 4;
const font = 'Arial';
const workbook = Workbook.create();
const chartSheet = workbook.worksheets.add('Chart');
const dataSheet = workbook.worksheets.add('Daily Data');
const sourceSheet = workbook.worksheets.add('Sources');
for (const sheet of [chartSheet, dataSheet, sourceSheet]) sheet.showGridLines = false;

// Main output view: an editable, range-backed Excel line chart.
chartSheet.getRange('A1').values = [['Source notes']];
chartSheet.getRange('A1:B5').format.font = { name: font, size: 11, color: '#263238' };
chartSheet.getRange('A1').format = { fill: '#17324D', font: { name: font, size: 12, bold: true, color: '#FFFFFF' } };
chartSheet.getRange('A2:B5').values = [
  ['Period', `2020-01-01 to ${latest}; source observations are not available on identical dates`],
  ['Missing dates', 'Source gaps remain blank. No interpolation, estimation, or forward-fill.'],
  ['Definitions', 'National methodologies differ; see the Sources tab for each series and unit.'],
  ['Use terms', 'France and Italy have source-specific redistribution restrictions; see Sources before sharing.'],
];
chartSheet.getRange('A2:A5').format.font = { name: font, size: 10, bold: true, color: '#425466' };
chartSheet.getRange('B2:B5').format.wrapText = true;
chartSheet.getRange('A:A').format.columnWidth = 18;
chartSheet.getRange('B:B').format.columnWidth = 105;
chartSheet.getRange('2:5').format.rowHeight = 24;
const categoryRange = dataSheet.getRange(`H6:H${dataEndRow}`);
const seriesRanges = countryKeys.map((_, i) => dataSheet.getRangeByIndexes(5, i + 1, csvBody.length, 1));
const chart = chartSheet.charts.add('line', [categoryRange, ...seriesRanges]);
chart.title = '10-year government bond yields (%)';
chart.titleTextStyle.fontSize = 20;
chart.titleTextStyle.typeface = font;
chart.legend = { position: 'top', textStyle: { typeface: font, fontSize: 12 } };
chart.xAxis = { axisType: 'textAxis', textStyle: { typeface: font, fontSize: 11 }, tickLabelInterval: 130 };
chart.yAxis = { numberFormatCode: '0.0', numberFormatSourceLinked: false, textStyle: { typeface: font, fontSize: 11 }, minimumScale: -2, maximumScale: 6, majorUnit: 1 };
chart.xAxis.title.text = 'Date';
chart.yAxis.title.text = 'Yield (%)';
chart.setPosition('A7', 'T31');
const seriesColors = ['#533620', '#DA8738', '#203E5C', '#55A6B9', '#2D7953', '#242424'];
const seriesStyles = ['dotted', 'solid', 'dashed', 'dashed', 'solid', 'solid'];
for (let i = 0; i < chart.series.items.length; i += 1) {
  const serie = chart.series.items[i];
  serie.name = labels[countryKeys[i]];
  serie.line = { fill: seriesColors[i], style: seriesStyles[i], width: 2.25 };
}

// Daily data tab: one row per observed date across sources; no value is carried forward.
dataSheet.getRange('A1').values = [['Daily observations (percent per annum)']];
dataSheet.getRange('A1:H1').merge();
dataSheet.getRange('A1:H1').format = { fill: '#17324D', font: { name: font, size: 15, bold: true, color: '#FFFFFF' } };
dataSheet.getRange('A2').values = [['Raw agency exports are preserved under data/raw. Blank means no source observation for that date; it is not zero.']];
dataSheet.getRange('A2:H2').merge();
dataSheet.getRange('A2:H2').format = { font: { name: font, size: 10, italic: true, color: '#425466' }, wrapText: true };
dataSheet.getRange('A3').values = [['Date alignment is a union of actual source observation dates. Yield values are unchanged; daily gaps are never interpolated or forward-filled.']];
dataSheet.getRange('A3:H3').merge();
dataSheet.getRange('A3:H3').format = { font: { name: font, size: 10, color: '#425466' }, wrapText: true };
dataSheet.getRangeByIndexes(4, 0, chartRows.length, 8).values = chartRows;
dataSheet.getRange('A5:H5').format = { fill: '#DCE6F1', font: { name: font, size: 10, bold: true, color: '#17324D' }, wrapText: true };
dataSheet.getRange(`A6:A${dataEndRow}`).format.numberFormat = 'dd mmm yyyy';
dataSheet.getRange(`B6:G${dataEndRow}`).format.numberFormat = '0.00000;[Red]-0.00000;–';
dataSheet.getRange(`H6:H${dataEndRow}`).format.font = { name: font, size: 9, color: '#666666' };
dataSheet.getRange('A:A').format.columnWidth = 15;
for (const col of ['B', 'C', 'D', 'E', 'F', 'G']) dataSheet.getRange(`${col}:${col}`).format.columnWidth = 15;
dataSheet.getRange('H:H').format.columnWidth = 25;
dataSheet.freezePanes.freezeRows(5);

// Sources tab: series identity, definitions, latest observations, reuse terms and snapshot hashes.
sourceSheet.getRange('A1').values = [['Sources, definitions and reuse notes']];
sourceSheet.getRange('A1:B1').merge();
sourceSheet.getRange('A1:B1').format = { fill: '#17324D', font: { name: font, size: 15, bold: true, color: '#FFFFFF' } };
sourceSheet.getRange('A2').values = [[`Retrieved ${metadata.retrieved_at_utc}; period begins ${metadata.period_start}; latest panel date ${latest}.`]];
sourceSheet.getRange('A2:B2').merge();
sourceSheet.getRange('A2:K2').format = { font: { name: font, size: 10, italic: true, color: '#425466' }, wrapText: true };
sourceSheet.getRange('A3').values = [['Values are source observations as published; daily series definitions are not fully harmonised. Do not treat cross-country levels as identical methodologies.']];
sourceSheet.getRange('A3:B3').merge();
sourceSheet.getRange('A3:K3').format = { font: { name: font, size: 10, color: '#425466' }, wrapText: true };
sourceSheet.getRange('A5:B5').values = [['Country / item', 'Source details']];
sourceSheet.getRange('A5:B5').format = { fill: '#DCE6F1', font: { name: font, size: 10, bold: true, color: '#17324D' } };
let sourceRow = 6;
for (const c of countryKeys) {
  const s = metadata.countries[c];
  sourceSheet.getRange(`A${sourceRow}:B${sourceRow}`).merge();
  sourceSheet.getRange(`A${sourceRow}`).values = [[`${labels[c]} — ${s.agency}`]];
  sourceSheet.getRange(`A${sourceRow}:B${sourceRow}`).format = { fill: '#17324D', font: { name: font, size: 11, bold: true, color: '#FFFFFF' } };
  sourceRow += 1;
  const details = [
    ['Dataset', s.dataset], ['Series ID / source field', s.series_id],
    ['Definition / method', s.definition], ['Frequency', s.frequency], ['Unit', s.unit],
    ['First observation', s.first_observation], ['Latest observation', s.latest_observation],
    ['Latest yield (%)', s.latest_value_pct], ['Official metadata/source URL', s.source_url],
    ['Direct download URL', s.download_url], ['Reuse / license limits', s.reuse],
    ['Raw source snapshot file(s)', s.raw_files],
  ];
  for (const [key, value] of details) {
    sourceSheet.getRange(`A${sourceRow}:B${sourceRow}`).values = [[key, value]];
    sourceSheet.getRange(`A${sourceRow}`).format.font = { name: font, size: 10, bold: true, color: '#425466' };
    sourceSheet.getRange(`B${sourceRow}`).format = { font: { name: font, size: 10, color: '#263238' }, wrapText: true, verticalAlignment: 'top' };
    sourceSheet.getRange(`${sourceRow}:${sourceRow}`).format.rowHeight = ['Definition / method', 'Direct download URL', 'Reuse / license limits'].includes(key) ? 56 : 25;
    if (key === 'Latest yield (%)') sourceSheet.getRange(`B${sourceRow}`).format.numberFormat = '0.00000';
    sourceRow += 1;
  }
  sourceRow += 1;
}
const sourcesEndRow = sourceRow - 1;
sourceSheet.getRange('A:A').format.columnWidth = 31;
sourceSheet.getRange('B:B').format.columnWidth = 120;
sourceSheet.freezePanes.freezeRows(5);

const hashStart = sourcesEndRow + 3;
sourceSheet.getRange(`A${hashStart}`).values = [['Downloaded raw-file snapshots (SHA-256)']];
sourceSheet.getRange(`A${hashStart}:B${hashStart}`).merge();
sourceSheet.getRange(`A${hashStart}:B${hashStart}`).format = { fill: '#17324D', font: { name: font, size: 11, bold: true, color: '#FFFFFF' } };
const hashRows = [['Raw file', 'SHA-256']];
for (const [filename, hash] of Object.entries(metadata.raw_file_sha256)) hashRows.push([filename, hash]);
sourceSheet.getRangeByIndexes(hashStart, 0, hashRows.length, 2).values = hashRows;
sourceSheet.getRangeByIndexes(hashStart, 0, 1, 2).format = { fill: '#DCE6F1', font: { name: font, size: 10, bold: true, color: '#17324D' } };
sourceSheet.getRangeByIndexes(hashStart + 1, 0, hashRows.length - 1, 2).format = { font: { name: font, size: 9, color: '#263238' }, wrapText: true };
const footerRow = hashStart + hashRows.length + 2;
sourceSheet.getRange(`A${footerRow}`).values = [['No Bloomberg data-series or Bloomberg account is used by this project. Italy is the official Banca d’Italia BMK0200 publication; its source metadata says “various sources” and does not enumerate upstream vendors.']];
sourceSheet.getRange(`A${footerRow}:B${footerRow + 1}`).merge();
sourceSheet.getRange(`A${footerRow}:B${footerRow + 1}`).format = { fill: '#FFF2CC', font: { name: font, size: 10, color: '#663C00' }, wrapText: true, verticalAlignment: 'center' };

workbook.recalculate();

// The workbook is values-only apart from the native chart. Scan populated cells for formula errors.
const errorPattern = /^#(?:REF!|DIV\/0!|VALUE!|NAME\?|N\/A|NUM!|NULL!)/i;
const errorCells = [];
for (const sheet of [chartSheet, dataSheet, sourceSheet]) {
  const used = sheet.getUsedRange();
  const values = used?.values ?? [];
  values.forEach((row, ri) => row.forEach((value, ci) => {
    if (typeof value === 'string' && errorPattern.test(value)) errorCells.push(`${sheet.name}!R${ri + 1}C${ci + 1}=${value}`);
  }));
}
if (errorCells.length) throw new Error(`Workbook contains error-like cell values: ${errorCells.slice(0, 10).join(', ')}`);

// Validate workbook data and chart bindings before export.
const chartInfo = {
  chartSeriesCount: chart.series.items.length,
  chartSeries: chart.series.items.map((s) => ({ formula: s.formula, categoryFormula: s.categoryFormula })),
  dataRows: csvBody.length,
  latestDate: latest,
  sourcesRows: countryKeys.length,
  errorCellCount: errorCells.length,
};
if (chartInfo.chartSeriesCount !== 6) throw new Error(`Expected six chart series, found ${chartInfo.chartSeriesCount}`);
for (const c of countryKeys) {
  const m = metadata.countries[c];
  if (!m.latest_observation || m.latest_value_pct === null) throw new Error(`No latest observation for ${c}`);
}

const chartPreview = await workbook.render({ sheetName: 'Chart', range: 'A1:T33', scale: 1, format: 'png' });
await fs.writeFile(path.join(outputDir, 'workbook_chart_preview.png'), new Uint8Array(await chartPreview.arrayBuffer()));
const dataPreview = await workbook.render({ sheetName: 'Daily Data', range: 'A1:H22', scale: 1, format: 'png' });
await fs.writeFile(path.join(outputDir, 'workbook_data_preview.png'), new Uint8Array(await dataPreview.arrayBuffer()));
const sourcePreview = await workbook.render({ sheetName: 'Sources', range: 'A1:B27', scale: 1, format: 'png' });
await fs.writeFile(path.join(outputDir, 'workbook_sources_preview.png'), new Uint8Array(await sourcePreview.arrayBuffer()));

const outputPath = path.join(outputDir, 'government_bond_yields_2020_latest.xlsx');
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
const inspection = await workbook.inspect({ kind: 'region', range: 'A5:G12', sheetId: 'Daily Data', maxChars: 3000 });
const savedWorkbook = await SpreadsheetFile.importXlsx(new Uint8Array(await fs.readFile(outputPath)));
const roundTrip = await savedWorkbook.inspect({ kind: 'workbook,sheet,drawing', maxChars: 6000 });
await fs.writeFile(path.join(outputDir, 'workbook_validation.json'), JSON.stringify({
  chartInfo,
  sampleData: dataSheet.getRange('A5:G12').values,
  regionInspectionRecordCount: inspection.recordCount,
  roundTripInspectionRecordCount: roundTrip.recordCount,
}, null, 2) + '\n');
console.log(JSON.stringify({ outputPath, ...chartInfo }, null, 2));
