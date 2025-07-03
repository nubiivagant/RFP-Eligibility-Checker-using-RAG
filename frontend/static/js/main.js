document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        // Show results
        document.getElementById('results').style.display = 'block';
        document.getElementById('eligibility').textContent = data.eligible ? 'Eligible' : 'Not Eligible';
        
        // Setup buttons
        document.getElementById('downloadBtn').href = data.report_url;
        document.getElementById('shareBtn').href = data.share_url;
        
    } catch (error) {
        alert('Analysis failed: ' + error);
    }
});
