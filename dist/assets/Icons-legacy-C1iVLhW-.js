!function(){function t(t,e,n){return(e=function(t){var e=function(t,e){if("object"!=typeof t||!t)return t;var n=t[Symbol.toPrimitive];if(void 0!==n){var r=n.call(t,e||"default");if("object"!=typeof r)return r;throw new TypeError("@@toPrimitive must return a primitive value.")}return("string"===e?String:Number)(t)}(t,"string");return"symbol"==typeof e?e:e+""}(e))in t?Object.defineProperty(t,e,{value:n,enumerable:!0,configurable:!0,writable:!0}):t[e]=n,t}System.register(["./index-legacy-DpCryoZn.js"],(function(e,n){"use strict";var r,i;return{setters:[t=>{r=t.d,i=t.a2}],execute:function(){e("g",n);e("c","undefined"!=typeof globalThis?globalThis:"undefined"!=typeof window?window:"undefined"!=typeof global?global:"undefined"!=typeof self?self:{});function n(t){return t&&t.__esModule&&Object.prototype.hasOwnProperty.call(t,"default")?t.default:t}var o={exports:{}};!function(t){t.exports=function(){var t=1e3,e=6e4,n=36e5,r="millisecond",i="second",o="minute",s="hour",a="day",c="week",u="month",l="quarter",f="year",d="date",h="Invalid Date",p=/^(\d{4})[-/]?(\d{1,2})?[-/]?(\d{0,2})[Tt\s]*(\d{1,2})?:?(\d{1,2})?:?(\d{1,2})?[.:]?(\d+)?$/,g=/\[([^\]]+)]|Y{1,4}|M{1,4}|D{1,2}|d{1,4}|H{1,2}|h{1,2}|a|A|m{1,2}|s{1,2}|Z{1,2}|SSS/g,m={name:"en",weekdays:"Sunday_Monday_Tuesday_Wednesday_Thursday_Friday_Saturday".split("_"),months:"January_February_March_April_May_June_July_August_September_October_November_December".split("_"),ordinal:function(t){var e=["th","st","nd","rd"],n=t%100;return"["+t+(e[(n-20)%10]||e[n]||e[0])+"]"}},v=function(t,e,n){var r=String(t);return!r||r.length>=e?t:""+Array(e+1-r.length).join(n)+t},y={s:v,z:function(t){var e=-t.utcOffset(),n=Math.abs(e),r=Math.floor(n/60),i=n%60;return(e<=0?"+":"-")+v(r,2,"0")+":"+v(i,2,"0")},m:function t(e,n){if(e.date()<n.date())return-t(n,e);var r=12*(n.year()-e.year())+(n.month()-e.month()),i=e.clone().add(r,u),o=n-i<0,s=e.clone().add(r+(o?-1:1),u);return+(-(r+(n-i)/(o?i-s:s-i))||0)},a:function(t){return t<0?Math.ceil(t)||0:Math.floor(t)},p:function(t){return{M:u,y:f,w:c,d:a,D:d,h:s,m:o,s:i,ms:r,Q:l}[t]||String(t||"").toLowerCase().replace(/s$/,"")},u:function(t){return void 0===t}},b="en",w={};w[b]=m;var x="$isDayjsObject",$=function(t){return t instanceof k||!(!t||!t[x])},M=function t(e,n,r){var i;if(!e)return b;if("string"==typeof e){var o=e.toLowerCase();w[o]&&(i=o),n&&(w[o]=n,i=o);var s=e.split("-");if(!i&&s.length>1)return t(s[0])}else{var a=e.name;w[a]=e,i=a}return!r&&i&&(b=i),i||!r&&b},S=function(t,e){if($(t))return t.clone();var n="object"==typeof e?e:{};return n.date=t,n.args=arguments,new k(n)},O=y;O.l=M,O.i=$,O.w=function(t,e){return S(t,{locale:e.$L,utc:e.$u,x:e.$x,$offset:e.$offset})};var k=function(){function m(t){this.$L=M(t.locale,null,!0),this.parse(t),this.$x=this.$x||t.x||{},this[x]=!0}var v=m.prototype;return v.parse=function(t){this.$d=function(t){var e=t.date,n=t.utc;if(null===e)return new Date(NaN);if(O.u(e))return new Date;if(e instanceof Date)return new Date(e);if("string"==typeof e&&!/Z$/i.test(e)){var r=e.match(p);if(r){var i=r[2]-1||0,o=(r[7]||"0").substring(0,3);return n?new Date(Date.UTC(r[1],i,r[3]||1,r[4]||0,r[5]||0,r[6]||0,o)):new Date(r[1],i,r[3]||1,r[4]||0,r[5]||0,r[6]||0,o)}}return new Date(e)}(t),this.init()},v.init=function(){var t=this.$d;this.$y=t.getFullYear(),this.$M=t.getMonth(),this.$D=t.getDate(),this.$W=t.getDay(),this.$H=t.getHours(),this.$m=t.getMinutes(),this.$s=t.getSeconds(),this.$ms=t.getMilliseconds()},v.$utils=function(){return O},v.isValid=function(){return!(this.$d.toString()===h)},v.isSame=function(t,e){var n=S(t);return this.startOf(e)<=n&&n<=this.endOf(e)},v.isAfter=function(t,e){return S(t)<this.startOf(e)},v.isBefore=function(t,e){return this.endOf(e)<S(t)},v.$g=function(t,e,n){return O.u(t)?this[e]:this.set(n,t)},v.unix=function(){return Math.floor(this.valueOf()/1e3)},v.valueOf=function(){return this.$d.getTime()},v.startOf=function(t,e){var n=this,r=!!O.u(e)||e,l=O.p(t),h=function(t,e){var i=O.w(n.$u?Date.UTC(n.$y,e,t):new Date(n.$y,e,t),n);return r?i:i.endOf(a)},p=function(t,e){return O.w(n.toDate()[t].apply(n.toDate("s"),(r?[0,0,0,0]:[23,59,59,999]).slice(e)),n)},g=this.$W,m=this.$M,v=this.$D,y="set"+(this.$u?"UTC":"");switch(l){case f:return r?h(1,0):h(31,11);case u:return r?h(1,m):h(0,m+1);case c:var b=this.$locale().weekStart||0,w=(g<b?g+7:g)-b;return h(r?v-w:v+(6-w),m);case a:case d:return p(y+"Hours",0);case s:return p(y+"Minutes",1);case o:return p(y+"Seconds",2);case i:return p(y+"Milliseconds",3);default:return this.clone()}},v.endOf=function(t){return this.startOf(t,!1)},v.$set=function(t,e){var n,c=O.p(t),l="set"+(this.$u?"UTC":""),h=(n={},n[a]=l+"Date",n[d]=l+"Date",n[u]=l+"Month",n[f]=l+"FullYear",n[s]=l+"Hours",n[o]=l+"Minutes",n[i]=l+"Seconds",n[r]=l+"Milliseconds",n)[c],p=c===a?this.$D+(e-this.$W):e;if(c===u||c===f){var g=this.clone().set(d,1);g.$d[h](p),g.init(),this.$d=g.set(d,Math.min(this.$D,g.daysInMonth())).$d}else h&&this.$d[h](p);return this.init(),this},v.set=function(t,e){return this.clone().$set(t,e)},v.get=function(t){return this[O.p(t)]()},v.add=function(r,l){var d,h=this;r=Number(r);var p=O.p(l),g=function(t){var e=S(h);return O.w(e.date(e.date()+Math.round(t*r)),h)};if(p===u)return this.set(u,this.$M+r);if(p===f)return this.set(f,this.$y+r);if(p===a)return g(1);if(p===c)return g(7);var m=(d={},d[o]=e,d[s]=n,d[i]=t,d)[p]||1,v=this.$d.getTime()+r*m;return O.w(v,this)},v.subtract=function(t,e){return this.add(-1*t,e)},v.format=function(t){var e=this,n=this.$locale();if(!this.isValid())return n.invalidDate||h;var r=t||"YYYY-MM-DDTHH:mm:ssZ",i=O.z(this),o=this.$H,s=this.$m,a=this.$M,c=n.weekdays,u=n.months,l=n.meridiem,f=function(t,n,i,o){return t&&(t[n]||t(e,r))||i[n].slice(0,o)},d=function(t){return O.s(o%12||12,t,"0")},p=l||function(t,e,n){var r=t<12?"AM":"PM";return n?r.toLowerCase():r};return r.replace(g,(function(t,r){return r||function(t){switch(t){case"YY":return String(e.$y).slice(-2);case"YYYY":return O.s(e.$y,4,"0");case"M":return a+1;case"MM":return O.s(a+1,2,"0");case"MMM":return f(n.monthsShort,a,u,3);case"MMMM":return f(u,a);case"D":return e.$D;case"DD":return O.s(e.$D,2,"0");case"d":return String(e.$W);case"dd":return f(n.weekdaysMin,e.$W,c,2);case"ddd":return f(n.weekdaysShort,e.$W,c,3);case"dddd":return c[e.$W];case"H":return String(o);case"HH":return O.s(o,2,"0");case"h":return d(1);case"hh":return d(2);case"a":return p(o,s,!0);case"A":return p(o,s,!1);case"m":return String(s);case"mm":return O.s(s,2,"0");case"s":return String(e.$s);case"ss":return O.s(e.$s,2,"0");case"SSS":return O.s(e.$ms,3,"0");case"Z":return i}return null}(t)||i.replace(":","")}))},v.utcOffset=function(){return 15*-Math.round(this.$d.getTimezoneOffset()/15)},v.diff=function(r,d,h){var p,g=this,m=O.p(d),v=S(r),y=(v.utcOffset()-this.utcOffset())*e,b=this-v,w=function(){return O.m(g,v)};switch(m){case f:p=w()/12;break;case u:p=w();break;case l:p=w()/3;break;case c:p=(b-y)/6048e5;break;case a:p=(b-y)/864e5;break;case s:p=b/n;break;case o:p=b/e;break;case i:p=b/t;break;default:p=b}return h?p:O.a(p)},v.daysInMonth=function(){return this.endOf(u).$D},v.$locale=function(){return w[this.$L]},v.locale=function(t,e){if(!t)return this.$L;var n=this.clone(),r=M(t,e,!0);return r&&(n.$L=r),n},v.clone=function(){return O.w(this.$d,this)},v.toDate=function(){return new Date(this.valueOf())},v.toJSON=function(){return this.isValid()?this.toISOString():null},v.toISOString=function(){return this.$d.toISOString()},v.toString=function(){return this.$d.toUTCString()},m}(),j=k.prototype;return S.prototype=j,[["$ms",r],["$s",i],["$m",o],["$H",s],["$W",a],["$M",u],["$y",f],["$D",d]].forEach((function(t){j[t[1]]=function(e){return this.$g(e,t[0],t[1])}})),S.extend=function(t,e){return t.$i||(t(e,k,S),t.$i=!0),S},S.locale=M,S.isDayjs=$,S.unix=function(t){return S(1e3*t)},S.en=w[b],S.Ls=w,S.p={},S}()}(o);var s=e("a",o.exports);const a=e("d",n(s)),c=(e("j",[{id:0,label:"None"},{id:1,label:"On the day 9:00"},{id:2,label:"1 day early 9:00"},{id:3,label:"2 day early 9:00"},{id:4,label:"3 day early 9:00"},{id:5,label:"4 day early 9:00"}]),e("R",[{id:0,label:"无",tag:""},{id:1,label:"每天",tag:"day"},{id:2,label:"每星期",tag:"week"},{id:3,label:"每月",tag:"month"},{id:4,label:"每年",tag:"year"}]),e("C",[{id:0,label:"None",tag:"white"},{id:1,label:"Red",tag:"red"},{id:2,label:"Yellow",tag:"yellow"},{id:3,label:"Blue",tag:"blue"},{id:4,label:"Green",tag:"green"}])),u=(e("f",(t=>{for(const e of c)if(e.id===t)return e;return c[0]})),e("P",[{id:0,icon:"mdi:roman-numeral-1",color:"#1a65eb !important",label:"较低"},{id:1,icon:"mdi:roman-numeral-2",color:"#2dd55b !important",label:"中等"},{id:2,icon:"mdi:roman-numeral-3",color:"#ffc409 !important",label:"较高"},{id:3,icon:"mdi:roman-numeral-4",color:"#cb1a27 !important",label:"核心"}])),l=(e("i",(t=>{for(const e of u)if(e.id===t)return e;return u[0]})),e("G",[{id:0,label:"未分类",color:"white"},{id:1,label:"工作",color:"red"},{id:2,label:"学习",color:"yellow"}])),f=(e("h",(t=>{for(const e of l)if(e.id===t)return e;return l[0]})),e("_",((t,e)=>{const n=t.__vccOpts||t;for(const[r,i]of e)n[r]=i;return n})),/^[a-z0-9]+(-[a-z0-9]+)*$/),d=(t,e,n,r="")=>{const i=t.split(":");if("@"===t.slice(0,1)){if(i.length<2||i.length>3)return null;r=i.shift().slice(1)}if(i.length>3||!i.length)return null;if(i.length>1){const t=i.pop(),n=i.pop(),o={provider:i.length>0?i[0]:r,prefix:n,name:t};return e&&!h(o)?null:o}const o=i[0],s=o.split("-");if(s.length>1){const t={provider:r,prefix:s.shift(),name:s.join("-")};return e&&!h(t)?null:t}if(n&&""===r){const t={provider:r,prefix:"",name:o};return e&&!h(t,n)?null:t}return null},h=(t,e)=>!!t&&!(!(e&&""===t.prefix||t.prefix)||!t.name),p=Object.freeze({left:0,top:0,width:16,height:16}),g=Object.freeze({rotate:0,vFlip:!1,hFlip:!1}),m=Object.freeze({...p,...g}),v=Object.freeze({...m,body:"",hidden:!1});function y(t,e){const n=function(t,e){const n={};!t.hFlip!=!e.hFlip&&(n.hFlip=!0),!t.vFlip!=!e.vFlip&&(n.vFlip=!0);const r=((t.rotate||0)+(e.rotate||0))%4;return r&&(n.rotate=r),n}(t,e);for(const r in v)r in g?r in t&&!(r in n)&&(n[r]=g[r]):r in e?n[r]=e[r]:r in t&&(n[r]=t[r]);return n}function b(t,e,n){const r=t.icons,i=t.aliases||Object.create(null);let o={};function s(t){o=y(r[t]||i[t],o)}return s(e),n.forEach(s),y(t,o)}function w(t,e){const n=[];if("object"!=typeof t||"object"!=typeof t.icons)return n;t.not_found instanceof Array&&t.not_found.forEach((t=>{e(t,null),n.push(t)}));const r=function(t){const e=t.icons,n=t.aliases||Object.create(null),r=Object.create(null);return Object.keys(e).concat(Object.keys(n)).forEach((function t(i){if(e[i])return r[i]=[];if(!(i in r)){r[i]=null;const e=n[i]&&n[i].parent,o=e&&t(e);o&&(r[i]=[e].concat(o))}return r[i]})),r}(t);for(const i in r){const o=r[i];o&&(e(i,b(t,i,o)),n.push(i))}return n}const x={provider:"",aliases:{},not_found:{},...p};function $(t,e){for(const n in e)if(n in t&&typeof t[n]!=typeof e[n])return!1;return!0}function M(t){if("object"!=typeof t||null===t)return null;const e=t;if("string"!=typeof e.prefix||!t.icons||"object"!=typeof t.icons)return null;if(!$(t,x))return null;const n=e.icons;for(const i in n){const t=n[i];if(!i||"string"!=typeof t.body||!$(t,v))return null}const r=e.aliases||Object.create(null);for(const i in r){const t=r[i],e=t.parent;if(!i||"string"!=typeof e||!n[e]&&!r[e]||!$(t,v))return null}return e}const S=Object.create(null);function O(t,e){const n=S[t]||(S[t]=Object.create(null));return n[e]||(n[e]=function(t,e){return{provider:t,prefix:e,icons:Object.create(null),missing:new Set}}(t,e))}function k(t,e){return M(e)?w(e,((e,n)=>{n?t.icons[e]=n:t.missing.add(e)})):[]}let j=!1;function T(t){return"boolean"==typeof t&&(j=t),j}function D(t,e){if("object"!=typeof t)return!1;if("string"!=typeof e&&(e=t.provider||""),j&&!e&&!t.prefix){let e=!1;return M(t)&&(t.prefix="",w(t,((t,n)=>{(function(t,e){const n=d(t,!0,j);if(!n)return!1;const r=O(n.provider,n.prefix);return e?function(t,e,n){try{if("string"==typeof n.body)return t.icons[e]={...n},!0}catch(r){}return!1}(r,n.name,e):(r.missing.add(n.name),!0)})(t,n)&&(e=!0)}))),e}const n=t.prefix;if(!h({provider:e,prefix:n,name:"a"}))return!1;return!!k(O(e,n),t)}const I=Object.freeze({width:null,height:null}),_=Object.freeze({...I,...g}),C=/(-?[0-9.]*[0-9]+[0-9.]*)/g,E=/^-?[0-9.]*[0-9]+[0-9.]*$/g;function L(t,e,n){if(1===e)return t;if(n=n||100,"number"==typeof t)return Math.ceil(t*e*n)/n;if("string"!=typeof t)return t;const r=t.split(C);if(null===r||!r.length)return t;const i=[];let o=r.shift(),s=E.test(o);for(;;){if(s){const t=parseFloat(o);isNaN(t)?i.push(o):i.push(Math.ceil(t*e*n)/n)}else i.push(o);if(o=r.shift(),void 0===o)return i.join("");s=!s}}const F=/\sid="(\S+)"/g,N="IconifyId"+Date.now().toString(16)+(16777216*Math.random()|0).toString(16);let z=0;const H=Object.create(null);function A(t){return H[t]||H[""]}function V(t){let e;if("string"==typeof t.resources)e=[t.resources];else if(e=t.resources,!(e instanceof Array&&e.length))return null;return{resources:e,path:t.path||"/",maxURL:t.maxURL||500,rotate:t.rotate||750,timeout:t.timeout||5e3,random:!0===t.random,index:t.index||0,dataAfterTimeout:!1!==t.dataAfterTimeout}}const Y=Object.create(null),P=["https://api.simplesvg.com","https://api.unisvg.com"],R=[];for(;P.length>0;)1===P.length||Math.random()>.5?R.push(P.shift()):R.push(P.pop());function J(t,e){const n=V(e);return null!==n&&(Y[t]=n,!0)}function U(t){return Y[t]}Y[""]=V({resources:["https://api.iconify.design"].concat(R)});let W=(()=>{let t;try{if(t=fetch,"function"==typeof t)return t}catch(e){}})();const B={prepare:(t,e,n)=>{const r=[],i=function(t,e){const n=U(t);if(!n)return 0;let r;if(n.maxURL){let t=0;n.resources.forEach((e=>{const n=e;t=Math.max(t,n.length)}));const i=e+".json?icons=";r=n.maxURL-t-n.path.length-i.length}else r=0;return r}(t,e),o="icons";let s={type:o,provider:t,prefix:e,icons:[]},a=0;return n.forEach(((n,c)=>{a+=n.length+1,a>=i&&c>0&&(r.push(s),s={type:o,provider:t,prefix:e,icons:[]},a=n.length),s.icons.push(n)})),r.push(s),r},send:(t,e,n)=>{if(!W)return void n("abort",424);let r=function(t){if("string"==typeof t){const e=U(t);if(e)return e.path}return"/"}(e.provider);switch(e.type){case"icons":{const t=e.prefix,n=e.icons.join(",");r+=t+".json?"+new URLSearchParams({icons:n}).toString();break}case"custom":{const t=e.uri;r+="/"===t.slice(0,1)?t.slice(1):t;break}default:return void n("abort",400)}let i=503;W(t+r).then((t=>{const e=t.status;if(200===e)return i=501,t.json();setTimeout((()=>{n(function(t){return 404===t}(e)?"abort":"next",e)}))})).then((t=>{"object"==typeof t&&null!==t?setTimeout((()=>{n("success",t)})):setTimeout((()=>{404===t?n("abort",t):n("next",i)}))})).catch((()=>{n("next",i)}))}};function q(t,e){t.forEach((t=>{const n=t.loaderCallbacks;n&&(t.loaderCallbacks=n.filter((t=>t.id!==e)))}))}let Q=0;var Z={resources:[],index:0,timeout:2e3,rotate:750,random:!1,dataAfterTimeout:!1};function G(t,e,n,r){const i=t.resources.length,o=t.random?Math.floor(Math.random()*i):t.index;let s;if(t.random){let e=t.resources.slice(0);for(s=[];e.length>1;){const t=Math.floor(Math.random()*e.length);s.push(e[t]),e=e.slice(0,t).concat(e.slice(t+1))}s=s.concat(e)}else s=t.resources.slice(o).concat(t.resources.slice(0,o));const a=Date.now();let c,u="pending",l=0,f=null,d=[],h=[];function p(){f&&(clearTimeout(f),f=null)}function g(){"pending"===u&&(u="aborted"),p(),d.forEach((t=>{"pending"===t.status&&(t.status="aborted")})),d=[]}function m(t,e){e&&(h=[]),"function"==typeof t&&h.push(t)}function v(){u="failed",h.forEach((t=>{t(void 0,c)}))}function y(){d.forEach((t=>{"pending"===t.status&&(t.status="aborted")})),d=[]}function b(){if("pending"!==u)return;p();const r=s.shift();if(void 0===r)return d.length?void(f=setTimeout((()=>{p(),"pending"===u&&(y(),v())}),t.timeout)):void v();const i={status:"pending",resource:r,callback:(e,n)=>{!function(e,n,r){const i="success"!==n;switch(d=d.filter((t=>t!==e)),u){case"pending":break;case"failed":if(i||!t.dataAfterTimeout)return;break;default:return}if("abort"===n)return c=r,void v();if(i)return c=r,void(d.length||(s.length?b():v()));if(p(),y(),!t.random){const n=t.resources.indexOf(e.resource);-1!==n&&n!==t.index&&(t.index=n)}u="completed",h.forEach((t=>{t(r)}))}(i,e,n)}};d.push(i),l++,f=setTimeout(b,t.rotate),n(r,e,i.callback)}return"function"==typeof r&&h.push(r),setTimeout(b),function(){return{startTime:a,payload:e,status:u,queriesSent:l,queriesPending:d.length,subscribe:m,abort:g}}}function K(t){const e={...Z,...t};let n=[];function r(){n=n.filter((t=>"pending"===t().status))}return{query:function(t,i,o){const s=G(e,t,i,((t,e)=>{r(),o&&o(t,e)}));return n.push(s),s},find:function(t){return n.find((e=>t(e)))||null},setIndex:t=>{e.index=t},getIndex:()=>e.index,cleanup:r}}function X(){}const tt=Object.create(null);function et(t,e,n){let r,i;if("string"==typeof t){const e=A(t);if(!e)return n(void 0,424),X;i=e.send;const o=function(t){if(!tt[t]){const e=U(t);if(!e)return;const n={config:e,redundancy:K(e)};tt[t]=n}return tt[t]}(t);o&&(r=o.redundancy)}else{const e=V(t);if(e){r=K(e);const n=A(t.resources?t.resources[0]:"");n&&(i=n.send)}}return r&&i?r.query(e,i,n)().abort:(n(void 0,424),X)}const nt="iconify2",rt="iconify",it=rt+"-count",ot=rt+"-version",st=36e5;function at(t,e){try{return t.getItem(e)}catch(n){}}function ct(t,e,n){try{return t.setItem(e,n),!0}catch(r){}}function ut(t,e){try{t.removeItem(e)}catch(n){}}function lt(t,e){return ct(t,it,e.toString())}function ft(t){return parseInt(at(t,it))||0}const dt={local:!0,session:!0},ht={local:new Set,session:new Set};let pt=!1;let gt="undefined"==typeof window?{}:window;function mt(t){const e=t+"Storage";try{if(gt&&gt[e]&&"number"==typeof gt[e].length)return gt[e]}catch(n){}dt[t]=!1}function vt(t,e){const n=mt(t);if(!n)return;const r=at(n,ot);if(r!==nt){if(r){const t=ft(n);for(let e=0;e<t;e++)ut(n,rt+e.toString())}return ct(n,ot,nt),void lt(n,0)}const i=Math.floor(Date.now()/st)-168,o=t=>{const r=rt+t.toString(),o=at(n,r);if("string"==typeof o){try{const n=JSON.parse(o);if("object"==typeof n&&"number"==typeof n.cached&&n.cached>i&&"string"==typeof n.provider&&"object"==typeof n.data&&"string"==typeof n.data.prefix&&e(n,t))return!0}catch(s){}ut(n,r)}};let s=ft(n);for(let a=s-1;a>=0;a--)o(a)||(a===s-1?(s--,lt(n,s)):ht[t].add(a))}function yt(){if(!pt){pt=!0;for(const t in dt)vt(t,(t=>{const e=t.data,n=O(t.provider,e.prefix);if(!k(n,e).length)return!1;const r=e.lastModified||-1;return n.lastModifiedCached=n.lastModifiedCached?Math.min(n.lastModifiedCached,r):r,!0}))}}function bt(t,e){function n(n){let r;if(!dt[n]||!(r=mt(n)))return;const i=ht[n];let o;if(i.size)i.delete(o=Array.from(i).shift());else if(o=ft(r),o>=50||!lt(r,o+1))return;const s={cached:Math.floor(Date.now()/st),provider:t.provider,data:e};return ct(r,rt+o.toString(),JSON.stringify(s))}pt||yt(),e.lastModified&&!function(t,e){const n=t.lastModifiedCached;if(n&&n>=e)return n===e;if(t.lastModifiedCached=e,n)for(const r in dt)vt(r,(n=>{const r=n.data;return n.provider!==t.provider||r.prefix!==t.prefix||r.lastModified===e}));return!0}(t,e.lastModified)||Object.keys(e.icons).length&&(e.not_found&&delete(e=Object.assign({},e)).not_found,n("local")||n("session"))}function wt(){}function xt(t){t.iconsLoaderFlag||(t.iconsLoaderFlag=!0,setTimeout((()=>{t.iconsLoaderFlag=!1,function(t){t.pendingCallbacksFlag||(t.pendingCallbacksFlag=!0,setTimeout((()=>{t.pendingCallbacksFlag=!1;const e=t.loaderCallbacks?t.loaderCallbacks.slice(0):[];if(!e.length)return;let n=!1;const r=t.provider,i=t.prefix;e.forEach((e=>{const o=e.icons,s=o.pending.length;o.pending=o.pending.filter((e=>{if(e.prefix!==i)return!0;const s=e.name;if(t.icons[s])o.loaded.push({provider:r,prefix:i,name:s});else{if(!t.missing.has(s))return n=!0,!0;o.missing.push({provider:r,prefix:i,name:s})}return!1})),o.pending.length!==s&&(n||q([t],e.id),e.callback(o.loaded.slice(0),o.missing.slice(0),o.pending.slice(0),e.abort))}))})))}(t)})))}function $t(t,e,n,r){function i(){const n=t.pendingIcons;e.forEach((e=>{n&&n.delete(e),t.icons[e]||t.missing.add(e)}))}if(n&&"object"==typeof n)try{if(!k(t,n).length)return void i();r&&bt(t,n)}catch(o){console.error(o)}i(),xt(t)}function Mt(t,e){t instanceof Promise?t.then((t=>{e(t)})).catch((()=>{e(null)})):e(t)}function St(t,e){t.iconsToLoad?t.iconsToLoad=t.iconsToLoad.concat(e).sort():t.iconsToLoad=e,t.iconsQueueFlag||(t.iconsQueueFlag=!0,setTimeout((()=>{t.iconsQueueFlag=!1;const{provider:e,prefix:n}=t,r=t.iconsToLoad;if(delete t.iconsToLoad,!r||!r.length)return;const i=t.loadIcon;if(t.loadIcons&&(r.length>1||!i))return void Mt(t.loadIcons(r,n,e),(e=>{$t(t,r,e,!1)}));if(i)return void r.forEach((r=>{Mt(i(r,n,e),(e=>{$t(t,[r],e?{prefix:n,icons:{[r]:e}}:null,!1)}))}));const{valid:o,invalid:s}=function(t){const e=[],n=[];return t.forEach((t=>{(t.match(f)?e:n).push(t)})),{valid:e,invalid:n}}(r);if(s.length&&$t(t,s,null,!1),!o.length)return;const a=n.match(f)?A(e):null;if(!a)return void $t(t,o,null,!1);a.prepare(e,n,o).forEach((n=>{et(e,n,(e=>{$t(t,n.icons,e,!0)}))}))})))}const Ot=(t,e)=>{const n=function(t,e=!0,n=!1){const r=[];return t.forEach((t=>{const i="string"==typeof t?d(t,e,n):t;i&&r.push(i)})),r}(t,!0,T()),r=function(t){const e={loaded:[],missing:[],pending:[]},n=Object.create(null);t.sort(((t,e)=>t.provider!==e.provider?t.provider.localeCompare(e.provider):t.prefix!==e.prefix?t.prefix.localeCompare(e.prefix):t.name.localeCompare(e.name)));let r={provider:"",prefix:"",name:""};return t.forEach((t=>{if(r.name===t.name&&r.prefix===t.prefix&&r.provider===t.provider)return;r=t;const i=t.provider,o=t.prefix,s=t.name,a=n[i]||(n[i]=Object.create(null)),c=a[o]||(a[o]=O(i,o));let u;u=s in c.icons?e.loaded:""===o||c.missing.has(s)?e.missing:e.pending;const l={provider:i,prefix:o,name:s};u.push(l)})),e}(n);if(!r.pending.length){let t=!0;return e&&setTimeout((()=>{t&&e(r.loaded,r.missing,r.pending,wt)})),()=>{t=!1}}const i=Object.create(null),o=[];let s,a;return r.pending.forEach((t=>{const{provider:e,prefix:n}=t;if(n===a&&e===s)return;s=e,a=n,o.push(O(e,n));const r=i[e]||(i[e]=Object.create(null));r[n]||(r[n]=[])})),r.pending.forEach((t=>{const{provider:e,prefix:n,name:r}=t,o=O(e,n),s=o.pendingIcons||(o.pendingIcons=new Set);s.has(r)||(s.add(r),i[e][n].push(r))})),o.forEach((t=>{const e=i[t.provider][t.prefix];e.length&&St(t,e)})),e?function(t,e,n){const r=Q++,i=q.bind(null,n,r);if(!e.pending.length)return i;const o={id:r,icons:e,callback:t,abort:i};return n.forEach((t=>{(t.loaderCallbacks||(t.loaderCallbacks=[])).push(o)})),i}(e,r,o):wt};const kt=/[\s,]+/;function jt(t,e){e.split(kt).forEach((e=>{switch(e.trim()){case"horizontal":t.hFlip=!0;break;case"vertical":t.vFlip=!0}}))}function Tt(t,e=0){const n=t.replace(/^-?[0-9.]*/,"");function r(t){for(;t<0;)t+=4;return t%4}if(""===n){const e=parseInt(t);return isNaN(e)?0:r(e)}if(n!==t){let e=0;switch(n){case"%":e=25;break;case"deg":e=90}if(e){let i=parseFloat(t.slice(0,t.length-n.length));return isNaN(i)?0:(i/=e,i%1==0?r(i):0)}}return e}const Dt={..._,inline:!1},It={xmlns:"http://www.w3.org/2000/svg","xmlns:xlink":"http://www.w3.org/1999/xlink","aria-hidden":!0,role:"img"},_t={display:"inline-block"},Ct={backgroundColor:"currentColor"},Et={backgroundColor:"transparent"},Lt={Image:"var(--svg)",Repeat:"no-repeat",Size:"100% 100%"},Ft={webkitMask:Ct,mask:Ct,background:Et};for(const t in Ft){const e=Ft[t];for(const n in Lt)e[t+n]=Lt[n]}const Nt={};function zt(t){return t+(t.match(/^[-0-9.]+$/)?"px":"")}["horizontal","vertical"].forEach((t=>{const e=t.slice(0,1)+"Flip";Nt[t+"-flip"]=e,Nt[t.slice(0,1)+"-flip"]=e,Nt[t+"Flip"]=e}));const Ht=(t,e)=>{const n=function(t,e){const n={...t};for(const r in e){const t=e[r],i=typeof t;r in I?(null===t||t&&("string"===i||"number"===i))&&(n[r]=t):i===typeof n[r]&&(n[r]="rotate"===r?t%4:t)}return n}(Dt,e),r={...It},o=e.mode||"svg",s={},a=e.style,c="object"!=typeof a||a instanceof Array?{}:a;for(let i in e){const t=e[i];if(void 0!==t)switch(i){case"icon":case"style":case"onLoad":case"mode":case"ssr":break;case"inline":case"hFlip":case"vFlip":n[i]=!0===t||"true"===t||1===t;break;case"flip":"string"==typeof t&&jt(n,t);break;case"color":s.color=t;break;case"rotate":"string"==typeof t?n[i]=Tt(t):"number"==typeof t&&(n[i]=t);break;case"ariaHidden":case"aria-hidden":!0!==t&&"true"!==t&&delete r["aria-hidden"];break;default:{const e=Nt[i];e?!0!==t&&"true"!==t&&1!==t||(n[e]=!0):void 0===Dt[i]&&(r[i]=t)}}}const u=function(t,e){const n={...m,...t},r={..._,...e},i={left:n.left,top:n.top,width:n.width,height:n.height};let o=n.body;[n,r].forEach((t=>{const e=[],n=t.hFlip,r=t.vFlip;let s,a=t.rotate;switch(n?r?a+=2:(e.push("translate("+(i.width+i.left).toString()+" "+(0-i.top).toString()+")"),e.push("scale(-1 1)"),i.top=i.left=0):r&&(e.push("translate("+(0-i.left).toString()+" "+(i.height+i.top).toString()+")"),e.push("scale(1 -1)"),i.top=i.left=0),a<0&&(a-=4*Math.floor(a/4)),a%=4,a){case 1:s=i.height/2+i.top,e.unshift("rotate(90 "+s.toString()+" "+s.toString()+")");break;case 2:e.unshift("rotate(180 "+(i.width/2+i.left).toString()+" "+(i.height/2+i.top).toString()+")");break;case 3:s=i.width/2+i.left,e.unshift("rotate(-90 "+s.toString()+" "+s.toString()+")")}a%2==1&&(i.left!==i.top&&(s=i.left,i.left=i.top,i.top=s),i.width!==i.height&&(s=i.width,i.width=i.height,i.height=s)),e.length&&(o=function(t,e,n){const r=function(t,e="defs"){let n="";const r=t.indexOf("<"+e);for(;r>=0;){const i=t.indexOf(">",r),o=t.indexOf("</"+e);if(-1===i||-1===o)break;const s=t.indexOf(">",o);if(-1===s)break;n+=t.slice(i+1,o).trim(),t=t.slice(0,r).trim()+t.slice(s+1)}return{defs:n,content:t}}(t);return i=r.defs,o=e+r.content+n,i?"<defs>"+i+"</defs>"+o:o;var i,o}(o,'<g transform="'+e.join(" ")+'">',"</g>"))}));const s=r.width,a=r.height,c=i.width,u=i.height;let l,f;null===s?(f=null===a?"1em":"auto"===a?u:a,l=L(f,c/u)):(l="auto"===s?c:s,f=null===a?L(l,u/c):"auto"===a?u:a);const d={},h=(t,e)=>{(t=>"unset"===t||"undefined"===t||"none"===t)(e)||(d[t]=e.toString())};h("width",l),h("height",f);const p=[i.left,i.top,c,u];return d.viewBox=p.join(" "),{attributes:d,viewBox:p,body:o}}(t,n),l=u.attributes;if(n.inline&&(s.verticalAlign="-0.125em"),"svg"===o){r.style={...s,...c},Object.assign(r,l);let t=0,n=e.id;return"string"==typeof n&&(n=n.replace(/-/g,"_")),r.innerHTML=function(t,e=N){const n=[];let r;for(;r=F.exec(t);)n.push(r[1]);if(!n.length)return t;const i="suffix"+(16777216*Math.random()|Date.now()).toString(16);return n.forEach((n=>{const r="function"==typeof e?e(n):e+(z++).toString(),o=n.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");t=t.replace(new RegExp('([#;"])('+o+')([")]|\\.[a-z])',"g"),"$1"+r+i+"$3")})),t=t.replace(new RegExp(i,"g"),"")}(u.body,n?()=>n+"ID"+t++:"iconifyVue"),i("svg",r)}const{body:f,width:d,height:h}=t,p="mask"===o||"bg"!==o&&-1!==f.indexOf("currentColor"),g=function(t,e){let n=-1===t.indexOf("xlink:")?"":' xmlns:xlink="http://www.w3.org/1999/xlink"';for(const r in e)n+=" "+r+'="'+e[r]+'"';return'<svg xmlns="http://www.w3.org/2000/svg"'+n+">"+t+"</svg>"}(f,{...l,width:d+"",height:h+""});var v;return r.style={...s,"--svg":(v=g,'url("'+function(t){return"data:image/svg+xml,"+function(t){return t.replace(/"/g,"'").replace(/%/g,"%25").replace(/#/g,"%23").replace(/</g,"%3C").replace(/>/g,"%3E").replace(/\s+/g," ")}(t)}(v)+'")'),width:zt(l.width),height:zt(l.height),..._t,...p?Ct:Et,...c},i("span",r)};var At;if(T(!0),At=B,H[""]=At,"undefined"!=typeof document&&"undefined"!=typeof window){yt();const t=window;if(void 0!==t.IconifyPreload){const e=t.IconifyPreload,n="Invalid IconifyPreload syntax.";"object"==typeof e&&null!==e&&(e instanceof Array?e:[e]).forEach((t=>{try{("object"!=typeof t||null===t||t instanceof Array||"object"!=typeof t.icons||"string"!=typeof t.prefix||!D(t))&&console.error(n)}catch(e){console.error(n)}}))}if(void 0!==t.IconifyProviders){const e=t.IconifyProviders;if("object"==typeof e&&null!==e)for(let t in e){const n="IconifyProviders["+t+"] is invalid.";try{const r=e[t];if("object"!=typeof r||!r||void 0===r.resources)continue;J(t,r)||console.error(n)}catch(Qt){console.error(n)}}}}const Vt={...m,body:""};e("I",r({inheritAttrs:!1,data:()=>({_name:"",_loadingIcon:null,iconMounted:!1,counter:0}),mounted(){this.iconMounted=!0},unmounted(){this.abortLoading()},methods:{abortLoading(){this._loadingIcon&&(this._loadingIcon.abort(),this._loadingIcon=null)},getIcon(t,e,n){if("object"==typeof t&&null!==t&&"string"==typeof t.body)return this._name="",this.abortLoading(),{data:t};let r;if("string"!=typeof t||null===(r=d(t,!1,!0)))return this.abortLoading(),null;let i=function(t){const e="string"==typeof t?d(t,!0,j):t;if(e){const t=O(e.provider,e.prefix),n=e.name;return t.icons[n]||(t.missing.has(n)?null:void 0)}}(r);if(!i)return this._loadingIcon&&this._loadingIcon.name===t||(this.abortLoading(),this._name="",null!==i&&(this._loadingIcon={name:t,abort:Ot([r],(()=>{this.counter++}))})),null;if(this.abortLoading(),this._name!==t&&(this._name=t,e&&e(t)),n){i=Object.assign({},i);const t=n(i.body,r.name,r.prefix,r.provider);"string"==typeof t&&(i.body=t)}const o=["iconify"];return""!==r.prefix&&o.push("iconify--"+r.prefix),""!==r.provider&&o.push("iconify--"+r.provider),{data:i,classes:o}}},render(){this.counter;const t=this.$attrs,e=this.iconMounted||t.ssr?this.getIcon(t.icon,t.onLoad,t.customise):null;if(!e)return Ht(Vt,t);let n=t;return e.classes&&(n={...t,class:("string"==typeof t.class?t.class+" ":"")+e.classes.join(" ")}),Ht({...m,...e.data},n)}}));class Yt{constructor(){t(this,"id",-1),t(this,"name",""),t(this,"imgIds",[])}static Copy(t){var e;return{id:t.id,name:t.name,imgIds:null===(e=t.imgIds)||void 0===e?void 0:e.concat()}}}e("S",Yt);class Pt{static Copy(t){var e,n,r;const i=JSON.parse(JSON.stringify(t));if(i.startTs=null===(e=t.startTs)||void 0===e?void 0:e.clone(),i.endTs=null===(n=t.endTs)||void 0===n?void 0:n.clone(),i.repeatEndTs=null===(r=t.repeatEndTs)||void 0===r?void 0:r.clone(),i.subtasks=[],t.subtasks)for(const o of t.subtasks)i.subtasks.push(Yt.Copy(o));return i}constructor(){t(this,"id",-1),t(this,"startTs",void 0),t(this,"endTs",void 0),t(this,"allDay",!0),t(this,"reminder",0),t(this,"repeat",0),t(this,"repeatEndTs",void 0),t(this,"title",void 0),t(this,"color",0),t(this,"priority",-1),t(this,"groupId",-1),t(this,"subtasks",[]),this.startTs=a().startOf("day"),this.endTs=a().startOf("day")}}e("b",Pt);class Rt{constructor(){t(this,"state",-1),t(this,"subtasks",{}),t(this,"scheduleOverride",void 0)}static Copy(t){const e=new Rt;return e.state=t.state,e.subtasks=JSON.parse(JSON.stringify(t.subtasks)),e}}e("e",Rt);class Jt{constructor(){t(this,"id",-1),t(this,"name",""),t(this,"schedules",[]),t(this,"save",{})}static Copy(t){const e=new Jt;e.id=t.id,e.name=t.name,e.schedules=[];for(const n of t.schedules)e.schedules.push(Pt.Copy(n));return e.save=JSON.parse(JSON.stringify(t.save)),e}}e("U",Jt);e("l",(t=>void 0===t?"":t.format("YYYY-MM-DD"))),e("p",(t=>{const e=JSON.parse(t);void 0===e.schedules&&(e.schedules=[]);for(let n=0;n<e.schedules.length;n++){const t=e.schedules[n];t.startTs=a(t.startTs),t.endTs=a(t.endTs),t.repeatEndTs=t.repeatEndTs&&a(t.repeatEndTs),void 0===t.subtasks&&(t.subtasks=[])}return e}));const Ut='data:image/svg+xml;utf8,\n  <svg class=\'ionicon\' xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24">\n    <path d="M14 7v2h-1v6h1v2h-4v-2h1V9h-1V7z"/>\n  </svg>\n',Wt='data:image/svg+xml;utf8,\n  <svg class=\'ionicon\' xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24">\n    <path d="M11 7v2h-1v6h1v2H7v-2h1V9H7V7zm6 0v2h-1v6h1v2h-4v-2h1V9h-1V7z"/></svg>\n',Bt='data:image/svg+xml;utf8,\n  <svg class=\'ionicon\' xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24">\n    <path d="M9 7v2H8v6h1v2H5v-2h1V9H5V7zm5 0v2h-1v6h1v2h-4v-2h1V9h-1V7zm5 0v2h-1v6h1v2h-4v-2h1V9h-1V7z"/></svg>\n',qt="data:image/svg+xml;utf8,\n  <svg class='ionicon' xmlns='http://www.w3.org/2000/svg' width=\"1em\" height=\"1em\" viewBox='0 0 24 24'>\n    <path d='m12 7l2 10h2l2-10h-2l-1 5l-1-5zm-1 0v2h-1v6h1v2H7v-2h1V9H7V7z' /></svg>\"\n";e("k",{mdiRomanNums:[Ut,Wt,Bt,qt],mdiRomanNum1:Ut,mdiRomanNum2:Wt,mdiRomanNum3:Bt,mdiRomanNum4:qt})}}}))}();