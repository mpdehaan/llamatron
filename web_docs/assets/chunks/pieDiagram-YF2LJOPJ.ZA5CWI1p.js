import{p as N}from"./chunk-TMUBEWPD.lqNfIsoP.js";import{g as B,s as U,a as V,b as Z,o as j,p as q,_ as i,l as C,c as H,E as J,I as K,L as Q,M as z,e as X,x as Y,N as ee,F as te}from"../app.Djy7s7r5.js";import{p as ae}from"./gitGraph-YCYPL57B.CucJSzFI.js";import{o as re}from"./d3-scale.35hnzshu.js";import"./framework.hw3Av5Vn.js";import"./theme.DWSpw-5F.js";import"./min.BVPOk518.js";import"./baseUniq.BHMmgQpD.js";var ie=te.pie,D={sections:new Map,showData:!1},m=D.sections,w=D.showData,se=structuredClone(ie),oe=i(()=>structuredClone(se),"getConfig"),ne=i(()=>{m=new Map,w=D.showData,Y()},"clear"),le=i(({label:e,value:a})=>{m.has(e)||(m.set(e,a),C.debug(`added new section: ${e}, with value: ${a}`))},"addSection"),ce=i(()=>m,"getSections"),pe=i(e=>{w=e},"setShowData"),de=i(()=>w,"getShowData"),F={getConfig:oe,clear:ne,setDiagramTitle:q,getDiagramTitle:j,setAccTitle:Z,getAccTitle:V,setAccDescription:U,getAccDescription:B,addSection:le,getSections:ce,setShowData:pe,getShowData:de},ge=i((e,a)=>{N(e,a),a.setShowData(e.showData),e.sections.map(a.addSection)},"populateDb"),ue={parse:i(async e=>{const a=await ae("pie",e);C.debug(a),ge(a,F)},"parse")},fe=i(e=>`
  .pieCircle{
    stroke: ${e.pieStrokeColor};
    stroke-width : ${e.pieStrokeWidth};
    opacity : ${e.pieOpacity};
  }
  .pieOuterCircle{
    stroke: ${e.pieOuterStrokeColor};
    stroke-width: ${e.pieOuterStrokeWidth};
    fill: none;
  }
  .pieTitleText {
    text-anchor: middle;
    font-size: ${e.pieTitleTextSize};
    fill: ${e.pieTitleTextColor};
    font-family: ${e.fontFamily};
  }
  .slice {
    font-family: ${e.fontFamily};
    fill: ${e.pieSectionTextColor};
    font-size:${e.pieSectionTextSize};
    // fill: white;
  }
  .legend text {
    fill: ${e.pieLegendTextColor};
    font-family: ${e.fontFamily};
    font-size: ${e.pieLegendTextSize};
  }
`,"getStyles"),me=fe,he=i(e=>{const a=[...e.entries()].map(s=>({label:s[0],value:s[1]})).sort((s,n)=>n.value-s.value);return ee().value(s=>s.value)(a)},"createPieArcs"),Se=i((e,a,G,s)=>{C.debug(`rendering pie chart
`+e);const n=s.db,$=H(),y=J(n.getConfig(),$.pie),T=40,o=18,d=4,c=450,h=c,S=K(a),l=S.append("g");l.attr("transform","translate("+h/2+","+c/2+")");const{themeVariables:r}=$;let[A]=Q(r.pieOuterStrokeWidth);A??(A=2);const _=y.textPosition,g=Math.min(h,c)/2-T,M=z().innerRadius(0).outerRadius(g),W=z().innerRadius(g*_).outerRadius(g*_);l.append("circle").attr("cx",0).attr("cy",0).attr("r",g+A/2).attr("class","pieOuterCircle");const E=n.getSections(),v=he(E),I=[r.pie1,r.pie2,r.pie3,r.pie4,r.pie5,r.pie6,r.pie7,r.pie8,r.pie9,r.pie10,r.pie11,r.pie12],p=re(I);l.selectAll("mySlices").data(v).enter().append("path").attr("d",M).attr("fill",t=>p(t.data.label)).attr("class","pieCircle");let b=0;E.forEach(t=>{b+=t}),l.selectAll("mySlices").data(v).enter().append("text").text(t=>(t.data.value/b*100).toFixed(0)+"%").attr("transform",t=>"translate("+W.centroid(t)+")").style("text-anchor","middle").attr("class","slice"),l.append("text").text(n.getDiagramTitle()).attr("x",0).attr("y",-400/2).attr("class","pieTitleText");const x=l.selectAll(".legend").data(p.domain()).enter().append("g").attr("class","legend").attr("transform",(t,u)=>{const f=o+d,O=f*p.domain().length/2,P=12*o,R=u*f-O;return"translate("+P+","+R+")"});x.append("rect").attr("width",o).attr("height",o).style("fill",p).style("stroke",p),x.data(v).append("text").attr("x",o+d).attr("y",o-d).text(t=>{const{label:u,value:f}=t.data;return n.getShowData()?`${u} [${f}]`:u});const L=Math.max(...x.selectAll("text").nodes().map(t=>(t==null?void 0:t.getBoundingClientRect().width)??0)),k=h+T+o+d+L;S.attr("viewBox",`0 0 ${k} ${c}`),X(S,c,k,y.useMaxWidth)},"draw"),ve={draw:Se},_e={parser:ue,db:F,renderer:ve,styles:me};export{_e as diagram};
