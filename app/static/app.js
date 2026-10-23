const pick = document.querySelector('#files');
const drop = document.querySelector('#drop');
const button = document.querySelector('#analyze');
const selected = document.querySelector('#selected');
const results = document.querySelector('#results');
const empty = document.querySelector('#empty');
let queue=[];
let perFile=new Map(), lastResults=[];
const inputKeys=['brand','abv','volume','class_type','producer','origin'];
function parseCSV(input){
 const rows=[];let row=[],field='',quoted=false;
 for(let i=0;i<input.length;i++){const c=input[i];if(quoted){if(c==='"'&&input[i+1]==='"'){field+='"';i++;}else if(c==='"')quoted=false;else field+=c;}else if(c==='"')quoted=true;else if(c===','){row.push(field);field='';}else if(c==='\n'){row.push(field.replace(/\r$/,''));rows.push(row);row=[];field='';}else field+=c;}
 if(quoted)throw Error('Unclosed CSV quote');
 if(field||row.length){row.push(field.replace(/\r$/,''));rows.push(row);}
 const headers=(rows.shift()||[]).map(x=>x.trim().toLowerCase());
 if(!headers.includes('filename'))throw Error('CSV must have filename column');
 const records=new Map();
 for(const values of rows){if(values.every(x=>!x.trim()))continue;const rec={};headers.forEach((h,i)=>rec[h]=(values[i]||'').trim());
 if(!rec.filename||records.has(rec.filename))throw Error('Missing or duplicate filename: '+rec.filename);
 records.set(rec.filename,rec);}
 return records;
}
const manifest=document.querySelector('#manifest'), manifestStatus=document.querySelector('#manifeststatus');
manifest.addEventListener('change',async()=>{perFile=new Map();if(!manifest.files.length){manifestStatus.textContent='';return;}try{perFile=parseCSV(await manifest.files[0].text());manifestStatus.textContent='Loaded '+perFile.size+' application rows.';}catch(e){manifestStatus.textContent='CSV error: '+e.message;manifest.value='';}});
document.querySelector('#csvexample').addEventListener('click',e=>{
 e.preventDefault();const example='filename,brand,abv,volume,class_type,producer,origin\n01_clean_bourbon.png,OLD TOM DISTILLERY,45%,750 mL,Kentucky Straight Bourbon Whiskey,,\n';
 const url=URL.createObjectURL(new Blob([example],{type:'text/csv'}));const a=document.createElement('a');a.href=url;a.download='application-template.csv';a.click();URL.revokeObjectURL(url);
});

const escapeHTML=s=>String(s??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function setFiles(list){queue=Array.from(list).slice(0,20);selected.innerHTML=queue.map(f=>`<div>▧ ${escapeHTML(f.name)} · ${(f.size/1024/1024).toFixed(2)} MB</div>`).join('');button.disabled=!queue.length;}
pick.addEventListener('change',e=>setFiles(e.target.files));
['dragenter','dragover'].forEach(x=>drop.addEventListener(x,e=>{e.preventDefault();drop.classList.add('drag')}));
['dragleave','drop'].forEach(x=>drop.addEventListener(x,e=>{e.preventDefault();drop.classList.remove('drag')}));
drop.addEventListener('drop',e=>setFiles(e.dataTransfer.files));
function renderCheck(label,data){return `<div class="check"><div class="check-head"><span>${label}</span><span class="status ${escapeHTML(data.status)}">${escapeHTML(data.status)}</span></div><small>Application: ${escapeHTML(data.expected)}</small><small>Detected: ${escapeHTML(data.found)}</small><small>${escapeHTML(data.note)}</small></div>`;}
function render(res){const checks=res.checks;return `<article class="result-card"><h3>${escapeHTML(res.filename)} <span class="status ${escapeHTML(res.overall)}">${escapeHTML(res.overall)}</span></h3><div class="meta">Processed in ${(res.duration_ms/1000).toFixed(2)} seconds · human review required</div>${renderCheck('Brand name',checks.brand || {status:'review',note:'No applicant brand supplied'})}${renderCheck('Alcohol content (ABV)',checks.abv)}${renderCheck('Net contents',checks.volume)}${renderCheck('Government health warning',checks.warning)}${['class_type','producer','origin'].filter(k=>checks[k]).map(k=>renderCheck(({class_type:'Class / Type',producer:'Producer / Bottler',origin:'Country of origin'})[k],checks[k])).join('')}<details><summary class="meta">View raw OCR evidence</summary><textarea class="ocr" readonly>${escapeHTML(res.ocr_text)}</textarea></details><div class="notice">${escapeHTML(res.notice)}</div></article>`}
button.addEventListener('click',async()=>{lastResults=[];button.disabled=true;button.textContent='Reviewing labels…';results.innerHTML='';empty.hidden=true;
 for(const file of queue){const card=document.createElement('div');results.appendChild(card);card.className='result-card';card.textContent='Analyzing '+file.name+'…';
 try{const form=new FormData();form.append('file',file);const appData=perFile.size?perFile.get(file.name):null;if(perFile.size&&!appData)throw Error('No CSV row for '+file.name);inputKeys.forEach(key=>form.append(key,appData?(appData[key]||''):document.getElementById(key).value));const response=await fetch('/api/analyze',{method:'POST',body:form});const kind=response.headers.get('content-type')||'';const raw=await response.text();let data;if(kind.includes('application/json')){try{data=JSON.parse(raw)}catch{throw Error('Invalid JSON returned by server')}}else{throw Error('Server returned HTTP '+response.status+' instead of JSON. The app may be restarting or overloaded; retry shortly.')}if(!response.ok)throw Error(data.detail||('Server error (HTTP '+response.status+')'));lastResults.push({filename:file.name,overall:data.overall,http:response.status,duration_ms:data.duration_ms,checks:data.checks});card.outerHTML=render(data)}catch(err){lastResults.push({filename:file.name,overall:'error',error:err.message});card.innerHTML=`<h3>${escapeHTML(file.name)}</h3><span class="status mismatch">Error</span><p>${escapeHTML(err.message)}</p>`}}
 button.disabled=false;button.innerHTML='Run label review <span>→</span>';});
const exportButton=document.createElement('button');exportButton.type='button';exportButton.className='primary';exportButton.textContent='Export results CSV';exportButton.hidden=true;exportButton.style.marginTop='12px';results.after(exportButton);
const observer=new MutationObserver(()=>{exportButton.hidden=lastResults.length===0;});observer.observe(results,{childList:true,subtree:true});
exportButton.addEventListener('click',()=>{
 const keys=['brand','abv','volume','warning','class_type','producer','origin'];
 const headings=['filename','http','overall','duration_ms',...keys,'error'];
 const quote=x=>'"'+String(x??'').replace(/"/g,'""')+'"';
 const rows=lastResults.map(r=>[r.filename,r.http,r.overall,r.duration_ms,...keys.map(k=>r.checks?.[k]?.status||''),r.error||'']);
 const csv=[headings,...rows].map(r=>r.map(quote).join(',')).join('\r\n');
 const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download='label-review-results.csv';a.click();URL.revokeObjectURL(url);
});
