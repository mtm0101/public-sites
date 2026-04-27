
(function(){
function qs(s,r=document){return r.querySelector(s)}
function qsa(s,r=document){return Array.from(r.querySelectorAll(s))}
function applySourcePreference(pref){
  qsa('.source-page-block').forEach(block=>{
    const btn=qs('.source-toggle',block);
    if(pref==='collapsed'){
      block.classList.remove('expanded');block.classList.add('collapsed');
      if(btn)btn.textContent='Expand source page';
    }else{
      block.classList.remove('collapsed');block.classList.add('expanded');
      if(btn)btn.textContent='Collapse source page';
    }
  });
  if(pref!=='collapsed')requestAnimationFrame(()=>qsa('.source-page-frame').forEach(fitSourceFrame));
}
document.addEventListener('click',e=>{
  const t=e.target;
  if(t.matches('.source-toggle')){
    const b=t.closest('.source-page-block');
    const c=b.classList.toggle('collapsed');
    b.classList.toggle('expanded',!c);
    t.textContent=c?'Expand source page':'Collapse source page';
    if(!c)requestAnimationFrame(()=>{const frame=qs('.source-page-frame',b);if(frame)fitSourceFrame(frame);});
  }
  if(t.matches('[data-source-action="collapse-all"]')){
    localStorage.setItem('sourcePagesPreference','collapsed');
    applySourcePreference('collapsed');
  }
  if(t.matches('[data-source-action="expand-all"]')){
    localStorage.setItem('sourcePagesPreference','expanded');
    applySourcePreference('expanded');
  }
});
applySourcePreference(localStorage.getItem('sourcePagesPreference')==='collapsed'?'collapsed':'expanded');

function fitSourceFrame(frame){
  let doc;
  try{doc=frame.contentDocument||frame.contentWindow.document;}catch(e){return;}
  if(!doc)return;
  const page=doc.querySelector('.pf');
  const container=doc.getElementById('page-container')||doc.body;
  if(!page||!container)return;
  const pageWidth=page.offsetWidth||page.getBoundingClientRect().width;
  const pageHeight=page.offsetHeight||page.getBoundingClientRect().height;
  if(!pageWidth||!pageHeight)return;
  const frameWidth=Math.max(frame.clientWidth||pageWidth,300);
  const scale=Math.min(1,frameWidth/pageWidth);
  const padY=24;
  const fittedHeight=Math.ceil(pageHeight*scale+padY);
  Object.assign(doc.documentElement.style,{overflow:'hidden',minWidth:'0'});
  Object.assign(doc.body.style,{overflow:'hidden',minWidth:'0'});
  Object.assign(container.style,{position:'relative',width:'100%',minWidth:'0',height:fittedHeight+'px',overflow:'hidden'});
  Object.assign(page.style,{position:'absolute',top:'12px',left:Math.max((frameWidth-pageWidth*scale)/2,0)+'px',margin:'0',transform:'scale('+scale+')',transformOrigin:'top left'});
  frame.style.height=fittedHeight+'px';
}
qsa('.source-page-frame').forEach(frame=>{frame.setAttribute('scrolling','no');frame.addEventListener('load',()=>fitSourceFrame(frame));fitSourceFrame(frame);});
let sourceResizeFrame=0;
window.addEventListener('resize',()=>{cancelAnimationFrame(sourceResizeFrame);sourceResizeFrame=requestAnimationFrame(()=>qsa('.source-page-frame').forEach(fitSourceFrame));});

function scoreQuiz(g){
  if(!g)return;
  let a=0,c=0,ic=0;
  qsa('.question',g).forEach(q=>{
    const s=qs('.option.selected',q);
    if(s){a++; if(s.dataset.correct==='true')c++; else ic++;}
  });
  const pct=a?Math.round(c/a*100):0;
  const score=qs('.quiz-score',g);
  if(score)score.textContent=`Answered: ${a} · Correct: ${c} · Incorrect: ${ic} · Score: ${pct}%`;
}
function selectOption(opt,save=true){
  const q=opt.closest('.question');
  qsa('.option',q).forEach(o=>o.classList.remove('selected','correct','incorrect'));
  opt.classList.add('selected');
  const ok=opt.dataset.correct==='true';
  opt.classList.add(ok?'correct':'incorrect');
  if(!ok){const co=qs('.option[data-correct="true"]',q); if(co)co.classList.add('correct');}
  const fb=qs('.feedback',q);
  if(fb){
    fb.className='feedback show '+(ok?'correct':'incorrect');
    fb.textContent=(ok?'Correct. ':'Incorrect. ')+(q.dataset.explanation||'');
  }
  if(save && q.dataset.qid)localStorage.setItem('quiz:'+q.dataset.qid,opt.dataset.index);
  scoreQuiz(opt.closest('.quiz-group'));
}
qsa('.quiz-group').forEach(g=>{
  qsa('.question',g).forEach(q=>{
    const saved=localStorage.getItem('quiz:'+q.dataset.qid);
    if(saved!==null){const opt=qs(`.option[data-index="${saved}"]`,q); if(opt)selectOption(opt,false);}
  });
  scoreQuiz(g);
});
document.addEventListener('click',e=>{
  const opt=e.target.closest('.option');
  if(opt)selectOption(opt,true);
  const ret=e.target.closest('[data-quiz-action]');
  if(ret){
    const g=ret.closest('.quiz-group');
    qsa('.question',g).forEach(q=>{
      if(ret.dataset.quizAction==='retest')localStorage.removeItem('quiz:'+q.dataset.qid);
      else{
        const s=qs('.option.selected',q);
        if(s && s.dataset.correct!=='true')localStorage.removeItem('quiz:'+q.dataset.qid);
      }
    });
    location.reload();
  }
});

// print controls only run when controls exist
(function(){
  const panel=qs('.print-controls');
  if(!panel)return;
  const font=qs('#print-font-size');
  const size=qs('#print-page-size');
  const style=document.createElement('style');
  document.head.appendChild(style);
  function apply(){
    const fontVal=font ? font.value : '14px';
    const sizeVal=size ? size.value : 'A4';
    document.documentElement.style.setProperty('--print-font-size', fontVal);
    style.textContent=`@media print{@page{size:${sizeVal}; margin:12mm;}}`;
    localStorage.setItem('printFontSize',fontVal);
    localStorage.setItem('printPageSize',sizeVal);
  }
  if(font){font.value=localStorage.getItem('printFontSize')||font.value; font.addEventListener('change',apply);}
  if(size){size.value=localStorage.getItem('printPageSize')||size.value; size.addEventListener('change',apply);}
  const reset=qs('#print-reset');
  if(reset)reset.addEventListener('click',()=>{localStorage.removeItem('printFontSize'); localStorage.removeItem('printPageSize'); location.reload();});
  const print=qs('#print-now');
  if(print)print.addEventListener('click',()=>window.print());
  apply();
})();
})();
