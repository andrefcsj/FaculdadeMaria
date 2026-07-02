
function applyTheme(){
 const t=localStorage.getItem('tema')||'dark';
 document.body.classList.toggle('light',t==='light');
 const c=document.getElementById('themeToggle');
 if(c) c.checked=t==='light';
}
document.addEventListener('DOMContentLoaded',()=>{
 applyTheme();
 const c=document.getElementById('themeToggle');
 if(c){
  c.addEventListener('change',()=>{
    localStorage.setItem('tema',c.checked?'light':'dark');
    applyTheme();
  });
 }
});
