System.register(["./Icons-legacy-Bfx6YagR.js","./index-legacy-CzYkv4eQ.js"],(function(e,t){"use strict";var l,n,a,s,o,r,u,i,d,c,f,p,h,g,_,D,m,y,T,v,O,S,x,I,R,b,Y,k;return{setters:[e=>{l=e.k,n=e.I,a=e.p,s=e.d,o=e.e,r=e.h,u=e.f,i=e.j,d=e.U,c=e._},e=>{f=e.d,p=e.a7,h=e.a8,g=e.r,_=e.p,D=e.a9,m=e.c,y=e.a,T=e.g,v=e.o,O=e.b,S=e.i,x=e.t,I=e.e,R=e.f,b=e.F,Y=e.j,k=e.v}],execute:function(){const t=f({components:{IonRefresher:p,IonRefresherContent:h,S_TS:l,Icon:n},setup(){const e=g(new d),t=g({isOpen:!1,duration:3e3,text:""});return _((()=>{D(1).then((t=>{e.value=a(t)})).catch((e=>{t.value.isOpen=!0,t.value.text=JSON.stringify(e)}))})),{userData:e,toastData:t,dayjs:s,S_TS:l,getColorOptions:o,getPriorityOptions:r,getGroupOptions:u,icons:i}},data:()=>({}),methods:{handleRefresh(e){D(1).then((t=>{this.userData=a(t);for(let e=0;e<this.userData.schedules.length;e++){const t=this.userData.schedules[e];t.startTs=s(t.startTs),t.endTs=s(t.endTs),t.repeatEndTs&&(t.repeatEndTs=s(t.repeatEndTs))}e.target.complete()})).catch((t=>{console.log("handleRefresh",t),this.toastData.isOpen=!0,this.toastData.text=JSON.stringify(t),e.target.complete()}))}}}),j={style:{display:"flex","align-items":"center"}};e("default",c(t,[["render",function(e,t,l,n,a,s){const o=T("ion-title"),r=T("ion-toolbar"),u=T("ion-header"),i=T("ion-refresher-content"),d=T("ion-refresher"),c=T("ion-label"),f=T("ion-item"),p=T("ion-list"),h=T("Icon"),g=T("ion-toast"),_=T("ion-content"),D=T("ion-page");return v(),m(D,null,{default:y((()=>[O(u,null,{default:y((()=>[O(r,null,{default:y((()=>[O(o,null,{default:y((()=>t[2]||(t[2]=[S("Tab 3")]))),_:1})])),_:1})])),_:1}),O(_,null,{default:y((()=>[O(d,{slot:"fixed",onIonRefresh:t[0]||(t[0]=t=>e.handleRefresh(t))},{default:y((()=>[O(i)])),_:1}),O(p,null,{default:y((()=>[O(f,null,{default:y((()=>[O(c,null,{default:y((()=>[S("Id: "+x(e.userData.id),1)])),_:1}),t[3]||(t[3]=S()),O(c,null,{default:y((()=>[S("Name: "+x(e.userData.name),1)])),_:1})])),_:1})])),_:1}),O(p,null,{default:y((()=>[O(f,null,{default:y((()=>[O(c,null,{default:y((()=>t[4]||(t[4]=[S("Schedule")]))),_:1}),O(h,{icon:"mdi:roman-numeral-7",size:"large",height:"36",color:"#1a65eb"})])),_:1}),(v(!0),I(b,null,R(e.userData.schedules,((t,l)=>(v(),m(f,{key:l},{default:y((()=>[O(c,null,{default:y((()=>{var l,n;return[Y("div",j,[Y("span",{class:"v-dot",style:k({"background-color":e.getColorOptions(t.color).tag,"margin-inline":"2px"})},null,4),O(h,{icon:e.getPriorityOptions(t.priority).icon,height:"36",color:e.getPriorityOptions(t.priority).color},null,8,["icon","color"]),O(c,null,{default:y((()=>[S(x("{"+e.getGroupOptions(t.groupId).label+"}"),1)])),_:2},1024),Y("h2",null,"["+x(t.id)+"] "+x(t.title),1)]),Y("p",null," range: "+x(null==t||null===(l=t.startTs)||void 0===l?void 0:l.format("YYYY-MM-DD"))+" - "+x(null==t||null===(n=t.endTs)||void 0===n?void 0:n.format("YYYY-MM-DD"))+" AllDay: "+x(t.allDay),1),Y("p",null," Remind: "+x(t.reminder)+" | Repeat: "+x(t.repeat)+" | RepeatEnd: "+x(e.S_TS(t.repeatEndTs)),1),(v(!0),I(b,null,R(t.subTasks,((e,t)=>(v(),I("p",{key:t},x(e.name),1)))),128))]})),_:2},1024)])),_:2},1024)))),128))])),_:1}),O(p,null,{default:y((()=>[O(f,null,{default:y((()=>[O(c,null,{default:y((()=>t[5]||(t[5]=[S("Save")]))),_:1})])),_:1}),(v(!0),I(b,null,R(e.userData.save,((e,t)=>(v(),m(f,{key:t},{default:y((()=>[O(c,null,{default:y((()=>[Y("h6",null,x(t),1),Y("p",null,x(e),1)])),_:2},1024)])),_:2},1024)))),128))])),_:1}),O(g,{"is-open":e.toastData.isOpen,message:e.toastData.text,duration:e.toastData.duration,onDidDismiss:t[1]||(t[1]=()=>{e.toastData.isOpen=!1})},null,8,["is-open","message","duration"])])),_:1})])),_:1})}]]))}}}));
