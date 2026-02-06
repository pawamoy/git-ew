// Main JavaScript for git-ew

document.addEventListener('DOMContentLoaded', function() {
    // Setup sync button
    const syncBtn = document.getElementById('sync-btn');
    if (syncBtn) {
        syncBtn.addEventListener('click', syncEmails);
    }
});

async function syncEmails() {
    const btn = document.getElementById('sync-btn');
    const originalText = btn.textContent;

    btn.disabled = true;
    btn.textContent = 'Syncing...';

    try {
        const response = await fetch('/api/sync', {
            method: 'POST'
        });

        if (response.ok) {
            const data = await response.json();
            alert(`Successfully synced ${data.synced} emails`);
            location.reload();
        } else {
            const error = await response.json();
            alert('Sync failed: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        alert('Sync failed: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// Utility function to format dates
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}
