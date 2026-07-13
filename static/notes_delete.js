document.addEventListener('DOMContentLoaded',()=>document.addEventListener('click',async event=>{
  const button=event.target.closest('[data-note-delete]');
  if(!button)return;
  if(!confirm('Deseja realmente excluir esta nota importada? O sistema e o saldo serão recalculados.'))return;
  button.disabled=true;
  try{
    const response=await fetch(`/api/notas-importadas/${encodeURIComponent(button.dataset.noteDelete)}`,{method:'DELETE',headers:{Accept:'application/json'}}),data=await response.json();
    if(!response.ok||!data.ok)throw new Error(data.error||'Não foi possível excluir a nota.');
    location.reload();
  }catch(error){alert(error.message);button.disabled=false}
}));
