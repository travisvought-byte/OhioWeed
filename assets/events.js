(()=>{
  const area=document.getElementById('event-area');
  const kind=document.getElementById('event-kind');
  const list=document.getElementById('events');
  const count=document.getElementById('event-count');
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const formatDate=value=>new Date(value+'T12:00:00').toLocaleDateString('en-US',{weekday:'long',year:'numeric',month:'long',day:'numeric'});
  const localToday=new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,10);
  let events=[];

  function render(){
    const query=area.value.trim().toLocaleLowerCase();
    const selectedKind=kind.value;
    const filtered=events.filter(event=>{
      const location=[event.city,event.region,event.venue].join(' ').toLocaleLowerCase();
      return event.start>=localToday
        && (!query||location.includes(query))
        && (selectedKind==='all'||event.kind===selectedKind);
    });
    count.textContent=filtered.length===1?'1 upcoming event':`${filtered.length} upcoming events`;
    list.innerHTML=filtered.length?filtered.map(event=>{
      const date=formatDate(event.start);
      const place=[event.city,event.region].filter(Boolean).join(' · ');
      const venue=event.venue?`<p class="event-venue">${esc(event.venue)}</p>`:'';
      const extra=[event.time,event.age,event.cost].filter(Boolean).map(esc).join(' · ');
      const directions=event.map?`<a class="text-link" href="${esc(event.map)}" target="_blank" rel="noopener">Open map ↗</a>`:'';
      return `<article class="event-card"><div class="date-tile" aria-hidden="true"><small>${esc(new Date(event.start+'T12:00:00').toLocaleString('en-US',{month:'short'}))}</small><strong>${new Date(event.start+'T12:00:00').getDate()}</strong></div><div class="event-copy"><div class="event-labels"><span class="tag">${esc(event.label)}</span><span class="event-place">${esc(place)}</span></div><h2>${esc(event.name)}</h2><p>${esc(event.description)}</p>${venue}<p class="event-facts">${esc(date)}${extra?' · '+extra:''}</p><div class="listing-actions"><a class="text-link" href="${esc(event.url)}" target="_blank" rel="noopener">Organizer details / RSVP ↗</a>${directions}</div></div></article>`;
    }).join(''):'<div class="empty-state"><strong>No matches in this calendar yet.</strong><br>Try another city or event type, or suggest a public Ohio event.</div>';
  }

  fetch('data/ohio-events.json').then(response=>{if(!response.ok)throw new Error('Unable to load events');return response.json()})
    .then(rows=>{events=rows;render();area.addEventListener('input',render);kind.addEventListener('change',render)})
    .catch(()=>{count.textContent='';list.innerHTML='<div class="empty-state">The event calendar could not load. Please refresh this page or try again later.</div>'});
})();
