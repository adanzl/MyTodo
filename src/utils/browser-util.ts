/** UC、夸克等使用 X5/WebKit 内核的浏览器，HTML5 audio 与 range 联动易出异常 */
export function isUCOrQuarkBrowser(): boolean {
  const ua = navigator.userAgent;
  return /UCBrowser|UCWEB|Quark/i.test(ua);
}
