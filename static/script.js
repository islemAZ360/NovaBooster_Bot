document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generateBtn');
    const loadingState = document.getElementById('loadingState');
    const resultState = document.getElementById('resultState');
    const errorState = document.getElementById('errorState');
    const retryBtn = document.getElementById('retryBtn');
    const linkContainer = document.getElementById('linkContainer');
    const finalLink = document.getElementById('finalLink');
    const copyBtn = document.getElementById('copyBtn');
    const copyMessage = document.getElementById('copyMessage');
    const errorMessage = document.getElementById('errorMessage');
    const restartBtn = document.getElementById('restartBtn');
    
    // Live Viewer Elements
    const liveBtn = document.getElementById('liveBtn');
    const liveState = document.getElementById('liveState');
    const liveScreenshot = document.getElementById('liveScreenshot');
    const liveTerminal = document.getElementById('liveTerminal');
    const liveSpinner = document.getElementById('liveSpinner');
    const actionButtons = document.querySelector('.action-buttons');
    const timerDisplay = document.getElementById('timerDisplay');

    // Progress steps simulation
    const steps = [
        document.getElementById('step1'),
        document.getElementById('step2'),
        document.getElementById('step3')
    ];

    let stepInterval;
    let globalTimerInterval;
    let startTime;

    function simulateProgress() {
        let currentStep = 0;
        steps.forEach(s => s.classList.remove('active'));
        steps[0].classList.add('active');

        stepInterval = setInterval(() => {
            currentStep++;
            if(currentStep < steps.length) {
                steps.forEach(s => s.classList.remove('active'));
                steps[currentStep].classList.add('active');
            }
        }, 15000); // Change step every 15 seconds roughly
    }

    function stopProgress() {
        clearInterval(stepInterval);
        clearInterval(globalTimerInterval);
    }

    async function startAutomation() {
        // UI Updates
        actionButtons.classList.add('hidden');
        errorState.classList.add('hidden');
        resultState.classList.add('hidden');
        loadingState.classList.remove('hidden');
        
        timerDisplay.textContent = '0.0s';
        startTime = Date.now();
        globalTimerInterval = setInterval(() => {
            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            timerDisplay.textContent = elapsed + 's';
        }, 100);
        
        simulateProgress();

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();
            stopProgress();

            if (data.success) {
                // Show result
                loadingState.classList.add('hidden');
                resultState.classList.remove('hidden');
                finalLink.value = data.link;
            } else {
                // Show error
                loadingState.classList.add('hidden');
                errorState.classList.remove('hidden');
                errorMessage.textContent = data.error || 'Unknown error occurred';
                actionButtons.classList.remove('hidden');
            }

        } catch (error) {
            stopProgress();
            loadingState.classList.add('hidden');
            errorState.classList.remove('hidden');
            errorMessage.textContent = 'Server connection error: ' + error.message;
            actionButtons.classList.remove('hidden');
        }
    }

    function copyLinkToClipboard() {
        finalLink.select();
        finalLink.setSelectionRange(0, 99999); // For mobile devices

        navigator.clipboard.writeText(finalLink.value).then(() => {
            copyMessage.classList.remove('hidden');
            
            // Change icon temporarily
            const icon = copyBtn.querySelector('i');
            icon.className = 'fa-solid fa-check';
            
            setTimeout(() => {
                copyMessage.classList.add('hidden');
                icon.className = 'fa-regular fa-copy';
            }, 3000);
        }).catch(err => {
            console.error('Failed to copy: ', err);
        });
    }

    // Live Automation Stream
    function startLiveAutomation() {
        actionButtons.classList.add('hidden');
        errorState.classList.add('hidden');
        resultState.classList.add('hidden');
        liveState.classList.remove('hidden');
        
        liveTerminal.innerHTML = '<p>> Starting live automation...</p>';
        liveScreenshot.src = '';
        liveScreenshot.classList.add('hidden');
        liveSpinner.classList.remove('hidden');

        const eventSource = new EventSource('/api/generate_stream');

        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.type === 'log') {
                const p = document.createElement('p');
                p.textContent = '> ' + data.message;
                liveTerminal.appendChild(p);
                liveTerminal.scrollTop = liveTerminal.scrollHeight;
            } 
            else if (data.type === 'result') {
                eventSource.close();
                liveState.classList.add('hidden');
                
                if (data.data.success) {
                    resultState.classList.remove('hidden');
                    finalLink.value = data.data.link;
                } else {
                    errorState.classList.remove('hidden');
                    errorMessage.textContent = data.data.error || 'Unknown error occurred';
                    actionButtons.classList.remove('hidden');
                }
            }
            else if (data.type === 'error') {
                eventSource.close();
                liveState.classList.add('hidden');
                errorState.classList.remove('hidden');
                errorMessage.textContent = 'Automation error: ' + data.error;
                actionButtons.classList.remove('hidden');
            }

            if (data.image) {
                liveScreenshot.src = 'data:image/jpeg;base64,' + data.image;
                liveScreenshot.classList.remove('hidden');
                liveSpinner.classList.add('hidden');
            }
        };

        eventSource.onerror = function(err) {
            eventSource.close();
            liveState.classList.add('hidden');
            errorState.classList.remove('hidden');
            errorMessage.textContent = 'Server connection stream error.';
            actionButtons.classList.remove('hidden');
        };
    }

    function resetUI() {
        errorState.classList.add('hidden');
        resultState.classList.add('hidden');
        loadingState.classList.add('hidden');
        liveState.classList.add('hidden');
        actionButtons.classList.remove('hidden');
    }

    // Event Listeners
    generateBtn.addEventListener('click', startAutomation);
    if(liveBtn) liveBtn.addEventListener('click', startLiveAutomation);
    retryBtn.addEventListener('click', resetUI);
    if(restartBtn) restartBtn.addEventListener('click', resetUI);
    
    // Copy on clicking either the container or the button
    linkContainer.addEventListener('click', copyLinkToClipboard);
});
