import { Capacitor } from "@capacitor/core";

/** 仅在原生 iOS/Android 下可用；在浏览器（含 Nexus 等）中不调用插件，避免报错。 */
function isLiveUpdateAvailable(): boolean {
  const platform = Capacitor.getPlatform();
  return platform === "ios" || platform === "android";
}

async function getLiveUpdate() {
  if (!isLiveUpdateAvailable()) return null;
  const { LiveUpdate } = await import("@capawesome/capacitor-live-update");
  return LiveUpdate;
}

export class LiveUpdateMgr {
  // https://github.com/capawesome-team/capacitor-plugins/blob/main/packages/live-update/android/src/main/java/io/capawesome/capacitorjs/plugins/liveupdate/LiveUpdate.java#L682
  // https://capawesome.io/plugins/live-update/#usage
  // https://capawesome.io/blog/announcing-the-capacitor-live-update-plugin/#installation
  // npm config set package-lock false
  public static async getDeviceId(): Promise<void> {
    const LiveUpdate = await getLiveUpdate();
    if (LiveUpdate) await LiveUpdate.getDeviceId();
  }
  public async getVersionCode(): Promise<void> {
    const LiveUpdate = await getLiveUpdate();
    if (LiveUpdate) await LiveUpdate.getVersionCode();
  }

  public async getVersionName(): Promise<void> {
    const LiveUpdate = await getLiveUpdate();
    if (LiveUpdate) await LiveUpdate.getVersionName();
  }

  public async ready(): Promise<void> {
    const LiveUpdate = await getLiveUpdate();
    if (LiveUpdate) await LiveUpdate.ready();
  }

  public async reload(): Promise<void> {
    const LiveUpdate = await getLiveUpdate();
    if (LiveUpdate) await LiveUpdate.reload();
  }

  public async reset(): Promise<void> {
    const LiveUpdate = await getLiveUpdate();
    if (LiveUpdate) await LiveUpdate.reset();
  }
  public async setBundle(bundleId?: string): Promise<void> {
    if (!bundleId) return;
    const LiveUpdate = await getLiveUpdate();
    if (LiveUpdate) await LiveUpdate.setNextBundle({ bundleId });
  }
  public async sync(): Promise<void> {
    const LiveUpdate = await getLiveUpdate();
    if (LiveUpdate) await LiveUpdate.sync();
  }
  public async downloadBundle(bundleId: string, downloadUrl: string): Promise<void> {
    if (!bundleId || !downloadUrl) return;
    const LiveUpdate = await getLiveUpdate();
    if (LiveUpdate) {
      await LiveUpdate.downloadBundle({
        url: downloadUrl,
        bundleId,
      });
    }
  }
}
export default {};
