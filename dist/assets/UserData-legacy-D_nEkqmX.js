!function(){function t(t,s,e){return(s=function(t){var s=function(t,s){if("object"!=typeof t||!t)return t;var e=t[Symbol.toPrimitive];if(void 0!==e){var a=e.call(t,s||"default");if("object"!=typeof a)return a;throw new TypeError("@@toPrimitive must return a primitive value.")}return("string"===s?String:Number)(t)}(t,"string");return"symbol"==typeof s?s:s+""}(s))in t?Object.defineProperty(t,s,{value:e,enumerable:!0,configurable:!0,writable:!0}):t[s]=e,t}System.register(["./index-legacy-B_eiWsle.js"],(function(s,e){"use strict";var a;return{setters:[t=>{a=t.i}],execute:function(){class e{constructor(){t(this,"id",-1),t(this,"name",""),t(this,"imgIds",[])}static Copy(t){var s;return{id:t.id,name:t.name,imgIds:null===(s=t.imgIds)||void 0===s?void 0:s.concat()}}}s("c",e);class r{static Copy(t){var s,a,r;const i=JSON.parse(JSON.stringify(t));if(i.startTs=null===(s=t.startTs)||void 0===s?void 0:s.clone(),i.endTs=null===(a=t.endTs)||void 0===a?void 0:a.clone(),i.repeatEndTs=null===(r=t.repeatEndTs)||void 0===r?void 0:r.clone(),i.subtasks=[],t.subtasks)for(const n of t.subtasks)i.subtasks.push(e.Copy(n));return i}constructor(){t(this,"id",-1),t(this,"startTs",void 0),t(this,"endTs",void 0),t(this,"allDay",!0),t(this,"reminder",0),t(this,"repeat",0),t(this,"repeatEndTs",void 0),t(this,"title",void 0),t(this,"color",0),t(this,"priority",-1),t(this,"groupId",-1),t(this,"subtasks",[]),this.startTs=a().startOf("day"),this.endTs=a().startOf("day")}}s("d",r);class i{constructor(){t(this,"state",-1),t(this,"subtasks",{}),t(this,"scheduleOverride",void 0)}static Copy(t){const s=new i;return s.state=t.state,t.subtasks&&(s.subtasks=JSON.parse(JSON.stringify(t.subtasks))),s}}s("S",i);class n{constructor(){t(this,"id",-1),t(this,"name",""),t(this,"schedules",[]),t(this,"save",{})}static Copy(t){const s=new n;s.id=t.id,s.name=t.name,s.schedules=[];for(const e of t.schedules)s.schedules.push(r.Copy(e));return s.save=JSON.parse(JSON.stringify(t.save)),s}}s("U",n);class o{constructor(s){t(this,"dt",a().startOf("day")),t(this,"events",[]),t(this,"save",{}),s&&(this.dt=s)}}s("D",o);class d{static createMonthData(t,s,e){const a=t.startOf("month");let r=a.startOf("week");const i=[];do{const t=[];for(let a=0;a<7;a++){var n;const a=d.createDayData(r,s);e&&(null===(n=e.value)||void 0===n?void 0:n.dt.unix())==r.unix()&&(e.value=a),t.push(a),r=r.add(1,"days")}i.push(t)}while(r.month()==t.month());return{vid:t.year(),month:t.month(),year:t.year(),firstDayOfMonth:a,weekArr:i}}static createWeekData(t,s,e){const a=t.startOf("month");let r=t.startOf("week");const i=[],n=[];for(let u=0;u<7;u++){var o;const t=d.createDayData(r,s);e&&(null===(o=e.value)||void 0===o?void 0:o.dt.unix())==r.unix()&&(e.value=t),n.push(t),r=r.add(1,"days")}return i.push(n),{vid:t.year(),month:t.month(),year:t.year(),firstDayOfMonth:a,weekArr:i}}static createDayData(t,s){const e=new o(t),a=t.unix(),i=u(t);let n=s.save[i];n&&0===Object.keys(n).length&&(console.log("delete",i),delete s.save[i],n=void 0);for(const o of s.schedules){var c;const s=r.Copy(o);if(s.startTs&&s.startTs.startOf("day").unix()<=a){if(s.startTs.startOf("day").unix()===a){e.events.push(s);continue}if(s.repeatEndTs&&s.repeatEndTs.unix()<a)continue;1==s.repeat?e.events.push(s):2==s.repeat?t.day()==s.startTs.day()&&e.events.push(s):3==s.repeat?t.date()==s.startTs.date()&&e.events.push(s):4==s.repeat&&t.date()==s.startTs.date()&&t.month()==s.startTs.month()&&e.events.push(s)}const i=null===(c=n)||void 0===c?void 0:c[s.id];if(i&&i.scheduleOverride){const t=i.scheduleOverride;t.title&&(s.title=t.title),t.color&&(s.color=t.color),t.priority&&(s.priority=t.priority),t.groupId&&(s.groupId=t.groupId),t.subtasks&&(s.subtasks=t.subtasks)}}return e.save=n,e.events.sort(((t,s)=>d.CmpScheduleData(t,s,n))),e}static CmpScheduleData(t,s,e){var a,r;const i=e&&(null===(a=e[t.id])||void 0===a?void 0:a.state)||0,n=e&&(null===(r=e[s.id])||void 0===r?void 0:r.state)||0;var o,d;return i===n?(null!==(o=t.id)&&void 0!==o?o:0)-(null!==(d=s.id)&&void 0!==d?d:0):i-n}static updateSchedularData(t,s,e,a,r){const i=u(a);if("all"===r){if(-1===s.id){const e=t.schedules.reduce(((t,s)=>s.id>t?s.id:t),0)+1;s.id=e,t.schedules.push(s)}else{const e=t.schedules.findIndex((t=>t.id===s.id));-1!==e&&(t.schedules[e]=s)}i in t.save||(t.save[i]={});t.save[i][s.id]=e}else{if("cur"!==r)return!1;i in t.save||(t.save[i]={});(t.save[i][s.id]=e).scheduleOverride=s}return!0}static parseScheduleData(t){const s=JSON.parse(t);return s.startTs=a(s.startTs),s.endTs=a(s.endTs),s.repeatEndTs=s.repeatEndTs&&a(s.repeatEndTs),s}static parseUserData(t){const s=JSON.parse(t);void 0===s.schedules&&(s.schedules=[]);for(let e=0;e<s.schedules.length;e++){const t=s.schedules[e];t.startTs=a(t.startTs),t.endTs=a(t.endTs),t.repeatEndTs=t.repeatEndTs&&a(t.repeatEndTs),void 0===t.subtasks&&(t.subtasks=[])}return s}}s("a",d);const u=s("b",(t=>void 0===t?"":t.format("YYYY-MM-DD")))}}}))}();