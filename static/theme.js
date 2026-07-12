
function applyTheme(){
 const t=localStorage.getItem('tema') || 'dark';
 document.body.classList.toggle('light', t==='light');
 const c=document.getElementById('themeToggle');
 if(c){ c.checked = t==='light'; }
}
document.addEventListener('DOMContentLoaded',()=>{
 applyTheme();
 const c=document.getElementById('themeToggle');
 if(c){
   c.addEventListener('change',()=>{
      const next = c.checked ? 'light' : 'dark';
      localStorage.setItem('tema', next);
      applyTheme();
   });
 }
 const now=new Date();
 const date=document.getElementById('topbarDate');
 const time=document.getElementById('topbarTime');
 if(date) date.textContent=now.toLocaleDateString('pt-BR',{day:'2-digit',month:'long',year:'numeric'});
 if(time) time.textContent=now.toLocaleDateString('pt-BR',{weekday:'long'})+', '+now.toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'});
 const layout=document.querySelector('.layout');
 const toggle=document.getElementById('sidebarToggle');
 if(layout && toggle){
   if(window.innerWidth<=760) layout.classList.add('sidebar-collapsed');
   toggle.addEventListener('click',()=>layout.classList.toggle('sidebar-collapsed'));
 }
});
