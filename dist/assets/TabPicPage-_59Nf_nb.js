import{d as V,C as v,D as z,aB as g,r as l,o as k,c as x,a as e,b as n,u as s,h as p,j as w,e as F,f as H,F as M,aa as y,z as W,t as j,y as A,x as P,aC as E,T as K,aD as q,a6 as G}from"./index-CitHbwVn.js";import{l as T,a as J,d as Q}from"./ImgMgr-CX4hNcG1.js";const U=["width","height"],X=["src"],ee=V({__name:"TabPicPage",setup(Y){const h=v(),d=v(400),u=v(300),c=v([]);z(()=>{g().then(i=>{c.value=i,console.log("picList",c.value)})});const B=async()=>{T(void 0,u.value,d.value).then(i=>{console.log("setPic id: ",i),i!==null&&g().then(t=>{c.value=t})})},O=(i,t)=>{const o=new Image;o.src=t.data,o.onload=()=>{if(h.value){const a=h.value.getContext("2d");if(a){const{dx:_,dy:C,drawWidth:m,drawHeight:b}=J(o,d.value,u.value);a.clearRect(0,0,d.value,u.value),a.drawImage(o,_,C,m,b)}}}},R=async(i,t)=>{await(await G.create({header:"Confirm",message:"确认删除这张图片么 ["+t.id+"]",buttons:[{text:"OK",handler:()=>{console.log("btnRemoveClk",t.id),Q(t.id).then(a=>{console.log("delPic",a),g().then(_=>{c.value=_})})}},"Cancel"]})).present()},L=(i,t)=>{T(t.id,u.value,d.value).then(o=>{console.log("setPic id: ",o),o!==null&&g().then(a=>{c.value=a})})};return(i,t)=>{const o=l("ion-title"),a=l("ion-header"),_=l("ion-button"),C=l("ion-buttons"),m=l("ion-item"),b=l("ion-label"),I=l("ion-icon"),D=l("ion-list"),N=l("ion-content");return k(),x(s(q),{class:"main-bg"},{default:e(()=>[n(a,null,{default:e(()=>[n(s(y),null,{default:e(()=>[n(o,null,{default:e(()=>t[0]||(t[0]=[p("Tab Pic")])),_:1})]),_:1})]),_:1}),n(m,{collapse:"condense"},{default:e(()=>[n(s(y),null,{default:e(()=>[n(o,{size:"large"},{default:e(()=>t[1]||(t[1]=[p("Tab 2")])),_:1}),n(C,{slot:"end"},{default:e(()=>[n(_,{onClick:B},{default:e(()=>t[2]||(t[2]=[p("选择图片")])),_:1})]),_:1})]),_:1})]),_:1}),w("canvas",{ref_key:"canvasRef",ref:h,width:d.value,height:u.value},null,8,U),n(N,null,{default:e(()=>[n(D,null,{default:e(()=>[(k(!0),F(M,null,H(c.value,(r,S)=>(k(),x(s(W),{key:S},{default:e(()=>[n(m,{onClick:f=>O(f,r)},{default:e(()=>[n(b,null,{default:e(()=>[p(j(r.id),1)]),_:2},1024),w("img",{src:r.data,style:{height:"60px"}},null,8,X)]),_:2},1032,["onClick"]),n(s(A),{side:"end"},{default:e(()=>[n(s(P),{onClick:f=>L(f,r)},{default:e(()=>[n(I,{icon:s(E)},null,8,["icon"])]),_:2},1032,["onClick"]),n(s(P),{color:"danger",onClick:f=>R(f,r)},{default:e(()=>[n(I,{icon:s(K)},null,8,["icon"])]),_:2},1032,["onClick"])]),_:2},1024)]),_:2},1024))),128))]),_:1})]),_:1})]),_:1})}}});export{ee as default};
