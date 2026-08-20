(()=>{
  const dialogSelector='[role="dialog"], dialog, [class$="-dialog"], [class*="__dialog"], .backup-modal > section, .password-error-modal > section';
  const interactive='button,a,input,select,textarea,label,[contenteditable="true"]';
  const initialize=dialog=>{
    if(dialog.dataset.draggableReady==='true')return;
    const handle=dialog.querySelector(':scope > header, :scope > form > header, [class*="__header"]');
    if(!handle)return;
    dialog.dataset.draggableReady='true';
    dialog.classList.add('system-draggable-dialog');
    handle.classList.add('system-dialog-drag-handle');
    handle.title=handle.title||'Arraste para mover esta janela';
    let startX=0,startY=0,originX=0,originY=0,pointerId=null;
    handle.addEventListener('pointerdown',event=>{
      if(event.button!==0||event.target.closest(interactive))return;
      pointerId=event.pointerId;startX=event.clientX;startY=event.clientY;
      originX=Number(dialog.dataset.dragX||0);originY=Number(dialog.dataset.dragY||0);
      handle.setPointerCapture(pointerId);dialog.classList.add('system-dialog-dragging');
      event.preventDefault();
    });
    handle.addEventListener('pointermove',event=>{
      if(pointerId!==event.pointerId)return;
      const x=originX+event.clientX-startX,y=originY+event.clientY-startY;
      dialog.dataset.dragX=String(x);dialog.dataset.dragY=String(y);
      dialog.style.setProperty('--dialog-drag-x',`${x}px`);
      dialog.style.setProperty('--dialog-drag-y',`${y}px`);
    });
    const stop=event=>{if(pointerId!==event.pointerId)return;pointerId=null;dialog.classList.remove('system-dialog-dragging')};
    handle.addEventListener('pointerup',stop);handle.addEventListener('pointercancel',stop);
  };
  const scan=root=>{if(root.matches?.(dialogSelector))initialize(root);root.querySelectorAll?.(dialogSelector).forEach(initialize)};
  document.addEventListener('DOMContentLoaded',()=>scan(document));
  new MutationObserver(records=>records.forEach(record=>record.addedNodes.forEach(node=>{if(node.nodeType===1)scan(node)}))).observe(document.documentElement,{childList:true,subtree:true});
})();
