// Garn-Auswahl Funktionen für Aufträge - Bereinigte Version
let selectedThreads = [];
let orderType = 'embroidery';
let lastLoadedColors = [];

function openThreadSelector() {
    try {
        console.log('Opening thread selector...');
        
        // Auftragstyp ermitteln
        const orderTypeElement = document.querySelector('input[name="order_type"]:checked') || 
                               document.querySelector('select[name="order_type"]');
        if (orderTypeElement) {
            orderType = orderTypeElement.value;
            console.log('Order type:', orderType);
        }
        
        // Bootstrap prüfen
        if (typeof bootstrap === 'undefined') {
            alert('Bootstrap ist nicht geladen. Bitte die Seite neu laden.');
            return;
        }
        
        // Modal entfernen und neu erstellen
        const existingModal = document.getElementById('threadSelectorModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        createThreadSelectorModal();
        loadAvailableThreads();
        
        // Modal öffnen
        const modal = new bootstrap.Modal(document.getElementById('threadSelectorModal'));
        modal.show();
        
    } catch (error) {
        console.error('Fehler beim Öffnen des Thread Selectors:', error);
        alert('Fehler beim Öffnen der Farbauswahl: ' + error.message);
    }
}

function createThreadSelectorModal() {
    try {
        console.log('Creating thread selector modal...');
        const isPrinting = orderType === 'printing' || orderType === 'dtf';
        
        const modalHtml = `
        <div class="modal fade" id="threadSelectorModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-palette"></i> ${isPrinting ? 'Druckfarben auswählen' : 'Garn-Farben auswählen'}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        ${isPrinting ? getPrintColorSection() : ''}
                        
                        <!-- Suchfeld -->
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <input type="text" class="form-control" id="threadSearchInput" 
                                       placeholder="Suche nach Farbnummer oder Name..." 
                                       onkeyup="filterThreads()">
                            </div>
                            <div class="col-md-3">
                                <select class="form-select" id="threadManufacturerFilter" onchange="filterThreads()">
                                    <option value="">Alle Hersteller</option>
                                </select>
                            </div>
                            <div class="col-md-3">
                                <select class="form-select" id="threadCategoryFilter" onchange="filterThreads()">
                                    <option value="">Alle Kategorien</option>
                                </select>
                            </div>
                        </div>
                        
                        <!-- Ausgewählte Farben -->
                        <div class="mb-3">
                            <h6>Ausgewählte Farben:</h6>
                            <div id="modalSelectedThreads" class="d-flex flex-wrap gap-2">
                                <span class="text-muted">Noch keine Farben ausgewählt</span>
                            </div>
                        </div>
                        
                        <!-- Verfügbare Farben -->
                        <div style="max-height: 400px; overflow-y: auto;">
                            <div id="availableThreadsList" class="row g-2">
                                <div class="text-center p-4">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Lade Farben...</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                        <button type="button" class="btn btn-primary" onclick="confirmThreadSelection()">
                            <i class="bi bi-check"></i> Auswahl übernehmen
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        console.log('Modal HTML added to DOM');
        
    } catch (error) {
        console.error('Fehler beim Erstellen des Modals:', error);
        alert('Fehler beim Erstellen der Farbauswahl: ' + error.message);
    }
}

function getPrintColorSection() {
    return `
    <div class="card mb-3">
        <div class="card-header">
            <h6 class="mb-0"><i class="bi bi-plus-circle"></i> Farbe hinzufügen</h6>
        </div>
        <div class="card-body">
            <div class="row g-2">
                <div class="col-md-2">
                    <input type="color" class="form-control form-control-color" id="printColorPicker" 
                           value="#000000" title="Farbe wählen">
                </div>
                <div class="col-md-3">
                    <input type="text" class="form-control" id="printColorHex" 
                           placeholder="#000000" pattern="^#[0-9A-Fa-f]{6}$">
                </div>
                <div class="col-md-5">
                    <input type="text" class="form-control" id="printColorLabel" 
                           placeholder="Bezeichnung (z.B. Logo, Schrift)">
                </div>
                <div class="col-md-2">
                    <button type="button" class="btn btn-primary w-100" onclick="addPrintColor()">
                        <i class="bi bi-plus"></i> Hinzufügen
                    </button>
                </div>
            </div>
            <small class="text-muted">Tipp: Sie können auch Farben aus der Bibliothek unten auswählen</small>
        </div>
    </div>`;
}

function loadAvailableThreads() {
    const isPrinting = orderType === 'printing' || orderType === 'dtf';
    const url = isPrinting ? '/threads/api/print-colors' : '/threads/api/colors';
    
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('HTTP error! status: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            console.log('API Response:', data);
            if (data.success && data.colors) {
                lastLoadedColors = data.colors;
                
                if (isPrinting) {
                    displayPrintColors(data.colors);
                    if (data.systems) {
                        updateSystemFilter(data.systems);
                    }
                } else {
                    displayAvailableThreads(data.colors);
                    if (data.manufacturers) {
                        updateManufacturerFilter(data.manufacturers);
                    }
                }
                
                // Kategorien aktualisieren
                const categories = [...new Set(data.colors.map(c => c.category).filter(Boolean))];
                if (categories.length > 0) {
                    updateCategoryFilter(categories);
                }
            } else {
                throw new Error('Keine Farben gefunden');
            }
        })
        .catch(error => {
            console.error('Fehler beim Laden der Farben:', error);
            document.getElementById('availableThreadsList').innerHTML = 
                `<div class="col-12 text-center text-danger">
                    <p>Fehler beim Laden der Farben</p>
                    <small>${error.message}</small>
                </div>`;
        });
}

function displayAvailableThreads(colors) {
    const container = document.getElementById('availableThreadsList');
    container.innerHTML = '';
    
    if (!colors || colors.length === 0) {
        container.innerHTML = '<div class="col-12 text-center text-muted p-4">Keine Garnfarben vorhanden</div>';
        return;
    }
    
    colors.forEach(color => {
        const isSelected = selectedThreads.some(t => t.id === color.id);
        const colorCard = `
            <div class="col-md-4 thread-item">
                <div class="card h-100 ${isSelected ? 'border-primary' : ''}" 
                     onclick="toggleThreadSelection('${color.id}')"
                     style="cursor: pointer;">
                    <div class="card-body p-2">
                        <div class="d-flex align-items-center">
                            <div class="color-preview me-2" style="width: 30px; height: 30px; 
                                 background-color: ${color.hex_color || '#ccc'}; 
                                 border: 1px solid #ddd; border-radius: 4px;"></div>
                            <div class="flex-grow-1">
                                <strong>${color.color_number}</strong><br>
                                <small>${color.color_name_de || color.color_name_en || ''}</small><br>
                                <small class="text-muted">${color.manufacturer}</small>
                            </div>
                            ${isSelected ? '<i class="bi bi-check-circle-fill text-primary"></i>' : ''}
                        </div>
                    </div>
                </div>
            </div>`;
        container.insertAdjacentHTML('beforeend', colorCard);
    });
}

function displayPrintColors(colors) {
    const container = document.getElementById('availableThreadsList');
    container.innerHTML = '';
    
    if (!colors || colors.length === 0) {
        container.innerHTML = '<div class="col-12 text-center text-muted p-4">Keine Druckfarben vorhanden</div>';
        return;
    }
    
    colors.forEach(color => {
        const isSelected = selectedThreads.some(t => t.id === color.id);
        const colorCard = `
            <div class="col-md-4 thread-item">
                <div class="card h-100 ${isSelected ? 'border-primary' : ''}" 
                     onclick="togglePrintColorSelection('${color.id}')"
                     style="cursor: pointer;">
                    <div class="card-body p-2">
                        <div class="d-flex align-items-start">
                            <div class="color-preview me-2" style="width: 40px; height: 40px; 
                                 background-color: ${color.hex || '#ccc'}; 
                                 border: 1px solid #ddd; border-radius: 4px;"></div>
                            <div class="flex-grow-1">
                                <strong>${color.system} ${color.code}</strong><br>
                                <small>${color.name}</small><br>
                                <small class="text-muted">
                                    ${color.hex}<br>
                                    RGB: ${color.rgb}<br>
                                    CMYK: ${color.cmyk}
                                </small>
                            </div>
                            ${isSelected ? '<i class="bi bi-check-circle-fill text-primary"></i>' : ''}
                        </div>
                    </div>
                </div>
            </div>`;
        container.insertAdjacentHTML('beforeend', colorCard);
    });
}

function toggleThreadSelection(colorId) {
    const color = lastLoadedColors.find(c => c.id === colorId);
    if (!color) return;
    
    const index = selectedThreads.findIndex(t => t.id === colorId);
    
    if (index > -1) {
        selectedThreads.splice(index, 1);
    } else {
        const threadData = {
            id: color.id,
            colorNumber: color.color_number,
            colorName: color.color_name_de || color.color_name_en,
            hexColor: color.hex_color,
            manufacturer: color.manufacturer
        };
        
        // Bei Stickerei: Nadelposition zuweisen
        if (orderType === 'embroidery' || orderType === 'combined') {
            threadData.needlePosition = selectedThreads.length + 1;
        }
        
        selectedThreads.push(threadData);
    }
    
    updateSelectedThreadsDisplay();
    displayAvailableThreads(lastLoadedColors);
}

function togglePrintColorSelection(colorId) {
    const color = lastLoadedColors.find(c => c.id === colorId);
    if (!color) return;
    
    const index = selectedThreads.findIndex(t => t.id === colorId);
    
    if (index > -1) {
        selectedThreads.splice(index, 1);
    } else {
        const colorData = {
            id: color.id,
            colorNumber: color.code,
            colorName: color.name,
            hexColor: color.hex,
            manufacturer: color.system,
            system: color.system,
            rgb: color.rgb,
            cmyk: color.cmyk
        };
        
        // Bei Druck optional Label abfragen
        const label = prompt('Bezeichnung für diese Farbe (optional, z.B. "Logo", "Hintergrund"):', '');
        if (label !== null && label.trim() !== '') {
            colorData.label = label.trim();
        }
        
        selectedThreads.push(colorData);
    }
    
    updateSelectedThreadsDisplay();
    displayPrintColors(lastLoadedColors);
}

function updateSelectedThreadsDisplay() {
    const modalDisplay = document.getElementById('modalSelectedThreads');
    
    if (selectedThreads.length === 0) {
        modalDisplay.innerHTML = '<span class="text-muted">Noch keine Farben ausgewählt</span>';
    } else {
        const isPrinting = orderType === 'printing' || orderType === 'dtf';
        const showNeedles = orderType === 'embroidery' || orderType === 'combined';
        
        modalDisplay.innerHTML = selectedThreads.map((thread, index) => {
            let displayText = '';
            
            if (isPrinting && thread.label) {
                displayText = `${thread.hexColor || thread.colorNumber} - ${thread.label}`;
            } else {
                displayText = `${thread.colorNumber} - ${thread.colorName || ''}`;
            }
            
            return `
            <span class="badge bg-secondary d-inline-flex align-items-center me-2 mb-2">
                ${showNeedles ? `<span class="me-1">N${thread.needlePosition}:</span>` : ''}
                <span class="color-dot me-1" style="display: inline-block; width: 12px; height: 12px; 
                      background-color: ${thread.hexColor || '#ccc'}; border-radius: 50%; border: 1px solid #666;"></span>
                ${displayText}
                <button type="button" class="btn-close btn-close-white ms-2" 
                        onclick="removeThreadSelection(${index})"
                        style="font-size: 0.7rem;"></button>
            </span>`;
        }).join('');
    }
}

function removeThreadSelection(index) {
    if (index >= 0 && index < selectedThreads.length) {
        selectedThreads.splice(index, 1);
        updateSelectedThreadsDisplay();
        
        // Anzeige aktualisieren
        const isPrinting = orderType === 'printing' || orderType === 'dtf';
        if (isPrinting) {
            displayPrintColors(lastLoadedColors);
        } else {
            displayAvailableThreads(lastLoadedColors);
        }
    }
}

function filterThreads() {
    const searchTerm = document.getElementById('threadSearchInput').value.toLowerCase();
    const manufacturerOrSystem = document.getElementById('threadManufacturerFilter').value;
    const category = document.getElementById('threadCategoryFilter').value;
    const isPrinting = orderType === 'printing' || orderType === 'dtf';
    
    if (lastLoadedColors) {
        const filteredColors = lastLoadedColors.filter(color => {
            let matchesSearch, matchesManufacturerOrSystem;
            
            if (isPrinting) {
                matchesSearch = !searchTerm || 
                    (color.code && color.code.toLowerCase().includes(searchTerm)) ||
                    (color.name && color.name.toLowerCase().includes(searchTerm)) ||
                    (color.hex && color.hex.toLowerCase().includes(searchTerm));
                matchesManufacturerOrSystem = !manufacturerOrSystem || color.system === manufacturerOrSystem;
            } else {
                matchesSearch = !searchTerm || 
                    color.color_number.toLowerCase().includes(searchTerm) ||
                    (color.color_name_de && color.color_name_de.toLowerCase().includes(searchTerm)) ||
                    (color.color_name_en && color.color_name_en.toLowerCase().includes(searchTerm));
                matchesManufacturerOrSystem = !manufacturerOrSystem || color.manufacturer === manufacturerOrSystem;
            }
            
            const matchesCategory = !category || color.category === category;
            
            return matchesSearch && matchesManufacturerOrSystem && matchesCategory;
        });
        
        if (isPrinting) {
            displayPrintColors(filteredColors);
        } else {
            displayAvailableThreads(filteredColors);
        }
    }
}

function updateManufacturerFilter(manufacturers) {
    const filter = document.getElementById('threadManufacturerFilter');
    filter.innerHTML = '<option value="">Alle Hersteller</option>';
    manufacturers.forEach(mfr => {
        filter.innerHTML += `<option value="${mfr}">${mfr}</option>`;
    });
}

function updateSystemFilter(systems) {
    const filter = document.getElementById('threadManufacturerFilter');
    filter.innerHTML = '<option value="">Alle Systeme</option>';
    systems.forEach(sys => {
        filter.innerHTML += `<option value="${sys}">${sys}</option>`;
    });
}

function updateCategoryFilter(categories) {
    const filter = document.getElementById('threadCategoryFilter');
    filter.innerHTML = '<option value="">Alle Kategorien</option>';
    categories.forEach(cat => {
        filter.innerHTML += `<option value="${cat}">${cat}</option>`;
    });
}

function confirmThreadSelection() {
    const isPrinting = orderType === 'printing' || orderType === 'dtf';
    
    // Hauptformular aktualisieren
    let displayValue = '';
    
    if (orderType === 'embroidery' || orderType === 'combined') {
        displayValue = selectedThreads.map(t => 
            `Nadel ${t.needlePosition}: ${t.colorNumber} - ${t.colorName}`
        ).join(', ');
    } else if (isPrinting) {
        displayValue = selectedThreads.map(t => {
            if (t.label) {
                return `${t.hexColor || t.colorNumber} - ${t.label}`;
            } else {
                return `${t.colorNumber} - ${t.colorName}`;
            }
        }).join(', ');
    }
    
    document.getElementById('thread_colors').value = displayValue;
    document.getElementById('selected_threads').value = JSON.stringify(selectedThreads);
    
    // Anzeige unter dem Eingabefeld aktualisieren
    const displayDiv = document.getElementById('selected-threads-display');
    displayDiv.innerHTML = selectedThreads.map(thread => {
        let badgeContent = '';
        
        if (thread.needlePosition) {
            badgeContent = `N${thread.needlePosition}: ${thread.colorNumber}`;
        } else if (thread.label) {
            badgeContent = thread.label;
        } else {
            badgeContent = thread.colorNumber;
        }
        
        return `
        <span class="badge bg-primary me-1 mb-1">
            <span class="color-dot me-1" style="display: inline-block; width: 10px; height: 10px; 
                  background-color: ${thread.hexColor || '#ccc'}; border-radius: 50%; border: 1px solid #fff;"></span>
            ${badgeContent}
        </span>`;
    }).join('');
    
    // Modal schließen
    const modal = bootstrap.Modal.getInstance(document.getElementById('threadSelectorModal'));
    modal.hide();
}

function addPrintColor() {
    const hexInput = document.getElementById('printColorHex');
    const labelInput = document.getElementById('printColorLabel');
    const colorPicker = document.getElementById('printColorPicker');
    
    if (!hexInput || !labelInput || !colorPicker) return;
    
    const hexColor = hexInput.value || colorPicker.value;
    const label = labelInput.value.trim();
    
    if (!/^#[0-9A-Fa-f]{6}$/i.test(hexColor)) {
        alert('Bitte geben Sie eine gültige Hex-Farbe ein (z.B. #FF0000)');
        return;
    }
    
    const colorId = 'custom_' + Date.now();
    
    const threadData = {
        id: colorId,
        colorNumber: hexColor,
        colorName: label || 'Benutzerdefiniert',
        hexColor: hexColor,
        manufacturer: 'Benutzerdefiniert',
        label: label,
        isCustom: true
    };
    
    selectedThreads.push(threadData);
    updateSelectedThreadsDisplay();
    
    // Felder zurücksetzen
    labelInput.value = '';
    hexInput.value = '#000000';
    colorPicker.value = '#000000';
}

// Initialisierung
document.addEventListener('DOMContentLoaded', function() {
    // Prüfen ob bereits Farben ausgewählt wurden
    const selectedThreadsInput = document.getElementById('selected_threads');
    if (selectedThreadsInput && selectedThreadsInput.value && selectedThreadsInput.value !== '[]') {
        try {
            selectedThreads = JSON.parse(selectedThreadsInput.value);
        } catch (e) {
            console.error('Fehler beim Parsen der ausgewählten Farben:', e);
        }
    }
});

console.log('Thread selector fixed version loaded successfully');