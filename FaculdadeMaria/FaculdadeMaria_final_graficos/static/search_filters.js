
document.addEventListener('DOMContentLoaded', () => {
  const search = document.getElementById('buscaAtivo');
  if (search) {
    search.addEventListener('input', () => {
      const termo = search.value.toLowerCase();
      document.querySelectorAll('tbody tr').forEach(linha => {
        linha.style.display = linha.innerText.toLowerCase().includes(termo) ? '' : 'none';
      });
    });
  }

  document.querySelectorAll('th').forEach((th, i) => {
    th.style.cursor = 'pointer';
    th.addEventListener('click', () => {
      const table = th.closest('table');
      const rows = [...table.querySelectorAll('tbody tr')];
      rows.sort((a, b) =>
        a.children[i].innerText.localeCompare(b.children[i].innerText, 'pt-BR', {numeric:true})
      );
      const body = table.querySelector('tbody');
      rows.forEach(r => body.appendChild(r));
    });
  });
});
