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

    // Progress steps simulation
    const steps = [
        document.getElementById('step1'),
        document.getElementById('step2'),
        document.getElementById('step3')
    ];

    let stepInterval;

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
    }

    async function startAutomation() {
        // UI Updates
        generateBtn.classList.add('hidden');
        errorState.classList.add('hidden');
        resultState.classList.add('hidden');
        loadingState.classList.remove('hidden');
        
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
                errorMessage.textContent = data.error || 'حدث خطأ غير معروف';
                generateBtn.classList.remove('hidden');
            }

        } catch (error) {
            stopProgress();
            loadingState.classList.add('hidden');
            errorState.classList.remove('hidden');
            errorMessage.textContent = 'خطأ في الاتصال بالخادم: ' + error.message;
            generateBtn.classList.remove('hidden');
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

    // Event Listeners
    generateBtn.addEventListener('click', startAutomation);
    retryBtn.addEventListener('click', startAutomation);
    
    // Copy on clicking either the container or the button
    linkContainer.addEventListener('click', copyLinkToClipboard);
});
