function applyTheme(){
    const tema = localStorage.getItem('tema') || 'dark';
    document.body.classList.toggle('light', tema === 'light');
}

function toggleTheme(){
    const novoTema = document.body.classList.contains('light')
        ? 'dark'
        : 'light';

    localStorage.setItem('tema', novoTema);
    applyTheme();
}

document.addEventListener('DOMContentLoaded', applyTheme);
