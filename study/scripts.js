// ===== Progress Tracking =====
function updateProgress() {
    const completedPages = localStorage.getItem('completedPages');
    const totalPages = 500;
    const completed = completedPages ? JSON.parse(completedPages).length : 0;
    const percentage = (completed / totalPages) * 100;
    
    const progressBar = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-text');
    
    if (progressBar && progressText) {
        progressBar.style.width = percentage + '%';
        progressText.textContent = `${completed} of ${totalPages} pages completed (${percentage.toFixed(1)}%)`;
    }
}

// ===== Mark Page as Complete =====
function markAsComplete(pageCode) {
    let completedPages = localStorage.getItem('completedPages');
    completedPages = completedPages ? JSON.parse(completedPages) : [];
    
    if (!completedPages.includes(pageCode)) {
        completedPages.push(pageCode);
        localStorage.setItem('completedPages', JSON.stringify(completedPages));
        
        // Visual feedback
        const btn = event.target;
        btn.textContent = '✓ Completed!';
        btn.style.background = '#059669';
        
        updateProgress();
    }
}

// ===== Toggle Section =====
function toggleSection(sectionNum) {
    const section = document.querySelector(`[data-section="${sectionNum}"]`);
    const content = document.getElementById(`section-${sectionNum}`);
    const header = section.querySelector('.section-header');
    
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        header.classList.remove('collapsed');
    } else {
        content.classList.add('collapsed');
        header.classList.add('collapsed');
    }
}

// ===== Toggle All Sections =====
function toggleAllSections() {
    const sections = document.querySelectorAll('.study-section');
    const allCollapsed = Array.from(sections).every(section => 
        section.querySelector('.section-content').classList.contains('collapsed')
    );
    
    sections.forEach(section => {
        const content = section.querySelector('.section-content');
        const header = section.querySelector('.section-header');
        
        if (allCollapsed) {
            content.classList.remove('collapsed');
            header.classList.remove('collapsed');
        } else {
            content.classList.add('collapsed');
            header.classList.add('collapsed');
        }
    });
}

// ===== Show MCQ Answer =====
function showAnswer(questionId) {
    const answerDiv = document.getElementById(`answer-${questionId}`);
    const btn = event.target;
    
    if (answerDiv.classList.contains('show')) {
        answerDiv.classList.remove('show');
        btn.textContent = 'Show Answer';
    } else {
        answerDiv.classList.add('show');
        btn.textContent = 'Hide Answer';
    }
}

// ===== Check Completed Pages on Load =====
document.addEventListener('DOMContentLoaded', function() {
    updateProgress();
    
    // Auto-expand first section on study pages
    const firstSection = document.querySelector('[data-section="1"]');
    if (firstSection) {
        setTimeout(() => {
            toggleSection(1);
        }, 300);
    }
});

// ===== Keyboard Shortcuts =====
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + P for print
    if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
        e.preventDefault();
        window.print();
    }
    
    // Space to toggle first section
    if (e.key === ' ' && e.target === document.body) {
        e.preventDefault();
        const firstSection = document.querySelector('[data-section="1"]');
        if (firstSection) toggleSection(1);
    }
});

// ===== Local Storage Helper =====
const StudyProgress = {
    add: (pageCode) => {
        let completed = JSON.parse(localStorage.getItem('completedPages') || '[]');
        if (!completed.includes(pageCode)) {
            completed.push(pageCode);
            localStorage.setItem('completedPages', JSON.stringify(completed));
        }
    },
    
    remove: (pageCode) => {
        let completed = JSON.parse(localStorage.getItem('completedPages') || '[]');
        completed = completed.filter(p => p !== pageCode);
        localStorage.setItem('completedPages', JSON.stringify(completed));
    },
    
    isCompleted: (pageCode) => {
        const completed = JSON.parse(localStorage.getItem('completedPages') || '[]');
        return completed.includes(pageCode);
    },
    
    getProgress: () => {
        const completed = JSON.parse(localStorage.getItem('completedPages') || '[]');
        return {
            completed: completed.length,
            total: 500,
            percentage: ((completed.length / 500) * 100).toFixed(1)
        };
    }
};