/**
 * Knowledge Base Page - JavaScript Module
 * Handles KB document display, upload, and management
 */

let currentOffset = 0;
const BATCH_SIZE = 10;

/**
 * Load knowledge base documents
 */
async function loadKBDocs(offset = 0) {
    try {
        const response = await fetch(`/api/knowledge-base?offset=${offset}&limit=${BATCH_SIZE}`);
        const data = await response.json();

        if (offset === 0) {
            document.getElementById('kb-docs-container').innerHTML = '';
        }

        if (data.documents && data.documents.length > 0) {
            renderDocuments(data.documents);
            currentOffset = offset + data.documents.length;

            // Hide load more if no more docs
            document.getElementById('load-more-btn').style.display =
                data.documents.length < BATCH_SIZE ? 'none' : 'block';
        } else {
            if (offset === 0) {
                document.getElementById('kb-docs-container').innerHTML =
                    '<p style="text-align: center; color: var(--flux-text-secondary);">No knowledge chunks found. Upload a PDF to get started.</p>';
            }
            document.getElementById('load-more-btn').style.display = 'none';
        }

        // Update stats
        if (data.total_count !== undefined) {
            document.getElementById('total-chunks').textContent = data.total_count;
        }
    } catch (error) {
        console.error('Error loading KB docs:', error);
    }
}

/**
 * Render documents to the grid
 */
function renderDocuments(docs) {
    const container = document.getElementById('kb-docs-container');

    docs.forEach(doc => {
        const card = document.createElement('div');
        card.className = 'kb-doc-card';

        card.innerHTML = `
            <div class="kb-doc-id">ID: ${doc.id || 'N/A'}</div>
            <div class="kb-doc-text">${escapeHtml(doc.text || doc.page_content || '')}</div>
            <div class="kb-doc-meta">
                <span>Source: ${doc.metadata?.source || 'Unknown'}</span>
                ${doc.metadata?.page ? `<span>Page: ${doc.metadata.page}</span>` : ''}
            </div>
        `;

        container.appendChild(card);
    });
}

/**
 * Load more documents
 */
function loadMoreDocs() {
    loadKBDocs(currentOffset);
}

/**
 * Update file name display
 */
function updateFileName() {
    const fileInput = document.getElementById('pdf-upload');
    const fileName = document.getElementById('file-name');
    const uploadBtn = document.getElementById('upload-btn');

    if (fileInput.files.length > 0) {
        fileName.textContent = fileInput.files[0].name;
        uploadBtn.disabled = false;
    } else {
        fileName.textContent = 'No file selected';
        uploadBtn.disabled = true;
    }
}

/**
 * Upload and ingest PDF
 */
async function uploadFile() {
    const fileInput = document.getElementById('pdf-upload');
    const statusDiv = document.getElementById('upload-status');
    const uploadBtn = document.getElementById('upload-btn');

    if (!fileInput.files.length) {
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    statusDiv.innerHTML = '<span style="color: var(--flux-info);">Uploading and ingesting...</span>';
    uploadBtn.disabled = true;

    try {
        const response = await fetch('/api/ingest-pdf', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            statusDiv.innerHTML = `<span style="color: var(--flux-success);">✓ Successfully ingested ${data.chunks_added || 0} chunks</span>`;
            fileInput.value = '';
            document.getElementById('file-name').textContent = 'No file selected';

            // Reload documents
            setTimeout(() => {
                loadKBDocs(0);
            }, 1000);
        } else {
            statusDiv.innerHTML = `<span style="color: var(--flux-error);">✗ Error: ${data.error || 'Upload failed'}</span>`;
            uploadBtn.disabled = false;
        }
    } catch (error) {
        statusDiv.innerHTML = `<span style="color: var(--flux-error);">✗ Error: ${error.message}</span>`;
        uploadBtn.disabled = false;
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Load stats
 */
async function loadStats() {
    try {
        const response = await fetch('/api/knowledge-base/stats');
        const data = await response.json();

        document.getElementById('total-chunks').textContent = data.total_chunks || 0;
        document.getElementById('total-docs').textContent = data.total_documents || 0;
        document.getElementById('last-updated').textContent = data.last_updated || '--';
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    loadKBDocs(0);
    loadStats();
});
