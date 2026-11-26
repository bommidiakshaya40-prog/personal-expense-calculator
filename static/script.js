/**
 * Group Food & Expense Splitter - Client-side Interactive Logic
 */

// ==========================================
// Toast Notifications
// ==========================================
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : '⚠️';
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ==========================================
// Group Creation & Editing Modals
// ==========================================
function openNewGroupModal() {
    const modal = document.getElementById('new-group-modal');
    if (modal) {
        modal.style.display = 'flex';
        const input = document.getElementById('modal-group-name');
        if (input) input.focus();
    }
}

function closeNewGroupModal() {
    const modal = document.getElementById('new-group-modal');
    if (modal) modal.style.display = 'none';
}

async function submitCreateGroup() {
    const nameInput = document.getElementById('modal-group-name');
    const notesInput = document.getElementById('modal-group-notes');
    const membersInput = document.getElementById('modal-initial-members');

    const name = nameInput ? nameInput.value.trim() : '';
    const notes = notesInput ? notesInput.value.trim() : '';
    const membersRaw = membersInput ? membersInput.value.trim() : '';

    if (!name) {
        showToast('Please enter a group / restaurant name.', 'error');
        if (nameInput) nameInput.focus();
        return;
    }

    const members = membersRaw
        ? membersRaw.split(',').map(m => m.trim()).filter(m => m.length > 0)
        : [];

    const btn = document.getElementById('btn-create-group');
    if (btn) {
        btn.disabled = true;
        btn.innerText = 'Creating...';
    }

    try {
        const response = await fetch('/api/groups', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, notes, members })
        });
        const data = await response.json();

        if (data.success) {
            showToast('Group created! Redirecting...', 'success');
            window.location.href = `/group/${data.group_id}`;
        } else {
            showToast(data.error || 'Failed to create group.', 'error');
            if (btn) {
                btn.disabled = false;
                btn.innerText = 'Create & Start Splitting';
            }
        }
    } catch (err) {
        showToast('Network error while creating group.', 'error');
        if (btn) {
            btn.disabled = false;
            btn.innerText = 'Create & Start Splitting';
        }
    }
}

function openEditGroupModal(groupId, currentName, currentNotes) {
    const modal = document.getElementById('edit-group-modal');
    if (modal) {
        document.getElementById('edit-group-id').value = groupId;
        document.getElementById('edit-group-name').value = currentName;
        document.getElementById('edit-group-notes').value = currentNotes || '';
        modal.style.display = 'flex';
    }
}

function closeEditGroupModal() {
    const modal = document.getElementById('edit-group-modal');
    if (modal) modal.style.display = 'none';
}

async function submitUpdateGroup() {
    const groupId = document.getElementById('edit-group-id').value;
    const name = document.getElementById('edit-group-name').value.trim();
    const notes = document.getElementById('edit-group-notes').value.trim();

    if (!name) {
        showToast('Group name cannot be empty.', 'error');
        return;
    }

    try {
        const res = await fetch(`/api/groups/${groupId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, notes })
        });
        const data = await res.json();
        if (data.success) {
            showToast('Group details updated!', 'success');
            setTimeout(() => window.location.reload(), 500);
        } else {
            showToast(data.error || 'Failed to update group.', 'error');
        }
    } catch (e) {
        showToast('Network error.', 'error');
    }
}

async function confirmDeleteGroup(groupId, groupName) {
    if (!confirm(`Are you sure you want to delete "${groupName}"? All associated food items and calculations will be permanently deleted.`)) {
        return;
    }

    try {
        const res = await fetch(`/api/groups/${groupId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Group deleted successfully.', 'success');
            setTimeout(() => window.location.reload(), 500);
        } else {
            showToast(data.error || 'Failed to delete group.', 'error');
        }
    } catch (e) {
        showToast('Error deleting group.', 'error');
    }
}

async function confirmClearExpenses(groupId) {
    if (!confirm('Are you sure you want to clear all food items and allocations in this bill? Members will remain.')) {
        return;
    }

    try {
        const res = await fetch(`/api/groups/${groupId}/clear`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('All items cleared.', 'success');
            setTimeout(() => window.location.reload(), 500);
        } else {
            showToast(data.error || 'Failed to clear items.', 'error');
        }
    } catch (e) {
        showToast('Error clearing items.', 'error');
    }
}

// ==========================================
// Member Management
// ==========================================
async function submitAddMember(groupId) {
    const input = document.getElementById('new-member-name');
    const name = input ? input.value.trim() : '';

    if (!name) {
        showToast('Please enter a friend name.', 'warning');
        if (input) input.focus();
        return;
    }

    try {
        const res = await fetch(`/api/groups/${groupId}/members`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Added ${name}!`, 'success');
            setTimeout(() => window.location.reload(), 400);
        } else {
            showToast(data.error || 'Failed to add member.', 'error');
        }
    } catch (e) {
        showToast('Error adding member.', 'error');
    }
}

async function confirmDeleteMember(memberId, memberName) {
    if (!confirm(`Remove ${memberName} from this group? Any items assigned to them will have allocations updated.`)) {
        return;
    }

    try {
        const res = await fetch(`/api/members/${memberId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast(`Removed ${memberName}`, 'success');
            setTimeout(() => window.location.reload(), 400);
        } else {
            showToast(data.error || 'Failed to remove member.', 'error');
        }
    } catch (e) {
        showToast('Error deleting member.', 'error');
    }
}

// ==========================================
// Food Item Allocation & Pricing UI
// ==========================================
function updateLiveItemTotal() {
    const qtyInput = document.getElementById('item-quantity');
    const priceInput = document.getElementById('item-price');
    const totalBadge = document.getElementById('live-item-total');

    const qty = parseFloat(qtyInput ? qtyInput.value : 1) || 0;
    const price = parseFloat(priceInput ? priceInput.value : 0) || 0;
    const total = qty * price;

    if (totalBadge) {
        totalBadge.innerText = `₹${total.toFixed(2)}`;
    }
    updateAllocationPreview();
}

function updateEditItemTotal() {
    const qtyInput = document.getElementById('edit-item-quantity');
    const priceInput = document.getElementById('edit-item-price');
    const totalBadge = document.getElementById('edit-live-item-total');

    const qty = parseFloat(qtyInput ? qtyInput.value : 1) || 0;
    const price = parseFloat(priceInput ? priceInput.value : 0) || 0;
    const total = qty * price;

    if (totalBadge) {
        totalBadge.innerText = `₹${total.toFixed(2)}`;
    }
}

function toggleAllocationMode() {
    const selectedMode = document.querySelector('input[name="split-type"]:checked')?.value || 'single';
    const singleBox = document.getElementById('single-person-selector');
    const sharedBox = document.getElementById('shared-person-selector');
    const unitWraps = document.querySelectorAll('.custom-unit-input-wrap');

    if (selectedMode === 'single') {
        if (singleBox) singleBox.style.display = 'block';
        if (sharedBox) sharedBox.style.display = 'none';
    } else {
        if (singleBox) singleBox.style.display = 'none';
        if (sharedBox) sharedBox.style.display = 'block';

        const showUnits = (selectedMode === 'custom_shared');
        unitWraps.forEach(w => w.style.display = showUnits ? 'flex' : 'none');
    }
    updateAllocationPreview();
}

function selectAllSharedMembers(checked) {
    const checkboxes = document.querySelectorAll('.shared-member-chk');
    checkboxes.forEach(chk => chk.checked = checked);
    updateAllocationPreview();
}

function updateAllocationPreview() {
    const previewEl = document.getElementById('allocation-live-preview');
    if (!previewEl) return;

    const mode = document.querySelector('input[name="split-type"]:checked')?.value || 'single';
    const qty = parseFloat(document.getElementById('item-quantity')?.value || 1) || 0;
    const price = parseFloat(document.getElementById('item-price')?.value || 0) || 0;
    const total = qty * price;

    if (mode === 'single') {
        const select = document.getElementById('single-member-select');
        const name = select && select.options[select.selectedIndex] ? select.options[select.selectedIndex].text : 'Selected person';
        previewEl.innerHTML = `<strong>${name}</strong> pays 100% of this item: <strong>₹${total.toFixed(2)}</strong>`;
        return;
    }

    const checkedBoxes = Array.from(document.querySelectorAll('.shared-member-chk:checked'));
    if (checkedBoxes.length === 0) {
        previewEl.innerHTML = `<span class="text-danger">⚠️ Please select at least one person who shared this item.</span>`;
        return;
    }

    if (mode === 'equal_shared') {
        const perPerson = total / checkedBoxes.length;
        const names = checkedBoxes.map(c => c.getAttribute('data-name')).join(', ');
        previewEl.innerHTML = `Split equally among <strong>${checkedBoxes.length} people</strong> (${names}): <strong>₹${perPerson.toFixed(2)} each</strong>.`;
    } else if (mode === 'custom_shared') {
        let totalUnits = 0;
        const shares = [];
        checkedBoxes.forEach(chk => {
            const mid = chk.value;
            const unitInput = document.querySelector(`.custom-unit-val[data-member-id="${mid}"]`);
            const units = parseFloat(unitInput?.value || 1) || 1;
            totalUnits += units;
            shares.push({ name: chk.getAttribute('data-name'), units });
        });

        const breakdownText = shares.map(s => {
            const amt = totalUnits > 0 ? (s.units / totalUnits) * total : 0;
            return `${s.name} (${s.units}u): ₹${amt.toFixed(2)}`;
        }).join(' | ');

        previewEl.innerHTML = `<div>Custom split across <strong>${totalUnits} total units</strong>:</div><div style="margin-top:4px;">${breakdownText}</div>`;
    }
}

// ==========================================
// Submit Add Food Item
// ==========================================
async function submitAddFoodItem(groupId) {
    const nameInput = document.getElementById('item-name');
    const catSelect = document.getElementById('item-category');
    const qtyInput = document.getElementById('item-quantity');
    const priceInput = document.getElementById('item-price');
    const splitType = document.querySelector('input[name="split-type"]:checked')?.value || 'single';

    const name = nameInput ? nameInput.value.trim() : '';
    const category = catSelect ? catSelect.value : 'Veg';
    const quantity = parseFloat(qtyInput?.value || 1);
    const price_per_item = parseFloat(priceInput?.value || 0);

    if (!name) {
        showToast('Please enter an item name.', 'error');
        nameInput.focus();
        return;
    }
    if (isNaN(quantity) || quantity <= 0) {
        showToast('Quantity must be greater than zero.', 'error');
        qtyInput.focus();
        return;
    }
    if (isNaN(price_per_item) || price_per_item < 0) {
        showToast('Price cannot be negative.', 'error');
        priceInput.focus();
        return;
    }

    let member_shares = [];
    if (splitType === 'single') {
        const select = document.getElementById('single-member-select');
        const memberId = parseInt(select?.value);
        if (!memberId) {
            showToast('Please select a member.', 'error');
            return;
        }
        member_shares.push({ member_id: memberId, share_units: 1.0 });
    } else {
        const checkedBoxes = Array.from(document.querySelectorAll('.shared-member-chk:checked'));
        if (checkedBoxes.length === 0) {
            showToast('Please select at least one person who shared this item.', 'error');
            return;
        }

        checkedBoxes.forEach(chk => {
            const mid = parseInt(chk.value);
            let units = 1.0;
            if (splitType === 'custom_shared') {
                const uInput = document.querySelector(`.custom-unit-val[data-member-id="${mid}"]`);
                units = parseFloat(uInput?.value || 1) || 1.0;
            }
            member_shares.push({ member_id: mid, share_units: units });
        });
    }

    const btn = document.getElementById('btn-add-item');
    if (btn) btn.disabled = true;

    try {
        const res = await fetch(`/api/groups/${groupId}/items`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                category,
                quantity,
                price_per_item,
                split_type: splitType,
                member_shares
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Added ${name}!`, 'success');
            setTimeout(() => window.location.reload(), 400);
        } else {
            showToast(data.error || 'Failed to add item.', 'error');
            if (btn) btn.disabled = false;
        }
    } catch (e) {
        showToast('Error adding item.', 'error');
        if (btn) btn.disabled = false;
    }
}

// ==========================================
// Edit Food Item
// ==========================================
let currentGroupItems = [];

async function openEditItemModal(itemId) {
    const modal = document.getElementById('edit-item-modal');
    if (!modal) return;

    try {
        const res = await fetch(`/api/items/${itemId}`);
        const data = await res.json();
        if (!data.success || !data.item) {
            showToast(data.error || 'Failed to load item.', 'error');
            return;
        }

        const item = data.item;

        document.getElementById('edit-item-id').value = item.id;
        document.getElementById('edit-item-name').value = item.name;
        document.getElementById('edit-item-category').value = item.category;
        document.getElementById('edit-item-quantity').value = item.quantity;
        document.getElementById('edit-item-price').value = item.price_per_item;

        updateEditItemTotal();

        // Set radio split type
        const radio = document.querySelector(`input[name="edit-split-type"][value="${item.split_type}"]`);
        if (radio) radio.checked = true;

        toggleEditAllocationMode();

        if (item.split_type === 'single') {
            const singleMid = item.allocations[0]?.member_id;
            const singleSelect = document.getElementById('edit-single-member-select');
            if (singleSelect && singleMid) singleSelect.value = singleMid;
        } else {
            const allocatedMids = item.allocations.map(a => a.member_id);
            document.querySelectorAll('.edit-shared-member-chk').forEach(chk => {
                const mid = parseInt(chk.value);
                const isChecked = allocatedMids.includes(mid);
                chk.checked = isChecked;

                const allocObj = item.allocations.find(a => a.member_id === mid);
                const unitInput = document.querySelector(`.edit-custom-unit-val[data-member-id="${mid}"]`);
                if (unitInput) {
                    unitInput.value = allocObj ? allocObj.share_units : 1;
                }
            });
        }

        modal.style.display = 'flex';
    } catch (e) {
        showToast('Failed to load item details.', 'error');
    }
}

function selectAllEditSharedMembers(checked) {
    const checkboxes = document.querySelectorAll('.edit-shared-member-chk');
    checkboxes.forEach(chk => chk.checked = checked);
}

function closeEditItemModal() {
    const modal = document.getElementById('edit-item-modal');
    if (modal) modal.style.display = 'none';
}

function toggleEditAllocationMode() {
    const selectedMode = document.querySelector('input[name="edit-split-type"]:checked')?.value || 'single';
    const singleBox = document.getElementById('edit-single-person-selector');
    const sharedBox = document.getElementById('edit-shared-person-selector');
    const unitWraps = document.querySelectorAll('#edit-shared-members-checklist .custom-unit-input-wrap');

    if (selectedMode === 'single') {
        if (singleBox) singleBox.style.display = 'block';
        if (sharedBox) sharedBox.style.display = 'none';
    } else {
        if (singleBox) singleBox.style.display = 'none';
        if (sharedBox) sharedBox.style.display = 'block';

        const showUnits = (selectedMode === 'custom_shared');
        unitWraps.forEach(w => w.style.display = showUnits ? 'flex' : 'none');
    }
}

async function submitUpdateFoodItem() {
    const itemId = document.getElementById('edit-item-id').value;
    const name = document.getElementById('edit-item-name').value.trim();
    const category = document.getElementById('edit-item-category').value;
    const quantity = parseFloat(document.getElementById('edit-item-quantity').value);
    const price_per_item = parseFloat(document.getElementById('edit-item-price').value);
    const splitType = document.querySelector('input[name="edit-split-type"]:checked')?.value || 'single';

    if (!name) {
        showToast('Item name is required.', 'error');
        return;
    }
    if (isNaN(quantity) || quantity <= 0 || isNaN(price_per_item) || price_per_item < 0) {
        showToast('Please enter valid quantity and price.', 'error');
        return;
    }

    let member_shares = [];
    if (splitType === 'single') {
        const mid = parseInt(document.getElementById('edit-single-member-select').value);
        member_shares.push({ member_id: mid, share_units: 1.0 });
    } else {
        const checkedBoxes = Array.from(document.querySelectorAll('.edit-shared-member-chk:checked'));
        if (checkedBoxes.length === 0) {
            showToast('Please select at least one person.', 'error');
            return;
        }
        checkedBoxes.forEach(chk => {
            const mid = parseInt(chk.value);
            let units = 1.0;
            if (splitType === 'custom_shared') {
                const uInput = document.querySelector(`.edit-custom-unit-val[data-member-id="${mid}"]`);
                units = parseFloat(uInput?.value || 1) || 1.0;
            }
            member_shares.push({ member_id: mid, share_units: units });
        });
    }

    try {
        const res = await fetch(`/api/items/${itemId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                category,
                quantity,
                price_per_item,
                split_type: splitType,
                member_shares
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast('Item updated successfully!', 'success');
            setTimeout(() => window.location.reload(), 400);
        } else {
            showToast(data.error || 'Update failed.', 'error');
        }
    } catch (e) {
        showToast('Error updating item.', 'error');
    }
}

async function confirmDeleteItem(itemId, itemName) {
    if (!confirm(`Delete "${itemName}" from the bill?`)) return;

    try {
        const res = await fetch(`/api/items/${itemId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Item removed.', 'success');
            setTimeout(() => window.location.reload(), 400);
        } else {
            showToast(data.error || 'Failed to delete item.', 'error');
        }
    } catch (e) {
        showToast('Error deleting item.', 'error');
    }
}

// ==========================================
// Search / Filter on Dashboard
// ==========================================
function filterGroups() {
    const input = document.getElementById('group-search');
    const term = input ? input.value.toLowerCase().trim() : '';
    const rows = document.querySelectorAll('.group-row');

    rows.forEach(r => {
        const name = r.getAttribute('data-name') || '';
        if (name.includes(term)) {
            r.style.display = '';
        } else {
            r.style.display = 'none';
        }
    });
}

// Initialize live total calculation on page load
document.addEventListener('DOMContentLoaded', () => {
    updateLiveItemTotal();
});
