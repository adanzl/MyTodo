import { LiveUpdate } from "@capawesome/capacitor-live-update";
export class LiveUpdatePage {
  // https://github.com/capawesome-team/capacitor-plugins/blob/main/packages/live-update/android/src/main/java/io/capawesome/capacitorjs/plugins/liveupdate/LiveUpdate.java#L682
  // https://capawesome.io/plugins/live-update/#usage
  // https://capawesome.io/blog/announcing-the-capacitor-live-update-plugin/#installation
  public static async getDeviceId(): Promise<void> {
    await LiveUpdate.getDeviceId();
  }
  public async getVersionCode(): Promise<void> {
    await LiveUpdate.getVersionCode();
  }

  public async getVersionName(): Promise<void> {
    await LiveUpdate.getVersionName();
  }

  public async ready(): Promise<void> {
    await LiveUpdate.ready();
  }

  public async reload(): Promise<void> {
    await LiveUpdate.reload();
  }

  public async reset(): Promise<void> {
    await LiveUpdate.reset();
  }
  public async setBundle(bundleId?: string): Promise<void> {
    if (!bundleId) {
      return;
    }
    await LiveUpdate.setNextBundle({ bundleId });
  }
  public async sync(): Promise<void> {
    await LiveUpdate.sync();
  }
  public async downloadBundle(bundleId: string, downloadUrl: string): Promise<void> {
    if (!bundleId || !downloadUrl) {
      return;
    }
    await LiveUpdate.downloadBundle({
      url: downloadUrl,
      bundleId,
    });
  }
}
export default {};
