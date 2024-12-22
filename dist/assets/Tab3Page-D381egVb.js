import{k as v,I as V,p as I,d as g,e as w,h as z,f as F,j as G,U as J,_ as A}from"./Icons-CmScL3ZH.js";import{d as L,a7 as q,a8 as H,r as R,p as K,a9 as k,c as y,a as o,g as r,o as p,b as t,i as d,t as s,e as D,f as T,F as O,j as f,v as Q}from"./index-DvZ-MHEE.js";const W=L({components:{IonRefresher:q,IonRefresherContent:H,S_TS:v,Icon:V},setup(){const a=R(new J),n=R({isOpen:!1,duration:3e3,text:""});return K(()=>{k(1).then(l=>{a.value=I(l)}).catch(l=>{n.value.isOpen=!0,n.value.text=JSON.stringify(l)})}),{userData:a,toastData:n,dayjs:g,S_TS:v,getColorOptions:w,getPriorityOptions:z,getGroupOptions:F,icons:G}},data(){return{}},methods:{handleRefresh(a){k(1).then(n=>{this.userData=I(n);for(let l=0;l<this.userData.schedules.length;l++){const i=this.userData.schedules[l];i.startTs=g(i.startTs),i.endTs=g(i.endTs),i.repeatEndTs&&(i.repeatEndTs=g(i.repeatEndTs))}a.target.complete()}).catch(n=>{console.log("handleRefresh",n),this.toastData.isOpen=!0,this.toastData.text=JSON.stringify(n),a.target.complete()})}}}),X={style:{display:"flex","align-items":"center"}};function Z(a,n,l,i,x,tt){const Y=r("ion-title"),C=r("ion-toolbar"),E=r("ion-header"),N=r("ion-refresher-content"),M=r("ion-refresher"),u=r("ion-label"),_=r("ion-item"),c=r("ion-list"),b=r("Icon"),B=r("ion-toast"),P=r("ion-content"),$=r("ion-page");return p(),y($,null,{default:o(()=>[t(E,null,{default:o(()=>[t(C,null,{default:o(()=>[t(Y,null,{default:o(()=>n[2]||(n[2]=[d("Tab 3")])),_:1})]),_:1})]),_:1}),t(P,null,{default:o(()=>[t(M,{slot:"fixed",onIonRefresh:n[0]||(n[0]=e=>a.handleRefresh(e))},{default:o(()=>[t(N)]),_:1}),t(c,null,{default:o(()=>[t(_,null,{default:o(()=>[t(u,null,{default:o(()=>[d("Id: "+s(a.userData.id),1)]),_:1}),n[3]||(n[3]=d()),t(u,null,{default:o(()=>[d("Name: "+s(a.userData.name),1)]),_:1})]),_:1})]),_:1}),t(c,null,{default:o(()=>[t(_,null,{default:o(()=>[t(u,null,{default:o(()=>n[4]||(n[4]=[d("Schedule")])),_:1}),t(b,{icon:"mdi:roman-numeral-7",size:"large",height:"36",color:"#1a65eb"})]),_:1}),(p(!0),D(O,null,T(a.userData.schedules,(e,m)=>(p(),y(_,{key:m},{default:o(()=>[t(u,null,{default:o(()=>{var S,h;return[f("div",X,[f("span",{class:"v-dot",style:Q({"background-color":a.getColorOptions(e.color).tag,"margin-inline":"2px"})},null,4),t(b,{icon:a.getPriorityOptions(e.priority).icon,height:"36",color:a.getPriorityOptions(e.priority).color},null,8,["icon","color"]),t(u,null,{default:o(()=>[d(s("{"+a.getGroupOptions(e.groupId).label+"}"),1)]),_:2},1024),f("h2",null,"["+s(e.id)+"] "+s(e.title),1)]),f("p",null," range: "+s((S=e==null?void 0:e.startTs)==null?void 0:S.format("YYYY-MM-DD"))+" - "+s((h=e==null?void 0:e.endTs)==null?void 0:h.format("YYYY-MM-DD"))+" AllDay: "+s(e.allDay),1),f("p",null," Remind: "+s(e.reminder)+" | Repeat: "+s(e.repeat)+" | RepeatEnd: "+s(a.S_TS(e.repeatEndTs)),1),(p(!0),D(O,null,T(e.subTasks,(j,U)=>(p(),D("p",{key:U},s(j.name),1))),128))]}),_:2},1024)]),_:2},1024))),128))]),_:1}),t(c,null,{default:o(()=>[t(_,null,{default:o(()=>[t(u,null,{default:o(()=>n[5]||(n[5]=[d("Save")])),_:1})]),_:1}),(p(!0),D(O,null,T(a.userData.save,(e,m)=>(p(),y(_,{key:m},{default:o(()=>[t(u,null,{default:o(()=>[f("h6",null,s(m),1),f("p",null,s(e),1)]),_:2},1024)]),_:2},1024))),128))]),_:1}),t(B,{"is-open":a.toastData.isOpen,message:a.toastData.text,duration:a.toastData.duration,onDidDismiss:n[1]||(n[1]=()=>{a.toastData.isOpen=!1})},null,8,["is-open","message","duration"])]),_:1})]),_:1})}const ot=A(W,[["render",Z]]);export{ot as default};