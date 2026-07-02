
document.addEventListener('DOMContentLoaded',()=>{
 const busca=document.getElementById('buscaAtivo');
 if(!busca) return;
 busca.addEventListener('input',()=>{
   const termo=busca.value.toLowerCase();
   document.querySelectorAll('#tabelaOperacoes tbody tr').forEach(linha=>{
      linha.style.display = linha.innerText.toLowerCase().includes(termo) ? '' : 'none';
   });
 });
});
