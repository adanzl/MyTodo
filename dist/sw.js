if(!self.define){let s,e={};const l=(l,i)=>(l=new URL(l+".js",i).href,e[l]||new Promise((e=>{if("document"in self){const s=document.createElement("script");s.src=l,s.onload=e,document.head.appendChild(s)}else s=l,importScripts(l),e()})).then((()=>{let s=e[l];if(!s)throw new Error(`Module ${l} didn’t register its module`);return s})));self.define=(i,n)=>{const r=s||("document"in self?document.currentScript.src:"")||location.href;if(e[r])return;let u={};const a=s=>l(s,r),t={module:{uri:r},exports:u,require:a};e[r]=Promise.all(i.map((s=>t[s]||a(s)))).then((s=>(n(...s),u)))}}define(["./workbox-5ffe50d4"],(function(s){"use strict";self.skipWaiting(),s.clientsClaim(),s.precacheAndRoute([{url:"assets/_plugin-vue_export-helper-DlAUqK2U.js",revision:null},{url:"assets/_plugin-vue_export-helper-legacy-DgAO6S8O.js",revision:null},{url:"assets/index-Bc0n4A46.js",revision:null},{url:"assets/index-CzX5YBhR.css",revision:null},{url:"assets/index-legacy-Bs3W3sfU.js",revision:null},{url:"assets/index9-CNdxdvkk.js",revision:null},{url:"assets/index9-legacy-BuFeiyHf.js",revision:null},{url:"assets/input-shims-D1FI3CiR.js",revision:null},{url:"assets/input-shims-legacy-CFduKDnE.js",revision:null},{url:"assets/ios.transition-BiMOEAws.js",revision:null},{url:"assets/ios.transition-legacy-DZsayCXa.js",revision:null},{url:"assets/md.transition-BPP76slZ.js",revision:null},{url:"assets/md.transition-legacy-BOxI9Lca.js",revision:null},{url:"assets/NetUtil.vue_vue_type_script_lang-CsB5WIaO.js",revision:null},{url:"assets/NetUtil.vue_vue_type_script_lang-legacy-xgosMxTm.js",revision:null},{url:"assets/polyfills-legacy-C8I4rzdL.js",revision:null},{url:"assets/status-tap-BEF6oY_I.js",revision:null},{url:"assets/status-tap-legacy-LAwz0Uo5.js",revision:null},{url:"assets/swipe-back-Da6VQf3f.js",revision:null},{url:"assets/swipe-back-legacy-wdXI7TS8.js",revision:null},{url:"assets/Tab2Page-C46RAOR_.css",revision:null},{url:"assets/Tab2Page-DuJNU6wl.js",revision:null},{url:"assets/Tab2Page-legacy-D6abbESo.js",revision:null},{url:"assets/Tab3Page-C8d3LdlT.js",revision:null},{url:"assets/Tab3Page-legacy-BmIX6neI.js",revision:null},{url:"assets/TabSchedulePage-CbuK1lCs.css",revision:null},{url:"assets/TabSchedulePage-D8NI6aux.js",revision:null},{url:"assets/TabSchedulePage-legacy-BxwGRgUU.js",revision:null},{url:"assets/web-C01Hh2V_.js",revision:null},{url:"assets/web-legacy-CJVIBXdS.js",revision:null},{url:"index.html",revision:"8e2cf1d7c52e117939b48653a78a3134"},{url:"registerSW.js",revision:"1872c500de691dce40960bb85481de07"},{url:"manifest.webmanifest",revision:"333881096e1621b4a7fa7b0f3a651958"}],{}),s.cleanupOutdatedCaches(),s.registerRoute(new s.NavigationRoute(s.createHandlerBoundToURL("index.html")))}));
