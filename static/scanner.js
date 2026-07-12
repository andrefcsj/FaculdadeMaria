document.addEventListener('DOMContentLoaded',()=>{
  const rows=[...document.querySelectorAll('#scannerRows tr')];
  if(!rows.length)return;
  const search=document.getElementById('scannerSearch'),status=document.getElementById('scannerStatus'),roi=document.getElementById('scannerRoi'),dte=document.getElementById('scannerDte'),visible=document.getElementById('scannerVisible');
  const apply=()=>{let count=0;rows.forEach(row=>{const show=(!search.value||row.dataset.search.toLowerCase().includes(search.value.toLowerCase()))&&(!status.value||row.dataset.status===status.value)&&Number(row.dataset.roi)>=Number(roi.value||0)&&Number(row.dataset.dte)<=Number(dte.value||9999);row.hidden=!show;if(show)count++;});visible.textContent=count;};
  [search,status,roi,dte].forEach(input=>input.addEventListener('input',apply));
  document.getElementById('scannerClear').addEventListener('click',()=>{search.value='';status.value='';roi.value='0';dte.value='90';apply();});apply();
});
