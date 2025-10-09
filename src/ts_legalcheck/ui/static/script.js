document.addEventListener('DOMContentLoaded', function() {
    const modelSelect = document.getElementById('model');
    const licensesSelect = document.getElementById('licenses');
    const presetSelect = document.getElementById('preset');
    const form = document.getElementById('mainForm');
    const resultsDiv = document.getElementById('results');

    let selectedModel = null;
    let licensesChoices = null;
    let modelChoices = null;
    let presetChoices = null;

    // Initialize Choices.js for all dropdowns
    modelChoices = new Choices(modelSelect, { searchEnabled: false, shouldSort: false, itemSelectText: '', removeItemButton: false });
    licensesChoices = new Choices(licensesSelect, { removeItemButton: true, shouldSort: false });
    presetChoices = new Choices(presetSelect, { searchEnabled: false, shouldSort: false, itemSelectText: '', removeItemButton: false });

    // Load preset values and populate questions
    presetSelect.addEventListener('change', function() {
        // For Choices.js, get value from presetChoices
        const preset = presetChoices.getValue(true);
        if (!preset) return;
        fetch(`/preset?preset=${encodeURIComponent(preset)}`)
            .then(res => res.json())
            .then(values => {
                Object.entries(values).forEach(([scope, group]) => {
                    Object.entries(group || {}).forEach(([key, val]) => {
                        const cb = document.querySelector(`#questions input[name='${scope}.${key}']`);
                        if (cb) cb.checked = !!val;
                    });
                });
            });
    });

    function updateLicensesChoices(licenses) {
        if (licensesChoices) {
            licensesChoices.clearStore();
            licensesChoices.setChoices(licenses.map(l => ({ value: l, label: l })), 'value', 'label', true);
        }
    }

    function loadLicenses() {
        // For Choices.js, get value from modelChoices
        selectedModel = modelChoices.getValue(true);
        if (!selectedModel) {
            updateLicensesChoices([]);
            return;
        }
        fetch(`/licenses?model=${encodeURIComponent(selectedModel)}`)
            .then(res => res.json())
            .then(licenses => {
                updateLicensesChoices(licenses);
            });
    }

    modelSelect.addEventListener('change', loadLicenses);

    if (modelSelect.value) {
        loadLicenses();
    }

    form.addEventListener('submit', function(e) {
        e.preventDefault();
                
        const errorDiv = document.getElementById('form-error');
        const model = modelChoices.getValue(true);
        const licenses = licensesChoices.getValue(true);
        
        resultsDiv.innerHTML = '';
        errorDiv.textContent = '';

        
        if (!model && (!licenses || (Array.isArray(licenses) && licenses.length === 0))) {
            errorDiv.textContent = 'Please select model and at least one license.';
            return false;

        } else if (!model) {
            errorDiv.textContent = 'Please select model.';
            return false;

        } else if (!licenses || (Array.isArray(licenses) && licenses.length === 0)) {
            errorDiv.textContent = 'Please select at least one license.';
            return false;
        }
        
        const data = {
            model: model,
            licenses: licenses,
            'use-case': {}
        };
        
        document.querySelectorAll('#questions input[type=checkbox]').forEach(cb => {
            const [scope, variable] = cb.name.split('.');
            if (!data['use-case'][scope]) data['use-case'][scope] = {};
            data['use-case'][scope][variable] = cb.checked;
        });

        fetch('/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(res => res.json())
        .then(res => {
            let html = '';
            // Violations/Warnings table FIRST
            if (res.violations && res.violations_tbl) {
                html += '<table><tr>' +
                    '<th style="text-align:center;max-width:440px;min-width:240px;width:44%;white-space:normal;word-break:break-word;font-weight:500;"><strong>Violations / Warnings</strong></th>';
                if (res.licenses) {
                    res.licenses.forEach(l => html += `<th>${l}</th>`);
                }
                html += '</tr>';
                for (let rowIdx = 0; rowIdx < res.violations.length; rowIdx++) {
                    const v = res.violations[rowIdx];
                    let rowStyle = '';
                    if (v.type === 'violation') rowStyle = 'background:#fee2e2;color:#991b1b;font-weight:500;';
                    else if (v.type === 'warning') rowStyle = 'background:#fef9c3;color:#92400e;font-weight:500;';
                    html += `<tr><td style="text-align:left;max-width:440px;min-width:240px;width:44%;white-space:normal;word-break:break-word;${rowStyle}">${v.message}</td>`;
                    for (let colIdx = 0; colIdx < res.violations_tbl.length; colIdx++) {
                        const val = res.violations_tbl[colIdx][rowIdx];
                        let cellStyle = '';
                        if (v.type === 'violation' && val) cellStyle = 'background:#fee2e2;color:#991b1b;font-weight:500;';
                        else if (v.type === 'warning' && val) cellStyle = 'background:#fef9c3;color:#92400e;font-weight:500;';
                        html += `<td style="${cellStyle}">${val ? '✔️' : '❌'}</td>`;
                    }
                    html += '</tr>';
                }
                html += '</table><br>';
            }

            // Obligations table SECOND
            if (res.obligations && res.obligations_tbl) {
                html += '<table><tr>' +
                    '<th style="text-align:center;max-width:440px;min-width:240px;width:44%;white-space:normal;word-break:break-word;font-weight:500;"><strong>Obligations</strong></th>';
                if (res.licenses) {
                    res.licenses.forEach(l => html += `<th>${l}</th>`);
                }
                html += '</tr>';
                for (let rowIdx = 0; rowIdx < res.obligations.length; rowIdx++) {
                    html += `<tr><td style="text-align:left;max-width:440px;min-width:240px;width:44%;white-space:normal;word-break:break-word;font-weight:500;">${res.obligations[rowIdx]}</td>`;
                    for (let colIdx = 0; colIdx < res.obligations_tbl.length; colIdx++) {
                        const val = res.obligations_tbl[colIdx][rowIdx];
                        html += `<td>${val ? '✔️' : '❌'}</td>`;
                    }
                    html += '</tr>';
                }
                html += '</table>';
            }

            resultsDiv.innerHTML = html;
        });
    });

    // Group help popups for question groups
    document.querySelectorAll('.group-help').forEach(function(el) {
        el.addEventListener('click', function(e) {
            e.stopPropagation();
            const msg = el.getAttribute('data-help');
            if (msg) {
                alert(msg);
            }
        });
        el.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                el.click();
            }
        });
    });
});
