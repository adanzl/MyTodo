/**
 * 把文本写入系统剪贴板。
 * Clipboard API 只在安全上下文（HTTPS、localhost）里存在；
 * 客户用局域网 IP 或普通 HTTP 打开时 navigator.clipboard 是 undefined，改走 execCommand。
 */
export async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard?.writeText && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "0";
  textarea.style.left = "0";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange(0, text.length);

  let copied = false;
  try {
    copied = document.execCommand("copy");
  } finally {
    textarea.remove();
  }
  if (!copied) {
    throw new Error("浏览器没有允许写入剪贴板");
  }
}
