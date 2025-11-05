// Garn-Auswahl Funktionen für Aufträge
let selectedThreads = [];
let orderType = 'embroidery'; // Default

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
        
        // Modal entfernen und neu erstellen, um sicherzustellen dass der richtige Typ angezeigt wird
        const existingModal = document.getElementById('threadSelectorModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        createThreadSelectorModal();
        
        // Garne laden
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
    <div class="modal fade" id="threadSelectorModal" tabindex="-1" aria-labelledby="threadSelectorModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="threadSelectorModalLabel">
                        <i class="bi bi-palette"></i> ${isPrinting ? 'Druckfarben auswählen' : 'Garn-Farben auswählen'}
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    ${isPrinting ? `
                    <!-- Manuelle Farbeingabe für Druck -->
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
                                           placeholder="#000000" pattern="^#[0-9A-Fa-f]{6}$"
                                           onchange="updateColorPicker(this.value)">
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
                    </div>
                    ` : ''}
                    
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
        
        // Event Listener für Farbauswahl bei Druck
        if (isPrinting) {
            setTimeout(() => {
                const colorPicker = document.getElementById('printColorPicker');
                const hexInput = document.getElementById('printColorHex');
                
                if (colorPicker && hexInput) {
                    colorPicker.addEventListener('change', function() {
                        hexInput.value = this.value;
                    });
                    
                    hexInput.value = colorPicker.value;
                }
            }, 100);
        }
        
    } catch (error) {
        console.error('Fehler beim Erstellen des Modals:', error);
        alert('Fehler beim Erstellen der Farbauswahl: ' + error.message);
    }
}

function loadAvailableThreads() {
    const isPrinting = orderType === 'printing' || orderType === 'dtf';
    
    // Für Druckaufträge: Lade Druckfarben
    if (isPrinting) {
        fetch('/threads/api/print-colors')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Print Colors API Response:', data); // Debug
                if (data.success && data.colors) {
                    window.lastLoadedColors = data.colors;
                    displayPrintColors(data.colors);
                    if (data.systems) {
                        updateSystemFilter(data.systems);
                    }
                    // Extract unique categories from colors if not provided
                    const categories = data.categories || [...new Set(data.colors.map(c => c.category).filter(Boolean))];
                    if (categories.length > 0) {
                        updateCategoryFilter(categories);
                    }
                } else {
                    throw new Error('Keine Druckfarben gefunden');
                }
            })
            .catch(error => {
                console.error('Fehler beim Laden der Druckfarben:', error);
                document.getElementById('availableThreadsList').innerHTML = 
                    `<div class="col-12 text-center text-danger">
                        <p>Fehler beim Laden der Druckfarben</p>
                        <small>${error.message}</small>
                    </div>`;
            });
    } else {
        // Für Stickerei: Lade Garnfarben
        fetch('/threads/api/colors')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('API Response:', data); // Debug
                if (data.success && data.colors) {
                    // Speichere die geladenen Farben für spätere Verwendung
                    window.lastLoadedColors = data.colors;
                    displayAvailableThreads(data.colors);
                    if (data.manufacturers) {
                        updateManufacturerFilter(data.manufacturers);
                    }
                    // Extract unique categories from colors
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
}

function displayAvailableThreads(colors) {
    const container = document.getElementById('availableThreadsList');
    container.innerHTML = '';
    
    if (!colors || colors.length === 0) {
        container.innerHTML = '<div class="col-12 text-center text-muted p-4">Keine Garnfarben im System vorhanden</div>';
        return;
    }
    
    colors.forEach(color => {
        const colorCard = `
            <div class="col-md-4 thread-item" data-manufacturer="${color.manufacturer}" 
                 data-category="${color.category}" data-search="${color.color_number} ${color.color_name_de} ${color.color_name_en}">
                <div class="card h-100 ${selectedThreads.some(t => t.id === color.id) ? 'border-primary' : ''}" 
                     onclick="toggleThreadSelection('${color.id}', '${color.color_number}', '${color.color_name_de || color.color_name_en}', '${color.hex_color}', '${color.manufacturer}', '${color.pantone || ''}', '${color.rgb || ''}', '${color.cmyk || ''}')"
                     style="cursor: pointer;">
                    <div class="card-body p-2">
                        <div class="d-flex align-items-center">
                            <div class="color-preview me-2" style="width: 30px; height: 30px; 
                                 background-color: ${color.hex_color || '#ccc'}; 
                                 border: 1px solid #ddd; border-radius: 4px;"></div>
                            <div class="flex-grow-1">
                                <strong>${color.color_number}</strong><br>
                                <small>${color.color_name_de || color.color_name_en}</small><br>
                                <small class="text-muted">${color.manufacturer}</small>
                            </div>
                            ${selectedThreads.some(t => t.id === color.id) ? 
                              '<i class="bi bi-check-circle-fill text-primary"></i>' : ''}
                        </div>
                    </div>
                </div>
            </div>`;
        container.insertAdjacentHTML('beforeend', colorCard);
    });
}

function updateManufacturerFilter(manufacturers) {
    const filter = document.getElementById('threadManufacturerFilter');
    filter.innerHTML = '<option value="">Alle Hersteller</option>';
    manufacturers.forEach(manufacturer => {
        filter.innerHTML += `<option value="${manufacturer}">${manufacturer}</option>`;
    });
}

function updateSystemFilter(systems) {
    const filter = document.getElementById('threadManufacturerFilter');
    filter.innerHTML = '<option value="">Alle Systeme</option>';
    systems.forEach(system => {
        filter.innerHTML += `<option value="${system}">${system}</option>`;
    });
}

function updateCategoryFilter(categories) {
    const filter = document.getElementById('threadCategoryFilter');
    filter.innerHTML = '<option value="">Alle Kategorien</option>';
    categories.forEach(category => {
        filter.innerHTML += `<option value="${category}">${category}</option>`;
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
        const colorCard = `
            <div class="col-md-4 thread-item" data-system="${color.system}" 
                 data-category="${color.category}" 
                 data-search="${color.code} ${color.name} ${color.hex} ${color.rgb} ${color.cmyk}">
                <div class="card h-100 ${selectedThreads.some(t => t.id === color.id) ? 'border-primary' : ''}" 
                     onclick="togglePrintColorSelection('${color.id}', '${color.code}', '${color.name}', '${color.hex}', '${color.system}', '${color.rgb}', '${color.cmyk}')"
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
                            ${selectedThreads.some(t => t.id === color.id) ? 
                              '<i class="bi bi-check-circle-fill text-primary"></i>' : ''}
                        </div>
                    </div>
                </div>
            </div>`;
        container.insertAdjacentHTML('beforeend', colorCard);
    });
}

function togglePrintColorSelection(id, code, name, hex, system, rgb, cmyk) {
    const index = selectedThreads.findIndex(t => t.id === id);
    
    if (index > -1) {
        selectedThreads.splice(index, 1);
    } else {
        const colorData = {
            id: id,
            colorNumber: code,
            colorName: name,
            hexColor: hex,
            manufacturer: system,
            system: system,
            rgb: rgb,
            cmyk: cmyk,
            code: code
        };
        
        // Bei Druck optional Label abfragen
        const label = prompt('Bezeichnung für diese Farbe (optional, z.B. "Logo", "Hintergrund"):', '');
        if (label !== null && label.trim() !== '') {
            colorData.label = label.trim();
        }
        
        selectedThreads.push(colorData);
    }
    
    updateSelectedThreadsDisplay();
    
    // Aktuelle Ansicht beibehalten
    const searchTerm = document.getElementById('threadSearchInput').value.toLowerCase();
    const selectedSystem = document.getElementById('threadManufacturerFilter').value;
    const category = document.getElementById('threadCategoryFilter').value;
    
    if (window.lastLoadedColors) {
        let colorsToDisplay = window.lastLoadedColors;
        
        // Wende aktuelle Filter an
        if (searchTerm || selectedSystem || category) {
            colorsToDisplay = window.lastLoadedColors.filter(color => {
                const matchesSearch = !searchTerm || 
                    (color.code && color.code.toLowerCase().includes(searchTerm)) ||
                    (color.name && color.name.toLowerCase().includes(searchTerm)) ||
                    (color.hex && color.hex.toLowerCase().includes(searchTerm));
                const matchesSystem = !selectedSystem || color.system === selectedSystem;
                const matchesCategory = !category || color.category === category;
                
                return matchesSearch && matchesSystem && matchesCategory;
            });
        }
        
        displayPrintColors(colorsToDisplay);
    }
}

function filterThreads() {
    const searchTerm = document.getElementById('threadSearchInput').value.toLowerCase();
    const manufacturerOrSystem = document.getElementById('threadManufacturerFilter').value;
    const category = document.getElementById('threadCategoryFilter').value;
    const isPrinting = orderType === 'printing' || orderType === 'dtf';
    
    console.log('Filtering with:', {searchTerm, manufacturerOrSystem, category, isPrinting}); // Debug
    
    // Filtere die Farben und speichere das gefilterte Ergebnis
    if (window.lastLoadedColors) {
        const filteredColors = window.lastLoadedColors.filter(color => {
            let matchesSearch, matchesManufacturerOrSystem;
            
            if (isPrinting) {
                // Für Druckfarben
                matchesSearch = !searchTerm || 
                    (color.code && color.code.toLowerCase().includes(searchTerm)) ||
                    (color.name && color.name.toLowerCase().includes(searchTerm)) ||
                    (color.hex && color.hex.toLowerCase().includes(searchTerm)) ||
                    (color.rgb && color.rgb.toLowerCase().includes(searchTerm)) ||
                    (color.cmyk && color.cmyk.toLowerCase().includes(searchTerm));
                matchesManufacturerOrSystem = !manufacturerOrSystem || color.system === manufacturerOrSystem;
            } else {
                // Für Garnfarben
                matchesSearch = !searchTerm || 
                    color.color_number.toLowerCase().includes(searchTerm) ||
                    (color.color_name_de && color.color_name_de.toLowerCase().includes(searchTerm)) ||
                    (color.color_name_en && color.color_name_en.toLowerCase().includes(searchTerm));
                matchesManufacturerOrSystem = !manufacturerOrSystem || color.manufacturer === manufacturerOrSystem;
            }
            
            const matchesCategory = !category || color.category === category;
            
            return matchesSearch && matchesManufacturerOrSystem && matchesCategory;
        });
        
        console.log('Filtered colors:', filteredColors.length); // Debug
        
        // Zeige nur die gefilterten Farben an
        if (isPrinting) {
            displayPrintColors(filteredColors);
        } else {
            displayAvailableThreads(filteredColors);
        }
    }
}

function toggleThreadSelection(id, colorNumber, colorName, hexColor, manufacturer, pantone, rgb, cmyk) {
    const index = selectedThreads.findIndex(t => t.id === id);
    const isPrinting = orderType === 'printing' || orderType === 'dtf';
    
    if (index > -1) {
        selectedThreads.splice(index, 1);
    } else {
        const threadData = {
            id: id,
            colorNumber: colorNumber,
            colorName: colorName,
            hexColor: hexColor,
            manufacturer: manufacturer
        };
        
        // Bei Stickerei: Nadelposition zuweisen
        if (orderType === 'embroidery' || orderType === 'combined') {
            threadData.needlePosition = selectedThreads.length + 1;
        }
        
        // Bei Druck: Farbinformationen speichern und nach Label fragen
        if (isPrinting || orderType === 'combined') {
            threadData.pantone = pantone || '';
            threadData.rgb = rgb || '';
            threadData.cmyk = cmyk || '';
            
            // Bei Druck optional Label abfragen
            if (isPrinting) {
                const label = prompt('Bezeichnung für diese Farbe (optional):', '');
                if (label !== null && label.trim() !== '') {
                    threadData.label = label.trim();
                }
            }
        }
        
        selectedThreads.push(threadData);
    }
    
    updateSelectedThreadsDisplay();
    
    // Aktuelle gefilterte Ansicht beibehalten
    const searchTerm = document.getElementById('threadSearchInput').value.toLowerCase();
    const selectedManufacturer = document.getElementById('threadManufacturerFilter').value;
    const category = document.getElementById('threadCategoryFilter').value;
    
    if (window.lastLoadedColors) {
        let colorsToDisplay = window.lastLoadedColors;
        
        // Wende aktuelle Filter an
        if (searchTerm || selectedManufacturer || category) {
            colorsToDisplay = window.lastLoadedColors.filter(color => {
                const matchesSearch = !searchTerm || 
                    color.color_number.toLowerCase().includes(searchTerm) ||
                    (color.color_name_de && color.color_name_de.toLowerCase().includes(searchTerm)) ||
                    (color.color_name_en && color.color_name_en.toLowerCase().includes(searchTerm));
                const matchesManufacturer = !selectedManufacturer || color.manufacturer === selectedManufacturer;
                const matchesCategory = !category || color.category === category;
                
                return matchesSearch && matchesManufacturer && matchesCategory;
            });
        }
        
        displayAvailableThreads(colorsToDisplay);
    }
}

function updateSelectedThreadsDisplay() {
    const modalDisplay = document.getElementById('modalSelectedThreads');
    
    if (selectedThreads.length === 0) {
        modalDisplay.innerHTML = '<span class="text-muted">Noch keine Farben ausgewählt</span>';
    } else {
        const showNeedles = orderType === 'embroidery' || orderType === 'combined';
        const isPrinting = orderType === 'printing' || orderType === 'dtf';
        
        modalDisplay.innerHTML = `
            <div class="thread-list ${showNeedles ? 'sortable' : ''}">
                ${selectedThreads.map((thread, index) => {
                    let displayText = '';
                    
                    // Bei Druck: Zeige Label oder Farbname
                    if (isPrinting && thread.label) {
                        displayText = `${thread.hexColor || thread.colorNumber} - ${thread.label}`;
                    } else if (isPrinting && thread.isCustom) {
                        displayText = `${thread.hexColor} - ${thread.colorName}`;
                    } else {
                        displayText = `${thread.colorNumber} - ${thread.colorName}`;
                        if (thread.pantone && isPrinting) {
                            displayText += ` (${thread.pantone})`;
                        }
                    }
                    
                    return `
                    <span class="badge bg-secondary d-inline-flex align-items-center me-2 mb-2 thread-item" 
                          data-index="${index}" ${showNeedles ? 'draggable="true"' : ''} 
                          style="cursor: ${showNeedles ? 'move' : 'default'};">
                        ${showNeedles ? `
                            <span class="needle-number me-1" style="min-width: 20px;">
                                <input type="number" class="form-control form-control-sm p-0 text-center" 
                                       value="${thread.needlePosition}" min="1" max="15"
                                       style="width: 35px; height: 20px; border: 1px solid rgba(255,255,255,0.3);"
                                       onclick="event.stopPropagation();"
                                       onchange="updateNeedlePosition(${index}, this.value)">
                            </span>
                            <i class="bi bi-grip-vertical me-1" style="opacity: 0.6;"></i>
                        ` : ''}
                        <span class="color-dot me-1" style="display: inline-block; width: 12px; height: 12px; 
                              background-color: ${thread.hexColor || '#ccc'}; border-radius: 50%; border: 1px solid #666;"></span>
                        ${displayText}
                        <button type="button" class="btn-close btn-close-white ms-2" 
                                onclick="removeThreadSelection(${index})"
                                style="font-size: 0.7rem;"></button>
                    </span>`;
                }).join('')}
            </div>
        `;
        
        // Drag&Drop initialisieren bei Stickerei
        if (showNeedles) {
            initDragAndDrop();
        }
    }
    
    // Nadelpositionen neu nummerieren bei Stickerei
    if (orderType === 'embroidery' || orderType === 'combined') {
        selectedThreads.forEach((thread, index) => {
            thread.needlePosition = index + 1;
        });
    }
}

function removeThreadSelection(index) {
    if (index >= 0 && index < selectedThreads.length) {
        selectedThreads.splice(index, 1);
        updateSelectedThreadsDisplay();
        
        // Karten neu rendern für konsistente Anzeige
        const currentColors = [];
        document.querySelectorAll('.thread-item').forEach(item => {
            if (item.style.display !== 'none') {
                // Extrahiere die Farb-ID aus dem data-search Attribut
                const colorData = window.lastLoadedColors.find(c => 
                    item.dataset.search.includes(c.color_number) && 
                    item.dataset.manufacturer === c.manufacturer
                );
                if (colorData) {
                    currentColors.push(colorData);
                }
            }
        });
        
        // Wenn wir die aktuellen Farben haben, zeige sie neu an
        if (currentColors.length > 0) {
            displayAvailableThreads(currentColors);
        } else if (window.lastLoadedColors) {
            // Fallback: zeige alle Farben
            displayAvailableThreads(window.lastLoadedColors);
        }
    }
}

function confirmThreadSelection() {
    // Hauptformular aktualisieren
    const isPrinting = orderType === 'printing' || orderType === 'dtf';
    
    if (orderType === 'embroidery' || orderType === 'combined') {
        // Bei Stickerei mit Nadelpositionen
        document.getElementById('thread_colors').value = selectedThreads.map(t => 
            `Nadel ${t.needlePosition}: ${t.colorNumber} - ${t.colorName}`
        ).join(', ');
    } else if (isPrinting) {
        // Bei Druck mit Labels
        document.getElementById('thread_colors').value = selectedThreads.map(t => {
            if (t.label) {
                return `${t.hexColor || t.colorNumber} - ${t.label}`;
            } else if (t.isCustom) {
                return `${t.hexColor} - ${t.colorName}`;
            } else {
                let colorInfo = `${t.colorNumber} - ${t.colorName}`;
                if (t.pantone) colorInfo += ` (${t.pantone})`;
                return colorInfo;
            }
        }).join(', ');
    } else {
        // Standard
        document.getElementById('thread_colors').value = selectedThreads.map(t => {
            let colorInfo = `${t.colorNumber} - ${t.colorName}`;
            if (t.pantone) colorInfo += ` (${t.pantone})`;
            return colorInfo;
        }).join(', ');
    }
    
    document.getElementById('selected_threads').value = JSON.stringify(selectedThreads);
    
    // Anzeige unter dem Eingabefeld aktualisieren
    const displayDiv = document.getElementById('selected-threads-display');
    displayDiv.innerHTML = selectedThreads.map((thread, index) => {
        let badgeContent = '';
        
        if (thread.needlePosition) {
            badgeContent = `N${thread.needlePosition}: ${thread.colorNumber}`;
        } else if (isPrinting && thread.label) {
            badgeContent = thread.label;
        } else if (isPrinting && thread.isCustom) {
            badgeContent = thread.hexColor;
        } else {
            badgeContent = thread.colorNumber;
        }
        
        const title = thread.label || thread.colorName || thread.hexColor;
        
        return `
        <span class="badge bg-primary me-1 mb-1" title="${title}">
            <span class="color-dot me-1" style="display: inline-block; width: 10px; height: 10px; 
                  background-color: ${thread.hexColor || '#ccc'}; border-radius: 50%; border: 1px solid #fff;"></span>
            ${badgeContent}
        </span>`;
    }).join('');
    
    // Modal schließen
    const modal = bootstrap.Modal.getInstance(document.getElementById('threadSelectorModal'));
    modal.hide();
}

// Initialisierung beim Laden der Seite
function initThreadSelector() {
    // Auftragstyp ermitteln
    const orderTypeElement = document.querySelector('input[name="order_type"]:checked') || 
                           document.querySelector('select[name="order_type"]');
    if (orderTypeElement) {
        orderType = orderTypeElement.value;
    }
    
    // Prüfen ob bereits Farben ausgewählt wurden (z.B. bei Bearbeitung)
    const selectedThreadsInput = document.getElementById('selected_threads');
    if (selectedThreadsInput && selectedThreadsInput.value && selectedThreadsInput.value !== '[]') {
        try {
            selectedThreads = JSON.parse(selectedThreadsInput.value);
            
            // Thread colors Feld aktualisieren
            if (selectedThreads.length > 0) {
                // Text im Eingabefeld
                if (orderType === 'embroidery' || orderType === 'combined') {
                    document.getElementById('thread_colors').value = selectedThreads.map(t => 
                        `Nadel ${t.needlePosition}: ${t.colorNumber} - ${t.colorName}`
                    ).join(', ');
                } else {
                    document.getElementById('thread_colors').value = selectedThreads.map(t => {
                        let colorInfo = `${t.colorNumber} - ${t.colorName}`;
                        if (t.pantone) colorInfo += ` (${t.pantone})`;
                        return colorInfo;
                    }).join(', ');
                }
                
                // Badge-Anzeige aktualisieren
                const displayDiv = document.getElementById('selected-threads-display');
                displayDiv.innerHTML = selectedThreads.map(thread => {
                    let badgeContent = thread.colorNumber;
                    if (thread.needlePosition) {
                        badgeContent = `N${thread.needlePosition}: ${badgeContent}`;
                    }
                    
                    return `
                    <span class="badge bg-primary me-1 mb-1" title="${thread.colorName}">
                        <span class="color-dot me-1" style="display: inline-block; width: 10px; height: 10px; 
                              background-color: ${thread.hexColor || '#ccc'}; border-radius: 50%; border: 1px solid #fff;"></span>
                        ${badgeContent}
                    </span>`;
                }).join('');
            }
        } catch (e) {
            console.error('Fehler beim Parsen der ausgewählten Farben:', e);
        }
    }
}

// Beim Laden der Seite initialisieren
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initThreadSelector);
} else {
    initThreadSelector();
}

// Drag & Drop Funktionen
let draggedElement = null;

function initDragAndDrop() {
    const items = document.querySelectorAll('.thread-item[draggable="true"]');
    
    items.forEach(item => {
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragend', handleDragEnd);
        item.addEventListener('dragover', handleDragOver);
        item.addEventListener('drop', handleDrop);
        item.addEventListener('dragenter', handleDragEnter);
        item.addEventListener('dragleave', handleDragLeave);
    });
}

function handleDragStart(e) {
    draggedElement = this;
    this.style.opacity = '0.4';
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.innerHTML);
}

function handleDragEnd(e) {
    this.style.opacity = '';
    
    const items = document.querySelectorAll('.thread-item');
    items.forEach(item => {
        item.classList.remove('drag-over');
    });
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';
    return false;
}

function handleDragEnter(e) {
    this.classList.add('drag-over');
}

function handleDragLeave(e) {
    this.classList.remove('drag-over');
}

function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }
    
    if (draggedElement !== this) {
        const draggedIndex = parseInt(draggedElement.dataset.index);
        const targetIndex = parseInt(this.dataset.index);
        
        // Threads neu sortieren
        const draggedThread = selectedThreads[draggedIndex];
        selectedThreads.splice(draggedIndex, 1);
        selectedThreads.splice(targetIndex, 0, draggedThread);
        
        // Nadelpositionen neu nummerieren
        selectedThreads.forEach((thread, index) => {
            thread.needlePosition = index + 1;
        });
        
        // Anzeige aktualisieren
        updateSelectedThreadsDisplay();
    }
    
    return false;
}

// Manuelle Nadelposition ändern
function updateNeedlePosition(index, newPosition) {
    newPosition = parseInt(newPosition);
    if (isNaN(newPosition) || newPosition < 1 || newPosition > 15) {
        // Ungültiger Wert - zurücksetzen
        updateSelectedThreadsDisplay();
        return;
    }
    
    const thread = selectedThreads[index];
    const oldPosition = thread.needlePosition;
    
    if (newPosition === oldPosition) return;
    
    // Thread an neue Position verschieben
    selectedThreads.splice(index, 1);
    
    // Neue Position finden
    let newIndex = newPosition - 1;
    if (newIndex > selectedThreads.length) {
        newIndex = selectedThreads.length;
    }
    
    // Thread einfügen
    selectedThreads.splice(newIndex, 0, thread);
    
    // Alle Nadelpositionen neu nummerieren
    selectedThreads.forEach((t, idx) => {
        t.needlePosition = idx + 1;
    });
    
    updateSelectedThreadsDisplay();
}

// Neue Funktionen für Druckfarben
function updateColorPicker(hexValue) {
    if (/^#[0-9A-Fa-f]{6}$/.test(hexValue)) {
        const colorPicker = document.getElementById('printColorPicker');
        if (colorPicker) {
            colorPicker.value = hexValue;
        }
    }
}

function addPrintColor() {
    const hexInput = document.getElementById('printColorHex');
    const labelInput = document.getElementById('printColorLabel');
    const colorPicker = document.getElementById('printColorPicker');
    
    if (!hexInput || !labelInput || !colorPicker) return;
    
    const hexColor = hexInput.value || colorPicker.value;
    const label = labelInput.value.trim();
    
    // Validiere Hex-Farbe
    if (!/^#[0-9A-Fa-f]{6}$/i.test(hexColor)) {
        alert('Bitte geben Sie eine gültige Hex-Farbe ein (z.B. #FF0000)');
        return;
    }
    
    // Erstelle einzigartige ID
    const colorId = 'custom_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    // Füge zur Auswahl hinzu
    const threadData = {
        id: colorId,
        colorNumber: hexColor,
        colorName: label || 'Benutzerdefiniert',
        hexColor: hexColor,
        manufacturer: 'Benutzerdefiniert',
        label: label,
        isCustom: true
    };
    
    // Prüfe ob Farbe bereits existiert
    const exists = selectedThreads.some(t => 
        t.hexColor.toLowerCase() === hexColor.toLowerCase() && 
        t.label === label
    );
    
    if (exists) {
        alert('Diese Farbe wurde bereits hinzugefügt');
        return;
    }
    
    selectedThreads.push(threadData);
    updateSelectedThreadsDisplay();
    
    // Felder zurücksetzen
    labelInput.value = '';
    hexInput.value = '#000000';
    colorPicker.value = '#000000';
}

// CSS für Drag&Drop
const style = document.createElement('style');
style.textContent = `
    .thread-item.drag-over {
        border: 2px dashed rgba(255, 255, 255, 0.8) !important;
        background-color: rgba(255, 255, 255, 0.1);
    }
    .thread-item[draggable="true"]:hover {
        transform: scale(1.02);
        transition: transform 0.2s;
    }
    .form-control-color {
        width: 100%;
        height: 38px;
        padding: 0.25rem;
    }
`;
document.head.appendChild(style);