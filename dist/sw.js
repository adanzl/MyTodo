if(!self.define){let s,e={};const l=(l,i)=>(l=new URL(l+".js",i).href,e[l]||new Promise((e=>{if("document"in self){const s=document.createElement("script");s.src=l,s.onload=e,document.head.appendChild(s)}else s=l,importScripts(l),e()})).then((()=>{let s=e[l];if(!s)throw new Error(`Module ${l} didn’t register its module`);return s})));self.define=(i,n)=>{const r=s||("document"in self?document.currentScript.src:"")||location.href;if(e[r])return;let u={};const t=s=>l(s,r),a={module:{uri:r},exports:u,require:t};e[r]=Promise.all(i.map((s=>a[s]||t(s)))).then((s=>(n(...s),u)))}}define(["./workbox-5ffe50d4"],(function(s){"use strict";self.skipWaiting(),s.clientsClaim(),s.precacheAndRoute([{url:"assets/_plugin-vue_export-helper-DlAUqK2U.js",revision:null},{url:"assets/_plugin-vue_export-helper-legacy-DgAO6S8O.js",revision:null},{url:"assets/ExploreContainer-C46RAOR_.css",revision:null},{url:"assets/ExploreContainer-gVOKhzVn.js",revision:null},{url:"assets/ExploreContainer-legacy-wYeNIb8u.js",revision:null},{url:"assets/index-CDGAtun_.js",revision:null},{url:"assets/index-DgnzCjHd.css",revision:null},{url:"assets/index-legacy-BFYMbORP.js",revision:null},{url:"assets/index9-CLOVEx0X.js",revision:null},{url:"assets/index9-legacy-VqT1ZAva.js",revision:null},{url:"assets/input-shims-BUGELsIX.js",revision:null},{url:"assets/input-shims-legacy-SgnZQdrN.js",revision:null},{url:"assets/ios.transition-B0t2Kdsu.js",revision:null},{url:"assets/ios.transition-legacy-BIxLS-pu.js",revision:null},{url:"assets/md.transition-hydEYkuU.js",revision:null},{url:"assets/md.transition-legacy-Di7msaPJ.js",revision:null},{url:"assets/polyfills-legacy-C8I4rzdL.js",revision:null},{url:"assets/status-tap-86_sBsnm.js",revision:null},{url:"assets/status-tap-legacy-BzC537Ve.js",revision:null},{url:"assets/swipe-back-Db6olV__.js",revision:null},{url:"assets/swipe-back-legacy-CRaiUWeM.js",revision:null},{url:"assets/Tab1Page-B86zoI3U.js",revision:null},{url:"assets/Tab1Page-DiSB_A7r.css",revision:null},{url:"assets/Tab1Page-legacy-CN8XbDtc.js",revision:null},{url:"assets/Tab2Page-CkrtHZZP.js",revision:null},{url:"assets/Tab2Page-legacy-CIyULYPE.js",revision:null},{url:"assets/Tab3Page-legacy-BdW19oWl.js",revision:null},{url:"assets/Tab3Page-nc9v3KXy.js",revision:null},{url:"assets/web-CBycGfLH.js",revision:null},{url:"assets/web-legacy-BRoOh0NZ.js",revision:null},{url:"index.html",revision:"595bb7b0d7c0a92a6c897770f3d4d631"},{url:"registerSW.js",revision:"1872c500de691dce40960bb85481de07"},{url:"manifest.webmanifest",revision:"333881096e1621b4a7fa7b0f3a651958"}],{}),s.cleanupOutdatedCaches(),s.registerRoute(new s.NavigationRoute(s.createHandlerBoundToURL("index.html")))}));
