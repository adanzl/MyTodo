import{d as S,r as R,p as W,aj as x,o as F,c as U,a,b as o,u as g,i as y,j as D,e as z,f as K,F as q,ak as E,g as m,al as O,a6 as G,t as J,a5 as Q,a4 as T,am as X,ah as Y,an as Z,ao as $,ap as ee}from"./index-DvZ-MHEE.js";const te=["width","height"],ne=["src"],le=S({__name:"Tab2Page",setup(ae){const u=R(),v=R(400),h=R(300),b=R([]),L=(l,e,t)=>{const n=l.width/l.height,s=e/t;let c,i;n>s?(c=e,i=e/n):(i=t,c=t*n);const d=(e-c)/2,r=(t-i)/2;return{dx:d,dy:r,drawWidth:c,drawHeight:i}},A=()=>{const l=document.createElement("input");l.type="file",l.accept="image/*",l.addEventListener("change",async e=>{var s;const t=(s=e.target)==null?void 0:s.files[0];if(!t)return;const n=new FileReader;n.onload=c=>{const i=c.target.result,d=new Image;d.src=i,d.onload=()=>{if(u.value){const r=u.value.getContext("2d");if(r){const{dx:p,dy:w,drawWidth:_,drawHeight:C}=L(d,v.value,h.value);r.clearRect(0,0,v.value,h.value),r.drawImage(d,p,w,_,C),u.value.toBlob(f=>{const k=new FileReader;k.onload=()=>{const P=k.result;E(void 0,P).then(I=>{console.log("setPic",I),x().then(B=>{b.value=B})})},k.readAsDataURL(f)},"image/webp")}}}},n.readAsDataURL(t)}),l.click()};W(()=>{x().then(l=>{b.value=l,console.log("picList",b.value)})});const N=(l,e)=>{const t=new Image;t.src=e.data,t.onload=()=>{if(u.value){const n=u.value.getContext("2d");if(n){const{dx:s,dy:c,drawWidth:i,drawHeight:d}=L(t,v.value,h.value);n.clearRect(0,0,v.value,h.value),n.drawImage(t,s,c,i,d)}}}},V=async(l,e)=>{await(await $.create({header:"Confirm",message:"确认删除这张图片么 ["+e.id+"]",buttons:[{text:"OK",handler:()=>{console.log("btnRemoveClk",e.id),ee(e.id).then(n=>{console.log("delPic",n),x().then(s=>{b.value=s})})}},"Cancel"]})).present()},j=(l,e)=>{const t=document.createElement("input");t.type="file",t.accept="image/*",t.addEventListener("change",async n=>{var i;const s=(i=n.target)==null?void 0:i.files[0];if(!s)return;const c=new FileReader;c.onload=d=>{const r=d.target.result,p=new Image;p.src=r,p.onload=()=>{if(u.value){const w=u.value.getContext("2d");if(w){const{dx:_,dy:C,drawWidth:f,drawHeight:k}=L(p,v.value,h.value);w.clearRect(0,0,v.value,h.value),w.drawImage(p,_,C,f,k),u.value.toBlob(P=>{const I=new FileReader;I.onload=()=>{const B=I.result;E(e.id,B).then(H=>{console.log("setPic",H),x().then(M=>{b.value=M})})},I.readAsDataURL(P)},"image/webp")}}}},c.readAsDataURL(s)}),t.click()};return(l,e)=>{const t=m("ion-title"),n=m("ion-header"),s=m("ion-button"),c=m("ion-buttons"),i=m("ion-label"),d=m("ion-item"),r=m("ion-icon"),p=m("ion-list"),w=m("ion-content");return F(),U(g(Z),null,{default:a(()=>[o(n,null,{default:a(()=>[o(g(O),null,{default:a(()=>[o(t,null,{default:a(()=>e[0]||(e[0]=[y("Tab 2")])),_:1})]),_:1})]),_:1}),o(w,{fullscreen:!0},{default:a(()=>[o(n,{collapse:"condense"},{default:a(()=>[o(g(O),null,{default:a(()=>[o(t,{size:"large"},{default:a(()=>e[1]||(e[1]=[y("Tab 2")])),_:1}),o(c,{slot:"end"},{default:a(()=>[o(s,{onClick:A},{default:a(()=>e[2]||(e[2]=[y("选择图片")])),_:1})]),_:1})]),_:1})]),_:1}),D("canvas",{ref_key:"canvasRef",ref:u,width:v.value,height:h.value},null,8,te),o(p,null,{default:a(()=>[(F(!0),z(q,null,K(b.value,(_,C)=>(F(),U(g(G),{key:C},{default:a(()=>[o(d,{onClick:f=>N(f,_)},{default:a(()=>[o(i,null,{default:a(()=>[y(J(_.id),1)]),_:2},1024),D("img",{src:_.data,style:{height:"60px"}},null,8,ne)]),_:2},1032,["onClick"]),o(g(Q),{side:"end"},{default:a(()=>[o(g(T),{onClick:f=>j(f,_)},{default:a(()=>[o(r,{icon:g(X)},null,8,["icon"])]),_:2},1032,["onClick"]),o(g(T),{color:"danger",onClick:f=>V(f,_)},{default:a(()=>[o(r,{icon:g(Y)},null,8,["icon"])]),_:2},1032,["onClick"])]),_:2},1024)]),_:2},1024))),128))]),_:1})]),_:1})]),_:1})}}});export{le as default};