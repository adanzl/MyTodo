const __vite__fileDeps=["assets/web-CErII-n0.js","assets/index-CitHbwVn.js","assets/index-fq9C_lx_.css","assets/swiper-vue-npxDqG0O.js","assets/UserData-B9K-9VU0.js","assets/ImgMgr-CX4hNcG1.js","assets/swiper-vue-BpIj2JMU.css","assets/Icons-CAW4rpst.js"],__vite__mapDeps=i=>i.map(i=>__vite__fileDeps[i]);
import{d as Pe,w as be,r as h,o as k,c as N,a as f,b as u,e as K,f as ie,F as re,u as q,I as we,g as Ce,h as ae,t as x,n as De,i as G,j as $,k as Oe,l as Ee,_ as Ae,m as Ie,p as Me,q as $e,s as Ue,v as je,x as xe,y as Re,z as Fe,A as He,B as Be,C as T,D as Ge,E as Ke,G as Ve,H as ze,J as We,K as qe,L as Ne,M as Je,N as Ye,O as Qe,P as Xe,Q as Ze,R as et,S as tt,T as nt,U as ot,V as st,W as at,X as it,Y as rt,Z as lt}from"./index-CitHbwVn.js";import{I as ye,S as dt,a as ct,b as ut,K as ft}from"./swiper-vue-npxDqG0O.js";import{i as ht}from"./Icons-CAW4rpst.js";import{U as mt,a as B,D as pt,S as vt}from"./UserData-B9K-9VU0.js";const gt={key:0,class:"dot"},bt=Pe({__name:"CalendarTab",props:{name:String,slide:{type:Object,default:null},daySelectCallback:{type:Function,default:()=>{}},selectedDate:{type:Object,default:null},swiperRef:Object},setup(e){const t=e,n=()=>{var r;(r=t.swiperRef)==null||r.emit("update")};be(()=>t.slide,n,{deep:!0}),be(()=>t.selectedDate,n,{deep:!0});const l=["日","一","二","三","四","五","六"];return(r,a)=>{const c=h("ion-chip");return k(),N(q(Ee),{style:{height:"auto"}},{default:f(()=>[u(q(we),null,{default:f(()=>[(k(),K(re,null,ie(l,s=>u(q(Ce),{class:"ion-text-center",key:s},{default:f(()=>[ae(x(s),1)]),_:2},1024)),64))]),_:1}),(k(!0),K(re,null,ie(e.slide.weekArr,s=>(k(),N(q(we),{key:s},{default:f(()=>[(k(!0),K(re,null,ie(s,i=>(k(),N(q(Ce),{class:"ion-text-center ion-no-padding",onClick:p=>e.daySelectCallback(e.slide,i),key:i},{default:f(()=>[u(c,{class:De({vertical:!0,transparent:i.dt.unix()!==e.selectedDate.dt.unix()&&i.dt.unix()!==q(G)().startOf("day").unix(),selected:e.selectedDate&&i.dt.unix()===e.selectedDate.dt.unix(),today:i.dt.unix()===q(G)().startOf("day").unix()&&e.selectedDate&&i.dt.unix()!==e.selectedDate.dt.unix(),gray:i.dt.month()!==e.slide.month})},{default:f(()=>[$("span",null,[$("strong",null,x(i.dt.date()),1)]),i.events.length>0?(k(),K("span",gt)):Oe("",!0)]),_:2},1032,["class"])]),_:2},1032,["onClick"]))),128))]),_:2},1024))),128))]),_:1})}}});/*! Capacitor: https://capacitorjs.com/ - MIT License */const wt=e=>{const t=new Map;t.set("web",{name:"web"});const n=e.CapacitorPlatforms||{currentPlatform:{name:"web"},platforms:t},l=(a,c)=>{n.platforms.set(a,c)},r=a=>{n.platforms.has(a)&&(n.currentPlatform=n.platforms.get(a))};return n.addPlatform=l,n.setPlatform=r,n},Ct=e=>e.CapacitorPlatforms=wt(e),Le=Ct(typeof globalThis<"u"?globalThis:typeof self<"u"?self:typeof window<"u"?window:typeof global<"u"?global:{});Le.addPlatform;Le.setPlatform;var X;(function(e){e.Unimplemented="UNIMPLEMENTED",e.Unavailable="UNAVAILABLE"})(X||(X={}));class ue extends Error{constructor(t,n,l){super(t),this.message=t,this.code=n,this.data=l}}const yt=e=>{var t,n;return e!=null&&e.androidBridge?"android":!((n=(t=e==null?void 0:e.webkit)===null||t===void 0?void 0:t.messageHandlers)===null||n===void 0)&&n.bridge?"ios":"web"},St=e=>{var t,n,l,r,a;const c=e.CapacitorCustomPlatform||null,s=e.Capacitor||{},i=s.Plugins=s.Plugins||{},p=e.CapacitorPlatforms,U=()=>c!==null?c.name:yt(e),L=((t=p==null?void 0:p.currentPlatform)===null||t===void 0?void 0:t.getPlatform)||U,j=()=>L()!=="web",V=((n=p==null?void 0:p.currentPlatform)===null||n===void 0?void 0:n.isNativePlatform)||j,_=v=>{const b=W.get(v);return!!(b!=null&&b.platforms.has(L())||R(v))},Z=((l=p==null?void 0:p.currentPlatform)===null||l===void 0?void 0:l.isPluginAvailable)||_,E=v=>{var b;return(b=s.PluginHeaders)===null||b===void 0?void 0:b.find(A=>A.name===v)},R=((r=p==null?void 0:p.currentPlatform)===null||r===void 0?void 0:r.getPluginHeader)||E,F=v=>e.console.error(v),z=(v,b,A)=>Promise.reject("".concat(A,' does not have an implementation of "').concat(b,'".')),W=new Map,J=(v,b={})=>{const A=W.get(v);if(A)return console.warn('Capacitor plugin "'.concat(v,'" already registered. Cannot register plugins twice.')),A.proxy;const I=L(),M=R(v);let P;const le=async()=>(!P&&I in b?P=typeof b[I]=="function"?P=await b[I]():P=b[I]:c!==null&&!P&&"web"in b&&(P=typeof b.web=="function"?P=await b.web():P=b.web),P),de=(C,w)=>{var D,S;if(M){const H=M==null?void 0:M.methods.find(o=>w===o.name);if(H)return H.rtype==="promise"?o=>s.nativePromise(v,w.toString(),o):(o,d)=>s.nativeCallback(v,w.toString(),o,d);if(C)return(D=C[w])===null||D===void 0?void 0:D.bind(C)}else{if(C)return(S=C[w])===null||S===void 0?void 0:S.bind(C);throw new ue('"'.concat(v,'" plugin is not implemented on ').concat(I),X.Unimplemented)}},Y=C=>{let w;const D=(...S)=>{const H=le().then(o=>{const d=de(o,C);if(d){const m=d(...S);return w=m==null?void 0:m.remove,m}else throw new ue('"'.concat(v,".").concat(C,'()" is not implemented on ').concat(I),X.Unimplemented)});return C==="addListener"&&(H.remove=async()=>w()),H};return D.toString=()=>"".concat(C.toString(),"() { [capacitor code] }"),Object.defineProperty(D,"name",{value:C,writable:!1,configurable:!1}),D},te=Y("addListener"),ne=Y("removeListener"),y=(C,w)=>{const D=te({eventName:C},w),S=async()=>{const o=await D;ne({eventName:C,callbackId:o},w)},H=new Promise(o=>D.then(()=>o({remove:S})));return H.remove=async()=>{console.warn("Using addListener() without 'await' is deprecated."),await S()},H},g=new Proxy({},{get(C,w){switch(w){case"$$typeof":return;case"toJSON":return()=>({});case"addListener":return M?y:te;case"removeListener":return ne;default:return Y(w)}}});return i[v]=g,W.set(v,{name:v,proxy:g,platforms:new Set([...Object.keys(b),...M?[I]:[]])}),g},ee=((a=p==null?void 0:p.currentPlatform)===null||a===void 0?void 0:a.registerPlugin)||J;return s.convertFileSrc||(s.convertFileSrc=v=>v),s.getPlatform=L,s.handleError=F,s.isNativePlatform=V,s.isPluginAvailable=Z,s.pluginMethodNoop=z,s.registerPlugin=ee,s.Exception=ue,s.DEBUG=!!s.DEBUG,s.isLoggingEnabled=!!s.isLoggingEnabled,s.platform=s.getPlatform(),s.isNative=s.isNativePlatform(),s},kt=e=>e.Capacitor=St(e),ce=kt(typeof globalThis<"u"?globalThis:typeof self<"u"?self:typeof window<"u"?window:typeof global<"u"?global:{}),fe=ce.registerPlugin;ce.Plugins;class Te{constructor(t){this.listeners={},this.retainedEventArguments={},this.windowListeners={},t&&(console.warn('Capacitor WebPlugin "'.concat(t.name,'" config object was deprecated in v3 and will be removed in v4.')),this.config=t)}addListener(t,n){let l=!1;this.listeners[t]||(this.listeners[t]=[],l=!0),this.listeners[t].push(n);const a=this.windowListeners[t];a&&!a.registered&&this.addWindowListener(a),l&&this.sendRetainedArgumentsForEvent(t);const c=async()=>this.removeListener(t,n);return Promise.resolve({remove:c})}async removeAllListeners(){this.listeners={};for(const t in this.windowListeners)this.removeWindowListener(this.windowListeners[t]);this.windowListeners={}}notifyListeners(t,n,l){const r=this.listeners[t];if(!r){if(l){let a=this.retainedEventArguments[t];a||(a=[]),a.push(n),this.retainedEventArguments[t]=a}return}r.forEach(a=>a(n))}hasListeners(t){return!!this.listeners[t].length}registerWindowListener(t,n){this.windowListeners[n]={registered:!1,windowEventName:t,pluginEventName:n,handler:l=>{this.notifyListeners(n,l)}}}unimplemented(t="not implemented"){return new ce.Exception(t,X.Unimplemented)}unavailable(t="not available"){return new ce.Exception(t,X.Unavailable)}async removeListener(t,n){const l=this.listeners[t];if(!l)return;const r=l.indexOf(n);this.listeners[t].splice(r,1),this.listeners[t].length||this.removeWindowListener(this.windowListeners[t])}addWindowListener(t){window.addEventListener(t.windowEventName,t.handler),t.registered=!0}removeWindowListener(t){t&&(window.removeEventListener(t.windowEventName,t.handler),t.registered=!1)}sendRetainedArgumentsForEvent(t){const n=this.retainedEventArguments[t];n&&(delete this.retainedEventArguments[t],n.forEach(l=>{this.notifyListeners(t,l)}))}}const Se=e=>encodeURIComponent(e).replace(/%(2[346B]|5E|60|7C)/g,decodeURIComponent).replace(/[()]/g,escape),ke=e=>e.replace(/(%[\dA-F]{2})+/gi,decodeURIComponent);class _t extends Te{async getCookies(){const t=document.cookie,n={};return t.split(";").forEach(l=>{if(l.length<=0)return;let[r,a]=l.replace(/=/,"CAP_COOKIE").split("CAP_COOKIE");r=ke(r).trim(),a=ke(a).trim(),n[r]=a}),n}async setCookie(t){try{const n=Se(t.key),l=Se(t.value),r="; expires=".concat((t.expires||"").replace("expires=","")),a=(t.path||"/").replace("path=",""),c=t.url!=null&&t.url.length>0?"domain=".concat(t.url):"";document.cookie="".concat(n,"=").concat(l||"").concat(r,"; path=").concat(a,"; ").concat(c,";")}catch(n){return Promise.reject(n)}}async deleteCookie(t){try{document.cookie="".concat(t.key,"=; Max-Age=0")}catch(n){return Promise.reject(n)}}async clearCookies(){try{const t=document.cookie.split(";")||[];for(const n of t)document.cookie=n.replace(/^ +/,"").replace(/=.*/,"=;expires=".concat(new Date().toUTCString(),";path=/"))}catch(t){return Promise.reject(t)}}async clearAllCookies(){try{await this.clearCookies()}catch(t){return Promise.reject(t)}}}fe("CapacitorCookies",{web:()=>new _t});const Pt=async e=>new Promise((t,n)=>{const l=new FileReader;l.onload=()=>{const r=l.result;t(r.indexOf(",")>=0?r.split(",")[1]:r)},l.onerror=r=>n(r),l.readAsDataURL(e)}),Dt=(e={})=>{const t=Object.keys(e);return Object.keys(e).map(r=>r.toLocaleLowerCase()).reduce((r,a,c)=>(r[a]=e[t[c]],r),{})},Ot=(e,t=!0)=>e?Object.entries(e).reduce((l,r)=>{const[a,c]=r;let s,i;return Array.isArray(c)?(i="",c.forEach(p=>{s=t?encodeURIComponent(p):p,i+="".concat(a,"=").concat(s,"&")}),i.slice(0,-1)):(s=t?encodeURIComponent(c):c,i="".concat(a,"=").concat(s)),"".concat(l,"&").concat(i)},"").substr(1):null,Lt=(e,t={})=>{const n=Object.assign({method:e.method||"GET",headers:e.headers},t),r=Dt(e.headers)["content-type"]||"";if(typeof e.data=="string")n.body=e.data;else if(r.includes("application/x-www-form-urlencoded")){const a=new URLSearchParams;for(const[c,s]of Object.entries(e.data||{}))a.set(c,s);n.body=a.toString()}else if(r.includes("multipart/form-data")||e.data instanceof FormData){const a=new FormData;if(e.data instanceof FormData)e.data.forEach((s,i)=>{a.append(i,s)});else for(const s of Object.keys(e.data))a.append(s,e.data[s]);n.body=a;const c=new Headers(n.headers);c.delete("content-type"),n.headers=c}else(r.includes("application/json")||typeof e.data=="object")&&(n.body=JSON.stringify(e.data));return n};class Tt extends Te{async request(t){const n=Lt(t,t.webFetchExtra),l=Ot(t.params,t.shouldEncodeUrlParams),r=l?"".concat(t.url,"?").concat(l):t.url,a=await fetch(r,n),c=a.headers.get("content-type")||"";let{responseType:s="text"}=a.ok?t:{};c.includes("application/json")&&(s="json");let i,p;switch(s){case"arraybuffer":case"blob":p=await a.blob(),i=await Pt(p);break;case"json":i=await a.json();break;case"document":case"text":default:i=await a.text()}const U={};return a.headers.forEach((L,j)=>{U[j]=L}),{data:i,headers:U,status:a.status,url:a.url}}async get(t){return this.request(Object.assign(Object.assign({},t),{method:"GET"}))}async post(t){return this.request(Object.assign(Object.assign({},t),{method:"POST"}))}async put(t){return this.request(Object.assign(Object.assign({},t),{method:"PUT"}))}async patch(t){return this.request(Object.assign(Object.assign({},t),{method:"PATCH"}))}async delete(t){return this.request(Object.assign(Object.assign({},t),{method:"DELETE"}))}}fe("CapacitorHttp",{web:()=>new Tt});var _e;(function(e){e[e.Sunday=1]="Sunday",e[e.Monday=2]="Monday",e[e.Tuesday=3]="Tuesday",e[e.Wednesday=4]="Wednesday",e[e.Thursday=5]="Thursday",e[e.Friday=6]="Friday",e[e.Saturday=7]="Saturday"})(_e||(_e={}));const Et=fe("LocalNotifications",{web:()=>Ae(()=>import("./web-CErII-n0.js"),__vite__mapDeps([0,1,2,3,4,5,6,7])).then(e=>new e.LocalNotificationsWeb)}),At=Pe({components:{IonAccordion:Ie,IonAccordionGroup:Me,IonCheckbox:$e,IonFab:Ue,IonFabButton:je,IonicSlides:ye,IonItemOption:xe,IonItemOptions:Re,IonItemSliding:Fe,IonRefresher:He,IonRefresherContent:Be,CalenderTab:bt,SchedulePop:dt,Swiper:ct,SwiperSlide:ut},emits:["view:didEnter"],setup(){const e=T(new mt);let t=G().startOf("day"),n,l=0;const r=T([{},{},{}]),a=T(),c=T(),s=T(!0),i=T(),p=T(),U=T(),L=T(),j=T(!1),V=T({isOpen:!1,duration:3e3,text:""}),_=T({isOpen:!1,data:void 0,text:""}),Z=[{text:"Cancel",role:"cancel"},{text:"OK",role:"confirm"}],E=()=>{s.value?r.value=[B.createWeekData(t.subtract(1,"weeks"),e.value,i),B.createWeekData(t,e.value,i),B.createWeekData(t.add(1,"weeks"),e.value,i)]:r.value=[B.createMonthData(t.subtract(1,"months"),e.value,i),B.createMonthData(t,e.value,i),B.createMonthData(t.add(1,"months"),e.value,i)]},R=()=>{const o=r.value[1];if(!o.weekArr){console.warn("no weekArr");return}i.value=void 0;const d=G().startOf("day");if(!i.value){e:for(const m of o.weekArr)for(const O of m)if(O.dt.unix()==d.unix()){i.value=O;break e}}if(!i.value){e:for(const m of o.weekArr)for(const O of m)if(O.dt.unix()==t.unix()){i.value=O;break e}}i.value||(i.value=o.weekArr[0][0])},F=async()=>{const o=await ot.create({message:"Loading..."});o.present(),st(1).then(d=>{e.value=B.parseUserData(d),E(),R(),setTimeout(()=>{var m;(m=c==null?void 0:c.value)==null||m.update()},100)}).catch(d=>{console.log("getSave",d),V.value.isOpen=!0,V.value.text=JSON.stringify(d)}).finally(()=>{o.dismiss()})};Ge(()=>{F(),Ke(()=>{F()})});const z=()=>{it(e.value.id,e.value.name,JSON.stringify(e.value)).then(o=>{console.log("doSaveUserData",o)}).catch(o=>{console.log("doSaveUserData",o)})},W=()=>{t=G().startOf("day"),i.value=new pt(G().startOf("day")),E()},J=()=>{var o;(o=c==null?void 0:c.value)==null||o.update()},ee=()=>{console.log(JSON.stringify(e.value)),Et.schedule({notifications:[{title:"On sale",body:"Widgets are 10% off. Act fast!",id:1,schedule:{at:new Date(Date.now()+1e3*5)},sound:void 0,attachments:void 0,actionTypeId:"",extra:null}]})},v=o=>{E(),o.slideTo(1,0,!1),o.update(),R()},b=o=>{s.value?t=t.add(1,"weeks").startOf("week"):t=t.add(1,"months").startOf("month"),v(o)},A=o=>{s.value?t=t.subtract(1,"weeks").startOf("week"):t=t.subtract(1,"months").startOf("month"),v(o)},I=o=>{c.value=o,o.slideTo(1,0,!1)},M=(o,d)=>{o.month!=d.dt.month()&&(o.year*100+o.month<d.dt.year()*100+d.dt.month()?c.value.slideNext():c.value.slidePrev()),i.value=d},P=()=>{s.value=!s.value,E(),setTimeout(()=>{c.value.update()},100)};return{icons:ht,ColorOptions:Ve,getColorOptions:ze,getPriorityOptions:We,getGroupOptions:qe,addCircleOutline:Ne,alarmOutline:Je,chevronDown:Ye,chevronUp:Qe,ellipseOutline:Xe,list:Ze,listOutline:et,swapVertical:tt,trashOutline:nt,slideArr:r,curScheduleList:a,swiperRef:c,bFold:s,selectedDate:i,scheduleModal:p,scheduleModalData:U,scheduleSave:L,isScheduleModalOpen:j,toastData:V,userData:e,currentDate:t,pTouch:n,lstTs:l,alertButtons:Z,scheduleDelConfirm:_,countFinishedSubtask:o=>{var d;try{return(d=o==null?void 0:o.subtasks)==null?void 0:d.filter(m=>{var O,Q,oe,se;return(((Q=(O=i.value)==null?void 0:O.save[o.id])==null?void 0:Q.subtasks)&&((se=(oe=i.value)==null?void 0:oe.save[o.id])==null?void 0:se.subtasks[m.id])||0)===1}).length}catch(m){return console.log("countFinishedSubtask",m),0}},IonicSlides:ye,updateScheduleData:E,Keyboard:ft,btnTodayClk:W,btnSortClk:J,onSlideChangeNext:b,onSlideChangePre:A,setSwiperInstance:I,onDaySelected:M,btnCalendarFoldClk:P,onScheduleListTouchStart:o=>{n=o.touches[0]},onScheduleListTouchMove:o=>{if(G().valueOf()-l<300)return;const m=o.touches[0].clientY-n.clientY;Math.abs(m)>20&&(l=G().valueOf(),m>0===s.value&&P())},handleRefresh:async o=>{await F(),o.target.complete()},scheduleChecked:o=>{var d;return((d=i.value.save[o])==null?void 0:d.state)===1},onScheduleCheckboxChange:(o,d,m)=>{if(d){const O=d.save[m]||new vt;O.state=o.detail.checked?1:0,d.save[m]=O,at(()=>{d.events.sort((Q,oe)=>{var me,pe,ve,ge;const se=((me=d.save[Q.id])==null?void 0:me.state)||0,he=((pe=d.save[oe.id])==null?void 0:pe.state)||0;return se===he?((ve=Q.id)!=null?ve:0)-((ge=oe.id)!=null?ge:0):se-he})}),z()}},btnScheduleClk:(o,d)=>{var m;j.value=!0,U.value=d,L.value=(m=i.value)==null?void 0:m.save[d.id],o.stopPropagation()},btnScheduleAlarmClk:()=>{console.log("btnScheduleAlarmClk")},btnScheduleRemoveClk:(o,d)=>{_.value.isOpen=!0,_.value.data=d,_.value.text="del "+d.title+"?"},onScheduleModalDismiss:o=>{if(j.value=!1,o.detail.role==="backdrop")return;const[d,m]=o.detail.data,O=i.value.dt;B.updateSchedularData(e.value,d,m,O,o.detail.role)&&(E(),z())},onDelSchedulerConfirm:o=>{if(_.value.isOpen=!1,o.detail.role==="confirm"){const d=e.value.schedules.findIndex(m=>m.id===_.value.data.id);d!==-1&&e.value.schedules.splice(d,1),E(),z()}},btnAddScheduleClk:()=>{U.value=void 0,L.value=void 0,j.value=!0},btnTestClk:ee}},methods:{}}),It={key:0},Mt={key:1},$t={style:{"margin-right":"8px"},class:"gray"},Ut={slot:"content"},jt=["onClick"],xt={class:"flex"},Rt={class:"schedule-lb-sub"},Ft={class:"schedule-lb-group"};function Ht(e,t,n,l,r,a){const c=h("ion-title"),s=h("ion-button"),i=h("ion-buttons"),p=h("ion-toolbar"),U=h("ion-header"),L=h("CalenderTab"),j=h("swiper-slide"),V=h("swiper"),_=h("ion-icon"),Z=h("ion-refresher-content"),E=h("ion-refresher"),R=h("ion-label"),F=h("ion-item"),z=h("ion-checkbox"),W=h("Icon"),J=h("ion-item-option"),ee=h("ion-item-options"),v=h("ion-item-sliding"),b=h("ion-list"),A=h("ion-accordion"),I=h("ion-accordion-group"),M=h("ion-content"),P=h("SchedulePop"),le=h("ion-alert"),de=h("ion-toast"),Y=h("ion-fab-button"),te=h("ion-fab"),ne=h("ion-page");return k(),N(ne,null,{default:f(()=>[u(U,null,{default:f(()=>[u(p,null,{default:f(()=>[u(c,{class:"ion-text-center"},{default:f(()=>[e.selectedDate?(k(),K("div",It,x(e.selectedDate.dt.format("YY年MM月")),1)):(k(),K("div",Mt,"日历"))]),_:1}),u(i,{slot:"end"},{default:f(()=>{var y;return[(y=e.selectedDate)!=null&&y.dt.isToday()?Oe("",!0):(k(),N(s,{key:0,style:{position:"absolute",right:"50px"},onClick:e.btnTodayClk},{default:f(()=>t[4]||(t[4]=[ae(" 今 ")])),_:1},8,["onClick"]))]}),_:1})]),_:1})]),_:1}),u(M,{"scroll-y":!1},{default:f(()=>[u(V,{onSlideNextTransitionEnd:e.onSlideChangeNext,onSlidePrevTransitionEnd:e.onSlideChangePre,onSwiper:e.setSwiperInstance,"centered-slides":!0,autoHeight:!0,modules:[e.IonicSlides,e.Keyboard],keyboard:!0},{default:f(()=>[(k(!0),K(re,null,ie(e.slideArr,(y,g)=>(k(),N(j,{key:g},{default:f(()=>[u(L,{slide:y,daySelectCallback:e.onDaySelected,selectedDate:e.selectedDate,swiperRef:e.swiperRef},null,8,["slide","daySelectCallback","selectedDate","swiperRef"])]),_:2},1024))),128))]),_:1},8,["onSlideNextTransitionEnd","onSlidePrevTransitionEnd","onSwiper","modules"]),u(s,{color:"light",expand:"full",fill:"clear",class:"ion-no-margin ion-no-padding",style:{"min-height":"auto"},onClick:t[0]||(t[0]=y=>e.btnCalendarFoldClk())},{default:f(()=>[u(_,{icon:e.bFold?e.chevronDown:e.chevronUp,color:"primary"},null,8,["icon"])]),_:1}),u(M,{color:"light",onTouchmove:e.onScheduleListTouchMove,onTouchstart:e.onScheduleListTouchStart},{default:f(()=>[u(E,{slot:"fixed",onIonRefresh:t[1]||(t[1]=y=>e.handleRefresh(y))},{default:f(()=>[u(Z)]),_:1}),u(I,{multiple:!0,value:["schedule","goals"]},{default:f(()=>[u(A,{value:"schedule"},{default:f(()=>[u(F,{slot:"header",color:"light",class:"schedule-group-item"},{default:f(()=>{var y;return[u(R,null,{default:f(()=>{var g;return[ae(x((g=e.selectedDate)==null?void 0:g.dt.format("MM-DD")),1)]}),_:1}),$("p",$t,x((y=e.selectedDate)==null?void 0:y.events.length),1)]}),_:1}),$("div",Ut,[u(b,{inset:!0,lines:"full",mode:"ios",ref:"curScheduleList",class:"schedule-list"},{default:f(()=>{var y;return[(k(!0),K(re,null,ie((y=e.selectedDate)==null?void 0:y.events,(g,C)=>(k(),N(v,{key:C},{default:f(()=>[u(F,null,{default:f(()=>{var w,D;return[u(z,{style:{"--size":"26px","padding-right":"5px"},slot:"start",checked:e.scheduleChecked(g.id),onIonChange:S=>e.onScheduleCheckboxChange(S,e.selectedDate,g.id)},null,8,["checked","onIonChange"]),$("div",{onClick:S=>e.btnScheduleClk(S,g),class:"scheduleItem"},[u(R,{class:De([{"text-line-through":((D=(w=e.selectedDate)==null?void 0:w.save[g.id])==null?void 0:D.state)===1},"scheduleItemLabel"])},{default:f(()=>{var S;return[$("h2",null,"["+x(g.id)+"]"+x(g.title),1),$("div",xt,[$("p",Rt,[u(_,{icon:e.listOutline,style:{position:"relative",top:"3px"}},null,8,["icon"]),ae(" "+x(e.countFinishedSubtask(g))+" / "+x((S=g==null?void 0:g.subtasks)==null?void 0:S.length),1)]),$("p",Ft,x(e.getGroupOptions(g.groupId).label),1)])]}),_:2},1032,["class"]),$("span",{class:"v-dot",style:lt({"background-color":e.getColorOptions(g.color).tag,"margin-left":"10px"})},null,4),u(W,{icon:e.getPriorityOptions(g.priority).icon,height:"36",color:e.getPriorityOptions(g.priority).color},null,8,["icon","color"])],8,jt)]}),_:2},1024),u(ee,{side:"end"},{default:f(()=>[u(J,{onClick:e.btnScheduleAlarmClk},{default:f(()=>[u(_,{icon:e.alarmOutline},null,8,["icon"])]),_:1},8,["onClick"]),u(J,{color:"danger",onClick:w=>e.btnScheduleRemoveClk(w,g)},{default:f(()=>[u(_,{icon:e.trashOutline},null,8,["icon"])]),_:2},1032,["onClick"])]),_:2},1024)]),_:2},1024))),128))]}),_:1},512)])]),_:1}),u(A,{value:"goals"},{default:f(()=>[u(F,{slot:"header",color:"light",class:"schedule-group-item"},{default:f(()=>[u(R,null,{default:f(()=>t[5]||(t[5]=[ae("里程碑")])),_:1})]),_:1}),t[6]||(t[6]=$("div",{class:"ion-padding",slot:"content"},"Content",-1))]),_:1})]),_:1})]),_:1},8,["onTouchmove","onTouchstart"]),u(P,{id:"pop-modal",ref:"scheduleModal","is-open":e.isScheduleModalOpen,modal:e.scheduleModal,schedule:e.scheduleModalData,save:e.scheduleSave,onWillDismiss:e.onScheduleModalDismiss},null,8,["is-open","modal","schedule","save","onWillDismiss"]),u(le,{"is-open":e.scheduleDelConfirm.isOpen,header:"Confirm!",buttons:e.alertButtons,"sub-header":e.scheduleDelConfirm.text,onDidDismiss:t[2]||(t[2]=y=>e.onDelSchedulerConfirm(y))},null,8,["is-open","buttons","sub-header"]),u(de,{"is-open":e.toastData.isOpen,message:e.toastData.text,duration:e.toastData.duration,onDidDismiss:t[3]||(t[3]=()=>e.toastData.isOpen=!1)},null,8,["is-open","message","duration"])]),_:1}),u(te,{slot:"fixed",vertical:"bottom",horizontal:"end"},{default:f(()=>[u(Y,{onClick:e.btnAddScheduleClk},{default:f(()=>[u(_,{icon:e.addCircleOutline,size:"large"},null,8,["icon"])]),_:1},8,["onClick"])]),_:1})]),_:1})}const Bt=rt(At,[["render",Ht],["__scopeId","data-v-16fd4f1d"]]),Wt=Object.freeze(Object.defineProperty({__proto__:null,default:Bt},Symbol.toStringTag,{value:"Module"}));export{Wt as T,Te as W};
