document.addEventListener('DOMContentLoaded',()=>{
 const busca=document.getElementById('buscaAtivo');
 if(!busca) return;

 busca.addEventListener('input',()=>{
   const termo=busca.value.toLowerCase();

   document.querySelectorAll('#tabelaOperacoes tbody tr').forEach(linha=>{
      linha.style.display =
         linha.innerText.toLowerCase().includes(termo)
         ? ''
         : 'none';
   });
 });
});

// Confirma exclusão de operação
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.btn-action.delete');
  if (!btn) return;

  const ok = confirm('Tem certeza que deseja excluir esta operação?');

  if (!ok) {
    e.preventDefault();
    e.stopPropagation();
  }
});
