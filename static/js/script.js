// static/js/script.js
document.addEventListener('DOMContentLoaded', function() {
    // Tab switching
    const singleTab = document.getElementById('single-tab');
    const multipleTab = document.getElementById('multiple-tab');
    const singleInput = document.getElementById('single-input');
    const multipleInput = document.getElementById('multiple-input');

    singleTab.addEventListener('click', function() {
        singleTab.classList.add('active');
        multipleTab.classList.remove('active');
        singleInput.classList.add('active');
        multipleInput.classList.remove('active');
    });

    multipleTab.addEventListener('click', function() {
        multipleTab.classList.add('active');
        singleTab.classList.remove('active');
        multipleInput.classList.add('active');
        singleInput.classList.remove('active');
    });

    // Process buttons
    const processSingleBtn = document.getElementById('process-single');
    const processMultipleBtn = document.getElementById('process-multiple');
    const loader = document.getElementById('loader');
    const resultsCard = document.getElementById('results');
    const resultsContainer = document.getElementById('results-container');
    const resultCount = document.getElementById('result-count');
    const downloadAllBtn = document.getElementById('download-all');

    processSingleBtn.addEventListener('click', function() {
        const url = document.getElementById('single-url').value.trim();
        if (!url) {
            showToast('Please enter a YouTube URL');
            return;
        }

        processUrls([url]);
    });

    processMultipleBtn.addEventListener('click', function() {
        const urlsText = document.getElementById('multiple-urls').value.trim();
        if (!urlsText) {
            showToast('Please enter at least one YouTube URL');
            return;
        }

        const urls = urlsText.split('\n')
            .map(url => url.trim())
            .filter(url => url.length > 0);

        if (urls.length === 0) {
            showToast('Please enter at least one valid YouTube URL');
            return;
        }

        processUrls(urls);
    });

    function processUrls(urls) {
        // Show loader, hide results
        loader.classList.remove('hidden');
        resultsCard.classList.add('hidden');

        // Send request to backend
        fetch('/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ urls: urls }),
        })
        .then(response => response.json())
        .then(data => {
            // Hide loader
            loader.classList.add('hidden');

            if (data.success) {
                displayResults(data.results);
                resultsCard.classList.remove('hidden');

                // Show download all button if there are successful results
                const successfulResults = data.results.filter(r => r.success);
                if (successfulResults.length > 0) {
                    downloadAllBtn.classList.remove('hidden');
                } else {
                    downloadAllBtn.classList.add('hidden');
                }

                // Update count
                resultCount.textContent = data.results.length;

                // Scroll to results
                resultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                showToast(data.message || 'An error occurred');
            }
        })
        .catch(error => {
            loader.classList.add('hidden');
            showToast('An error occurred. Please try again.');
            console.error('Error:', error);
        });
    }

    function displayResults(results) {
        resultsContainer.innerHTML = '';

        results.forEach(result => {
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item';

            const statusClass = result.success ? 'status-success' : 'status-error';
            const statusText = result.success ? 'Success' : 'Failed';

            // Create header
            const header = document.createElement('div');
            header.className = 'result-header';
            header.innerHTML = `
                <div class="result-info">
                    <div class="result-url">${result.url}</div>
                    <div class="result-message">${result.message}</div>
                </div>
                <div class="result-status ${statusClass}">${statusText}</div>
            `;

            resultItem.appendChild(header);

            // Add download buttons if successful
            if (result.success) {
                const actions = document.createElement('div');
                actions.className = 'result-actions';
                actions.innerHTML = `
                    <button class="btn primary-btn download-txt-btn" data-video-id="${result.video_id}">
                        <i class="fas fa-download"></i> Download TXT
                    </button>
                    <button class="btn secondary-btn download-csv-btn" data-video-id="${result.video_id}">
                        <i class="fas fa-file-csv"></i> Download CSV
                    </button>
                `;
                resultItem.appendChild(actions);

                // Store transcript data in a hidden element to use when downloading
                const transcriptData = document.createElement('div');
                transcriptData.className = 'transcript-data hidden';
                transcriptData.dataset.transcript = JSON.stringify(result.transcript);
                resultItem.appendChild(transcriptData);

                // Add transcript preview
                if (result.transcript && result.transcript.length > 0) {
                    const preview = document.createElement('div');
                    preview.className = 'transcript-preview';

                    // Take first 8 lines for preview
                    const previewLines = result.transcript.slice(0, 8);

                    previewLines.forEach(line => {
                        const lineEl = document.createElement('div');
                        lineEl.className = 'transcript-line';
                        lineEl.innerHTML = `
                            <div class="timestamp">${line.timestamp}</div>
                            <div class="transcript-text">${line.text}</div>
                        `;
                        preview.appendChild(lineEl);
                    });

                    if (result.transcript.length > 8) {
                        const moreIndicator = document.createElement('div');
                        moreIndicator.className = 'more-indicator';
                        moreIndicator.textContent = `... and ${result.transcript.length - 8} more lines`;
                        preview.appendChild(moreIndicator);
                    }

                    resultItem.appendChild(preview);
                }
            }

            resultsContainer.appendChild(resultItem);
        });

        // Add event listeners for download buttons
        document.querySelectorAll('.download-txt-btn').forEach(button => {
            button.addEventListener('click', function() {
                const videoId = this.dataset.videoId;
                const transcriptData = JSON.parse(this.closest('.result-item').querySelector('.transcript-data').dataset.transcript);
                downloadTranscript(transcriptData, videoId, 'txt');
            });
        });

        document.querySelectorAll('.download-csv-btn').forEach(button => {
            button.addEventListener('click', function() {
                const videoId = this.dataset.videoId;
                const transcriptData = JSON.parse(this.closest('.result-item').querySelector('.transcript-data').dataset.transcript);
                downloadTranscript(transcriptData, videoId, 'csv');
            });
        });
    }

    // Function to handle downloading transcripts
    async function downloadTranscript(transcript, videoId, format) {
        try {
            const response = await fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    transcript: transcript,
                    video_id: videoId,
                    format: format
                })
            });

            if (!response.ok) {
                throw new Error('Download failed');
            }

            // Get the file name from the Content-Disposition header if available
            let filename = `${videoId}_transcript.${format}`;
            const contentDisposition = response.headers.get('Content-Disposition');
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1];
                }
            }

            // Create a blob from the response
            const blob = await response.blob();

            // Create a download link and trigger it
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();

            // Clean up
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            showToast(`Transcript downloaded as ${format.toUpperCase()}`);
        } catch (error) {
            showToast('Download failed. Please try again.');
            console.error('Download error:', error);
        }
    }

    // Toast notification
    function showToast(message) {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toast-message');

        toastMessage.textContent = message;
        toast.classList.add('show');

        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    // Download all button functionality
    downloadAllBtn.addEventListener('click', function() {
        showToast('Please use individual download buttons for each transcript');
    });

    // Enter key functionality for single URL input
    document.getElementById('single-url').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            processSingleBtn.click();
        }
    });

    // Add demo sidebar functionality
    const sidebarItems = document.querySelectorAll('.sidebar-nav li');
    sidebarItems.forEach(item => {
        item.addEventListener('click', function() {
            if (!this.classList.contains('active')) {
                showToast('Only YouTube Transcripts is currently available');
            }
        });
    });

    // Add responsive behavior for mobile
    function checkScreenSize() {
        const sidebar = document.querySelector('.sidebar');
        const mainContent = document.querySelector('.main-content');

        if (window.innerWidth <= 575) {
            // Mobile view - add menu toggle button if it doesn't exist
            if (!document.getElementById('menu-toggle')) {
                const menuToggle = document.createElement('button');
                menuToggle.id = 'menu-toggle';
                menuToggle.className = 'menu-toggle';
                menuToggle.innerHTML = '<i class="fas fa-bars"></i>';

                const header = document.querySelector('.main-header');
                header.insertBefore(menuToggle, header.firstChild);

                menuToggle.addEventListener('click', function() {
                    sidebar.classList.toggle('show-mobile');
                    document.body.classList.toggle('sidebar-open');
                });

                // Add overlay for closing sidebar
                const overlay = document.createElement('div');
                overlay.className = 'sidebar-overlay';
                document.body.appendChild(overlay);

                overlay.addEventListener('click', function() {
                    sidebar.classList.remove('show-mobile');
                    document.body.classList.remove('sidebar-open');
                });
            }
        } else {
            // Desktop view - remove menu toggle if it exists
            const menuToggle = document.getElementById('menu-toggle');
            if (menuToggle) {
                menuToggle.remove();
            }

            const overlay = document.querySelector('.sidebar-overlay');
            if (overlay) {
                overlay.remove();
            }

            sidebar.classList.remove('show-mobile');
            document.body.classList.remove('sidebar-open');
        }
    }

    // Initial check and add resize listener
    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);

    // Add these additional styles for mobile menu via JavaScript
    const style = document.createElement('style');
    style.textContent = `
        .menu-toggle {
            background: none;
            border: none;
            font-size: 1.2rem;
            color: var(--text-primary);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 1rem;
        }

        .sidebar-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 9;
            display: none;
        }

        .sidebar-open .sidebar-overlay {
            display: block;
        }

        @media (max-width: 575px) {
            .show-mobile {
                width: 240px !important;
                transform: translateX(0) !important;
            }

            .show-mobile .company-name,
            .show-mobile .sidebar-footer p {
                display: block;
            }

            .show-mobile .sidebar-nav li {
                justify-content: flex-start;
                padding: 0.8rem 1.5rem;
            }

            .show-mobile .sidebar-nav li i {
                margin-right: 0.8rem;
                font-size: 1rem;
            }

            .sidebar-open {
                overflow: hidden;
            }
        }

        .more-indicator {
            font-style: italic;
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 0.5rem;
            text-align: center;
        }

        /* Additional styles for download buttons */
        .result-actions {
            display: flex;
            gap: 10px;
        }

        .transcript-data {
            display: none;
        }
    `;
    document.head.appendChild(style);
});