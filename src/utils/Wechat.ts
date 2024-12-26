import { __extends } from "tslib";

interface Window {
  wx?: any;
}
declare let window: Window;
class Wechat {
  constructor(_super?: any) {
    __extends(Wechat, _super);
    return (_super !== null && _super?.apply(this, undefined)) || this;
  }
  static env() {
    return Wechat.call("env", {}, undefined);
  }
  static call(method: string, options: any, args: any) {
    if (window.wx && window.wx[method]) {
      return window.wx[method](options, args);
    }
  }
  // Wechat.prototype.isInstalled = function () {
  //   return call("isInstalled", {}, undefined);
  // };
  // Wechat.prototype.share = function (params: any) {
  //   return call("share", {}, params);
  // };
  // Wechat.prototype.auth = function (scope: any, state: any) {
  //   return call("auth", {}, { scope: scope, state: state });
  // };
  // Wechat.prototype.sendPaymentRequest = function (params: any) {
  //   return call("sendPaymentRequest", {}, params);
  // };
  // Wechat.prototype.jumpToWechat = function (url: string) {
  //   return call("jumpToWechat", {}, url);
  // };
  // Wechat.prototype.chooseInvoiceFromWX = function (params: any) {
  //   return call("chooseInvoiceFromWX", {}, params);
  // };
  // Wechat.prototype.openMiniProgram = function (params: any) {
  //   return call("openMiniProgram", {}, params);
  // };
}
export { Wechat };
