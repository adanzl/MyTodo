import{a2 as _e,o as m,e as P,j as I,d as ue,i as H,D as x,w as ge,c as q,a as s,r as D,b as a,t as V,a0 as ae,h as $,u as o,f as j,F as K,Z as we,a3 as be,q as xe,n as se,T as Se,M as ye,K as ce,a1 as De,L as re,s as ke,v as Ce,N as Me,Y as Te,$ as fe,E as Oe,G as Ie,H as $e,k as Ee,W as ze,X as Pe,x as qe,I as ie,g as L,l as Ne}from"./index-BCutpD3H.js";import{g as oe,c as Ue,d as Be,S as Ye,a as pe,I as ve,K as me,b as he}from"./swiper-vue-YJFVh5lo.js";import{a as N,b as Ae,S as Fe,U as Le}from"./UserData-1-Ihtlon.js";import"./ImgMgr-DVm5uqdS.js";function He(E){const{effect:n,swiper:l,on:i,setTranslate:S,setTransition:g,overwriteParams:d,perspective:u,recreateShadows:h,getEffectParams:T}=E;i("beforeInit",()=>{if(l.params.effect!==n)return;l.classNames.push("".concat(l.params.containerModifierClass).concat(n)),u&&u()&&l.classNames.push("".concat(l.params.containerModifierClass,"3d"));const p=d?d():{};Object.assign(l.params,p),Object.assign(l.originalParams,p)}),i("setTranslate",()=>{l.params.effect===n&&S()}),i("setTransition",(p,w)=>{l.params.effect===n&&g(w)}),i("transitionEnd",()=>{if(l.params.effect===n&&h){if(!T||!T().slideShadows)return;l.slides.forEach(p=>{p.querySelectorAll(".swiper-slide-shadow-top, .swiper-slide-shadow-right, .swiper-slide-shadow-bottom, .swiper-slide-shadow-left").forEach(w=>w.remove())}),h()}});let f;i("virtualUpdate",()=>{l.params.effect===n&&(l.slides.length||(f=!0),requestAnimationFrame(()=>{f&&l.slides&&l.slides.length&&(S(),f=!1)}))})}function Ve(E,n){const l=oe(n);return l!==n&&(l.style.backfaceVisibility="hidden",l.style["-webkit-backface-visibility"]="hidden"),l}function de(E,n,l){const i="swiper-slide-shadow".concat(l?"-".concat(l):"").concat(" swiper-slide-shadow-".concat(E)),S=oe(n);let g=S.querySelector(".".concat(i.split(" ").join(".")));return g||(g=Ue("div",i.split(" ")),S.append(g)),g}function Ge(E){let{swiper:n,extendParams:l,on:i}=E;l({coverflowEffect:{rotate:50,stretch:0,depth:100,scale:1,modifier:1,slideShadows:!0}}),He({effect:"coverflow",swiper:n,on:i,setTranslate:()=>{const{width:d,height:u,slides:h,slidesSizesGrid:T}=n,f=n.params.coverflowEffect,p=n.isHorizontal(),w=n.translate,O=p?-w+d/2:-w+u/2,R=p?f.rotate:-f.rotate,J=f.depth,W=Be(n);for(let U=0,Z=h.length;U<Z;U+=1){const C=h[U],B=T[U],Q=C.swiperSlideOffset,r=(O-Q-B/2)/B,e=typeof f.modifier=="function"?f.modifier(r):r*f.modifier;let t=p?R*e:0,c=p?0:R*e,b=-J*Math.abs(e),v=f.stretch;typeof v=="string"&&v.indexOf("%")!==-1&&(v=parseFloat(f.stretch)/100*B);let M=p?0:v*e,Y=p?v*e:0,G=1-(1-f.scale)*Math.abs(e);Math.abs(Y)<.001&&(Y=0),Math.abs(M)<.001&&(M=0),Math.abs(b)<.001&&(b=0),Math.abs(t)<.001&&(t=0),Math.abs(c)<.001&&(c=0),Math.abs(G)<.001&&(G=0);const X="translate3d(".concat(Y,"px,").concat(M,"px,").concat(b,"px)  rotateX(").concat(W(c),"deg) rotateY(").concat(W(t),"deg) scale(").concat(G,")"),ee=Ve(f,C);if(ee.style.transform=X,C.style.zIndex=-Math.abs(Math.round(e))+1,f.slideShadows){let _=p?C.querySelector(".swiper-slide-shadow-left"):C.querySelector(".swiper-slide-shadow-top"),z=p?C.querySelector(".swiper-slide-shadow-right"):C.querySelector(".swiper-slide-shadow-bottom");_||(_=de("coverflow",C,p?"left":"top")),z||(z=de("coverflow",C,p?"right":"bottom")),_&&(_.style.opacity=e>0?e:0),z&&(z.style.opacity=-e>0?-e:0)}}},setTransition:d=>{n.slides.map(h=>oe(h)).forEach(h=>{h.style.transitionDuration="".concat(d,"ms"),h.querySelectorAll(".swiper-slide-shadow-top, .swiper-slide-shadow-right, .swiper-slide-shadow-bottom, .swiper-slide-shadow-left").forEach(T=>{T.style.transitionDuration="".concat(d,"ms")})})},perspective:()=>!0,overwriteParams:()=>({watchSlidesProgress:!0})})}const Re={viewBox:"0 0 24 24",width:"1.2em",height:"1.2em"};function We(E,n){return m(),P("svg",Re,n[0]||(n[0]=[I("path",{fill:"currentColor",d:"M16.5 11L13 7.5l1.4-1.4l2.1 2.1L20.7 4l1.4 1.4zM11 7H2v2h9zm10 6.4L19.6 12L17 14.6L14.4 12L13 13.4l2.6 2.6l-2.6 2.6l1.4 1.4l2.6-2.6l2.6 2.6l1.4-1.4l-2.6-2.6zM11 15H2v2h9z"},null,-1)]))}const Xe=_e({name:"mdi-list-status",render:We}),je={class:"text-xl font-bold text-white"},Ke=["onClick"],Je={class:"truncate"},Ze={class:"flex text-gray-400"},Qe={class:"schedule-lb-sub"},et={class:"schedule-lb-group"},tt=ue({__name:"CalendarCover",props:{dt:{type:Object,default:H()},userData:{type:Object,required:!0}},emits:["update:data"],setup(E,{emit:n}){const l=["星期日","星期一","星期二","星期三","星期四","星期五","星期六"],i=E,S=n,g=x([{},{},{}]),d=x(),u=x(H(i.dt)),h=x(),T=x(),f=x(),p=x(),w=x(!1);ge(()=>i.dt,e=>{u.value=e,O()},{deep:!0});const O=()=>{g.value=[N.createDayData(u.value.subtract(1,"day"),i.userData),N.createDayData(u.value,i.userData),N.createDayData(u.value.add(1,"day"),i.userData)]};function R(e){if(e.activeIndex===1)return;const t=e.activeIndex,c=e.previousIndex;t<c?(u.value=u.value.subtract(1,"day"),O(),e.slideTo(1,0,!1)):t>c&&(u.value=u.value.add(1,"day"),O(),e.slideTo(1,0,!1))}const J=e=>{d.value=e,e.slideTo(1,0,!1)},W=(e,t)=>{var c;try{return(c=t==null?void 0:t.subtasks)==null?void 0:c.filter(b=>{var v,M;return(e.save&&((v=e.save[t.id])==null?void 0:v.subtasks)&&((M=e.save[t.id])==null?void 0:M.subtasks[b.id])||0)===1}).length}catch(b){return console.log("countFinishedSubtask",b),0}},U=(e,t,c)=>{if(t){if(t.save===void 0){t.save={};const v=i.userData.save;v[Ae(t.dt)]=t.save}const b=t.save[c]||new Fe;b.state=e.detail.checked?1:0,t.save[c]=b,Te(()=>{t.events.sort((v,M)=>N.CmpScheduleData(v,M,t.save))}),B(),S("update:data",u.value)}},Z=(e,t,c)=>{w.value=!0,f.value=t,p.value=c.save?c.save[t.id]:void 0},C=e=>{if(w.value=!1,e.detail.role==="backdrop")return;const[t,c]=e.detail.data,b=u.value;N.updateSchedularData(i.userData,t,c,b,e.detail.role)&&(O(),B(),S("update:data",u.value))};function B(){we(i.userData.id,i.userData.name,JSON.stringify(i.userData)).then(e=>{console.log("doSaveUserData",e)}).catch(e=>{console.log("doSaveUserData",e)})}function Q(){var e;u.value=H(),O(),(e=d==null?void 0:d.value)==null||e.slideTo(1,0,!1)}const r=()=>{f.value=void 0,p.value=void 0,w.value=!0};return(e,t)=>{const c=be,b=D("ion-button"),v=D("ion-item"),M=Xe,Y=D("ion-icon"),G=D("ion-label"),X=D("ion-content"),ee=D("ion-modal");return m(),q(ee,{mode:"ios",ref_key:"selfRef",ref:h},{default:s(()=>[a(X,{class:"main_content"},{default:s(()=>[a(v,{class:"transparent"},{default:s(()=>[I("h2",je,V(u.value.format("YYYY-MM-DD")+" "+l[u.value.day()]),1),a(b,{slot:"end",color:"danger",onClick:Q,size:"small",class:"ion-padding",style:ae({padding:"0px 10px",opacity:u.value.isToday()?"0":"1"})},{default:s(()=>[a(c,{height:"16",slot:"start"}),t[1]||(t[1]=$(" 今天 "))]),_:1},8,["style"])]),_:1}),a(o(pe),{onTransitionEnd:R,onSwiper:J,"centered-slides":!0,modules:[o(ve),o(me),o(Ge)],effect:"coverflow",slidesPerView:"auto",freeMode:!1,coverflowEffect:{rotate:10,stretch:0,depth:100,modifier:1,slideShadows:!1},keyboard:!0,class:"h-[90%]"},{default:s(()=>[(m(!0),P(K,null,j(g.value,(_,z)=>(m(),q(o(he),{key:z,class:"data-content"},{default:s(()=>[a(X,null,{default:s(()=>[a(v,{color:"light"},{default:s(()=>[a(M,{class:"text-blue-500",height:"30",width:"30",slot:"start"}),t[2]||(t[2]=I("div",{class:"h-12"},null,-1))]),_:1}),(m(!0),P(K,null,j(_.events,(y,te)=>(m(),q(v,{key:te},{default:s(()=>{var k,A;return[a(o(xe),{style:{"--size":"26px"},slot:"start",checked:_.save&&((k=_.save[y.id])==null?void 0:k.state)===1,onIonChange:F=>U(F,_,y.id)},null,8,["checked","onIonChange"]),I("div",{onClick:F=>Z(F,y,_),class:"flex w-full items-center"},[a(G,{class:se([{"text-line-through":_.save&&((A=_.save[y.id])==null?void 0:A.state)===1},"p-2.5 flex-1"])},{default:s(()=>{var F;return[I("h2",Je,V(y.title),1),I("div",Ze,[I("p",Qe,[a(Y,{icon:o(Se),class:"relative top-0.5"},null,8,["icon"]),$(" "+V(W(_,y))+" / "+V((F=y==null?void 0:y.subtasks)==null?void 0:F.length),1)]),I("p",et,V(o(ye)(y.groupId).label),1)])]}),_:2},1032,["class"]),I("span",{class:"v-dot ml-2.5",style:ae({"background-color":o(ce)(y.color).tag})},null,4),(m(),q(De(o(re)(y.priority).icon),{height:"36px",width:"36px",color:o(re)(y.priority).color},null,8,["color"]))],8,Ke)]}),_:2},1024))),128))]),_:2},1024)]),_:2},1024))),128))]),_:1},8,["modules"]),a(o(ke),{slot:"fixed",vertical:"bottom",horizontal:"end"},{default:s(()=>[a(o(Ce),{onClick:r},{default:s(()=>[a(Y,{icon:o(Me),size:"large"},null,8,["icon"])]),_:1})]),_:1})]),_:1}),I("div",{class:"w-full h-[10%]",onClick:t[0]||(t[0]=_=>h.value.$el.dismiss())}),a(Ye,{id:"pop-modal","aria-hidden":"false",ref_key:"scheduleModal",ref:T,"is-open":w.value,modal:T.value,schedule:f.value,save:p.value,onWillDismiss:C},null,8,["is-open","modal","schedule","save"])]),_:1},512)}}}),at=fe(tt,[["__scopeId","data-v-291be0a3"]]),st={key:0},ot={key:1},nt={class:"bg-gray-200 text-left text-sm/4 block"},lt=ue({__name:"TabCalendarPage",setup(E){const n=x({isOpen:!1,duration:3e3,text:""}),l=x([{},{},{}]),i=x(new Le),S=x(),g=x(),d=x(H().startOf("day")),u=x(!1),h=x({}),T=Oe("eventBus"),f=async()=>{const r=await ze.create({message:"Loading..."});r.present(),Pe(1).then(e=>{i.value=N.parseUserData(e),w(),setTimeout(()=>{var t;(t=S==null?void 0:S.value)==null||t.update()},100)}).catch(e=>{console.log("getSave",e),n.value.isOpen=!0,n.value.text=JSON.stringify(e)}).finally(()=>{r.dismiss()})};Ie(async()=>{f(),$e(()=>{f()}),T.$on("menuClose",r=>{h.value=r})});function p(r){const[e,t,c]=[h.value.group,h.value.color,h.value.priority];return!(e&&e.get(r.groupId)===!1||t&&t.get(r.color)===!1||c&&c.get(r.priority)===!1)}const w=()=>{l.value=[N.createMonthData(d.value.subtract(1,"months"),i.value),N.createMonthData(d.value,i.value),N.createMonthData(d.value.add(1,"months"),i.value)]},O=r=>{w(),r.slideTo(1,0,!1),r.update(),g.value&&g.value.dt.month()!==d.value.month()&&(g.value=void 0)},R=r=>{d.value=d.value.add(1,"months").startOf("month"),O(r)},J=r=>{d.value=d.value.subtract(1,"months").startOf("month"),O(r)},W=r=>{S.value=r,r.slideTo(1,0,!1)},U=(r,e)=>{g.value=e,u.value=!0};function Z(){u.value=!1}function C(){d.value=H().startOf("day"),w()}function B(){const r=H().startOf("day");return r.month()===d.value.month()&&r.year()===d.value.year()}function Q(){w(),O(S.value)}return(r,e)=>{const t=D("ion-buttons"),c=D("ion-title"),b=D("ion-button"),v=D("ion-toolbar"),M=D("ion-header"),Y=D("ion-chip"),G=D("ion-content"),X=D("ion-toast"),ee=D("ion-page");return m(),q(ee,{id:"main-content",main:""},{default:s(()=>{var _;return[a(M,null,{default:s(()=>[a(v,null,{default:s(()=>[a(t,{slot:"start"},{default:s(()=>[a(o(qe))]),_:1}),a(c,null,{default:s(()=>[d.value?(m(),P("div",st,V(d.value.format("YY年MM月")),1)):(m(),P("div",ot,"日历"))]),_:1}),a(t,{slot:"end"},{default:s(()=>[B()?Ee("",!0):(m(),q(b,{key:0,style:{position:"absolute",right:"50px"},onClick:C},{default:s(()=>e[1]||(e[1]=[$(" 今 ")])),_:1}))]),_:1})]),_:1})]),_:1}),a(o(ie),{style:{"background-color":"antiquewhite",color:"blue"}},{default:s(()=>[a(o(L),{class:"ion-text-center text-red-600"},{default:s(()=>e[2]||(e[2]=[$("日")])),_:1}),a(o(L),{class:"ion-text-center"},{default:s(()=>e[3]||(e[3]=[$("一")])),_:1}),a(o(L),{class:"ion-text-center"},{default:s(()=>e[4]||(e[4]=[$("二")])),_:1}),a(o(L),{class:"ion-text-center"},{default:s(()=>e[5]||(e[5]=[$("三")])),_:1}),a(o(L),{class:"ion-text-center"},{default:s(()=>e[6]||(e[6]=[$("四")])),_:1}),a(o(L),{class:"ion-text-center"},{default:s(()=>e[7]||(e[7]=[$("五")])),_:1}),a(o(L),{class:"ion-text-center text-red-600"},{default:s(()=>e[8]||(e[8]=[$("六")])),_:1})]),_:1}),a(G,null,{default:s(()=>[a(o(pe),{onSlideNextTransitionEnd:R,onSlidePrevTransitionEnd:J,onSwiper:W,"centered-slides":!0,autoHeight:!0,modules:[o(ve),o(me)]},{default:s(()=>[(m(!0),P(K,null,j(l.value,(z,y)=>(m(),q(o(he),{key:y},{default:s(()=>[a(o(Ne),{class:"w-full"},{default:s(()=>[(m(!0),P(K,null,j(z.weekArr,te=>(m(),q(o(ie),{key:te,class:"flex-nowrap"},{default:s(()=>[(m(!0),P(K,null,j(te,k=>(m(),q(o(L),{class:"p-0 min-h-32 border-[1px] border-gray-100 border-solid w-[14.28%]",onClick:A=>U(z,k),key:k},{default:s(()=>[I("span",nt,[a(Y,{class:se([{transparent:k.dt.unix()!==o(H)().startOf("day").unix(),today:k.dt.unix()===o(H)().startOf("day").unix(),gray:k.dt.month()!==z.month},"py-[1px] px-1 min-h-0"])},{default:s(()=>[$(V(k.dt.date()),1)]),_:2},1032,["class"])]),(m(!0),P(K,null,j(k.events.filter(p),(A,F)=>{var ne,le;return m(),P("div",{key:F,class:se([{"text-line-through":k.save&&((ne=k.save[A.id])==null?void 0:ne.state)===1,gray:k.save&&((le=k.save[A.id])==null?void 0:le.state)===1},"text-left truncate mt-[1px] rounded-sm py-[1px] px-1"]),style:ae({"background-color":o(ce)(A.color).tag,"font-size":"clamp(9px, 2.8vw, 16px)"})},V(A.title),7)}),128))]),_:2},1032,["onClick"]))),128))]),_:2},1024))),128))]),_:2},1024)]),_:2},1024))),128))]),_:1},8,["modules"])]),_:1}),a(X,{"is-open":n.value.isOpen,message:n.value.text,duration:n.value.duration,onDidDismiss:e[0]||(e[0]=()=>n.value.isOpen=!1)},null,8,["is-open","message","duration"]),a(at,{ref:"scheduleModal","is-open":u.value,dt:(_=g.value)==null?void 0:_.dt,userData:i.value,"onUpdate:data":Q,onWillDismiss:Z},null,8,["is-open","dt","userData"])]}),_:1})}}}),ct=fe(lt,[["__scopeId","data-v-2ae2fd94"]]);export{ct as default};
