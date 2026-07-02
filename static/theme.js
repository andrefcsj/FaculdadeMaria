function applyTheme(){
    const tema = localStorage.getItem('tema') || 'dark';
    document.body.classList.toggle('light', tema === 'light');

    const icon = document.querySelector('.theme-icon');
    if(icon){
        icon.textContent = tema === 'light' ? '🌙' : '☀️';
    }
}

function toggleTheme(){
    const novoTema = document.body.classList.contains('light')
        ? 'dark'
        : 'light';

    localStorage.setItem('tema', novoTema);
    applyTheme();
}

document.addEventListener('DOMContentLoaded', () => {
    applyTheme();

    const btn = document.querySelector('.theme-switch');
    if(btn){
        btn.addEventListener('click', toggleTheme);
    }
});
