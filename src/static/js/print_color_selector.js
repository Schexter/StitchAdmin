// Print Color Selector für StitchAdmin
// Globale Variable für ausgewählte Druckfarben
let selectedPrintColors = [];

// Standard-Farben Definition
const standardColors = [
    { name: 'Schwarz', hex: '#000000', cmyk: 'C:0 M:0 Y:0 K:100', rgb: '0, 0, 0' },
    { name: 'Weiß', hex: '#FFFFFF', cmyk: 'C:0 M:0 Y:0 K:0', rgb: '255, 255, 255' },
    { name: 'Rot', hex: '#FF0000', cmyk: 'C:0 M:100 Y:100 K:0', rgb: '255, 0, 0' },
    { name: 'Grün', hex: '#00FF00', cmyk: 'C:100 M:0 Y:100 K:0', rgb: '0, 255, 0' },
    { name: 'Blau', hex: '#0000FF', cmyk: 'C:100 M:100 Y:0 K:0', rgb: '0, 0, 255' },
    { name: 'Gelb', hex: '#FFFF00', cmyk: 'C:0 M:0 Y:100 K:0', rgb: '255, 255, 0' },
    { name: 'Orange', hex: '#FFA500', cmyk: 'C:0 M:35 Y:100 K:0', rgb: '255, 165, 0' },
    { name: 'Violett', hex: '#800080', cmyk: 'C:50 M:100 Y:0 K:0', rgb: '128, 0, 128' },
    { name: 'Pink', hex: '#FFC0CB', cmyk: 'C:0 M:25 Y:20 K:0', rgb: '255, 192, 203' },
    { name: 'Braun', hex: '#964B00', cmyk: 'C:30 M:75 Y:100 K:30', rgb: '150, 75, 0' },
    { name: 'Grau', hex: '#808080', cmyk: 'C:0 M:0 Y:0 K:50', rgb: '128, 128, 128' },
    { name: 'Navy', hex: '#000080', cmyk: 'C:100 M:100 Y:0 K:50', rgb: '0, 0, 128' },
    { name: 'Türkis', hex: '#00CED1', cmyk: 'C:100 M:0 Y:25 K:0', rgb: '0, 206, 209' },
    { name: 'Gold', hex: '#FFD700', cmyk: 'C:0 M:15 Y:100 K:0', rgb: '255, 215, 0' },
    { name: 'Silber', hex: '#C0C0C0', cmyk: 'C:0 M:0 Y:0 K:25', rgb: '192, 192, 192' }
];

// Häufige Pantone-Farben
const pantoneColors = [
    { name: 'Pantone 186C', hex: '#C8102E', pantone: '186C', cmyk: 'C:0 M:100 Y:81 K:4' },
    { name: 'Pantone 281C', hex: '#00205B', pantone: '281C', cmyk: 'C:100 M:85 Y:5 K:22' },
    { name: 'Pantone 109C', hex: '#FFD100', pantone: '109C', cmyk: 'C:0 M:10 Y:100 K:0' },
    { name: 'Pantone 354C', hex: '#00B140', pantone: '354C', cmyk: 'C:80 M:0 Y:90 K:0' },
    { name: 'Pantone Orange 021C', hex: '#FE5000', pantone: 'Orange 021C', cmyk: 'C:0 M:65 Y:100 K:0' },
    { name: 'Pantone Black C', hex: '#000000', pantone: 'Black C', cmyk: 'C:0 M:0 Y:0 K:100' },
    { name: 'Pantone Cool Gray 11C', hex: '#53565A', pantone: 'Cool Gray 11C', cmyk: 'C:0 M:0 Y:0 K:70' },
    { name: 'Pantone 2728C', hex: '#0047BB', pantone: '2728C', cmyk: 'C:100 M:75 Y:0 K:0' },
    { name: 'Pantone Process Blue C', hex: '#0085CA', pantone: 'Process Blue C', cmyk: 'C:100 M:10 Y:0 K:0' },
    { name: 'Pantone Reflex Blue C', hex: '#001489', pantone: 'Reflex Blue C', cmyk: 'C:100 M:90 Y:10 K:0' }
];

// Initialisierung beim Laden der Seite
document.addEventListener('DOMContentLoaded', function() {
    // Lade gespeicherte Farben falls vorhanden
    const savedColorsElement = document.getElementById('selected_print_colors');
    if (savedColorsElement && savedColorsElement.value) {
        try {
            selectedPrintColors = JSON.parse(savedColorsElement.value);
            updatePrintColorsDisplay();
        } catch (e) {
            console.error('Fehler beim Laden der gespeicherten Farben:', e);
        }
    }
});

// Öffne Druckfarben-Auswahl Modal
function openPrintColorSelector() {
    // Erstelle Modal wenn noch nicht vorhanden
    if (!document.getElementById('printColorModal')) {
        createPrintColorModal();
    }
    
    // Lade gespeicherte Farben
    const savedColors = document.getElementById('selected_print_colors').value;
    if (savedColors) {
        try {
            selectedPrintColors = JSON.parse(savedColors);
        } catch (e) {
            selectedPrintColors = [];
        }
    }
    
    updateModalSelectedColors();
    const modal = new bootstrap.Modal(document.getElementById('printColorModal'));
    modal.show();
}

// Erstelle Modal dynamisch
function createPrintColorModal() {
    const modalHtml = `
    <div class="modal fade" id="printColorModal" tabindex="-1" aria-labelledby="printColorModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="printColorModalLabel">
                        <i class="bi bi-palette"></i> Druckfarben auswählen
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <!-- Tabs für verschiedene Farbsysteme -->
                    <ul class="nav nav-tabs mb-3" id="colorSystemTabs" role="tablist">
                        <li class="nav-item" role="presentation">
                            <button class="nav-link active" id="standard-tab" data-bs-toggle="tab" 
                                    data-bs-target="#standard-colors" type="button" role="tab">
                                Standard-Farben
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="pantone-tab" data-bs-toggle="tab" 
                                    data-bs-target="#pantone-colors" type="button" role="tab">
                                Pantone
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="custom-tab" data-bs-toggle="tab" 
                                    data-bs-target="#custom-colors" type="button" role="tab">
                                Eigene Farbe
                            </button>
                        </li>
                    </ul>

                    <div class="tab-content" id="colorSystemContent">
                        <!-- Standard-Farben Tab -->
                        <div class="tab-pane fade show active" id="standard-colors" role="tabpanel">
                            <div class="row g-2" id="standard-color-grid">
                                ${standardColors.map(color => createColorCard(color)).join('')}
                            </div>
                        </div>

                        <!-- Pantone Tab -->
                        <div class="tab-pane fade" id="pantone-colors" role="tabpanel">
                            <div class="mb-3">
                                <input type="text" class="form-control" id="pantone-search" 
                                       placeholder="Pantone-Nummer eingeben (z.B. 186C)">
                            </div>
                            <div class="row g-2" id="pantone-color-grid">
                                ${pantoneColors.map(color => createColorCard(color)).join('')}
                            </div>
                        </div>

                        <!-- Eigene Farbe Tab -->
                        <div class="tab-pane fade" id="custom-colors" role="tabpanel">
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">Farbname</label>
                                        <input type="text" class="form-control" id="custom-color-name" 
                                               placeholder="z.B. Firmenblau">
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">Farbcode</label>
                                        <div class="input-group">
                                            <select class="form-select" id="color-code-type" style="max-width: 120px;">
                                                <option value="hex">HEX</option>
                                                <option value="rgb">RGB</option>
                                                <option value="cmyk">CMYK</option>
                                                <option value="pantone">Pantone</option>
                                            </select>
                                            <input type="text" class="form-control" id="custom-color-code" 
                                                   placeholder="#000000">
                                            <input type="color" class="form-control form-control-color" 
                                                   id="color-picker" value="#000000" style="max-width: 60px;">
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-12">
                                    <button type="button" class="btn btn-primary" onclick="addCustomPrintColor()">
                                        <i class="bi bi-plus-circle"></i> Farbe hinzufügen
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Ausgewählte Farben -->
                    <hr class="my-4">
                    <h6>Ausgewählte Farben:</h6>
                    <div id="modal-selected-colors" class="d-flex flex-wrap gap-2">
                        <!-- Ausgewählte Farben werden hier angezeigt -->
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                    <button type="button" class="btn btn-primary" onclick="savePrintColors()">
                        <i class="bi bi-check"></i> Farben übernehmen
                    </button>
                </div>
            </div>
        </div>
    </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Event Listener für Color Picker
    document.getElementById('color-picker').addEventListener('change', function(e) {
        document.getElementById('custom-color-code').value = e.target.value;
    });
    
    document.getElementById('custom-color-code').addEventListener('input', function(e) {
        if (document.getElementById('color-code-type').value === 'hex' && e.target.value.match(/^#?[0-9A-Fa-f]{6}$/)) {
            document.getElementById('color-picker').value = e.target.value.startsWith('#') ? e.target.value : '#' + e.target.value;
        }
    });
}

// Erstelle Farbkarte
function createColorCard(color) {
    const textColor = getContrastColor(color.hex);
    const isSelected = selectedPrintColors.some(c => c.name === color.name);
    return `
        <div class="col-3">
            <div class="color-card border rounded p-2 text-center cursor-pointer ${isSelected ? 'selected' : ''}" 
                 onclick="togglePrintColor('${color.name}', '${color.hex}', '${color.pantone || ''}', '${color.cmyk || ''}', '${color.rgb || ''}')"
                 style="background-color: ${color.hex}; color: ${textColor};">
                <small class="d-block fw-bold">${color.name}</small>
                <small class="d-block" style="font-size: 10px;">${color.hex}</small>
                ${isSelected ? '<i class="bi bi-check-circle-fill"></i>' : ''}
            </div>
        </div>
    `;
}

// Toggle Farbe
function togglePrintColor(name, hex, pantone, cmyk, rgb) {
    const index = selectedPrintColors.findIndex(c => c.name === name);
    
    if (index > -1) {
        selectedPrintColors.splice(index, 1);
    } else {
        selectedPrintColors.push({
            name: name,
            hex: hex,
            pantone: pantone,
            cmyk: cmyk,
            rgb: rgb || hexToRgb(hex)
        });
    }
    
    updateModalSelectedColors();
    
    // Update Farbkarten
    document.querySelectorAll('.color-card').forEach(card => {
        const cardName = card.querySelector('.fw-bold').textContent;
        if (cardName === name) {
            card.classList.toggle('selected');
            const icon = card.querySelector('.bi-check-circle-fill');
            if (icon) {
                icon.remove();
            } else {
                card.insertAdjacentHTML('beforeend', '<i class="bi bi-check-circle-fill"></i>');
            }
        }
    });
}

// Füge eigene Farbe hinzu
function addCustomPrintColor() {
    const name = document.getElementById('custom-color-name').value.trim();
    const codeType = document.getElementById('color-code-type').value;
    const code = document.getElementById('custom-color-code').value.trim();
    const colorPicker = document.getElementById('color-picker').value;
    
    if (!name) {
        alert('Bitte geben Sie einen Farbnamen ein.');
        return;
    }
    
    let hex = colorPicker;
    let cmyk = '';
    let pantone = '';
    let rgb = '';
    
    if (code) {
        switch (codeType) {
            case 'hex':
                hex = code.startsWith('#') ? code : '#' + code;
                rgb = hexToRgb(hex);
                break;
            case 'rgb':
                const rgbMatch = code.match(/(\d+),?\s*(\d+),?\s*(\d+)/);
                if (rgbMatch) {
                    rgb = `${rgbMatch[1]}, ${rgbMatch[2]}, ${rgbMatch[3]}`;
                    hex = rgbToHex(parseInt(rgbMatch[1]), parseInt(rgbMatch[2]), parseInt(rgbMatch[3]));
                }
                break;
            case 'cmyk':
                cmyk = code;
                rgb = hexToRgb(hex);
                break;
            case 'pantone':
                pantone = code;
                rgb = hexToRgb(hex);
                break;
        }
    } else {
        rgb = hexToRgb(hex);
    }
    
    selectedPrintColors.push({
        name: name,
        hex: hex,
        pantone: pantone,
        cmyk: cmyk,
        rgb: rgb
    });
    
    // Felder zurücksetzen
    document.getElementById('custom-color-name').value = '';
    document.getElementById('custom-color-code').value = '';
    document.getElementById('color-picker').value = '#000000';
    
    updateModalSelectedColors();
}

// Update Modal ausgewählte Farben
function updateModalSelectedColors() {
    const container = document.getElementById('modal-selected-colors');
    
    if (selectedPrintColors.length === 0) {
        container.innerHTML = '<p class="text-muted mb-0">Keine Farben ausgewählt</p>';
        return;
    }
    
    container.innerHTML = selectedPrintColors.map((color, index) => {
        const textColor = getContrastColor(color.hex);
        return `
            <div class="selected-color-chip d-inline-flex align-items-center gap-2 px-3 py-2 rounded"
                 style="background-color: ${color.hex}; color: ${textColor};">
                <span>${color.name}</span>
                <small>(${color.pantone || color.hex})</small>
                <button type="button" class="btn-close btn-close-${textColor === '#FFFFFF' ? 'white' : 'dark'} btn-sm" 
                        onclick="removePrintColor(${index})" aria-label="Entfernen"></button>
            </div>
        `;
    }).join('');
}

// Entferne Druckfarbe
function removePrintColor(index) {
    const removed = selectedPrintColors.splice(index, 1)[0];
    updateModalSelectedColors();
    
    // Update Farbkarten
    document.querySelectorAll('.color-card').forEach(card => {
        const cardName = card.querySelector('.fw-bold').textContent;
        if (cardName === removed.name) {
            card.classList.remove('selected');
            const icon = card.querySelector('.bi-check-circle-fill');
            if (icon) icon.remove();
        }
    });
}

// Speichere Druckfarben
function savePrintColors() {
    // Speichere als JSON
    document.getElementById('selected_print_colors').value = JSON.stringify(selectedPrintColors);
    
    // Update Anzeige
    const displayText = selectedPrintColors.map(c => c.name).join(', ');
    document.getElementById('print_colors').value = displayText;
    
    // Update Detail-Anzeige
    updatePrintColorsDisplay();
    
    // Schließe Modal
    bootstrap.Modal.getInstance(document.getElementById('printColorModal')).hide();
}

// Update Druckfarben-Anzeige
function updatePrintColorsDisplay() {
    const container = document.getElementById('selected-print-colors-display');
    
    if (selectedPrintColors.length === 0) {
        container.innerHTML = '';
        return;
    }
    
    container.innerHTML = `
        <div class="mt-2">
            <small class="text-muted d-block mb-1">Ausgewählte Farben:</small>
            <div class="d-flex flex-wrap gap-1">
                ${selectedPrintColors.map(color => {
                    const textColor = getContrastColor(color.hex);
                    let details = [color.name];
                    
                    // Füge Details hinzu
                    if (color.pantone) details.push(`Pantone ${color.pantone}`);
                    if (color.hex) details.push(color.hex);
                    if (color.rgb) details.push(`RGB(${color.rgb})`);
                    if (color.cmyk) details.push(color.cmyk);
                    
                    return `
                        <span class="badge" style="background-color: ${color.hex}; color: ${textColor};"
                              title="${details.join(' | ')}">
                            ${color.name}
                        </span>
                    `;
                }).join('')}
            </div>
        </div>
    `;
}

// Hilfsfunktionen
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : '';
}

function rgbToHex(r, g, b) {
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

function getContrastColor(hexColor) {
    const r = parseInt(hexColor.slice(1, 3), 16);
    const g = parseInt(hexColor.slice(3, 5), 16);
    const b = parseInt(hexColor.slice(5, 7), 16);
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;
    return brightness > 128 ? '#000000' : '#FFFFFF';
}
