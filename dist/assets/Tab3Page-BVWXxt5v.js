import{f as I,I as j,p as R,d as g,g as w,c as z,b as F,i as G,U as J}from"./Icons-CzX3WCjC.js";import{d as A,a7 as L,a8 as q,r as h,p as H,a9 as Y,c as y,a as o,g as r,o as p,b as t,i as f,t as s,e as D,f as T,F as O,j as d,v as K}from"./index-D5ScMZaJ.js";import{_ as Q}from"./_plugin-vue_export-helper-DlAUqK2U.js";const W=A({components:{IonRefresher:L,IonRefresherContent:q,S_TS:I,Icon:j},setup(){const a=h(new J),n=h({isOpen:!1,duration:3e3,text:""});return H(()=>{Y(1).then(l=>{a.value=R(l)}).catch(l=>{n.value.isOpen=!0,n.value.text=JSON.stringify(l)})}),{userData:a,toastData:n,dayjs:g,S_TS:I,getColorOptions:w,getPriorityOptions:z,getGroupOptions:F,icons:G}},data(){return{}},methods:{handleRefresh(a){Y(1).then(n=>{this.userData=R(n);for(let l=0;l<this.userData.schedules.length;l++){const i=this.userData.schedules[l];i.startTs=g(i.startTs),i.endTs=g(i.endTs),i.repeatEndTs&&(i.repeatEndTs=g(i.repeatEndTs))}a.target.complete()}).catch(n=>{console.log("handleRefresh",n),this.toastData.isOpen=!0,this.toastData.text=JSON.stringify(n),a.target.complete()})}}}),X={style:{display:"flex","align-items":"center"}};function Z(a,n,l,i,x,tt){const k=r("ion-title"),C=r("ion-toolbar"),E=r("ion-header"),N=r("ion-refresher-content"),M=r("ion-refresher"),u=r("ion-label"),m=r("ion-item"),c=r("ion-list"),b=r("Icon"),B=r("ion-toast"),P=r("ion-content"),$=r("ion-page");return p(),y($,null,{default:o(()=>[t(E,null,{default:o(()=>[t(C,null,{default:o(()=>[t(k,null,{default:o(()=>n[2]||(n[2]=[f("Tab 3")])),_:1})]),_:1})]),_:1}),t(P,null,{default:o(()=>[t(M,{slot:"fixed",onIonRefresh:n[0]||(n[0]=e=>a.handleRefresh(e))},{default:o(()=>[t(N)]),_:1}),t(c,null,{default:o(()=>[t(m,null,{default:o(()=>[t(u,null,{default:o(()=>[f("Id: "+s(a.userData.id),1)]),_:1}),n[3]||(n[3]=f()),t(u,null,{default:o(()=>[f("Name: "+s(a.userData.name),1)]),_:1})]),_:1})]),_:1}),t(c,null,{default:o(()=>[t(m,null,{default:o(()=>[t(u,null,{default:o(()=>n[4]||(n[4]=[f("Schedule")])),_:1}),t(b,{icon:"mdi:roman-numeral-7",size:"large",height:"36",color:"#1a65eb"})]),_:1}),(p(!0),D(O,null,T(a.userData.schedules,(e,_)=>(p(),y(m,{key:_},{default:o(()=>[t(u,null,{default:o(()=>{var S,v;return[d("div",X,[d("span",{class:"v-dot",style:K({"background-color":a.getColorOptions(e.color).tag,"margin-inline":"2px"})},null,4),t(b,{icon:a.getPriorityOptions(e.priority).icon,height:"36",color:a.getPriorityOptions(e.priority).color},null,8,["icon","color"]),t(u,null,{default:o(()=>[f(s("{"+a.getGroupOptions(e.groupId).label+"}"),1)]),_:2},1024),d("h2",null,"["+s(e.id)+"] "+s(e.title),1)]),d("p",null," range: "+s((S=e==null?void 0:e.startTs)==null?void 0:S.format("YYYY-MM-DD"))+" - "+s((v=e==null?void 0:e.endTs)==null?void 0:v.format("YYYY-MM-DD"))+" AllDay: "+s(e.allDay),1),d("p",null," Remind: "+s(e.reminder)+" | Repeat: "+s(e.repeat)+" | RepeatEnd: "+s(a.S_TS(e.repeatEndTs)),1),(p(!0),D(O,null,T(e.subTasks,(U,V)=>(p(),D("p",{key:V},s(U.name),1))),128))]}),_:2},1024)]),_:2},1024))),128))]),_:1}),t(c,null,{default:o(()=>[t(m,null,{default:o(()=>[t(u,null,{default:o(()=>n[5]||(n[5]=[f("Save")])),_:1})]),_:1}),(p(!0),D(O,null,T(a.userData.save,(e,_)=>(p(),y(m,{key:_},{default:o(()=>[t(u,null,{default:o(()=>[d("h6",null,s(_),1),d("p",null,s(e),1)]),_:2},1024)]),_:2},1024))),128))]),_:1}),t(B,{"is-open":a.toastData.isOpen,message:a.toastData.text,duration:a.toastData.duration,onDidDismiss:n[1]||(n[1]=()=>{a.toastData.isOpen=!1})},null,8,["is-open","message","duration"])]),_:1})]),_:1})}const at=Q(W,[["render",Z]]);export{at as default};