import{g as Te,s as xe,o as be,p as we,a as _e,b as De,_ as l,c as st,d as yt,e as Se,aq as q,l as xt,k as Ce,j as Ee,x as Me,u as Ae}from"../app.DwH7I4q2.js";import{t as Ie,m as Ye,a as Fe,l as Le,h as We,c as jt,d as Zt,e as Ve,f as Oe,g as Pe,i as ze,j as Re,k as Ne,n as Be,p as Qt,q as Kt,r as Jt,s as $t,u as te}from"./d3-scale.35hnzshu.js";import"./framework.hw3Av5Vn.js";import"./theme.CmGLpcWF.js";function He(t){return t}var vt=1,Et=2,It=3,gt=4,ee=1e-6;function Ge(t){return"translate("+t+",0)"}function qe(t){return"translate(0,"+t+")"}function Ue(t){return e=>+t(e)}function Xe(t,e){return e=Math.max(0,t.bandwidth()-e*2)/2,t.round()&&(e=Math.round(e)),r=>+t(r)+e}function je(){return!this.__axis}function ce(t,e){var r=[],a=null,i=null,o=6,c=6,T=3,y=typeof window<"u"&&window.devicePixelRatio>1?0:.5,x=t===vt||t===gt?-1:1,p=t===gt||t===Et?"x":"y",M=t===vt||t===It?Ge:qe;function w(g){var F=a??(e.ticks?e.ticks.apply(e,r):e.domain()),_=i??(e.tickFormat?e.tickFormat.apply(e,r):He),P=Math.max(o,0)+T,z=e.range(),U=+z[0]+y,H=+z[z.length-1]+y,X=(e.bandwidth?Xe:Ue)(e.copy(),y),G=g.selection?g.selection():g,R=G.selectAll(".domain").data([null]),V=G.selectAll(".tick").data(F,e).order(),v=V.exit(),S=V.enter().append("g").attr("class","tick"),b=V.select("line"),D=V.select("text");R=R.merge(R.enter().insert("path",".tick").attr("class","domain").attr("stroke","currentColor")),V=V.merge(S),b=b.merge(S.append("line").attr("stroke","currentColor").attr(p+"2",x*o)),D=D.merge(S.append("text").attr("fill","currentColor").attr(p,x*P).attr("dy",t===vt?"0em":t===It?"0.71em":"0.32em")),g!==G&&(R=R.transition(g),V=V.transition(g),b=b.transition(g),D=D.transition(g),v=v.transition(g).attr("opacity",ee).attr("transform",function(k){return isFinite(k=X(k))?M(k+y):this.getAttribute("transform")}),S.attr("opacity",ee).attr("transform",function(k){var E=this.parentNode.__axis;return M((E&&isFinite(E=E(k))?E:X(k))+y)})),v.remove(),R.attr("d",t===gt||t===Et?c?"M"+x*c+","+U+"H"+y+"V"+H+"H"+x*c:"M"+y+","+U+"V"+H:c?"M"+U+","+x*c+"V"+y+"H"+H+"V"+x*c:"M"+U+","+y+"H"+H),V.attr("opacity",1).attr("transform",function(k){return M(X(k)+y)}),b.attr(p+"2",x*o),D.attr(p,x*P).text(_),G.filter(je).attr("fill","none").attr("font-size",10).attr("font-family","sans-serif").attr("text-anchor",t===Et?"start":t===gt?"end":"middle"),G.each(function(){this.__axis=X})}return w.scale=function(g){return arguments.length?(e=g,w):e},w.ticks=function(){return r=Array.from(arguments),w},w.tickArguments=function(g){return arguments.length?(r=g==null?[]:Array.from(g),w):r.slice()},w.tickValues=function(g){return arguments.length?(a=g==null?null:Array.from(g),w):a&&a.slice()},w.tickFormat=function(g){return arguments.length?(i=g,w):i},w.tickSize=function(g){return arguments.length?(o=c=+g,w):o},w.tickSizeInner=function(g){return arguments.length?(o=+g,w):o},w.tickSizeOuter=function(g){return arguments.length?(c=+g,w):c},w.tickPadding=function(g){return arguments.length?(T=+g,w):T},w.offset=function(g){return arguments.length?(y=+g,w):y},w}function Ze(t){return ce(vt,t)}function Qe(t){return ce(It,t)}var Mt="day",Ke="week",Je="year",$e="YYYY-MM-DDTHH:mm:ssZ",tr="isoweek";const er=function(t,e,r){var a=function(y,x){var p=(x?r.utc:r)().year(y).startOf(Je),M=4-p.isoWeekday();return p.isoWeekday()>4&&(M+=7),p.add(M,Mt)},i=function(y){return y.add(4-y.isoWeekday(),Mt)},o=e.prototype;o.isoWeekYear=function(){var T=i(this);return T.year()},o.isoWeek=function(T){if(!this.$utils().u(T))return this.add((T-this.isoWeek())*7,Mt);var y=i(this),x=a(this.isoWeekYear(),this.$u);return y.diff(x,Ke)+1},o.isoWeekday=function(T){return this.$utils().u(T)?this.day()||7:this.day(this.day()%7?T:T-7)};var c=o.startOf;o.startOf=function(T,y){var x=this.$utils(),p=x.u(y)?!0:y,M=x.p(T);return M===tr?p?this.date(this.date()-(this.isoWeekday()-1)).startOf("day"):this.date(this.date()-1-(this.isoWeekday()-1)+7).endOf("day"):c.bind(this)(T,y)}};var rr=function(e){return e.replace(/(\[[^\]]+])|(MMMM|MM|DD|dddd)/g,function(r,a,i){return a||i.slice(1)})},ar={LTS:"h:mm:ss A",LT:"h:mm A",L:"MM/DD/YYYY",LL:"MMMM D, YYYY",LLL:"MMMM D, YYYY h:mm A",LLLL:"dddd, MMMM D, YYYY h:mm A"},ir=function(e,r){return e.replace(/(\[[^\]]+])|(LTS?|l{1,4}|L{1,4})/g,function(a,i,o){var c=o&&o.toUpperCase();return i||r[o]||ar[o]||rr(r[c])})},nr=/(\[[^[]*\])|([-_:/.,()\s]+)|(A|a|Q|YYYY|YY?|ww?|MM?M?M?|Do|DD?|hh?|HH?|mm?|ss?|S{1,3}|z|ZZ?)/g,re=/\d/,lt=/\d\d/,sr=/\d{3}/,or=/\d{4}/,K=/\d\d?/,cr=/[+-]?\d+/,lr=/[+-]\d\d:?(\d\d)?|Z/,ut=/\d*[^-_:/,()\s\d]+/,rt={},le=function(e){return e=+e,e+(e>68?1900:2e3)};function ur(t){if(!t||t==="Z")return 0;var e=t.match(/([+-]|\d\d)/g),r=+(e[1]*60)+(+e[2]||0);return r===0?0:e[0]==="+"?-r:r}var B=function(e){return function(r){this[e]=+r}},ae=[lr,function(t){var e=this.zone||(this.zone={});e.offset=ur(t)}],At=function(e){var r=rt[e];return r&&(r.indexOf?r:r.s.concat(r.f))},ie=function(e,r){var a,i=rt,o=i.meridiem;if(!o)a=e===(r?"pm":"PM");else for(var c=1;c<=24;c+=1)if(e.indexOf(o(c,0,r))>-1){a=c>12;break}return a},dr={A:[ut,function(t){this.afternoon=ie(t,!1)}],a:[ut,function(t){this.afternoon=ie(t,!0)}],Q:[re,function(t){this.month=(t-1)*3+1}],S:[re,function(t){this.milliseconds=+t*100}],SS:[lt,function(t){this.milliseconds=+t*10}],SSS:[sr,function(t){this.milliseconds=+t}],s:[K,B("seconds")],ss:[K,B("seconds")],m:[K,B("minutes")],mm:[K,B("minutes")],H:[K,B("hours")],h:[K,B("hours")],HH:[K,B("hours")],hh:[K,B("hours")],D:[K,B("day")],DD:[lt,B("day")],Do:[ut,function(t){var e=rt,r=e.ordinal,a=t.match(/\d+/);if(this.day=a[0],!!r)for(var i=1;i<=31;i+=1)r(i).replace(/\[|\]/g,"")===t&&(this.day=i)}],w:[K,B("week")],ww:[lt,B("week")],M:[K,B("month")],MM:[lt,B("month")],MMM:[ut,function(t){var e=At("months"),r=At("monthsShort"),a=(r||e.map(function(i){return i.slice(0,3)})).indexOf(t)+1;if(a<1)throw new Error;this.month=a%12||a}],MMMM:[ut,function(t){var e=At("months"),r=e.indexOf(t)+1;if(r<1)throw new Error;this.month=r%12||r}],Y:[cr,B("year")],YY:[lt,function(t){this.year=le(t)}],YYYY:[or,B("year")],Z:ae,ZZ:ae};function fr(t){var e=t.afternoon;if(e!==void 0){var r=t.hours;e?r<12&&(t.hours+=12):r===12&&(t.hours=0),delete t.afternoon}}function hr(t){t=ir(t,rt&&rt.formats);for(var e=t.match(nr),r=e.length,a=0;a<r;a+=1){var i=e[a],o=dr[i],c=o&&o[0],T=o&&o[1];T?e[a]={regex:c,parser:T}:e[a]=i.replace(/^\[|\]$/g,"")}return function(y){for(var x={},p=0,M=0;p<r;p+=1){var w=e[p];if(typeof w=="string")M+=w.length;else{var g=w.regex,F=w.parser,_=y.slice(M),P=g.exec(_),z=P[0];F.call(x,z),y=y.replace(z,"")}}return fr(x),x}}var mr=function(e,r,a,i){try{if(["x","X"].indexOf(r)>-1)return new Date((r==="X"?1e3:1)*e);var o=hr(r),c=o(e),T=c.year,y=c.month,x=c.day,p=c.hours,M=c.minutes,w=c.seconds,g=c.milliseconds,F=c.zone,_=c.week,P=new Date,z=x||(!T&&!y?P.getDate():1),U=T||P.getFullYear(),H=0;T&&!y||(H=y>0?y-1:P.getMonth());var X=p||0,G=M||0,R=w||0,V=g||0;if(F)return new Date(Date.UTC(U,H,z,X,G,R,V+F.offset*60*1e3));if(a)return new Date(Date.UTC(U,H,z,X,G,R,V));var v;return v=new Date(U,H,z,X,G,R,V),_&&(v=i(v).week(_).toDate()),v}catch{return new Date("")}};const kr=function(t,e,r){r.p.customParseFormat=!0,t&&t.parseTwoDigitYear&&(le=t.parseTwoDigitYear);var a=e.prototype,i=a.parse;a.parse=function(o){var c=o.date,T=o.utc,y=o.args;this.$u=T;var x=y[1];if(typeof x=="string"){var p=y[2]===!0,M=y[3]===!0,w=p||M,g=y[2];M&&(g=y[2]),rt=this.$locale(),!p&&g&&(rt=r.Ls[g]),this.$d=mr(c,x,T,r),this.init(),g&&g!==!0&&(this.$L=this.locale(g).$L),w&&c!=this.format(x)&&(this.$d=new Date("")),rt={}}else if(x instanceof Array)for(var F=x.length,_=1;_<=F;_+=1){y[1]=x[_-1];var P=r.apply(this,y);if(P.isValid()){this.$d=P.$d,this.$L=P.$L,this.init();break}_===F&&(this.$d=new Date(""))}else i.call(this,o)}},yr=function(t,e){var r=e.prototype,a=r.format;r.format=function(i){var o=this,c=this.$locale();if(!this.isValid())return a.bind(this)(i);var T=this.$utils(),y=i||$e,x=y.replace(/\[([^\]]+)]|Q|wo|ww|w|WW|W|zzz|z|gggg|GGGG|Do|X|x|k{1,2}|S/g,function(p){switch(p){case"Q":return Math.ceil((o.$M+1)/3);case"Do":return c.ordinal(o.$D);case"gggg":return o.weekYear();case"GGGG":return o.isoWeekYear();case"wo":return c.ordinal(o.week(),"W");case"w":case"ww":return T.s(o.week(),p==="w"?1:2,"0");case"W":case"WW":return T.s(o.isoWeek(),p==="W"?1:2,"0");case"k":case"kk":return T.s(String(o.$H===0?24:o.$H),p==="k"?1:2,"0");case"X":return Math.floor(o.$d.getTime()/1e3);case"x":return o.$d.getTime();case"z":return"["+o.offsetName()+"]";case"zzz":return"["+o.offsetName("long")+"]";default:return p}});return a.bind(this)(x)}};var Yt=function(){var t=l(function(E,u,f,m){for(f=f||{},m=E.length;m--;f[E[m]]=u);return f},"o"),e=[6,8,10,12,13,14,15,16,17,18,20,21,22,23,24,25,26,27,28,29,30,31,33,35,36,38,40],r=[1,26],a=[1,27],i=[1,28],o=[1,29],c=[1,30],T=[1,31],y=[1,32],x=[1,33],p=[1,34],M=[1,9],w=[1,10],g=[1,11],F=[1,12],_=[1,13],P=[1,14],z=[1,15],U=[1,16],H=[1,19],X=[1,20],G=[1,21],R=[1,22],V=[1,23],v=[1,25],S=[1,35],b={trace:l(function(){},"trace"),yy:{},symbols_:{error:2,start:3,gantt:4,document:5,EOF:6,line:7,SPACE:8,statement:9,NL:10,weekday:11,weekday_monday:12,weekday_tuesday:13,weekday_wednesday:14,weekday_thursday:15,weekday_friday:16,weekday_saturday:17,weekday_sunday:18,weekend:19,weekend_friday:20,weekend_saturday:21,dateFormat:22,inclusiveEndDates:23,topAxis:24,axisFormat:25,tickInterval:26,excludes:27,includes:28,todayMarker:29,title:30,acc_title:31,acc_title_value:32,acc_descr:33,acc_descr_value:34,acc_descr_multiline_value:35,section:36,clickStatement:37,taskTxt:38,taskData:39,click:40,callbackname:41,callbackargs:42,href:43,clickStatementDebug:44,$accept:0,$end:1},terminals_:{2:"error",4:"gantt",6:"EOF",8:"SPACE",10:"NL",12:"weekday_monday",13:"weekday_tuesday",14:"weekday_wednesday",15:"weekday_thursday",16:"weekday_friday",17:"weekday_saturday",18:"weekday_sunday",20:"weekend_friday",21:"weekend_saturday",22:"dateFormat",23:"inclusiveEndDates",24:"topAxis",25:"axisFormat",26:"tickInterval",27:"excludes",28:"includes",29:"todayMarker",30:"title",31:"acc_title",32:"acc_title_value",33:"acc_descr",34:"acc_descr_value",35:"acc_descr_multiline_value",36:"section",38:"taskTxt",39:"taskData",40:"click",41:"callbackname",42:"callbackargs",43:"href"},productions_:[0,[3,3],[5,0],[5,2],[7,2],[7,1],[7,1],[7,1],[11,1],[11,1],[11,1],[11,1],[11,1],[11,1],[11,1],[19,1],[19,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,2],[9,2],[9,1],[9,1],[9,1],[9,2],[37,2],[37,3],[37,3],[37,4],[37,3],[37,4],[37,2],[44,2],[44,3],[44,3],[44,4],[44,3],[44,4],[44,2]],performAction:l(function(u,f,m,h,C,s,d){var n=s.length-1;switch(C){case 1:return s[n-1];case 2:this.$=[];break;case 3:s[n-1].push(s[n]),this.$=s[n-1];break;case 4:case 5:this.$=s[n];break;case 6:case 7:this.$=[];break;case 8:h.setWeekday("monday");break;case 9:h.setWeekday("tuesday");break;case 10:h.setWeekday("wednesday");break;case 11:h.setWeekday("thursday");break;case 12:h.setWeekday("friday");break;case 13:h.setWeekday("saturday");break;case 14:h.setWeekday("sunday");break;case 15:h.setWeekend("friday");break;case 16:h.setWeekend("saturday");break;case 17:h.setDateFormat(s[n].substr(11)),this.$=s[n].substr(11);break;case 18:h.enableInclusiveEndDates(),this.$=s[n].substr(18);break;case 19:h.TopAxis(),this.$=s[n].substr(8);break;case 20:h.setAxisFormat(s[n].substr(11)),this.$=s[n].substr(11);break;case 21:h.setTickInterval(s[n].substr(13)),this.$=s[n].substr(13);break;case 22:h.setExcludes(s[n].substr(9)),this.$=s[n].substr(9);break;case 23:h.setIncludes(s[n].substr(9)),this.$=s[n].substr(9);break;case 24:h.setTodayMarker(s[n].substr(12)),this.$=s[n].substr(12);break;case 27:h.setDiagramTitle(s[n].substr(6)),this.$=s[n].substr(6);break;case 28:this.$=s[n].trim(),h.setAccTitle(this.$);break;case 29:case 30:this.$=s[n].trim(),h.setAccDescription(this.$);break;case 31:h.addSection(s[n].substr(8)),this.$=s[n].substr(8);break;case 33:h.addTask(s[n-1],s[n]),this.$="task";break;case 34:this.$=s[n-1],h.setClickEvent(s[n-1],s[n],null);break;case 35:this.$=s[n-2],h.setClickEvent(s[n-2],s[n-1],s[n]);break;case 36:this.$=s[n-2],h.setClickEvent(s[n-2],s[n-1],null),h.setLink(s[n-2],s[n]);break;case 37:this.$=s[n-3],h.setClickEvent(s[n-3],s[n-2],s[n-1]),h.setLink(s[n-3],s[n]);break;case 38:this.$=s[n-2],h.setClickEvent(s[n-2],s[n],null),h.setLink(s[n-2],s[n-1]);break;case 39:this.$=s[n-3],h.setClickEvent(s[n-3],s[n-1],s[n]),h.setLink(s[n-3],s[n-2]);break;case 40:this.$=s[n-1],h.setLink(s[n-1],s[n]);break;case 41:case 47:this.$=s[n-1]+" "+s[n];break;case 42:case 43:case 45:this.$=s[n-2]+" "+s[n-1]+" "+s[n];break;case 44:case 46:this.$=s[n-3]+" "+s[n-2]+" "+s[n-1]+" "+s[n];break}},"anonymous"),table:[{3:1,4:[1,2]},{1:[3]},t(e,[2,2],{5:3}),{6:[1,4],7:5,8:[1,6],9:7,10:[1,8],11:17,12:r,13:a,14:i,15:o,16:c,17:T,18:y,19:18,20:x,21:p,22:M,23:w,24:g,25:F,26:_,27:P,28:z,29:U,30:H,31:X,33:G,35:R,36:V,37:24,38:v,40:S},t(e,[2,7],{1:[2,1]}),t(e,[2,3]),{9:36,11:17,12:r,13:a,14:i,15:o,16:c,17:T,18:y,19:18,20:x,21:p,22:M,23:w,24:g,25:F,26:_,27:P,28:z,29:U,30:H,31:X,33:G,35:R,36:V,37:24,38:v,40:S},t(e,[2,5]),t(e,[2,6]),t(e,[2,17]),t(e,[2,18]),t(e,[2,19]),t(e,[2,20]),t(e,[2,21]),t(e,[2,22]),t(e,[2,23]),t(e,[2,24]),t(e,[2,25]),t(e,[2,26]),t(e,[2,27]),{32:[1,37]},{34:[1,38]},t(e,[2,30]),t(e,[2,31]),t(e,[2,32]),{39:[1,39]},t(e,[2,8]),t(e,[2,9]),t(e,[2,10]),t(e,[2,11]),t(e,[2,12]),t(e,[2,13]),t(e,[2,14]),t(e,[2,15]),t(e,[2,16]),{41:[1,40],43:[1,41]},t(e,[2,4]),t(e,[2,28]),t(e,[2,29]),t(e,[2,33]),t(e,[2,34],{42:[1,42],43:[1,43]}),t(e,[2,40],{41:[1,44]}),t(e,[2,35],{43:[1,45]}),t(e,[2,36]),t(e,[2,38],{42:[1,46]}),t(e,[2,37]),t(e,[2,39])],defaultActions:{},parseError:l(function(u,f){if(f.recoverable)this.trace(u);else{var m=new Error(u);throw m.hash=f,m}},"parseError"),parse:l(function(u){var f=this,m=[0],h=[],C=[null],s=[],d=this.table,n="",Y=0,A=0,I=2,N=1,L=s.slice.call(arguments,1),W=Object.create(this.lexer),$={yy:{}};for(var _t in this.yy)Object.prototype.hasOwnProperty.call(this.yy,_t)&&($.yy[_t]=this.yy[_t]);W.setInput(u,$.yy),$.yy.lexer=W,$.yy.parser=this,typeof W.yylloc>"u"&&(W.yylloc={});var Dt=W.yylloc;s.push(Dt);var ve=W.options&&W.options.ranges;typeof $.yy.parseError=="function"?this.parseError=$.yy.parseError:this.parseError=Object.getPrototypeOf(this).parseError;function pe(Z){m.length=m.length-2*Z,C.length=C.length-Z,s.length=s.length-Z}l(pe,"popStack");function Ut(){var Z;return Z=h.pop()||W.lex()||N,typeof Z!="number"&&(Z instanceof Array&&(h=Z,Z=h.pop()),Z=f.symbols_[Z]||Z),Z}l(Ut,"lex");for(var j,at,Q,St,nt={},mt,tt,Xt,kt;;){if(at=m[m.length-1],this.defaultActions[at]?Q=this.defaultActions[at]:((j===null||typeof j>"u")&&(j=Ut()),Q=d[at]&&d[at][j]),typeof Q>"u"||!Q.length||!Q[0]){var Ct="";kt=[];for(mt in d[at])this.terminals_[mt]&&mt>I&&kt.push("'"+this.terminals_[mt]+"'");W.showPosition?Ct="Parse error on line "+(Y+1)+`:
`+W.showPosition()+`
Expecting `+kt.join(", ")+", got '"+(this.terminals_[j]||j)+"'":Ct="Parse error on line "+(Y+1)+": Unexpected "+(j==N?"end of input":"'"+(this.terminals_[j]||j)+"'"),this.parseError(Ct,{text:W.match,token:this.terminals_[j]||j,line:W.yylineno,loc:Dt,expected:kt})}if(Q[0]instanceof Array&&Q.length>1)throw new Error("Parse Error: multiple actions possible at state: "+at+", token: "+j);switch(Q[0]){case 1:m.push(j),C.push(W.yytext),s.push(W.yylloc),m.push(Q[1]),j=null,A=W.yyleng,n=W.yytext,Y=W.yylineno,Dt=W.yylloc;break;case 2:if(tt=this.productions_[Q[1]][1],nt.$=C[C.length-tt],nt._$={first_line:s[s.length-(tt||1)].first_line,last_line:s[s.length-1].last_line,first_column:s[s.length-(tt||1)].first_column,last_column:s[s.length-1].last_column},ve&&(nt._$.range=[s[s.length-(tt||1)].range[0],s[s.length-1].range[1]]),St=this.performAction.apply(nt,[n,A,Y,$.yy,Q[1],C,s].concat(L)),typeof St<"u")return St;tt&&(m=m.slice(0,-1*tt*2),C=C.slice(0,-1*tt),s=s.slice(0,-1*tt)),m.push(this.productions_[Q[1]][0]),C.push(nt.$),s.push(nt._$),Xt=d[m[m.length-2]][m[m.length-1]],m.push(Xt);break;case 3:return!0}}return!0},"parse")},D=function(){var E={EOF:1,parseError:l(function(f,m){if(this.yy.parser)this.yy.parser.parseError(f,m);else throw new Error(f)},"parseError"),setInput:l(function(u,f){return this.yy=f||this.yy||{},this._input=u,this._more=this._backtrack=this.done=!1,this.yylineno=this.yyleng=0,this.yytext=this.matched=this.match="",this.conditionStack=["INITIAL"],this.yylloc={first_line:1,first_column:0,last_line:1,last_column:0},this.options.ranges&&(this.yylloc.range=[0,0]),this.offset=0,this},"setInput"),input:l(function(){var u=this._input[0];this.yytext+=u,this.yyleng++,this.offset++,this.match+=u,this.matched+=u;var f=u.match(/(?:\r\n?|\n).*/g);return f?(this.yylineno++,this.yylloc.last_line++):this.yylloc.last_column++,this.options.ranges&&this.yylloc.range[1]++,this._input=this._input.slice(1),u},"input"),unput:l(function(u){var f=u.length,m=u.split(/(?:\r\n?|\n)/g);this._input=u+this._input,this.yytext=this.yytext.substr(0,this.yytext.length-f),this.offset-=f;var h=this.match.split(/(?:\r\n?|\n)/g);this.match=this.match.substr(0,this.match.length-1),this.matched=this.matched.substr(0,this.matched.length-1),m.length-1&&(this.yylineno-=m.length-1);var C=this.yylloc.range;return this.yylloc={first_line:this.yylloc.first_line,last_line:this.yylineno+1,first_column:this.yylloc.first_column,last_column:m?(m.length===h.length?this.yylloc.first_column:0)+h[h.length-m.length].length-m[0].length:this.yylloc.first_column-f},this.options.ranges&&(this.yylloc.range=[C[0],C[0]+this.yyleng-f]),this.yyleng=this.yytext.length,this},"unput"),more:l(function(){return this._more=!0,this},"more"),reject:l(function(){if(this.options.backtrack_lexer)this._backtrack=!0;else return this.parseError("Lexical error on line "+(this.yylineno+1)+`. You can only invoke reject() in the lexer when the lexer is of the backtracking persuasion (options.backtrack_lexer = true).
`+this.showPosition(),{text:"",token:null,line:this.yylineno});return this},"reject"),less:l(function(u){this.unput(this.match.slice(u))},"less"),pastInput:l(function(){var u=this.matched.substr(0,this.matched.length-this.match.length);return(u.length>20?"...":"")+u.substr(-20).replace(/\n/g,"")},"pastInput"),upcomingInput:l(function(){var u=this.match;return u.length<20&&(u+=this._input.substr(0,20-u.length)),(u.substr(0,20)+(u.length>20?"...":"")).replace(/\n/g,"")},"upcomingInput"),showPosition:l(function(){var u=this.pastInput(),f=new Array(u.length+1).join("-");return u+this.upcomingInput()+`
`+f+"^"},"showPosition"),test_match:l(function(u,f){var m,h,C;if(this.options.backtrack_lexer&&(C={yylineno:this.yylineno,yylloc:{first_line:this.yylloc.first_line,last_line:this.last_line,first_column:this.yylloc.first_column,last_column:this.yylloc.last_column},yytext:this.yytext,match:this.match,matches:this.matches,matched:this.matched,yyleng:this.yyleng,offset:this.offset,_more:this._more,_input:this._input,yy:this.yy,conditionStack:this.conditionStack.slice(0),done:this.done},this.options.ranges&&(C.yylloc.range=this.yylloc.range.slice(0))),h=u[0].match(/(?:\r\n?|\n).*/g),h&&(this.yylineno+=h.length),this.yylloc={first_line:this.yylloc.last_line,last_line:this.yylineno+1,first_column:this.yylloc.last_column,last_column:h?h[h.length-1].length-h[h.length-1].match(/\r?\n?/)[0].length:this.yylloc.last_column+u[0].length},this.yytext+=u[0],this.match+=u[0],this.matches=u,this.yyleng=this.yytext.length,this.options.ranges&&(this.yylloc.range=[this.offset,this.offset+=this.yyleng]),this._more=!1,this._backtrack=!1,this._input=this._input.slice(u[0].length),this.matched+=u[0],m=this.performAction.call(this,this.yy,this,f,this.conditionStack[this.conditionStack.length-1]),this.done&&this._input&&(this.done=!1),m)return m;if(this._backtrack){for(var s in C)this[s]=C[s];return!1}return!1},"test_match"),next:l(function(){if(this.done)return this.EOF;this._input||(this.done=!0);var u,f,m,h;this._more||(this.yytext="",this.match="");for(var C=this._currentRules(),s=0;s<C.length;s++)if(m=this._input.match(this.rules[C[s]]),m&&(!f||m[0].length>f[0].length)){if(f=m,h=s,this.options.backtrack_lexer){if(u=this.test_match(m,C[s]),u!==!1)return u;if(this._backtrack){f=!1;continue}else return!1}else if(!this.options.flex)break}return f?(u=this.test_match(f,C[h]),u!==!1?u:!1):this._input===""?this.EOF:this.parseError("Lexical error on line "+(this.yylineno+1)+`. Unrecognized text.
`+this.showPosition(),{text:"",token:null,line:this.yylineno})},"next"),lex:l(function(){var f=this.next();return f||this.lex()},"lex"),begin:l(function(f){this.conditionStack.push(f)},"begin"),popState:l(function(){var f=this.conditionStack.length-1;return f>0?this.conditionStack.pop():this.conditionStack[0]},"popState"),_currentRules:l(function(){return this.conditionStack.length&&this.conditionStack[this.conditionStack.length-1]?this.conditions[this.conditionStack[this.conditionStack.length-1]].rules:this.conditions.INITIAL.rules},"_currentRules"),topState:l(function(f){return f=this.conditionStack.length-1-Math.abs(f||0),f>=0?this.conditionStack[f]:"INITIAL"},"topState"),pushState:l(function(f){this.begin(f)},"pushState"),stateStackSize:l(function(){return this.conditionStack.length},"stateStackSize"),options:{"case-insensitive":!0},performAction:l(function(f,m,h,C){switch(h){case 0:return this.begin("open_directive"),"open_directive";case 1:return this.begin("acc_title"),31;case 2:return this.popState(),"acc_title_value";case 3:return this.begin("acc_descr"),33;case 4:return this.popState(),"acc_descr_value";case 5:this.begin("acc_descr_multiline");break;case 6:this.popState();break;case 7:return"acc_descr_multiline_value";case 8:break;case 9:break;case 10:break;case 11:return 10;case 12:break;case 13:break;case 14:this.begin("href");break;case 15:this.popState();break;case 16:return 43;case 17:this.begin("callbackname");break;case 18:this.popState();break;case 19:this.popState(),this.begin("callbackargs");break;case 20:return 41;case 21:this.popState();break;case 22:return 42;case 23:this.begin("click");break;case 24:this.popState();break;case 25:return 40;case 26:return 4;case 27:return 22;case 28:return 23;case 29:return 24;case 30:return 25;case 31:return 26;case 32:return 28;case 33:return 27;case 34:return 29;case 35:return 12;case 36:return 13;case 37:return 14;case 38:return 15;case 39:return 16;case 40:return 17;case 41:return 18;case 42:return 20;case 43:return 21;case 44:return"date";case 45:return 30;case 46:return"accDescription";case 47:return 36;case 48:return 38;case 49:return 39;case 50:return":";case 51:return 6;case 52:return"INVALID"}},"anonymous"),rules:[/^(?:%%\{)/i,/^(?:accTitle\s*:\s*)/i,/^(?:(?!\n||)*[^\n]*)/i,/^(?:accDescr\s*:\s*)/i,/^(?:(?!\n||)*[^\n]*)/i,/^(?:accDescr\s*\{\s*)/i,/^(?:[\}])/i,/^(?:[^\}]*)/i,/^(?:%%(?!\{)*[^\n]*)/i,/^(?:[^\}]%%*[^\n]*)/i,/^(?:%%*[^\n]*[\n]*)/i,/^(?:[\n]+)/i,/^(?:\s+)/i,/^(?:%[^\n]*)/i,/^(?:href[\s]+["])/i,/^(?:["])/i,/^(?:[^"]*)/i,/^(?:call[\s]+)/i,/^(?:\([\s]*\))/i,/^(?:\()/i,/^(?:[^(]*)/i,/^(?:\))/i,/^(?:[^)]*)/i,/^(?:click[\s]+)/i,/^(?:[\s\n])/i,/^(?:[^\s\n]*)/i,/^(?:gantt\b)/i,/^(?:dateFormat\s[^#\n;]+)/i,/^(?:inclusiveEndDates\b)/i,/^(?:topAxis\b)/i,/^(?:axisFormat\s[^#\n;]+)/i,/^(?:tickInterval\s[^#\n;]+)/i,/^(?:includes\s[^#\n;]+)/i,/^(?:excludes\s[^#\n;]+)/i,/^(?:todayMarker\s[^\n;]+)/i,/^(?:weekday\s+monday\b)/i,/^(?:weekday\s+tuesday\b)/i,/^(?:weekday\s+wednesday\b)/i,/^(?:weekday\s+thursday\b)/i,/^(?:weekday\s+friday\b)/i,/^(?:weekday\s+saturday\b)/i,/^(?:weekday\s+sunday\b)/i,/^(?:weekend\s+friday\b)/i,/^(?:weekend\s+saturday\b)/i,/^(?:\d\d\d\d-\d\d-\d\d\b)/i,/^(?:title\s[^\n]+)/i,/^(?:accDescription\s[^#\n;]+)/i,/^(?:section\s[^\n]+)/i,/^(?:[^:\n]+)/i,/^(?::[^#\n;]+)/i,/^(?::)/i,/^(?:$)/i,/^(?:.)/i],conditions:{acc_descr_multiline:{rules:[6,7],inclusive:!1},acc_descr:{rules:[4],inclusive:!1},acc_title:{rules:[2],inclusive:!1},callbackargs:{rules:[21,22],inclusive:!1},callbackname:{rules:[18,19,20],inclusive:!1},href:{rules:[15,16],inclusive:!1},click:{rules:[24,25],inclusive:!1},INITIAL:{rules:[0,1,3,5,8,9,10,11,12,13,14,17,23,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52],inclusive:!0}}};return E}();b.lexer=D;function k(){this.yy={}}return l(k,"Parser"),k.prototype=b,b.Parser=k,new k}();Yt.parser=Yt;var gr=Yt;q.extend(er);q.extend(kr);q.extend(yr);var ne={friday:5,saturday:6},J="",Vt="",Ot=void 0,Pt="",dt=[],ft=[],zt=new Map,Rt=[],bt=[],ct="",Nt="",ue=["active","done","crit","milestone"],Bt=[],ht=!1,Ht=!1,Gt="sunday",wt="saturday",Ft=0,vr=l(function(){Rt=[],bt=[],ct="",Bt=[],pt=0,Wt=void 0,Tt=void 0,O=[],J="",Vt="",Nt="",Ot=void 0,Pt="",dt=[],ft=[],ht=!1,Ht=!1,Ft=0,zt=new Map,Me(),Gt="sunday",wt="saturday"},"clear"),pr=l(function(t){Vt=t},"setAxisFormat"),Tr=l(function(){return Vt},"getAxisFormat"),xr=l(function(t){Ot=t},"setTickInterval"),br=l(function(){return Ot},"getTickInterval"),wr=l(function(t){Pt=t},"setTodayMarker"),_r=l(function(){return Pt},"getTodayMarker"),Dr=l(function(t){J=t},"setDateFormat"),Sr=l(function(){ht=!0},"enableInclusiveEndDates"),Cr=l(function(){return ht},"endDatesAreInclusive"),Er=l(function(){Ht=!0},"enableTopAxis"),Mr=l(function(){return Ht},"topAxisEnabled"),Ar=l(function(t){Nt=t},"setDisplayMode"),Ir=l(function(){return Nt},"getDisplayMode"),Yr=l(function(){return J},"getDateFormat"),Fr=l(function(t){dt=t.toLowerCase().split(/[\s,]+/)},"setIncludes"),Lr=l(function(){return dt},"getIncludes"),Wr=l(function(t){ft=t.toLowerCase().split(/[\s,]+/)},"setExcludes"),Vr=l(function(){return ft},"getExcludes"),Or=l(function(){return zt},"getLinks"),Pr=l(function(t){ct=t,Rt.push(t)},"addSection"),zr=l(function(){return Rt},"getSections"),Rr=l(function(){let t=se();const e=10;let r=0;for(;!t&&r<e;)t=se(),r++;return bt=O,bt},"getTasks"),de=l(function(t,e,r,a){return a.includes(t.format(e.trim()))?!1:r.includes("weekends")&&(t.isoWeekday()===ne[wt]||t.isoWeekday()===ne[wt]+1)||r.includes(t.format("dddd").toLowerCase())?!0:r.includes(t.format(e.trim()))},"isInvalidDate"),Nr=l(function(t){Gt=t},"setWeekday"),Br=l(function(){return Gt},"getWeekday"),Hr=l(function(t){wt=t},"setWeekend"),fe=l(function(t,e,r,a){if(!r.length||t.manualEndTime)return;let i;t.startTime instanceof Date?i=q(t.startTime):i=q(t.startTime,e,!0),i=i.add(1,"d");let o;t.endTime instanceof Date?o=q(t.endTime):o=q(t.endTime,e,!0);const[c,T]=Gr(i,o,e,r,a);t.endTime=c.toDate(),t.renderEndTime=T},"checkTaskDates"),Gr=l(function(t,e,r,a,i){let o=!1,c=null;for(;t<=e;)o||(c=e.toDate()),o=de(t,r,a,i),o&&(e=e.add(1,"d")),t=t.add(1,"d");return[e,c]},"fixTaskDates"),Lt=l(function(t,e,r){r=r.trim();const i=/^after\s+(?<ids>[\d\w- ]+)/.exec(r);if(i!==null){let c=null;for(const y of i.groups.ids.split(" ")){let x=it(y);x!==void 0&&(!c||x.endTime>c.endTime)&&(c=x)}if(c)return c.endTime;const T=new Date;return T.setHours(0,0,0,0),T}let o=q(r,e.trim(),!0);if(o.isValid())return o.toDate();{xt.debug("Invalid date:"+r),xt.debug("With date format:"+e.trim());const c=new Date(r);if(c===void 0||isNaN(c.getTime())||c.getFullYear()<-1e4||c.getFullYear()>1e4)throw new Error("Invalid date:"+r);return c}},"getStartDate"),he=l(function(t){const e=/^(\d+(?:\.\d+)?)([Mdhmswy]|ms)$/.exec(t.trim());return e!==null?[Number.parseFloat(e[1]),e[2]]:[NaN,"ms"]},"parseDuration"),me=l(function(t,e,r,a=!1){r=r.trim();const o=/^until\s+(?<ids>[\d\w- ]+)/.exec(r);if(o!==null){let p=null;for(const w of o.groups.ids.split(" ")){let g=it(w);g!==void 0&&(!p||g.startTime<p.startTime)&&(p=g)}if(p)return p.startTime;const M=new Date;return M.setHours(0,0,0,0),M}let c=q(r,e.trim(),!0);if(c.isValid())return a&&(c=c.add(1,"d")),c.toDate();let T=q(t);const[y,x]=he(r);if(!Number.isNaN(y)){const p=T.add(y,x);p.isValid()&&(T=p)}return T.toDate()},"getEndDate"),pt=0,ot=l(function(t){return t===void 0?(pt=pt+1,"task"+pt):t},"parseId"),qr=l(function(t,e){let r;e.substr(0,1)===":"?r=e.substr(1,e.length):r=e;const a=r.split(","),i={};qt(a,i,ue);for(let c=0;c<a.length;c++)a[c]=a[c].trim();let o="";switch(a.length){case 1:i.id=ot(),i.startTime=t.endTime,o=a[0];break;case 2:i.id=ot(),i.startTime=Lt(void 0,J,a[0]),o=a[1];break;case 3:i.id=ot(a[0]),i.startTime=Lt(void 0,J,a[1]),o=a[2];break}return o&&(i.endTime=me(i.startTime,J,o,ht),i.manualEndTime=q(o,"YYYY-MM-DD",!0).isValid(),fe(i,J,ft,dt)),i},"compileData"),Ur=l(function(t,e){let r;e.substr(0,1)===":"?r=e.substr(1,e.length):r=e;const a=r.split(","),i={};qt(a,i,ue);for(let o=0;o<a.length;o++)a[o]=a[o].trim();switch(a.length){case 1:i.id=ot(),i.startTime={type:"prevTaskEnd",id:t},i.endTime={data:a[0]};break;case 2:i.id=ot(),i.startTime={type:"getStartDate",startData:a[0]},i.endTime={data:a[1]};break;case 3:i.id=ot(a[0]),i.startTime={type:"getStartDate",startData:a[1]},i.endTime={data:a[2]};break}return i},"parseData"),Wt,Tt,O=[],ke={},Xr=l(function(t,e){const r={section:ct,type:ct,processed:!1,manualEndTime:!1,renderEndTime:null,raw:{data:e},task:t,classes:[]},a=Ur(Tt,e);r.raw.startTime=a.startTime,r.raw.endTime=a.endTime,r.id=a.id,r.prevTaskId=Tt,r.active=a.active,r.done=a.done,r.crit=a.crit,r.milestone=a.milestone,r.order=Ft,Ft++;const i=O.push(r);Tt=r.id,ke[r.id]=i-1},"addTask"),it=l(function(t){const e=ke[t];return O[e]},"findTaskById"),jr=l(function(t,e){const r={section:ct,type:ct,description:t,task:t,classes:[]},a=qr(Wt,e);r.startTime=a.startTime,r.endTime=a.endTime,r.id=a.id,r.active=a.active,r.done=a.done,r.crit=a.crit,r.milestone=a.milestone,Wt=r,bt.push(r)},"addTaskOrg"),se=l(function(){const t=l(function(r){const a=O[r];let i="";switch(O[r].raw.startTime.type){case"prevTaskEnd":{const o=it(a.prevTaskId);a.startTime=o.endTime;break}case"getStartDate":i=Lt(void 0,J,O[r].raw.startTime.startData),i&&(O[r].startTime=i);break}return O[r].startTime&&(O[r].endTime=me(O[r].startTime,J,O[r].raw.endTime.data,ht),O[r].endTime&&(O[r].processed=!0,O[r].manualEndTime=q(O[r].raw.endTime.data,"YYYY-MM-DD",!0).isValid(),fe(O[r],J,ft,dt))),O[r].processed},"compileTask");let e=!0;for(const[r,a]of O.entries())t(r),e=e&&a.processed;return e},"compileTasks"),Zr=l(function(t,e){let r=e;st().securityLevel!=="loose"&&(r=Ee(e)),t.split(",").forEach(function(a){it(a)!==void 0&&(ge(a,()=>{window.open(r,"_self")}),zt.set(a,r))}),ye(t,"clickable")},"setLink"),ye=l(function(t,e){t.split(",").forEach(function(r){let a=it(r);a!==void 0&&a.classes.push(e)})},"setClass"),Qr=l(function(t,e,r){if(st().securityLevel!=="loose"||e===void 0)return;let a=[];if(typeof r=="string"){a=r.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/);for(let o=0;o<a.length;o++){let c=a[o].trim();c.startsWith('"')&&c.endsWith('"')&&(c=c.substr(1,c.length-2)),a[o]=c}}a.length===0&&a.push(t),it(t)!==void 0&&ge(t,()=>{Ae.runFunc(e,...a)})},"setClickFun"),ge=l(function(t,e){Bt.push(function(){const r=document.querySelector(`[id="${t}"]`);r!==null&&r.addEventListener("click",function(){e()})},function(){const r=document.querySelector(`[id="${t}-text"]`);r!==null&&r.addEventListener("click",function(){e()})})},"pushFun"),Kr=l(function(t,e,r){t.split(",").forEach(function(a){Qr(a,e,r)}),ye(t,"clickable")},"setClickEvent"),Jr=l(function(t){Bt.forEach(function(e){e(t)})},"bindFunctions"),$r={getConfig:l(()=>st().gantt,"getConfig"),clear:vr,setDateFormat:Dr,getDateFormat:Yr,enableInclusiveEndDates:Sr,endDatesAreInclusive:Cr,enableTopAxis:Er,topAxisEnabled:Mr,setAxisFormat:pr,getAxisFormat:Tr,setTickInterval:xr,getTickInterval:br,setTodayMarker:wr,getTodayMarker:_r,setAccTitle:De,getAccTitle:_e,setDiagramTitle:we,getDiagramTitle:be,setDisplayMode:Ar,getDisplayMode:Ir,setAccDescription:xe,getAccDescription:Te,addSection:Pr,getSections:zr,getTasks:Rr,addTask:Xr,findTaskById:it,addTaskOrg:jr,setIncludes:Fr,getIncludes:Lr,setExcludes:Wr,getExcludes:Vr,setClickEvent:Kr,setLink:Zr,getLinks:Or,bindFunctions:Jr,parseDuration:he,isInvalidDate:de,setWeekday:Nr,getWeekday:Br,setWeekend:Hr};function qt(t,e,r){let a=!0;for(;a;)a=!1,r.forEach(function(i){const o="^\\s*"+i+"\\s*$",c=new RegExp(o);t[0].match(c)&&(e[i]=!0,t.shift(1),a=!0)})}l(qt,"getTaskTags");var ta=l(function(){xt.debug("Something is calling, setConf, remove the call")},"setConf"),oe={monday:Be,tuesday:Ne,wednesday:Re,thursday:ze,friday:Pe,saturday:Oe,sunday:Ve},ea=l((t,e)=>{let r=[...t].map(()=>-1/0),a=[...t].sort((o,c)=>o.startTime-c.startTime||o.order-c.order),i=0;for(const o of a)for(let c=0;c<r.length;c++)if(o.startTime>=r[c]){r[c]=o.endTime,o.order=c+e,c>i&&(i=c);break}return i},"getMaxIntersections"),et,ra=l(function(t,e,r,a){const i=st().gantt,o=st().securityLevel;let c;o==="sandbox"&&(c=yt("#i"+e));const T=o==="sandbox"?yt(c.nodes()[0].contentDocument.body):yt("body"),y=o==="sandbox"?c.nodes()[0].contentDocument:document,x=y.getElementById(e);et=x.parentElement.offsetWidth,et===void 0&&(et=1200),i.useWidth!==void 0&&(et=i.useWidth);const p=a.db.getTasks();let M=[];for(const v of p)M.push(v.type);M=V(M);const w={};let g=2*i.topPadding;if(a.db.getDisplayMode()==="compact"||i.displayMode==="compact"){const v={};for(const b of p)v[b.section]===void 0?v[b.section]=[b]:v[b.section].push(b);let S=0;for(const b of Object.keys(v)){const D=ea(v[b],S)+1;S+=D,g+=D*(i.barHeight+i.barGap),w[b]=D}}else{g+=p.length*(i.barHeight+i.barGap);for(const v of M)w[v]=p.filter(S=>S.type===v).length}x.setAttribute("viewBox","0 0 "+et+" "+g);const F=T.select(`[id="${e}"]`),_=Ie().domain([Ye(p,function(v){return v.startTime}),Fe(p,function(v){return v.endTime})]).rangeRound([0,et-i.leftPadding-i.rightPadding]);function P(v,S){const b=v.startTime,D=S.startTime;let k=0;return b>D?k=1:b<D&&(k=-1),k}l(P,"taskCompare"),p.sort(P),z(p,et,g),Se(F,g,et,i.useMaxWidth),F.append("text").text(a.db.getDiagramTitle()).attr("x",et/2).attr("y",i.titleTopMargin).attr("class","titleText");function z(v,S,b){const D=i.barHeight,k=D+i.barGap,E=i.topPadding,u=i.leftPadding,f=Le().domain([0,M.length]).range(["#00B9FA","#F95002"]).interpolate(We);H(k,E,u,S,b,v,a.db.getExcludes(),a.db.getIncludes()),X(u,E,S,b),U(v,k,E,u,D,f,S),G(k,E),R(u,E,S,b)}l(z,"makeGantt");function U(v,S,b,D,k,E,u){const m=[...new Set(v.map(d=>d.order))].map(d=>v.find(n=>n.order===d));F.append("g").selectAll("rect").data(m).enter().append("rect").attr("x",0).attr("y",function(d,n){return n=d.order,n*S+b-2}).attr("width",function(){return u-i.rightPadding/2}).attr("height",S).attr("class",function(d){for(const[n,Y]of M.entries())if(d.type===Y)return"section section"+n%i.numberSectionStyles;return"section section0"});const h=F.append("g").selectAll("rect").data(v).enter(),C=a.db.getLinks();if(h.append("rect").attr("id",function(d){return d.id}).attr("rx",3).attr("ry",3).attr("x",function(d){return d.milestone?_(d.startTime)+D+.5*(_(d.endTime)-_(d.startTime))-.5*k:_(d.startTime)+D}).attr("y",function(d,n){return n=d.order,n*S+b}).attr("width",function(d){return d.milestone?k:_(d.renderEndTime||d.endTime)-_(d.startTime)}).attr("height",k).attr("transform-origin",function(d,n){return n=d.order,(_(d.startTime)+D+.5*(_(d.endTime)-_(d.startTime))).toString()+"px "+(n*S+b+.5*k).toString()+"px"}).attr("class",function(d){const n="task";let Y="";d.classes.length>0&&(Y=d.classes.join(" "));let A=0;for(const[N,L]of M.entries())d.type===L&&(A=N%i.numberSectionStyles);let I="";return d.active?d.crit?I+=" activeCrit":I=" active":d.done?d.crit?I=" doneCrit":I=" done":d.crit&&(I+=" crit"),I.length===0&&(I=" task"),d.milestone&&(I=" milestone "+I),I+=A,I+=" "+Y,n+I}),h.append("text").attr("id",function(d){return d.id+"-text"}).text(function(d){return d.task}).attr("font-size",i.fontSize).attr("x",function(d){let n=_(d.startTime),Y=_(d.renderEndTime||d.endTime);d.milestone&&(n+=.5*(_(d.endTime)-_(d.startTime))-.5*k),d.milestone&&(Y=n+k);const A=this.getBBox().width;return A>Y-n?Y+A+1.5*i.leftPadding>u?n+D-5:Y+D+5:(Y-n)/2+n+D}).attr("y",function(d,n){return n=d.order,n*S+i.barHeight/2+(i.fontSize/2-2)+b}).attr("text-height",k).attr("class",function(d){const n=_(d.startTime);let Y=_(d.endTime);d.milestone&&(Y=n+k);const A=this.getBBox().width;let I="";d.classes.length>0&&(I=d.classes.join(" "));let N=0;for(const[W,$]of M.entries())d.type===$&&(N=W%i.numberSectionStyles);let L="";return d.active&&(d.crit?L="activeCritText"+N:L="activeText"+N),d.done?d.crit?L=L+" doneCritText"+N:L=L+" doneText"+N:d.crit&&(L=L+" critText"+N),d.milestone&&(L+=" milestoneText"),A>Y-n?Y+A+1.5*i.leftPadding>u?I+" taskTextOutsideLeft taskTextOutside"+N+" "+L:I+" taskTextOutsideRight taskTextOutside"+N+" "+L+" width-"+A:I+" taskText taskText"+N+" "+L+" width-"+A}),st().securityLevel==="sandbox"){let d;d=yt("#i"+e);const n=d.nodes()[0].contentDocument;h.filter(function(Y){return C.has(Y.id)}).each(function(Y){var A=n.querySelector("#"+Y.id),I=n.querySelector("#"+Y.id+"-text");const N=A.parentNode;var L=n.createElement("a");L.setAttribute("xlink:href",C.get(Y.id)),L.setAttribute("target","_top"),N.appendChild(L),L.appendChild(A),L.appendChild(I)})}}l(U,"drawRects");function H(v,S,b,D,k,E,u,f){if(u.length===0&&f.length===0)return;let m,h;for(const{startTime:A,endTime:I}of E)(m===void 0||A<m)&&(m=A),(h===void 0||I>h)&&(h=I);if(!m||!h)return;if(q(h).diff(q(m),"year")>5){xt.warn("The difference between the min and max time is more than 5 years. This will cause performance issues. Skipping drawing exclude days.");return}const C=a.db.getDateFormat(),s=[];let d=null,n=q(m);for(;n.valueOf()<=h;)a.db.isInvalidDate(n,C,u,f)?d?d.end=n:d={start:n,end:n}:d&&(s.push(d),d=null),n=n.add(1,"d");F.append("g").selectAll("rect").data(s).enter().append("rect").attr("id",function(A){return"exclude-"+A.start.format("YYYY-MM-DD")}).attr("x",function(A){return _(A.start)+b}).attr("y",i.gridLineStartPadding).attr("width",function(A){const I=A.end.add(1,"day");return _(I)-_(A.start)}).attr("height",k-S-i.gridLineStartPadding).attr("transform-origin",function(A,I){return(_(A.start)+b+.5*(_(A.end)-_(A.start))).toString()+"px "+(I*v+.5*k).toString()+"px"}).attr("class","exclude-range")}l(H,"drawExcludeDays");function X(v,S,b,D){let k=Qe(_).tickSize(-D+S+i.gridLineStartPadding).tickFormat(jt(a.db.getAxisFormat()||i.axisFormat||"%Y-%m-%d"));const u=/^([1-9]\d*)(millisecond|second|minute|hour|day|week|month)$/.exec(a.db.getTickInterval()||i.tickInterval);if(u!==null){const f=u[1],m=u[2],h=a.db.getWeekday()||i.weekday;switch(m){case"millisecond":k.ticks(te.every(f));break;case"second":k.ticks($t.every(f));break;case"minute":k.ticks(Jt.every(f));break;case"hour":k.ticks(Kt.every(f));break;case"day":k.ticks(Qt.every(f));break;case"week":k.ticks(oe[h].every(f));break;case"month":k.ticks(Zt.every(f));break}}if(F.append("g").attr("class","grid").attr("transform","translate("+v+", "+(D-50)+")").call(k).selectAll("text").style("text-anchor","middle").attr("fill","#000").attr("stroke","none").attr("font-size",10).attr("dy","1em"),a.db.topAxisEnabled()||i.topAxis){let f=Ze(_).tickSize(-D+S+i.gridLineStartPadding).tickFormat(jt(a.db.getAxisFormat()||i.axisFormat||"%Y-%m-%d"));if(u!==null){const m=u[1],h=u[2],C=a.db.getWeekday()||i.weekday;switch(h){case"millisecond":f.ticks(te.every(m));break;case"second":f.ticks($t.every(m));break;case"minute":f.ticks(Jt.every(m));break;case"hour":f.ticks(Kt.every(m));break;case"day":f.ticks(Qt.every(m));break;case"week":f.ticks(oe[C].every(m));break;case"month":f.ticks(Zt.every(m));break}}F.append("g").attr("class","grid").attr("transform","translate("+v+", "+S+")").call(f).selectAll("text").style("text-anchor","middle").attr("fill","#000").attr("stroke","none").attr("font-size",10)}}l(X,"makeGrid");function G(v,S){let b=0;const D=Object.keys(w).map(k=>[k,w[k]]);F.append("g").selectAll("text").data(D).enter().append(function(k){const E=k[0].split(Ce.lineBreakRegex),u=-(E.length-1)/2,f=y.createElementNS("http://www.w3.org/2000/svg","text");f.setAttribute("dy",u+"em");for(const[m,h]of E.entries()){const C=y.createElementNS("http://www.w3.org/2000/svg","tspan");C.setAttribute("alignment-baseline","central"),C.setAttribute("x","10"),m>0&&C.setAttribute("dy","1em"),C.textContent=h,f.appendChild(C)}return f}).attr("x",10).attr("y",function(k,E){if(E>0)for(let u=0;u<E;u++)return b+=D[E-1][1],k[1]*v/2+b*v+S;else return k[1]*v/2+S}).attr("font-size",i.sectionFontSize).attr("class",function(k){for(const[E,u]of M.entries())if(k[0]===u)return"sectionTitle sectionTitle"+E%i.numberSectionStyles;return"sectionTitle"})}l(G,"vertLabels");function R(v,S,b,D){const k=a.db.getTodayMarker();if(k==="off")return;const E=F.append("g").attr("class","today"),u=new Date,f=E.append("line");f.attr("x1",_(u)+v).attr("x2",_(u)+v).attr("y1",i.titleTopMargin).attr("y2",D-i.titleTopMargin).attr("class","today"),k!==""&&f.attr("style",k.replace(/,/g,";"))}l(R,"drawToday");function V(v){const S={},b=[];for(let D=0,k=v.length;D<k;++D)Object.prototype.hasOwnProperty.call(S,v[D])||(S[v[D]]=!0,b.push(v[D]));return b}l(V,"checkUnique")},"draw"),aa={setConf:ta,draw:ra},ia=l(t=>`
  .mermaid-main-font {
    font-family: var(--mermaid-font-family, "trebuchet ms", verdana, arial, sans-serif);
  }

  .exclude-range {
    fill: ${t.excludeBkgColor};
  }

  .section {
    stroke: none;
    opacity: 0.2;
  }

  .section0 {
    fill: ${t.sectionBkgColor};
  }

  .section2 {
    fill: ${t.sectionBkgColor2};
  }

  .section1,
  .section3 {
    fill: ${t.altSectionBkgColor};
    opacity: 0.2;
  }

  .sectionTitle0 {
    fill: ${t.titleColor};
  }

  .sectionTitle1 {
    fill: ${t.titleColor};
  }

  .sectionTitle2 {
    fill: ${t.titleColor};
  }

  .sectionTitle3 {
    fill: ${t.titleColor};
  }

  .sectionTitle {
    text-anchor: start;
    font-family: var(--mermaid-font-family, "trebuchet ms", verdana, arial, sans-serif);
  }


  /* Grid and axis */

  .grid .tick {
    stroke: ${t.gridColor};
    opacity: 0.8;
    shape-rendering: crispEdges;
  }

  .grid .tick text {
    font-family: ${t.fontFamily};
    fill: ${t.textColor};
  }

  .grid path {
    stroke-width: 0;
  }


  /* Today line */

  .today {
    fill: none;
    stroke: ${t.todayLineColor};
    stroke-width: 2px;
  }


  /* Task styling */

  /* Default task */

  .task {
    stroke-width: 2;
  }

  .taskText {
    text-anchor: middle;
    font-family: var(--mermaid-font-family, "trebuchet ms", verdana, arial, sans-serif);
  }

  .taskTextOutsideRight {
    fill: ${t.taskTextDarkColor};
    text-anchor: start;
    font-family: var(--mermaid-font-family, "trebuchet ms", verdana, arial, sans-serif);
  }

  .taskTextOutsideLeft {
    fill: ${t.taskTextDarkColor};
    text-anchor: end;
  }


  /* Special case clickable */

  .task.clickable {
    cursor: pointer;
  }

  .taskText.clickable {
    cursor: pointer;
    fill: ${t.taskTextClickableColor} !important;
    font-weight: bold;
  }

  .taskTextOutsideLeft.clickable {
    cursor: pointer;
    fill: ${t.taskTextClickableColor} !important;
    font-weight: bold;
  }

  .taskTextOutsideRight.clickable {
    cursor: pointer;
    fill: ${t.taskTextClickableColor} !important;
    font-weight: bold;
  }


  /* Specific task settings for the sections*/

  .taskText0,
  .taskText1,
  .taskText2,
  .taskText3 {
    fill: ${t.taskTextColor};
  }

  .task0,
  .task1,
  .task2,
  .task3 {
    fill: ${t.taskBkgColor};
    stroke: ${t.taskBorderColor};
  }

  .taskTextOutside0,
  .taskTextOutside2
  {
    fill: ${t.taskTextOutsideColor};
  }

  .taskTextOutside1,
  .taskTextOutside3 {
    fill: ${t.taskTextOutsideColor};
  }


  /* Active task */

  .active0,
  .active1,
  .active2,
  .active3 {
    fill: ${t.activeTaskBkgColor};
    stroke: ${t.activeTaskBorderColor};
  }

  .activeText0,
  .activeText1,
  .activeText2,
  .activeText3 {
    fill: ${t.taskTextDarkColor} !important;
  }


  /* Completed task */

  .done0,
  .done1,
  .done2,
  .done3 {
    stroke: ${t.doneTaskBorderColor};
    fill: ${t.doneTaskBkgColor};
    stroke-width: 2;
  }

  .doneText0,
  .doneText1,
  .doneText2,
  .doneText3 {
    fill: ${t.taskTextDarkColor} !important;
  }


  /* Tasks on the critical line */

  .crit0,
  .crit1,
  .crit2,
  .crit3 {
    stroke: ${t.critBorderColor};
    fill: ${t.critBkgColor};
    stroke-width: 2;
  }

  .activeCrit0,
  .activeCrit1,
  .activeCrit2,
  .activeCrit3 {
    stroke: ${t.critBorderColor};
    fill: ${t.activeTaskBkgColor};
    stroke-width: 2;
  }

  .doneCrit0,
  .doneCrit1,
  .doneCrit2,
  .doneCrit3 {
    stroke: ${t.critBorderColor};
    fill: ${t.doneTaskBkgColor};
    stroke-width: 2;
    cursor: pointer;
    shape-rendering: crispEdges;
  }

  .milestone {
    transform: rotate(45deg) scale(0.8,0.8);
  }

  .milestoneText {
    font-style: italic;
  }
  .doneCritText0,
  .doneCritText1,
  .doneCritText2,
  .doneCritText3 {
    fill: ${t.taskTextDarkColor} !important;
  }

  .activeCritText0,
  .activeCritText1,
  .activeCritText2,
  .activeCritText3 {
    fill: ${t.taskTextDarkColor} !important;
  }

  .titleText {
    text-anchor: middle;
    font-size: 18px;
    fill: ${t.titleColor||t.textColor};
    font-family: var(--mermaid-font-family, "trebuchet ms", verdana, arial, sans-serif);
  }
`,"getStyles"),na=ia,ua={parser:gr,db:$r,renderer:aa,styles:na};export{ua as diagram};
