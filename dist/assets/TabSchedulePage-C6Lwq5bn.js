const __vite__fileDeps=["assets/web-wcQ-trBh.js","assets/index-DxqavktZ.js","assets/index-D-qxhZ3A.css","assets/swiper-vue-ClC_cqZI.js","assets/UserData-CEifgoE-.js","assets/ImgMgr-GqnYifhv.js","assets/swiper-vue-B1PwbnQR.css","assets/Icons-CAW4rpst.js"],__vite__mapDeps=i=>i.map(i=>__vite__fileDeps[i]);
import{d as Oe,w as be,o as k,c as N,a as f,b as d,e as K,r as le,F as ie,u as W,f as h,I as we,g as Ce,h as ae,t as H,n as De,i as B,j as $,k as Le,l as Ae,_ as Ie,m as Me,p as $e,q as Ue,s as xe,v as je,x as Re,y as Fe,z as He,A as Be,B as Ge,C as L,D as Ke,E as ye,G as ze,H as Ve,J as qe,K as We,L as Ne,M as Je,N as Ye,O as Qe,P as Xe,Q as Ze,R as et,S as tt}from"./index-DxqavktZ.js";import{I as Se,S as nt,a as ot,b as st,K as at}from"./swiper-vue-ClC_cqZI.js";import{i as lt}from"./Icons-CAW4rpst.js";import{I as it,U as G,C as rt,g as ct,a as dt,b as ut,c as ft,D as ht,S as mt,_ as pt}from"./UserData-CEifgoE-.js";const vt={key:0,class:"dot"},gt=Oe({__name:"CalendarTab",props:{name:String,slide:{type:Object,default:null},daySelectCallback:{type:Function,default:()=>{}},selectedDate:{type:Object,default:null},swiperRef:Object},setup(e){const t=e,o=()=>{var i;(i=t.swiperRef)==null||i.emit("update")};be(()=>t.slide,o,{deep:!0}),be(()=>t.selectedDate,o,{deep:!0});const u=["日","一","二","三","四","五","六"];return(i,l)=>{const r=h("ion-chip");return k(),N(W(Ae),{style:{height:"auto"}},{default:f(()=>[d(W(we),null,{default:f(()=>[(k(),K(ie,null,le(u,s=>d(W(Ce),{class:"ion-text-center",key:s},{default:f(()=>[ae(H(s),1)]),_:2},1024)),64))]),_:1}),(k(!0),K(ie,null,le(e.slide.weekArr,s=>(k(),N(W(we),{key:s},{default:f(()=>[(k(!0),K(ie,null,le(s,a=>(k(),N(W(Ce),{class:"ion-text-center ion-no-padding",onClick:m=>e.daySelectCallback(e.slide,a),key:a},{default:f(()=>[d(r,{class:De({vertical:!0,transparent:a.dt.unix()!==e.selectedDate.dt.unix()&&a.dt.unix()!==W(B)().startOf("day").unix(),selected:e.selectedDate&&a.dt.unix()===e.selectedDate.dt.unix(),today:a.dt.unix()===W(B)().startOf("day").unix()&&e.selectedDate&&a.dt.unix()!==e.selectedDate.dt.unix(),gray:a.dt.month()!==e.slide.month})},{default:f(()=>[$("span",null,[$("strong",null,H(a.dt.date()),1)]),a.events.length>0?(k(),K("span",vt)):Le("",!0)]),_:2},1032,["class"])]),_:2},1032,["onClick"]))),128))]),_:2},1024))),128))]),_:1})}}});/*! Capacitor: https://capacitorjs.com/ - MIT License */const bt=e=>{const t=new Map;t.set("web",{name:"web"});const o=e.CapacitorPlatforms||{currentPlatform:{name:"web"},platforms:t},u=(l,r)=>{o.platforms.set(l,r)},i=l=>{o.platforms.has(l)&&(o.currentPlatform=o.platforms.get(l))};return o.addPlatform=u,o.setPlatform=i,o},wt=e=>e.CapacitorPlatforms=bt(e),Te=wt(typeof globalThis<"u"?globalThis:typeof self<"u"?self:typeof window<"u"?window:typeof global<"u"?global:{});Te.addPlatform;Te.setPlatform;var X;(function(e){e.Unimplemented="UNIMPLEMENTED",e.Unavailable="UNAVAILABLE"})(X||(X={}));class ue extends Error{constructor(t,o,u){super(t),this.message=t,this.code=o,this.data=u}}const Ct=e=>{var t,o;return e!=null&&e.androidBridge?"android":!((o=(t=e==null?void 0:e.webkit)===null||t===void 0?void 0:t.messageHandlers)===null||o===void 0)&&o.bridge?"ios":"web"},yt=e=>{var t,o,u,i,l;const r=e.CapacitorCustomPlatform||null,s=e.Capacitor||{},a=s.Plugins=s.Plugins||{},m=e.CapacitorPlatforms,U=()=>r!==null?r.name:Ct(e),D=((t=m==null?void 0:m.currentPlatform)===null||t===void 0?void 0:t.getPlatform)||U,x=()=>D()!=="web",T=((o=m==null?void 0:m.currentPlatform)===null||o===void 0?void 0:o.isNativePlatform)||x,j=p=>{const b=q.get(p);return!!(b!=null&&b.platforms.has(D())||R(p))},Z=((u=m==null?void 0:m.currentPlatform)===null||u===void 0?void 0:u.isPluginAvailable)||j,E=p=>{var b;return(b=s.PluginHeaders)===null||b===void 0?void 0:b.find(A=>A.name===p)},R=((i=m==null?void 0:m.currentPlatform)===null||i===void 0?void 0:i.getPluginHeader)||E,z=p=>e.console.error(p),V=(p,b,A)=>Promise.reject("".concat(A,' does not have an implementation of "').concat(b,'".')),q=new Map,J=(p,b={})=>{const A=q.get(p);if(A)return console.warn('Capacitor plugin "'.concat(p,'" already registered. Cannot register plugins twice.')),A.proxy;const I=D(),M=R(p);let _;const re=async()=>(!_&&I in b?_=typeof b[I]=="function"?_=await b[I]():_=b[I]:r!==null&&!_&&"web"in b&&(_=typeof b.web=="function"?_=await b.web():_=b.web),_),ce=(C,w)=>{var P,y;if(M){const F=M==null?void 0:M.methods.find(n=>w===n.name);if(F)return F.rtype==="promise"?n=>s.nativePromise(p,w.toString(),n):(n,c)=>s.nativeCallback(p,w.toString(),n,c);if(C)return(P=C[w])===null||P===void 0?void 0:P.bind(C)}else{if(C)return(y=C[w])===null||y===void 0?void 0:y.bind(C);throw new ue('"'.concat(p,'" plugin is not implemented on ').concat(I),X.Unimplemented)}},Y=C=>{let w;const P=(...y)=>{const F=re().then(n=>{const c=ce(n,C);if(c){const v=c(...y);return w=v==null?void 0:v.remove,v}else throw new ue('"'.concat(p,".").concat(C,'()" is not implemented on ').concat(I),X.Unimplemented)});return C==="addListener"&&(F.remove=async()=>w()),F};return P.toString=()=>"".concat(C.toString(),"() { [capacitor code] }"),Object.defineProperty(P,"name",{value:C,writable:!1,configurable:!1}),P},te=Y("addListener"),ne=Y("removeListener"),S=(C,w)=>{const P=te({eventName:C},w),y=async()=>{const n=await P;ne({eventName:C,callbackId:n},w)},F=new Promise(n=>P.then(()=>n({remove:y})));return F.remove=async()=>{console.warn("Using addListener() without 'await' is deprecated."),await y()},F},g=new Proxy({},{get(C,w){switch(w){case"$$typeof":return;case"toJSON":return()=>({});case"addListener":return M?S:te;case"removeListener":return ne;default:return Y(w)}}});return a[p]=g,q.set(p,{name:p,proxy:g,platforms:new Set([...Object.keys(b),...M?[I]:[]])}),g},ee=((l=m==null?void 0:m.currentPlatform)===null||l===void 0?void 0:l.registerPlugin)||J;return s.convertFileSrc||(s.convertFileSrc=p=>p),s.getPlatform=D,s.handleError=z,s.isNativePlatform=T,s.isPluginAvailable=Z,s.pluginMethodNoop=V,s.registerPlugin=ee,s.Exception=ue,s.DEBUG=!!s.DEBUG,s.isLoggingEnabled=!!s.isLoggingEnabled,s.platform=s.getPlatform(),s.isNative=s.isNativePlatform(),s},St=e=>e.Capacitor=yt(e),de=St(typeof globalThis<"u"?globalThis:typeof self<"u"?self:typeof window<"u"?window:typeof global<"u"?global:{}),fe=de.registerPlugin;de.Plugins;class Ee{constructor(t){this.listeners={},this.retainedEventArguments={},this.windowListeners={},t&&(console.warn('Capacitor WebPlugin "'.concat(t.name,'" config object was deprecated in v3 and will be removed in v4.')),this.config=t)}addListener(t,o){let u=!1;this.listeners[t]||(this.listeners[t]=[],u=!0),this.listeners[t].push(o);const l=this.windowListeners[t];l&&!l.registered&&this.addWindowListener(l),u&&this.sendRetainedArgumentsForEvent(t);const r=async()=>this.removeListener(t,o);return Promise.resolve({remove:r})}async removeAllListeners(){this.listeners={};for(const t in this.windowListeners)this.removeWindowListener(this.windowListeners[t]);this.windowListeners={}}notifyListeners(t,o,u){const i=this.listeners[t];if(!i){if(u){let l=this.retainedEventArguments[t];l||(l=[]),l.push(o),this.retainedEventArguments[t]=l}return}i.forEach(l=>l(o))}hasListeners(t){return!!this.listeners[t].length}registerWindowListener(t,o){this.windowListeners[o]={registered:!1,windowEventName:t,pluginEventName:o,handler:u=>{this.notifyListeners(o,u)}}}unimplemented(t="not implemented"){return new de.Exception(t,X.Unimplemented)}unavailable(t="not available"){return new de.Exception(t,X.Unavailable)}async removeListener(t,o){const u=this.listeners[t];if(!u)return;const i=u.indexOf(o);this.listeners[t].splice(i,1),this.listeners[t].length||this.removeWindowListener(this.windowListeners[t])}addWindowListener(t){window.addEventListener(t.windowEventName,t.handler),t.registered=!0}removeWindowListener(t){t&&(window.removeEventListener(t.windowEventName,t.handler),t.registered=!1)}sendRetainedArgumentsForEvent(t){const o=this.retainedEventArguments[t];o&&(delete this.retainedEventArguments[t],o.forEach(u=>{this.notifyListeners(t,u)}))}}const ke=e=>encodeURIComponent(e).replace(/%(2[346B]|5E|60|7C)/g,decodeURIComponent).replace(/[()]/g,escape),_e=e=>e.replace(/(%[\dA-F]{2})+/gi,decodeURIComponent);class kt extends Ee{async getCookies(){const t=document.cookie,o={};return t.split(";").forEach(u=>{if(u.length<=0)return;let[i,l]=u.replace(/=/,"CAP_COOKIE").split("CAP_COOKIE");i=_e(i).trim(),l=_e(l).trim(),o[i]=l}),o}async setCookie(t){try{const o=ke(t.key),u=ke(t.value),i="; expires=".concat((t.expires||"").replace("expires=","")),l=(t.path||"/").replace("path=",""),r=t.url!=null&&t.url.length>0?"domain=".concat(t.url):"";document.cookie="".concat(o,"=").concat(u||"").concat(i,"; path=").concat(l,"; ").concat(r,";")}catch(o){return Promise.reject(o)}}async deleteCookie(t){try{document.cookie="".concat(t.key,"=; Max-Age=0")}catch(o){return Promise.reject(o)}}async clearCookies(){try{const t=document.cookie.split(";")||[];for(const o of t)document.cookie=o.replace(/^ +/,"").replace(/=.*/,"=;expires=".concat(new Date().toUTCString(),";path=/"))}catch(t){return Promise.reject(t)}}async clearAllCookies(){try{await this.clearCookies()}catch(t){return Promise.reject(t)}}}fe("CapacitorCookies",{web:()=>new kt});const _t=async e=>new Promise((t,o)=>{const u=new FileReader;u.onload=()=>{const i=u.result;t(i.indexOf(",")>=0?i.split(",")[1]:i)},u.onerror=i=>o(i),u.readAsDataURL(e)}),Pt=(e={})=>{const t=Object.keys(e);return Object.keys(e).map(i=>i.toLocaleLowerCase()).reduce((i,l,r)=>(i[l]=e[t[r]],i),{})},Ot=(e,t=!0)=>e?Object.entries(e).reduce((u,i)=>{const[l,r]=i;let s,a;return Array.isArray(r)?(a="",r.forEach(m=>{s=t?encodeURIComponent(m):m,a+="".concat(l,"=").concat(s,"&")}),a.slice(0,-1)):(s=t?encodeURIComponent(r):r,a="".concat(l,"=").concat(s)),"".concat(u,"&").concat(a)},"").substr(1):null,Dt=(e,t={})=>{const o=Object.assign({method:e.method||"GET",headers:e.headers},t),i=Pt(e.headers)["content-type"]||"";if(typeof e.data=="string")o.body=e.data;else if(i.includes("application/x-www-form-urlencoded")){const l=new URLSearchParams;for(const[r,s]of Object.entries(e.data||{}))l.set(r,s);o.body=l.toString()}else if(i.includes("multipart/form-data")||e.data instanceof FormData){const l=new FormData;if(e.data instanceof FormData)e.data.forEach((s,a)=>{l.append(a,s)});else for(const s of Object.keys(e.data))l.append(s,e.data[s]);o.body=l;const r=new Headers(o.headers);r.delete("content-type"),o.headers=r}else(i.includes("application/json")||typeof e.data=="object")&&(o.body=JSON.stringify(e.data));return o};class Lt extends Ee{async request(t){const o=Dt(t,t.webFetchExtra),u=Ot(t.params,t.shouldEncodeUrlParams),i=u?"".concat(t.url,"?").concat(u):t.url,l=await fetch(i,o),r=l.headers.get("content-type")||"";let{responseType:s="text"}=l.ok?t:{};r.includes("application/json")&&(s="json");let a,m;switch(s){case"arraybuffer":case"blob":m=await l.blob(),a=await _t(m);break;case"json":a=await l.json();break;case"document":case"text":default:a=await l.text()}const U={};return l.headers.forEach((D,x)=>{U[x]=D}),{data:a,headers:U,status:l.status,url:l.url}}async get(t){return this.request(Object.assign(Object.assign({},t),{method:"GET"}))}async post(t){return this.request(Object.assign(Object.assign({},t),{method:"POST"}))}async put(t){return this.request(Object.assign(Object.assign({},t),{method:"PUT"}))}async patch(t){return this.request(Object.assign(Object.assign({},t),{method:"PATCH"}))}async delete(t){return this.request(Object.assign(Object.assign({},t),{method:"DELETE"}))}}fe("CapacitorHttp",{web:()=>new Lt});var Pe;(function(e){e[e.Sunday=1]="Sunday",e[e.Monday=2]="Monday",e[e.Tuesday=3]="Tuesday",e[e.Wednesday=4]="Wednesday",e[e.Thursday=5]="Thursday",e[e.Friday=6]="Friday",e[e.Saturday=7]="Saturday"})(Pe||(Pe={}));const Tt=fe("LocalNotifications",{web:()=>Ie(()=>import("./web-wcQ-trBh.js"),__vite__mapDeps([0,1,2,3,4,5,6,7])).then(e=>new e.LocalNotificationsWeb)}),Et=Oe({components:{IonAccordion:Me,IonAccordionGroup:$e,IonCheckbox:Ue,IonFab:xe,IonFabButton:je,IonicSlides:Se,IonItemOption:Re,IonItemOptions:Fe,IonItemSliding:He,IonRefresher:Be,IonRefresherContent:Ge,CalenderTab:gt,SchedulePop:nt,Swiper:ot,SwiperSlide:st,Icon:it},setup(){const e=L(new ft);let t=B().startOf("day"),o,u=0;const i=L([{},{},{}]),l=L(),r=L(),s=L(!0),a=L(),m=L(),U=L(),D=L(),x=L(!1),T=L({isOpen:!1,duration:3e3,text:""}),j=L({isOpen:!1,data:void 0,text:""}),Z=[{text:"Cancel",role:"cancel"},{text:"OK",role:"confirm"}],E=()=>{s.value?i.value=[G.createWeekData(t.subtract(1,"weeks"),e.value,a),G.createWeekData(t,e.value,a),G.createWeekData(t.add(1,"weeks"),e.value,a)]:i.value=[G.createMonthData(t.subtract(1,"months"),e.value,a),G.createMonthData(t,e.value,a),G.createMonthData(t.add(1,"months"),e.value,a)]},R=()=>{const n=i.value[1];if(!n.weekArr){console.warn("no weekArr");return}a.value=void 0;const c=B().startOf("day");if(!a.value){e:for(const v of n.weekArr)for(const O of v)if(O.dt.unix()==c.unix()){a.value=O;break e}}if(!a.value){e:for(const v of n.weekArr)for(const O of v)if(O.dt.unix()==t.unix()){a.value=O;break e}}a.value||(a.value=n.weekArr[0][0])},z=()=>{var n;return B().startOf("day").unix()==((n=a.value)==null?void 0:n.dt.unix())};Ke(()=>{ye(1).then(n=>{e.value=G.parseUserData(n),console.log("getSave",e.value),E(),R(),setTimeout(()=>{var c;(c=r==null?void 0:r.value)==null||c.update()},100)}).catch(n=>{console.log("getSave",n),T.value.isOpen=!0,T.value.text=JSON.stringify(n)})});const V=()=>{et(e.value.id,e.value.name,JSON.stringify(e.value)).then(n=>{console.log("doSaveUserData",n)}).catch(n=>{console.log("doSaveUserData",n)})},q=()=>{t=B().startOf("day"),a.value=new ht(B().startOf("day")),E()},J=()=>{var n;(n=r==null?void 0:r.value)==null||n.update()},ee=()=>{console.log(JSON.stringify(e.value)),Tt.schedule({notifications:[{title:"On sale",body:"Widgets are 10% off. Act fast!",id:1,schedule:{at:new Date(Date.now()+1e3*5)},sound:void 0,attachments:void 0,actionTypeId:"",extra:null}]})},p=n=>{E(),n.slideTo(1,0,!1),n.update(),R()},b=n=>{s.value?t=t.add(1,"weeks").startOf("week"):t=t.add(1,"months").startOf("month"),p(n)},A=n=>{s.value?t=t.subtract(1,"weeks").startOf("week"):t=t.subtract(1,"months").startOf("month"),p(n)},I=n=>{r.value=n,n.slideTo(1,0,!1)},M=(n,c)=>{n.month!=c.dt.month()&&(n.year*100+n.month<c.dt.year()*100+c.dt.month()?r.value.slideNext():r.value.slidePrev()),a.value=c},_=()=>{s.value=!s.value,E(),setTimeout(()=>{r.value.update()},100)};return{icons:lt,ColorOptions:rt,getColorOptions:ct,getPriorityOptions:dt,getGroupOptions:ut,addCircleOutline:ze,alarmOutline:Ve,chevronDown:qe,chevronUp:We,ellipseOutline:Ne,list:Je,listOutline:Ye,swapVertical:Qe,trashOutline:Xe,slideArr:i,curScheduleList:l,swiperRef:r,bFold:s,selectedDate:a,scheduleModal:m,scheduleModalData:U,scheduleSave:D,isScheduleModalOpen:x,toastData:T,userData:e,currentDate:t,pTouch:o,lstTs:u,alertButtons:Z,scheduleDelConfirm:j,countFinishedSubtask:n=>{var c;try{return(c=n==null?void 0:n.subtasks)==null?void 0:c.filter(v=>{var O,Q,oe,se;return(((Q=(O=a.value)==null?void 0:O.save[n.id])==null?void 0:Q.subtasks)&&((se=(oe=a.value)==null?void 0:oe.save[n.id])==null?void 0:se.subtasks[v.id])||0)===1}).length}catch(v){return console.log("countFinishedSubtask",v),0}},IonicSlides:Se,updateScheduleData:E,Keyboard:at,btnTodayClk:q,btnSortClk:J,onSlideChangeNext:b,onSlideChangePre:A,setSwiperInstance:I,onDaySelected:M,btnCalendarFoldClk:_,onScheduleListTouchStart:n=>{o=n.touches[0]},onScheduleListTouchMove:n=>{if(B().valueOf()-u<300)return;const v=n.touches[0].clientY-o.clientY;Math.abs(v)>20&&(u=B().valueOf(),v>0===s.value&&_())},handleRefresh:n=>{ye(1).then(c=>{console.log("handleRefresh",c),T.value.isOpen=!0,T.value.text="更新成功",n.target.complete()}).catch(c=>{console.log("handleRefresh",c),T.value.isOpen=!0,T.value.text=JSON.stringify(c),n.target.complete()})},scheduleChecked:n=>{var c;return((c=a.value.save[n])==null?void 0:c.state)===1},onScheduleCheckboxChange:(n,c,v)=>{if(c){const O=c.save[v]||new mt;O.state=n.detail.checked?1:0,c.save[v]=O,Ze(()=>{c.events.sort((Q,oe)=>{var me,pe,ve,ge;const se=((me=c.save[Q.id])==null?void 0:me.state)||0,he=((pe=c.save[oe.id])==null?void 0:pe.state)||0;return se===he?((ve=Q.id)!=null?ve:0)-((ge=oe.id)!=null?ge:0):se-he})}),V()}},btnScheduleClk:(n,c)=>{var v;x.value=!0,U.value=c,D.value=(v=a.value)==null?void 0:v.save[c.id],n.stopPropagation()},btnScheduleAlarmClk:()=>{console.log("btnScheduleAlarmClk")},btnScheduleRemoveClk:(n,c)=>{j.value.isOpen=!0,j.value.data=c,j.value.text="del "+c.title+"?"},onScheduleModalDismiss:n=>{if(x.value=!1,n.detail.role==="backdrop")return;const[c,v]=n.detail.data,O=a.value.dt;G.updateSchedularData(e.value,c,v,O,n.detail.role)&&(E(),V())},onDelSchedulerConfirm:n=>{if(j.value.isOpen=!1,n.detail.role==="confirm"){const c=e.value.schedules.findIndex(v=>v.id===j.value.data.id);c!==-1&&e.value.schedules.splice(c,1),E(),V()}},btnAddScheduleClk:()=>{U.value=void 0,D.value=void 0,x.value=!0},btnTestClk:ee,isToday:z}},methods:{}}),At={key:0},It={key:1},Mt={style:{"margin-right":"8px"},class:"gray"},$t={slot:"content"},Ut=["onClick"],xt={class:"flex"},jt={class:"schedule-lb-sub"},Rt={class:"schedule-lb-group"};function Ft(e,t,o,u,i,l){const r=h("ion-icon"),s=h("ion-button"),a=h("ion-buttons"),m=h("ion-title"),U=h("ion-toolbar"),D=h("ion-header"),x=h("CalenderTab"),T=h("swiper-slide"),j=h("swiper"),Z=h("ion-refresher-content"),E=h("ion-refresher"),R=h("ion-label"),z=h("ion-item"),V=h("ion-checkbox"),q=h("Icon"),J=h("ion-item-option"),ee=h("ion-item-options"),p=h("ion-item-sliding"),b=h("ion-list"),A=h("ion-accordion"),I=h("ion-accordion-group"),M=h("ion-content"),_=h("SchedulePop"),re=h("ion-alert"),ce=h("ion-toast"),Y=h("ion-fab-button"),te=h("ion-fab"),ne=h("ion-page");return k(),N(ne,null,{default:f(()=>[d(D,null,{default:f(()=>[d(U,null,{default:f(()=>[d(a,{slot:"start"},{default:f(()=>[d(s,null,{default:f(()=>[d(r,{color:"default",icon:e.list},null,8,["icon"])]),_:1})]),_:1}),d(m,{class:"ion-text-center"},{default:f(()=>[e.selectedDate?(k(),K("h3",At,H(e.selectedDate.dt.format("YY年MM月")),1)):(k(),K("h3",It,"日历"))]),_:1}),d(a,{slot:"end"},{default:f(()=>[e.isToday()?Le("",!0):(k(),N(s,{key:0,style:{position:"absolute",right:"50px"},onClick:e.btnTodayClk},{default:f(()=>t[4]||(t[4]=[ae(" 今 ")])),_:1},8,["onClick"])),d(s,{onClick:e.btnSortClk},{default:f(()=>[d(r,{icon:e.swapVertical,class:"button-native"},null,8,["icon"])]),_:1},8,["onClick"])]),_:1})]),_:1})]),_:1}),d(M,{"scroll-y":!1},{default:f(()=>[d(j,{onSlideNextTransitionEnd:e.onSlideChangeNext,onSlidePrevTransitionEnd:e.onSlideChangePre,onSwiper:e.setSwiperInstance,"centered-slides":!0,autoHeight:!0,modules:[e.IonicSlides,e.Keyboard],keyboard:!0},{default:f(()=>[(k(!0),K(ie,null,le(e.slideArr,(S,g)=>(k(),N(T,{key:g},{default:f(()=>[d(x,{slide:S,daySelectCallback:e.onDaySelected,selectedDate:e.selectedDate,swiperRef:e.swiperRef},null,8,["slide","daySelectCallback","selectedDate","swiperRef"])]),_:2},1024))),128))]),_:1},8,["onSlideNextTransitionEnd","onSlidePrevTransitionEnd","onSwiper","modules"]),d(s,{color:"light",expand:"full",fill:"clear",class:"ion-no-margin ion-no-padding",style:{"min-height":"auto"},onClick:t[0]||(t[0]=S=>e.btnCalendarFoldClk())},{default:f(()=>[d(r,{icon:e.bFold?e.chevronDown:e.chevronUp,color:"primary"},null,8,["icon"])]),_:1}),d(M,{color:"light",onTouchmove:e.onScheduleListTouchMove,onTouchstart:e.onScheduleListTouchStart},{default:f(()=>[d(E,{slot:"fixed",onIonRefresh:t[1]||(t[1]=S=>e.handleRefresh(S))},{default:f(()=>[d(Z)]),_:1}),d(I,{multiple:!0,value:["schedule","goals"]},{default:f(()=>[d(A,{value:"schedule"},{default:f(()=>[d(z,{slot:"header",color:"light",class:"schedule-group-item"},{default:f(()=>{var S;return[d(R,null,{default:f(()=>{var g;return[ae(H((g=e.selectedDate)==null?void 0:g.dt.format("MM-DD")),1)]}),_:1}),$("p",Mt,H((S=e.selectedDate)==null?void 0:S.events.length),1)]}),_:1}),$("div",$t,[d(b,{inset:!0,lines:"full",mode:"ios",ref:"curScheduleList",class:"schedule-list"},{default:f(()=>{var S;return[(k(!0),K(ie,null,le((S=e.selectedDate)==null?void 0:S.events,(g,C)=>(k(),N(p,{key:C},{default:f(()=>[d(z,null,{default:f(()=>{var w,P;return[d(V,{style:{"--size":"26px","padding-right":"5px"},slot:"start",checked:e.scheduleChecked(g.id),onIonChange:y=>e.onScheduleCheckboxChange(y,e.selectedDate,g.id)},null,8,["checked","onIonChange"]),$("div",{onClick:y=>e.btnScheduleClk(y,g),class:"scheduleItem"},[d(R,{class:De([{"text-line-through":((P=(w=e.selectedDate)==null?void 0:w.save[g.id])==null?void 0:P.state)===1},"scheduleItemLabel"])},{default:f(()=>{var y;return[$("h2",null,H(g.title),1),$("div",xt,[$("p",jt,[d(r,{icon:e.listOutline,style:{position:"relative",top:"3px"}},null,8,["icon"]),ae(" "+H(e.countFinishedSubtask(g))+" / "+H((y=g==null?void 0:g.subtasks)==null?void 0:y.length),1)]),$("p",Rt,H(e.getGroupOptions(g.groupId).label),1)])]}),_:2},1032,["class"]),$("span",{class:"v-dot",style:tt({"background-color":e.getColorOptions(g.color).tag,"margin-left":"10px"})},null,4),d(q,{icon:e.getPriorityOptions(g.priority).icon,height:"36",color:e.getPriorityOptions(g.priority).color},null,8,["icon","color"])],8,Ut)]}),_:2},1024),d(ee,{side:"end"},{default:f(()=>[d(J,{onClick:e.btnScheduleAlarmClk},{default:f(()=>[d(r,{icon:e.alarmOutline},null,8,["icon"])]),_:1},8,["onClick"]),d(J,{color:"danger",onClick:w=>e.btnScheduleRemoveClk(w,g)},{default:f(()=>[d(r,{icon:e.trashOutline},null,8,["icon"])]),_:2},1032,["onClick"])]),_:2},1024)]),_:2},1024))),128))]}),_:1},512)])]),_:1}),d(A,{value:"goals"},{default:f(()=>[d(z,{slot:"header",color:"light",class:"schedule-group-item"},{default:f(()=>[d(R,null,{default:f(()=>t[5]||(t[5]=[ae("里程碑")])),_:1})]),_:1}),t[6]||(t[6]=$("div",{class:"ion-padding",slot:"content"},"Content",-1))]),_:1})]),_:1})]),_:1},8,["onTouchmove","onTouchstart"]),d(_,{id:"pop-modal",ref:"scheduleModal","is-open":e.isScheduleModalOpen,modal:e.scheduleModal,schedule:e.scheduleModalData,save:e.scheduleSave,onWillDismiss:e.onScheduleModalDismiss},null,8,["is-open","modal","schedule","save","onWillDismiss"]),d(re,{"is-open":e.scheduleDelConfirm.isOpen,header:"Confirm!",buttons:e.alertButtons,"sub-header":e.scheduleDelConfirm.text,onDidDismiss:t[2]||(t[2]=S=>e.onDelSchedulerConfirm(S))},null,8,["is-open","buttons","sub-header"]),d(ce,{"is-open":e.toastData.isOpen,message:e.toastData.text,duration:e.toastData.duration,onDidDismiss:t[3]||(t[3]=()=>e.toastData.isOpen=!1)},null,8,["is-open","message","duration"])]),_:1}),d(te,{slot:"fixed",vertical:"bottom",horizontal:"end"},{default:f(()=>[d(Y,{onClick:e.btnAddScheduleClk},{default:f(()=>[d(r,{icon:e.addCircleOutline,size:"large"},null,8,["icon"])]),_:1},8,["onClick"])]),_:1})]),_:1})}const Ht=pt(Et,[["render",Ft],["__scopeId","data-v-23493bc3"]]),Vt=Object.freeze(Object.defineProperty({__proto__:null,default:Ht},Symbol.toStringTag,{value:"Module"}));export{Vt as T,Ee as W};