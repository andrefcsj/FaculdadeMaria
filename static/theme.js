
function applyTheme(){
 const t=localStorage.getItem('tema') || 'dark';
 document.body.classList.toggle('light', t==='light');
 const c=document.getElementById('themeToggle');
 if(c){ c.checked = t==='light'; }
}
document.addEventListener('DOMContentLoaded',()=>{
 applyTheme();
 const legacyWalletLink=document.querySelector('.executive-nav a[href="/carteira"]');
 if(legacyWalletLink){legacyWalletLink.href='/carteira-acoes';const textNode=[...legacyWalletLink.childNodes].find(node=>node.nodeType===Node.TEXT_NODE);if(textNode)textNode.textContent='Carteira';legacyWalletLink.classList.toggle('active',location.pathname==='/carteira-acoes');}
 document.querySelector('.equity-nav-shortcut')?.remove();
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
 const bell=document.getElementById('notificationBell');
 const popover=document.getElementById('notificationPopover');
 const list=document.getElementById('notificationList');
 const count=document.getElementById('notificationCount');
 const close=document.getElementById('notificationClose');
 let alertsLoaded=false;
 const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
 async function loadAlerts(){
   try{
     const response=await fetch('/api/alertas-operacionais',{headers:{Accept:'application/json'}});
     if(!response.ok) throw new Error('Falha ao carregar alertas');
     const data=await response.json();
     count.textContent=data.count;
     count.hidden=!data.count;
     list.innerHTML=data.items.length?data.items.map(item=>`<a class="notification-item notification-item--${escapeHtml(item.severity)}" href="/operacoes-abertas"><i></i><span><strong>${escapeHtml(item.option_code)}</strong><small>${escapeHtml(item.message)}</small></span><b>${escapeHtml(item.label)}</b></a>`).join(''):'<div class="notification-empty"><strong>Tudo sob controle</strong><small>Nenhuma PUT exige atenção agora.</small></div>';
     alertsLoaded=true;
   }catch(error){list.innerHTML='<div class="notification-empty notification-empty--error"><strong>Não foi possível carregar</strong><small>Atualize os dados e tente novamente.</small></div>';}
 }
 if(bell && popover){
   bell.addEventListener('click',async()=>{const opening=popover.hidden;popover.hidden=!opening;bell.setAttribute('aria-expanded',String(opening));if(opening&&!alertsLoaded)await loadAlerts();});
   close?.addEventListener('click',()=>{popover.hidden=true;bell.setAttribute('aria-expanded','false');});
   document.addEventListener('click',event=>{if(!popover.hidden&&!event.target.closest('.notification-center')){popover.hidden=true;bell.setAttribute('aria-expanded','false');}});
   loadAlerts();
 }
});
