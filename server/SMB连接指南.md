# SMB 共享连接指南

## 快速连接步骤

### 方法 1: 使用资源管理器（最简单）

1. 打开 **文件资源管理器**
2. 在地址栏输入：`\\192.168.50.171`
3. 双击 **MINI_EXT** 共享
4. 输入用户名：`leo` 和密码
5. 勾选"记住我的凭据"
6. 成功后，可以右键 MINI_EXT → **映射网络驱动器** → 选择 **Z:**

### 方法 2: 使用命令行

**以管理员身份运行 PowerShell**，执行：

```powershell
# 1. 修复 Windows SMB 配置（只需执行一次）
Set-SmbClientConfiguration -RequireSecuritySignature $false -Confirm:$false
Set-SmbClientConfiguration -EnableInsecureGuestLogons $true -Confirm:$false
Restart-Service -Name "LanmanWorkstation" -Force

# 2. 挂载共享（开机自动挂载）
net use Z: \\192.168.50.171\MINI_EXT /user:leo /persistent:yes
# 输入密码
# 注意：/persistent:yes 表示开机自动挂载

# 3. 验证
explorer Z:\
```

## 服务器信息

- **服务器 IP**: 192.168.50.171
- **共享名**: MINI_EXT
- **路径**: /mnt/ext
- **用户名**: leo

## 注意事项

1. **首次连接需要修复 SMB 配置**（方法 2 的第 1 步）
2. **需要管理员权限**才能修改 SMB 配置
3. **SMB 完美支持 UTF-8 和中文**，比 NFS 更适合 Windows

## 开机自动挂载

使用 `/persistent:yes` 参数挂载后，下次开机会自动挂载：

```cmd
net use Z: \\192.168.50.171\MINI_EXT /user:leo /persistent:yes
```

**注意**：首次挂载需要输入密码，Windows 会保存凭据，之后开机自动挂载时无需再次输入密码。

## 卸载

```cmd
# 临时卸载（下次开机仍会自动挂载）
net use Z: /delete

# 永久删除（取消自动挂载）
net use Z: /delete /persistent:no
```


