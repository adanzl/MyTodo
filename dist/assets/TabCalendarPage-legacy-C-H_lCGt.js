System.register(["./index-legacy-CiG0jpAC.js","./swiper-vue-legacy-0eOvY6bK.js","./UserData-legacy-B6jXLD_R.js","./ImgMgr-legacy-CsyEYu4m.js"],(function(e,t){"use strict";var a,l,s,o,n,i,r,d,u,c,v,p,f,h,m,g,y,b,w,x,k,_,D,S,M,C,O,T,$,E,I,z,j,q,H,P,L,U,V,Y,N,A,F,B,J,W,K,R,X,G,Z,Q,ee;return{setters:[e=>{a=e.a0,l=e.o,s=e.e,o=e.j,n=e.d,i=e.i,r=e.C,d=e.w,u=e.c,c=e.a,v=e.r,p=e.b,f=e.t,h=e.Z,m=e.h,g=e.u,y=e.f,b=e.F,w=e.X,x=e.q,k=e.n,_=e.R,D=e.K,S=e.H,M=e.$,C=e.J,O=e.s,T=e.v,$=e.L,E=e.W,I=e.Y,z=e.a1,j=e.D,q=e.E,H=e.k,P=e.U,L=e.V,U=e.a2,V=e.I,Y=e.g,N=e.l},e=>{A=e.g,F=e.c,B=e.d,J=e.S,W=e.a,K=e.I,R=e.K,X=e.b},e=>{G=e.a,Z=e.b,Q=e.S,ee=e.U},null],execute:function(){var t=document.createElement("style");function te(e,t){const a=A(t);return a!==t&&(a.style.backfaceVisibility="hidden",a.style["-webkit-backface-visibility"]="hidden"),a}function ae(e,t,a){const l=`swiper-slide-shadow${a?`-${a}`:""} swiper-slide-shadow-${e}`,s=A(t);let o=s.querySelector(`.${l.split(" ").join(".")}`);return o||(o=F("div",l.split(" ")),s.append(o)),o}function le(e){let{swiper:t,extendParams:a,on:l}=e;a({coverflowEffect:{rotate:50,stretch:0,depth:100,scale:1,modifier:1,slideShadows:!0}}),function(e){const{effect:t,swiper:a,on:l,setTranslate:s,setTransition:o,overwriteParams:n,perspective:i,recreateShadows:r,getEffectParams:d}=e;let u;l("beforeInit",(()=>{if(a.params.effect!==t)return;a.classNames.push(`${a.params.containerModifierClass}${t}`),i&&i()&&a.classNames.push(`${a.params.containerModifierClass}3d`);const e=n?n():{};Object.assign(a.params,e),Object.assign(a.originalParams,e)})),l("setTranslate",(()=>{a.params.effect===t&&s()})),l("setTransition",((e,l)=>{a.params.effect===t&&o(l)})),l("transitionEnd",(()=>{if(a.params.effect===t&&r){if(!d||!d().slideShadows)return;a.slides.forEach((e=>{e.querySelectorAll(".swiper-slide-shadow-top, .swiper-slide-shadow-right, .swiper-slide-shadow-bottom, .swiper-slide-shadow-left").forEach((e=>e.remove()))})),r()}})),l("virtualUpdate",(()=>{a.params.effect===t&&(a.slides.length||(u=!0),requestAnimationFrame((()=>{u&&a.slides&&a.slides.length&&(s(),u=!1)})))}))}({effect:"coverflow",swiper:t,on:l,setTranslate:()=>{const{width:e,height:a,slides:l,slidesSizesGrid:s}=t,o=t.params.coverflowEffect,n=t.isHorizontal(),i=t.translate,r=n?e/2-i:a/2-i,d=n?o.rotate:-o.rotate,u=o.depth,c=B(t);for(let t=0,v=l.length;t<v;t+=1){const e=l[t],a=s[t],i=(r-e.swiperSlideOffset-a/2)/a,v="function"==typeof o.modifier?o.modifier(i):i*o.modifier;let p=n?d*v:0,f=n?0:d*v,h=-u*Math.abs(v),m=o.stretch;"string"==typeof m&&-1!==m.indexOf("%")&&(m=parseFloat(o.stretch)/100*a);let g=n?0:m*v,y=n?m*v:0,b=1-(1-o.scale)*Math.abs(v);Math.abs(y)<.001&&(y=0),Math.abs(g)<.001&&(g=0),Math.abs(h)<.001&&(h=0),Math.abs(p)<.001&&(p=0),Math.abs(f)<.001&&(f=0),Math.abs(b)<.001&&(b=0);const w=`translate3d(${y}px,${g}px,${h}px)  rotateX(${c(f)}deg) rotateY(${c(p)}deg) scale(${b})`;if(te(0,e).style.transform=w,e.style.zIndex=1-Math.abs(Math.round(v)),o.slideShadows){let t=n?e.querySelector(".swiper-slide-shadow-left"):e.querySelector(".swiper-slide-shadow-top"),a=n?e.querySelector(".swiper-slide-shadow-right"):e.querySelector(".swiper-slide-shadow-bottom");t||(t=ae("coverflow",e,n?"left":"top")),a||(a=ae("coverflow",e,n?"right":"bottom")),t&&(t.style.opacity=v>0?v:0),a&&(a.style.opacity=-v>0?-v:0)}}},setTransition:e=>{t.slides.map((e=>A(e))).forEach((t=>{t.style.transitionDuration=`${e}ms`,t.querySelectorAll(".swiper-slide-shadow-top, .swiper-slide-shadow-right, .swiper-slide-shadow-bottom, .swiper-slide-shadow-left").forEach((t=>{t.style.transitionDuration=`${e}ms`}))}))},perspective:()=>!0,overwriteParams:()=>({watchSlidesProgress:!0})})}t.textContent=".main_content[data-v-ccbe50c9]::part(scroll){height:90%;margin-top:20%}.main_content[data-v-ccbe50c9]::part(background){display:none}ion-modal[data-v-ccbe50c9]::part(backdrop){background-color:var(--ion-color-dark)!important;opacity:.3!important}ion-modal[data-v-ccbe50c9]::part(content){background-color:transparent!important;align-items:center}ion-modal[data-v-ccbe50c9]{--height: 100%;--width: 100%;align-items:center}.data-content[data-v-ccbe50c9]{height:100%;width:80vw}.data-content ion-content[data-v-ccbe50c9]::part(scroll){height:100%;border:1px solid #e2d0d0;border-radius:10px}.data-content ion-content[data-v-ccbe50c9]::part(background){border-radius:10px}ion-chip.today[data-v-d1bd742b]{--background: rgb(255, 98, 0) !important}\n",document.head.appendChild(t);const se={viewBox:"0 0 24 24",width:"1.2em",height:"1.2em"},oe=a({name:"mdi-list-status",render:function(e,t){return l(),s("svg",se,t[0]||(t[0]=[o("path",{fill:"currentColor",d:"M16.5 11L13 7.5l1.4-1.4l2.1 2.1L20.7 4l1.4 1.4zM11 7H2v2h9zm10 6.4L19.6 12L17 14.6L14.4 12L13 13.4l2.6 2.6l-2.6 2.6l1.4 1.4l2.6-2.6l2.6 2.6l1.4-1.4l-2.6-2.6zM11 15H2v2h9z"},null,-1)]))}}),ne={viewBox:"0 0 24 24",width:"1.2em",height:"1.2em"},ie=a({name:"mdi-calendar-today-outline",render:function(e,t){return l(),s("svg",ne,t[0]||(t[0]=[o("path",{fill:"currentColor",d:"M19 3h-1V1h-2v2H8V1H6v2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14c1.11 0 2-.89 2-2V5c0-1.11-.89-2-2-2m0 16H5V9h14zm0-12H5V5h14M7 11h5v5H7"},null,-1)]))}}),re={class:"text-xl font-bold text-white"},de=["onClick"],ue={class:"truncate"},ce={class:"flex"},ve={class:"schedule-lb-sub"},pe={class:"schedule-lb-group"},fe=n({__name:"CalendarCover",props:{dt:{type:Object,default:i()},userData:{type:Object,required:!0}},emits:["update:data"],setup(e,{emit:t}){const a=["星期日","星期一","星期二","星期三","星期四","星期五","星期六"],n=e,I=t,z=r([{},{},{}]),j=r(),q=r(i(n.dt)),H=r(),P=r(),L=r(),U=r(),V=r(!1);d((()=>n.dt),(e=>{q.value=e,Y()}),{deep:!0});const Y=()=>{z.value=[G.createDayData(q.value.subtract(1,"day"),n.userData),G.createDayData(q.value,n.userData),G.createDayData(q.value.add(1,"day"),n.userData)]};function N(e){if(1===e.activeIndex)return;const t=e.activeIndex,a=e.previousIndex;t<a?(q.value=q.value.subtract(1,"day"),Y(),e.slideTo(1,0,!1)):t>a&&(q.value=q.value.add(1,"day"),Y(),e.slideTo(1,0,!1))}const A=e=>{j.value=e,e.slideTo(1,0,!1)},F=(e,t)=>{try{var a;return null==t||null===(a=t.subtasks)||void 0===a?void 0:a.filter((a=>{var l,s;return 1===(e.save&&(null===(l=e.save[t.id])||void 0===l?void 0:l.subtasks)&&(null===(s=e.save[t.id])||void 0===s?void 0:s.subtasks[a.id])||0)})).length}catch(l){return console.log("countFinishedSubtask",l),0}},B=e=>{if(V.value=!1,"backdrop"===e.detail.role)return;const[t,a]=e.detail.data,l=q.value;G.updateSchedularData(n.userData,t,a,l,e.detail.role)&&(Y(),ee(),I("update:data",q.value))};function ee(){w(n.userData.id,n.userData.name,JSON.stringify(n.userData)).then((e=>{console.log("doSaveUserData",e)})).catch((e=>{console.log("doSaveUserData",e)}))}function te(){var e;q.value=i(),Y(),null==j||null===(e=j.value)||void 0===e||e.slideTo(1,0,!1)}const ae=()=>{L.value=void 0,U.value=void 0,V.value=!0};return(e,t)=>{const i=ie,r=v("ion-button"),d=v("ion-item"),w=oe,j=v("ion-icon"),Y=v("ion-label"),se=v("ion-content"),ne=v("ion-modal");return l(),u(ne,{mode:"ios",ref_key:"selfRef",ref:H},{default:c((()=>[p(se,{class:"main_content"},{default:c((()=>[p(d,{class:"transparent"},{default:c((()=>[o("h2",re,f(q.value.format("YYYY-MM-DD")+" "+a[q.value.day()]),1),p(r,{slot:"end",color:"danger",onClick:te,size:"default",style:h({padding:"0px 10px",opacity:q.value.isToday()?"0":"1"})},{default:c((()=>[p(i,{height:"16",slot:"start"}),t[1]||(t[1]=m(" 今天 "))])),_:1},8,["style"])])),_:1}),p(g(W),{onTransitionEnd:N,onSwiper:A,"centered-slides":!0,modules:[g(K),g(R),g(le)],effect:"coverflow",slidesPerView:"auto",freeMode:!1,coverflowEffect:{rotate:10,stretch:0,depth:100,modifier:1,slideShadows:!1},keyboard:!0,class:"h-[90%]"},{default:c((()=>[(l(!0),s(b,null,y(z.value,((e,a)=>(l(),u(g(X),{key:a,class:"data-content"},{default:c((()=>[p(se,null,{default:c((()=>[p(d,{color:"light"},{default:c((()=>[p(w,{class:"text-blue-500",height:"30",width:"30",slot:"start"}),t[2]||(t[2]=o("div",{class:"h-12"},null,-1))])),_:1}),(l(!0),s(b,null,y(e.events,((t,a)=>(l(),u(d,{key:a},{default:c((()=>{var a,s;return[p(g(x),{style:{"--size":"26px"},slot:"start",checked:e.save&&1===(null===(a=e.save[t.id])||void 0===a?void 0:a.state),onIonChange:a=>((e,t,a)=>{if(t){void 0===t.save&&(t.save={},n.userData.save[Z(t.dt)]=t.save);const l=t.save[a]||new Q;l.state=e.detail.checked?1:0,t.save[a]=l,E((()=>{t.events.sort(((e,a)=>G.CmpScheduleData(e,a,t.save)))})),ee(),I("update:data",q.value)}})(a,e,t.id)},null,8,["checked","onIonChange"]),o("div",{onClick:a=>((e,t,a)=>{V.value=!0,L.value=t,U.value=a.save?a.save[t.id]:void 0})(0,t,e),class:"flex w-full items-center"},[p(Y,{class:k([{"text-line-through":e.save&&1===(null===(s=e.save[t.id])||void 0===s?void 0:s.state)},"p-2.5 flex-1"])},{default:c((()=>{var a;return[o("h2",ue,f(t.title),1),o("div",ce,[o("p",ve,[p(j,{icon:g(_),class:"relative top-0.5"},null,8,["icon"]),m(" "+f(F(e,t))+" / "+f(null==t||null===(a=t.subtasks)||void 0===a?void 0:a.length),1)]),o("p",pe,f(g(D)(t.groupId).label),1)])]})),_:2},1032,["class"]),o("span",{class:"v-dot ml-2.5",style:h({"background-color":g(S)(t.color).tag})},null,4),(l(),u(M(g(C)(t.priority).icon),{height:"36px",width:"36px",color:g(C)(t.priority).color},null,8,["color"]))],8,de)]})),_:2},1024)))),128))])),_:2},1024)])),_:2},1024)))),128))])),_:1},8,["modules"]),p(g(O),{slot:"fixed",vertical:"bottom",horizontal:"end"},{default:c((()=>[p(g(T),{onClick:ae},{default:c((()=>[p(j,{icon:g($),size:"large"},null,8,["icon"])])),_:1})])),_:1})])),_:1}),o("div",{class:"w-full h-[10%]",onClick:t[0]||(t[0]=e=>H.value.$el.dismiss())}),p(J,{id:"pop-modal","aria-hidden":"false",ref_key:"scheduleModal",ref:P,"is-open":V.value,modal:P.value,schedule:L.value,save:U.value,onWillDismiss:B},null,8,["is-open","modal","schedule","save"])])),_:1},512)}}}),he=I(fe,[["__scopeId","data-v-ccbe50c9"]]),me={key:0},ge={key:1},ye={class:"bg-gray-200 text-left text-sm/4 block"};e("default",I(n({__name:"TabCalendarPage",setup(e){const t=["日","一","二","三","四","五","六"],a=r({isOpen:!1,duration:3e3,text:""}),n=r([{},{},{}]),d=r(new ee),w=r(),x=r(),_=r(i().startOf("day")),D=r(!1),M=r({}),C=z("eventBus"),O=async()=>{const e=await P.create({message:"Loading..."});e.present(),L(1).then((e=>{d.value=G.parseUserData(e),$(),setTimeout((()=>{var e;null==w||null===(e=w.value)||void 0===e||e.update()}),100)})).catch((e=>{console.log("getSave",e),a.value.isOpen=!0,a.value.text=JSON.stringify(e)})).finally((()=>{e.dismiss()}))};function T(e){const[t,a,l]=[M.value.group,M.value.color,M.value.priority];return!(t&&!1===t.get(e.groupId)||a&&!1===a.get(e.color)||l&&!1===l.get(e.priority))}j((async()=>{O(),q((()=>{O()})),C.$on("menuClose",(e=>{M.value=e}))}));const $=()=>{n.value=[G.createMonthData(_.value.subtract(1,"months"),d.value),G.createMonthData(_.value,d.value),G.createMonthData(_.value.add(1,"months"),d.value)]},E=e=>{$(),e.slideTo(1,0,!1),e.update(),x.value&&x.value.dt.month()!==_.value.month()&&(x.value=void 0)},I=e=>{_.value=_.value.add(1,"months").startOf("month"),E(e)},A=e=>{_.value=_.value.subtract(1,"months").startOf("month"),E(e)},F=e=>{w.value=e,e.slideTo(1,0,!1)};function B(){D.value=!1}function J(){_.value=i().startOf("day"),$()}function Z(){const e=i().startOf("day");return e.month()===_.value.month()&&e.year()===_.value.year()}function Q(){$(),E(w.value)}return(e,r)=>{const w=v("ion-buttons"),M=v("ion-title"),C=v("ion-button"),O=v("ion-toolbar"),$=v("ion-header"),E=v("ion-chip"),z=v("ion-content"),j=v("ion-toast"),q=v("ion-page");return l(),u(q,{id:"main-content",main:""},{default:c((()=>{var e;return[p($,null,{default:c((()=>[p(O,null,{default:c((()=>[p(w,{slot:"start"},{default:c((()=>[p(g(U))])),_:1}),p(M,{class:"ion-text-center"},{default:c((()=>[_.value?(l(),s("div",me,f(_.value.format("YY年MM月")),1)):(l(),s("div",ge,"日历"))])),_:1}),p(w,{slot:"end"},{default:c((()=>[Z()?H("",!0):(l(),u(C,{key:0,style:{position:"absolute",right:"50px"},onClick:J},{default:c((()=>r[1]||(r[1]=[m(" 今 ")]))),_:1}))])),_:1})])),_:1})])),_:1}),p(g(V),{style:{"background-color":"antiquewhite",color:"blue"}},{default:c((()=>[(l(),s(b,null,y(t,(e=>p(g(Y),{class:"ion-text-center flex-1",key:e},{default:c((()=>[m(f(e),1)])),_:2},1024))),64))])),_:1}),p(z,null,{default:c((()=>[p(g(W),{onSlideNextTransitionEnd:I,onSlidePrevTransitionEnd:A,onSwiper:F,"centered-slides":!0,autoHeight:!0,modules:[g(K),g(R)]},{default:c((()=>[(l(!0),s(b,null,y(n.value,((e,t)=>(l(),u(g(X),{key:t},{default:c((()=>[p(g(N),{class:"w-full"},{default:c((()=>[(l(!0),s(b,null,y(e.weekArr,(t=>(l(),u(g(V),{key:t,class:"flex-nowrap"},{default:c((()=>[(l(!0),s(b,null,y(t,(t=>(l(),u(g(Y),{class:"p-0 min-h-32 border-[1px] border-gray-100 border-solid w-[14.28%]",onClick:e=>((e,t)=>{x.value=t,D.value=!0})(0,t),key:t},{default:c((()=>[o("span",ye,[p(E,{class:k([{transparent:t.dt.unix()!==g(i)().startOf("day").unix(),today:t.dt.unix()===g(i)().startOf("day").unix(),gray:t.dt.month()!==e.month},"py-[1px] px-1 min-h-0"])},{default:c((()=>[m(f(t.dt.date()),1)])),_:2},1032,["class"])]),(l(!0),s(b,null,y(t.events.filter(T),((e,a)=>{var o,n;return l(),s("div",{key:a,class:k([{"text-line-through":t.save&&1===(null===(o=t.save[e.id])||void 0===o?void 0:o.state),gray:t.save&&1===(null===(n=t.save[e.id])||void 0===n?void 0:n.state)},"text-left truncate mt-[1px] rounded-sm py-[1px] px-1"]),style:h({"background-color":g(S)(e.color).tag,"font-size":"clamp(9px, 2.8vw, 16px)"})},f(e.title),7)})),128))])),_:2},1032,["onClick"])))),128))])),_:2},1024)))),128))])),_:2},1024)])),_:2},1024)))),128))])),_:1},8,["modules"])])),_:1}),p(j,{"is-open":a.value.isOpen,message:a.value.text,duration:a.value.duration,onDidDismiss:r[0]||(r[0]=()=>a.value.isOpen=!1)},null,8,["is-open","message","duration"]),p(he,{ref:"scheduleModal","is-open":D.value,dt:null===(e=x.value)||void 0===e?void 0:e.dt,userData:d.value,"onUpdate:data":Q,onWillDismiss:B},null,8,["is-open","dt","userData"])]})),_:1})}}}),[["__scopeId","data-v-d1bd742b"]]))}}}));
